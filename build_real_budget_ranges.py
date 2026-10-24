"""
Build the anonymous real-budget values file (change use-real-budget-ranges, design D2, D3, D4, D6).

    python build_real_budget_ranges.py --store <final_v4 folder or budget_scan_v2.sqlite> --out <data dir>
                                       [--cpi <Ref_CPI_VN.csv>] [--map <folder in Savills-local>]
                                       [--nfa-table <nfa_per_file.csv in Savills-local>] [--master <master list csv>]

Reads (read-only): the scan store's file_profile, dim_file, project_map, fact_line and vat_cut_period; the per-file
NFA table (when given) and the residential master list.
Writes:
  <out>/Ref_RealBudgetValues.csv          one row per anonymous project and code (no name, no file name)
  <out>/README.txt                        rules, build date, counts; files excluded or merged BY STORE ID only
  <map>/real_budget_ranges_map.csv        project_id -> file_id, project name, file name (stays in Savills-local)
  <map>/real_budget_ranges_names.txt      every project and file name of the store, for verification's name scan
`--out` has no default: the data folder is live data, so it is always named on the command line.

Store rules (approved 2026-10-12, D3; grouping and NFA approved 2026-10-18):
  - Excel sources only (no scanned PDF, no converted xlsb), no content duplicate;
  - the file's main operating-fund sheet, only when its leaf lines tie to the total rows (primary_confidence high);
  - fee-paying NFA = file_profile.nfa_total; when the store summed the product rows (nfa_how = sum_of_types) it
    also summed the group rows, so the "I." products group is used instead (it leaves out the II. parking group,
    as Dim_Property_v2_verified does); a "Management Fee" pseudo-product is taken out as in the service-level build;
  - one project per normalised name, but two files of the same name whose NFA differs by more than 5% are two
    projects (a stale name cell), flagged, and carry no name_key so that only NFA matches them at run time; two files with the same NFA to the m2 are one project; an unnamed file
    is its own project, flagged;
  - per project the latest budget year, tie: the later file date;
  - value = the code's amount excluding VAT per month (the store divides by the period's real months and takes
    VAT out at the sheet's factor) / fee-paying NFA; a sum of 0 or blank is written as status zero_or_blank with
    no value;
  - CPI factor to 2027 from Ref_CPI_VN.csv (design D4);
  - rate codes (real_budget_ranges.RATE_CODES, today RM.AP; change price-fee-and-parking-from-portfolio): the value
    is (RM.AP + RM.0A, the developer's share on units not yet handed over) per month / file_profile.nfa_apartment,
    written with basis = apartment_nfa; a file with the line above 0 but no apartment NFA is left out for that code.

Checked NFA (change widen-real-budget-store, approved 2026-10-22, design D4):
  - first the per-file table (`--nfa-table`): a row the user approved (approved_on filled) gives the fee-paying NFA,
    and the apartment NFA when known, as written in the file outside its info sheet; it wins over the profile's NFA
    too (a reviewed correction);
  - else the master list (`--master`): the project name equal after removing accents, case, spaces and punctuation,
    one match only; the master list has no apartment NFA, so such a file is left out for RM.AP;
  - either NFA is used only when the implied fee rate (all RM.* lines per month excluding VAT on the main sheet /
    NFA) is within 15% of the reference rate: the table's ref_rate, else the master list's rate; a rate including
    VAT is taken out of VAT at the budget year's rate (8% when most months of the year fall in a cut period of the
    store's vat_cut_period table, else 10%). A file with no fee revenue passes only through an approved table row.
    When the fee revenue mixes products at different rates (apartments, shops, nursery, villas, parking), the table's
    ref_rate is the area-weighted rate of the rates written in the file (approved 2026-10-22), not the apartment rate.

The script refuses to write when any output cell or the README would contain a store project or file name.
"""
import argparse
import csv
import datetime
import os
import re
import sqlite3
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import real_budget_ranges as rbr  # noqa: E402

STORE_FILE = 'budget_scan_v2.sqlite'
MAP_FILE = 'real_budget_ranges_map.csv'
NAMES_FILE = 'real_budget_ranges_names.txt'
VALUES_FILE = 'Ref_RealBudgetValues.csv'
README_FILE = 'README.txt'
SAME_NAME_NFA_GAP = 0.05

FLAG_UNNAMED = 'file không có tên dự án'
FLAG_NFA_GROUP_I = 'NFA lấy theo dòng I. (kho cộng cả dòng nhóm)'
FLAG_STALE_NAME = 'tên trùng dự án khác nhưng NFA lệch trên 5%, tính riêng'
FLAG_PARTIAL = 'kỳ {m:g} tháng'
FLAG_NFA_TABLE = 'NFA lấy theo bảng NFA từng file (đã duyệt)'
FLAG_NFA_MASTER = 'NFA lấy theo master list'
MASTER_CSV = os.path.join(rbr.BUDGET_AGENT, 'data', 'master_list_verified', 'Dim_Property_Residential.csv')
FEE_CHECK_BAND = 0.15
VAT_STANDARD = 0.10


class NameWouldLeak(RuntimeError):
    """A store name was about to be written into the anonymous output."""


def _norm(s):
    return ''.join(ch for ch in unicodedata.normalize('NFC', str(s or '')).casefold() if ch.isalnum())


def _f(v):
    try:
        return float(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def fee_nfa(nfa_total, nfa_how, nfa_types):
    """(fee-paying NFA, flag). See the module docstring."""
    total = _f(nfa_total)
    if total is None:
        return None, ''
    if (nfa_how or '') == 'sum_of_types' and nfa_types:
        m = re.match(r'\s*I\.\s*=\s*([0-9.]+)', nfa_types)
        if m and float(m.group(1)) > 0:
            return float(m.group(1)), FLAG_NFA_GROUP_I
        m = re.search(r'Management Fee=([0-9.]+)', nfa_types)
        if m:
            total -= float(m.group(1))
    return (total if total > 0 else None), ''


def store_path(arg):
    return os.path.join(arg, STORE_FILE) if os.path.isdir(arg) else arg


RM0A = 'RM.0A'                       # the developer's share, added to RM.AP for the full apartment fee (design D2)
STORE_CODES = rbr.ALL_CODES + (RM0A,)


def read_store(path, codes=STORE_CODES):
    """(files, names, lines): candidate file rows, every name in the store, {(file_id, code): [amounts]} on each
    file's primary sheet."""
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        con.row_factory = sqlite3.Row
        files = [dict(r) for r in con.execute(
            'select f.file_id, f.file_name, f.source_type, f.content_dup_of, f.primary_sheet, f.primary_confidence, '
            'f.budget_year_v2, f.months_in_period, f.nfa_total, f.nfa_how, f.nfa_types, f.nfa_apartment, '
            'd.modified, d.rel_path, d.source_type as dim_source_type, d.content_dup_of as dim_dup, p.project_name '
            'from file_profile f left join dim_file d using(file_id) left join project_map p using(file_id)')]
        names = set()
        for r in con.execute('select project_name, file_name from project_map'):
            names.update(x for x in r if x)
        for r in con.execute('select file_name, rel_path from dim_file'):
            names.update(x for x in r if x)
            if r['rel_path']:
                names.add(os.path.basename(r['rel_path']))
        for r in con.execute('select file_name from file_profile'):
            if r[0]:
                names.add(r[0])
        q = ('select l.file_id, l.code, l.amount_excl_vat_per_month from fact_line l join file_profile f '
             'on f.file_id = l.file_id and f.primary_sheet = l.sheet where l.code in (%s)' % ','.join('?' * len(codes)))
        lines = {}
        for r in con.execute(q, list(codes)):
            lines.setdefault((r['file_id'], r['code']), []).append(r['amount_excl_vat_per_month'])
        # management-fee revenue per month excluding VAT on the main sheet (every RM.* leaf), for the NFA fee check
        rm = {r[0]: r[1] or 0.0 for r in con.execute(
            "select l.file_id, sum(l.amount_excl_vat_per_month) from fact_line l join file_profile f "
            "on f.file_id = l.file_id and f.primary_sheet = l.sheet where l.code like 'RM.%' group by l.file_id")}
        try:
            cuts = [(str(r[0]), str(r[1]), float(r[2])) for r in con.execute(
                'select "from", "to", rate from vat_cut_period')]
        except sqlite3.OperationalError:
            cuts = []
    finally:
        con.close()
    for f in files:
        f['rm_month'] = rm.get(f['file_id'], 0.0)
    return files, names, lines, cuts


def vat_rate_of_year(year, cuts):
    """The VAT rate of a budget year: the cut rate when most of its months fall in a cut period, else 10%."""
    months = [f'{int(year)}-{m:02d}' for m in range(1, 13)]
    for rate in sorted({c[2] for c in cuts}):
        if sum(1 for m in months if any(a <= m <= b and r == rate for a, b, r in cuts)) > 6:
            return rate
    return VAT_STANDARD


def load_nfa_table(path):
    """{file_id: row} of the per-file NFA table; only rows the user approved (approved_on filled)."""
    if not path:
        return {}
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return {r['file_id'].strip(): r for r in csv.DictReader(fh)
                if (r.get('file_id') or '').strip() and (r.get('approved_on') or '').strip()}


def load_master(path):
    """{normalised name: [(NFA, fee rate, VAT label)]} of the residential master list."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            k = _norm(r.get('Name'))
            if k:
                out.setdefault(k, []).append((_f(r.get('NFA_m2')), _f(r.get('MgmtFeeRate_Primary')),
                                              (r.get('MgmtFeeVAT') or '').strip()))
    return out


def checked_nfa(f, table, master, cuts):
    """(nfa, nfa_apartment, flag, None) or (None, None, '', reason) for a file whose profile has no fee-paying NFA.
    The log line never carries the project name (only store id, figures and the source)."""
    fid, year = f['file_id'], _f(f.get('budget_year_v2'))
    vat = vat_rate_of_year(year, cuts) if year else VAT_STANDARD
    rm = f.get('rm_month') or 0.0

    def excl(rate, label):
        return rate / (1 + vat) if rate and 'incl' in (label or '').lower() else rate

    hits = master.get(_norm(f.get('project_name'))) if _norm(f.get('project_name')) else None
    row = table.get(fid)
    if row:
        nfa, apt = _f(row.get('nfa_fee')), _f(row.get('nfa_apartment'))
        if not nfa:
            return None, None, '', 'per-file table row without nfa_fee'
        if rm <= 0:                                     # no fee revenue: the user's approval in the table is the check
            return nfa, apt, FLAG_NFA_TABLE, None
        ref = excl(_f(row.get('ref_rate')), row.get('ref_rate_vat'))
        if not ref and hits and len(hits) == 1:         # no rate written in the file: the master list's rate
            ref = excl(hits[0][1], hits[0][2])
        source, why = 'table', 'NFA bảng lệch đơn giá'
    else:
        if not hits:
            return None, None, '', 'no fee-paying NFA, no master-list match'
        if len(hits) > 1:
            return None, None, '', 'no fee-paying NFA, trùng tên master (several master-list rows)'
        nfa, rate, label = hits[0]
        apt = None
        if not nfa:
            return None, None, '', 'no fee-paying NFA, master list has none'
        if rm <= 0:
            return None, None, '', 'no fee-paying NFA, no fee revenue to check the master NFA'
        ref = excl(rate, label)
        source, why = 'master list', 'NFA master lệch đơn giá'
    if not ref:
        return None, None, '', f'NFA from {source} but no reference rate'
    implied = rm / nfa
    gap = implied / ref - 1
    note = f'NFA {nfa:,.1f} from {source}, implied {implied:,.0f} vs reference {ref:,.0f} ({gap:+.1%})'
    if abs(gap) > FEE_CHECK_BAND:
        return None, None, '', f'{why}: {note}'
    return nfa, apt, (FLAG_NFA_TABLE if source == 'table' else FLAG_NFA_MASTER), note


def candidates(files, log, table=None, master=None, cuts=(), nfa_log=None):
    out = []
    for f in sorted(files, key=lambda f: f['file_id']):
        fid = f['file_id']
        src = f.get('source_type') or f.get('dim_source_type') or 'excel'
        if src != 'excel':
            log.append(f'{fid}: {src} source, left out')
            continue
        if f.get('content_dup_of') or f.get('dim_dup'):
            log.append(f'{fid}: content duplicate of {f.get("content_dup_of") or f.get("dim_dup")}, left out')
            continue
        if not f.get('primary_sheet'):
            log.append(f'{fid}: no main operating-fund sheet, left out')
            continue
        if (f.get('primary_confidence') or '') != 'high':
            log.append(f'{fid}: main sheet does not tie to its total rows ({f.get("primary_confidence") or "none"}), left out')
            continue
        nfa, nfa_flag = fee_nfa(f.get('nfa_total'), f.get('nfa_how'), f.get('nfa_types'))
        if not nfa or fid in (table or {}):          # an approved table row is a reviewed correction: it wins
            nfa, apt, nfa_flag, note = checked_nfa(f, table or {}, master or {}, cuts)
            if not nfa:
                log.append(f'{fid}: {note}, left out')
                continue
            if apt:
                f = dict(f, nfa_apartment=apt)
            if nfa_log is not None:
                nfa_log.append(f'{fid}: {note or "NFA " + format(nfa, ",.1f") + " from table, no fee revenue, approved"}')
        if not _f(f.get('months_in_period')) or not _f(f.get('budget_year_v2')):
            log.append(f'{fid}: no budget period or year, left out')
            continue
        flags = [nfa_flag] if nfa_flag else []
        if not (f.get('project_name') or '').strip():
            flags.append(FLAG_UNNAMED)
        if _f(f['months_in_period']) != 12:
            flags.append(FLAG_PARTIAL.format(m=_f(f['months_in_period'])))
        out.append(dict(f, nfa=nfa, flags=flags))
    return out


def group_projects(cands, log):
    """Union by name (NFA within 5%) and by identical NFA to the m2; keep the latest budget year, then file date."""
    parent = {c['file_id']: c['file_id'] for c in cands}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_name = {}
    for c in cands:
        k = _norm(c.get('project_name'))
        if k:
            by_name.setdefault(k, []).append(c)
    for members in by_name.values():
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if abs(a['nfa'] - b['nfa']) <= SAME_NAME_NFA_GAP * max(a['nfa'], b['nfa']):
                    parent[find(b['file_id'])] = find(a['file_id'])
                else:
                    for x in (a, b):
                        if FLAG_STALE_NAME not in x['flags']:
                            x['flags'].append(FLAG_STALE_NAME)
                    log.append(f'{a["file_id"]} / {b["file_id"]}: same name, NFA differs by more than 5%, two projects')
    by_nfa = {}
    for c in cands:
        by_nfa.setdefault(round(c['nfa']), []).append(c)
    for members in by_nfa.values():
        for b in members[1:]:
            parent[find(b['file_id'])] = find(members[0]['file_id'])
    groups = {}
    for c in cands:
        groups.setdefault(find(c['file_id']), []).append(c)
    chosen = []
    for members in groups.values():
        members.sort(key=lambda c: (_f(c['budget_year_v2']) or 0, c.get('modified') or ''), reverse=True)
        keep = members[0]
        for m in members[1:]:
            log.append(f'{m["file_id"]}: same project as {keep["file_id"]}, older budget year or file date, left out')
        chosen.append(keep)
    return chosen


def build_rows(chosen, lines, cpi, codes=rbr.ALL_CODES, log=None):
    """(rows, project_ids): rows in VALUE_COLUMNS order; project_ids maps file_id -> P001...
    A rate code (rbr.RATE_CODES, today RM.AP) is the full apartment fee (RM.AP + RM.0A) per m2 of APARTMENT NFA
    (design D1, D2); a file with the line above 0 but no apartment NFA gets no row and is listed in `log`."""
    chosen = sorted(chosen, key=lambda c: c['file_id'])
    pids = {c['file_id']: f'P{i:03d}' for i, c in enumerate(chosen, start=1)}
    rows = []
    for c in chosen:
        year = int(_f(c['budget_year_v2']))
        factor = rbr.cpi_factor(year, cpi)
        for code in codes:
            amounts = lines.get((c['file_id'], code))
            if amounts is None:
                continue                      # the sheet has no line for this code
            total = sum(a for a in amounts if a)
            is_rate = code in rbr.RATE_CODES
            denominator = c['nfa']
            if is_rate:
                total += sum(a for a in (lines.get((c['file_id'], RM0A)) or []) if a)
                denominator = _f(c.get('nfa_apartment'))
                if total > 0 and not denominator:
                    if log is not None:
                        log.append(f'{c["file_id"]}: {code} above 0 but no apartment NFA, left out for {code}')
                    continue
            # a stale name (same name, NFA more than 5% apart) is matched by NFA only at run time
            key = '' if FLAG_STALE_NAME in c['flags'] else rbr.name_key(c.get('project_name'))
            row = {'project_id': pids[c['file_id']], 'name_key': key,
                   'nfa_m2': round(c['nfa'], -1), 'budget_year': year, 'code': code,
                   'cpi_factor': round(factor, 6), 'flag': '; '.join(c['flags']),
                   'basis': rbr.BASIS_APARTMENT_NFA if is_rate else rbr.BASIS_FEE_NFA}
            if total > 0:
                v = total / denominator
                row.update(status=rbr.STATUS_VALUE, value_m2_month=round(v, 4), value_m2_month_2027=round(v * factor, 4))
            else:
                row.update(status=rbr.STATUS_ZERO, value_m2_month='', value_m2_month_2027='')
            rows.append(row)
    return rows, pids


def name_scan(rows, texts, names):
    """Raise NameWouldLeak if any output cell or text contains a store project or file name (4+ characters,
    normalised). Runs before any file is opened for writing."""
    tokens = {_norm(n) for n in names if len(_norm(n)) >= 4}
    cells = [(f'{r["project_id"]}.{col}', r.get(col, '')) for r in rows for col in rbr.VALUE_COLUMNS]
    cells += [(label, t) for label, t in texts]
    for label, cell in cells:
        c = _norm(cell)
        if not c:
            continue
        for t in tokens:
            if t in c:
                raise NameWouldLeak(f'{label} would carry a store name; nothing written')


def summarise(rows, chosen, cpi, snapshot, log, codes=rbr.ALL_CODES, nfa_log=()):
    lines = [f'Ref_RealBudgetValues.csv, built {datetime.datetime.now():%Y-%m-%d %H:%M}; {snapshot}',
             'Build: build_real_budget_ranges.py (change use-real-budget-ranges). Rules: see the script docstring.',
             'Unit: VND per m2 of fee-paying NFA per month, excluding VAT; value_m2_month at budget-year prices,',
             'value_m2_month_2027 = value_m2_month x cpi_factor (Ref_CPI_VN.csv). Rebuild after a CPI change.',
             f'basis = {rbr.BASIS_APARTMENT_NFA} ({", ".join(rbr.RATE_CODES)}): a unit rate per m2 of APARTMENT NFA, '
             f'= (RM.AP + RM.0A, the developer share on units not yet handed over) / apartment NFA, excluding VAT;',
             f'basis = {rbr.BASIS_FEE_NFA} for every other code. A file with RM.AP above 0 but no apartment NFA is left '
             'out for RM.AP (listed below).',
             f'projects: {len(chosen)}',
             'budget years: ' + ', '.join(f'{y} {n}' for y, n in sorted(_count(int(_f(c["budget_year_v2"])) for c in chosen).items())),
             'CPI factors: ' + ', '.join(f'{y} {rbr.cpi_factor(y, cpi):.6f}' for y in sorted({int(_f(c["budget_year_v2"])) for c in chosen})),
             'flags: ' + ', '.join(f'{k} {v}' for k, v in sorted(_count(f for c in chosen for f in c['flags']).items())),
             '', 'Per code: projects with a value / with 0 or blank / without the line']
    for code in codes:
        nv = sum(1 for r in rows if r['code'] == code and r['status'] == rbr.STATUS_VALUE)
        nz = sum(1 for r in rows if r['code'] == code and r['status'] == rbr.STATUS_ZERO)
        lines.append(f'  {code}: {nv} / {nz} / {len(chosen) - nv - nz}')
    nfa_src = _count(FLAG_NFA_TABLE if FLAG_NFA_TABLE in c['flags'] else
                     (FLAG_NFA_MASTER if FLAG_NFA_MASTER in c['flags'] else 'file profile') for c in chosen)
    lines += ['', 'NFA source of the projects kept: ' + ', '.join(f'{k} {v}' for k, v in sorted(nfa_src.items())),
              'Files that took a checked NFA from the per-file table or the master list (store ids only; fee check within '
              f'{FEE_CHECK_BAND:.0%}):'] + ['  ' + x for x in nfa_log]
    lines += ['', 'Files excluded or merged (store ids only):'] + ['  ' + x for x in log]
    return '\n'.join(lines) + '\n'


def _count(items):
    out = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return out


def write_outputs(rows, chosen, pids, names, readme, out_dir, map_dir):
    name_scan(rows, [(f'README line {i}', t) for i, t in enumerate(readme.splitlines(), start=1)], names)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(map_dir, exist_ok=True)
    with open(os.path.join(out_dir, VALUES_FILE), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=rbr.VALUE_COLUMNS, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(os.path.join(out_dir, README_FILE), 'w', encoding='utf-8') as fh:
        fh.write(readme)
    with open(os.path.join(map_dir, MAP_FILE), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['project_id', 'file_id', 'project_name', 'file_name', 'nfa_fee_m2', 'budget_year'])
        for c in sorted(chosen, key=lambda c: pids[c['file_id']]):
            w.writerow([pids[c['file_id']], c['file_id'], c.get('project_name') or '', c.get('file_name') or '',
                        round(c['nfa'], 1), int(_f(c['budget_year_v2']))])
    with open(os.path.join(map_dir, NAMES_FILE), 'w', encoding='utf-8') as fh:
        for n in sorted(names):
            fh.write(n + '\n')


def build(store, out_dir, cpi_path=None, map_dir=None, nfa_table=None, master_path=MASTER_CSV):
    path = store_path(store)
    map_dir = map_dir or os.path.dirname(os.path.abspath(path))
    if os.path.abspath(map_dir).startswith(os.path.abspath(os.path.join(rbr.BUDGET_AGENT, ''))):
        raise ValueError('the name map must stay outside Budget_Agent (Savills-local)')
    if nfa_table and os.path.abspath(nfa_table).startswith(os.path.abspath(os.path.join(rbr.BUDGET_AGENT, ''))):
        raise ValueError('the per-file NFA table must stay outside Budget_Agent (Savills-local)')
    cpi = rbr.load_cpi(cpi_path)
    files, names, lines, cuts = read_store(path)
    log, nfa_log = [], []
    cands = candidates(files, log, load_nfa_table(nfa_table), load_master(master_path), cuts, nfa_log)
    chosen = group_projects(cands, log)
    rows, pids = build_rows(chosen, lines, cpi, log=log)
    snapshot = f'store {datetime.datetime.fromtimestamp(os.path.getmtime(path)):%Y-%m-%d}, {len(files)} files'
    readme = summarise(rows, chosen, cpi, snapshot, log, nfa_log=nfa_log)
    write_outputs(rows, chosen, pids, names, readme, out_dir, map_dir)
    return rows, readme


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build the anonymous real-budget values file.')
    ap.add_argument('--store', required=True, help='the scan store folder (final_v4) or its sqlite file')
    ap.add_argument('--out', required=True, help='output folder, e.g. Budget_Agent/data/real_budget_ranges')
    ap.add_argument('--cpi', default=rbr.CPI_CSV)
    ap.add_argument('--map', default=None, help='folder for the name map and names list (default: the store folder)')
    ap.add_argument('--nfa-table', default=None, help='per-file NFA table (nfa_per_file.csv, in Savills-local)')
    ap.add_argument('--master', default=MASTER_CSV, help='residential master list for the checked NFA')
    a = ap.parse_args(argv)
    rows, readme = build(a.store, a.out, a.cpi, a.map, a.nfa_table, a.master)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print(readme)
    print(f'written: {os.path.join(a.out, VALUES_FILE)} ({len(rows)} rows)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
