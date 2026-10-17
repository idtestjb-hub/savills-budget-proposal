"""
Build the anonymous real-project service-level table (change add-service-level-table, design D5, D7, D10, D11).

    python build_service_levels.py --store <budget_scan_v2.sqlite> --levels <level_assignment_v7.csv>
                                   [--out <Budget_Agent/data/service_levels>] [--map <folder in Savills-local>]

Reads (read-only):
  the scan store       file_profile (budget year, total fee-paying NFA), dim_file (file date), project_map (names);
  the levels file      per file: security 24-hour posts, cleaning people, and whether each was read from the
                       budget's own A2/A3 form ("form") or inferred from the service's cost ("cost").
                       It is the output of the level-of-service readers in Savills-local (not in the store).
Writes:
  <out>/Ref_ServiceLevelProjects.csv        one anonymous row per project (no name, no file name)
  <map>/service_levels_map.csv              project_id -> file_id, project name, file name (stays in Savills-local)
  <map>/service_levels_names.txt            every project and file name of the store, for verification's name scan
  <out>/Ref_ServiceLevelProjects.build.txt  counts and the list of excluded or unclassified files BY ID only

Store rules (approved 2026-10-12 and 2026-10-18): Excel sources only (no scanned PDF, no converted xlsb), no content
duplicate; one file per project, the latest budget year (tie: later file date); a file with no project name is its
own project; two files with the same fee-paying NFA to the square metre are one project. The total fee-paying NFA
is file_profile.nfa_total less the "Management Fee" pseudo-product when the store summed product rows.

The script refuses to write when any output cell would contain a store project or file name.
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
import service_levels as sl  # noqa: E402

MAP_FILE = 'service_levels_map.csv'
NAMES_FILE = 'service_levels_names.txt'
BUILD_INFO = 'Ref_ServiceLevelProjects.build.txt'


class NameWouldLeak(RuntimeError):
    """A store name was about to be written into the anonymous table."""


def _norm(s):
    return ''.join(ch for ch in unicodedata.normalize('NFC', str(s or '')).casefold() if ch.isalnum())


def fee_nfa(nfa_total, nfa_how, nfa_types):
    """Total fee-paying NFA. When the store summed product rows and one of them is the 'Management Fee' total
    itself, take it out (design D6)."""
    if nfa_total in (None, ''):
        return None
    total = float(nfa_total)
    if (nfa_how or '') == 'sum_of_types' and nfa_types:
        m = re.search(r'Management Fee=([0-9.]+)', nfa_types)
        if m:
            total -= float(m.group(1))
    return total if total > 0 else None


def read_store(store_path):
    con = sqlite3.connect(f'file:{store_path}?mode=ro', uri=True)
    try:
        con.row_factory = sqlite3.Row
        cols = {r[1] for r in con.execute('pragma table_info(file_profile)')}
        want = ['file_id', 'file_name', 'budget_year_v2', 'nfa_total', 'nfa_how', 'nfa_types', 'content_dup_of',
                'source_type']
        sel = ', '.join(c if c in cols else f"NULL AS {c}" for c in want)
        profile = {r['file_id']: dict(r) for r in con.execute(f'select {sel} from file_profile')}
        files = {r['file_id']: dict(r) for r in con.execute('select file_id, file_name, modified from dim_file')}
        names = {r['file_id']: (r['project_name'] or '') for r in con.execute('select file_id, project_name from project_map')}
    finally:
        con.close()
    return profile, files, names


def read_levels(levels_path):
    with open(levels_path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _f(v):
    try:
        return float(v) if v not in (None, '') else None
    except ValueError:
        return None


def select_projects(level_rows, profile, files, names, log):
    """Apply the store rules; return the chosen rows with their measures' inputs attached."""
    cands = []
    for r in level_rows:
        fid = r['file_id']
        p = profile.get(fid)
        if p is None:
            log.append(f'{fid}: not in the store, left out')
            continue
        if (p.get('source_type') or 'excel') != 'excel':
            log.append(f'{fid}: {p["source_type"]} source, left out')
            continue
        if p.get('content_dup_of'):
            log.append(f'{fid}: content duplicate of {p["content_dup_of"]}, left out')
            continue
        nfa = fee_nfa(p.get('nfa_total'), p.get('nfa_how'), p.get('nfa_types'))
        name = names.get(fid, '') or r.get('project', '') or ''
        cands.append({
            'file_id': fid, 'project_name': name, 'file_name': files.get(fid, {}).get('file_name') or p.get('file_name') or '',
            'modified': files.get(fid, {}).get('modified') or '', 'budget_year': _f(p.get('budget_year_v2')),
            'nfa': nfa,
            'cln_people': _f(r.get('cln_equiv_posts')), 'cln_src': r.get('cln_src') or '',
            'sec_posts24': _f(r.get('sec_equiv_posts')), 'sec_src': r.get('sec_src') or '',
        })
    # group: by normalised name, else own file; then merge groups whose fee NFA is identical to the m² (D7)
    parent = {c['file_id']: c['file_id'] for c in cands}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_name = {}
    for c in cands:
        k = _norm(c['project_name'])
        if k:
            by_name.setdefault(k, []).append(c['file_id'])
    for ids in by_name.values():
        for other in ids[1:]:
            union(ids[0], other)
    by_nfa = {}
    for c in cands:
        if c['nfa']:
            by_nfa.setdefault(round(c['nfa']), []).append(c['file_id'])
    for ids in by_nfa.values():
        for other in ids[1:]:
            union(ids[0], other)
    groups = {}
    for c in cands:
        groups.setdefault(find(c['file_id']), []).append(c)
    chosen = []
    for members in groups.values():
        members.sort(key=lambda c: ((c['budget_year'] or 0), c['modified']), reverse=True)
        keep = members[0]
        for m in members[1:]:
            log.append(f'{m["file_id"]}: same project as {keep["file_id"]}, older budget year or file date, left out')
        chosen.append(keep)
    return chosen


def build_rows(chosen, thresholds, snapshot):
    rows = []
    for c in sorted(chosen, key=lambda c: c['file_id']):
        nfa = c['nfa']
        cln_v = sl.measure_cleaning(nfa, c['cln_people'])
        sec_v = sl.measure_security(nfa, c['sec_posts24'])
        reason = sl.REASON_NO_NFA if not nfa else sl.REASON_NO_HEADCOUNT
        cln = sl.classify('cleaning', cln_v, thresholds, reason_if_missing=reason)
        sec = sl.classify('security', sec_v, thresholds, reason_if_missing=reason)
        flags = []
        if cln.reason == sl.REASON_OUT_OF_BOUNDS:
            flags.append('nghi đọc sai: vệ sinh ngoài cận')
        if sec.reason == sl.REASON_OUT_OF_BOUNDS:
            flags.append('nghi đọc sai: bảo vệ ngoài cận')
        if not c['project_name']:
            flags.append('file không có tên dự án')
        rows.append({
            'file_id': c['file_id'], 'project_name': c['project_name'], 'file_name': c['file_name'],
            'name_key': sl.name_key(c['project_name']), 'nfa_m2': round(nfa, -1) if nfa else '',
            'budget_year': int(c['budget_year']) if c['budget_year'] else '',
            'nfa_fee_m2': round(nfa) if nfa else '',
            'cln_people': round(c['cln_people'], 1) if c['cln_people'] else '',
            'cln_source': sl.SOURCE_FORM if c['cln_src'] == 'form' else (sl.SOURCE_COST if c['cln_src'] else ''),
            'cln_m2_per_person': round(cln_v, 1) if cln_v else '',
            'cln_level': cln.level or sl.NOT_CLASSIFIED, 'cln_reason': cln.reason, 'cln_near': sl.NEAR_MARK if cln.near else '',
            'sec_posts24': round(c['sec_posts24'], 2) if c['sec_posts24'] else '',
            'sec_source': sl.SOURCE_FORM if c['sec_src'] == 'form' else (sl.SOURCE_COST if c['sec_src'] else ''),
            'sec_per_10k': round(sec_v, 3) if sec_v else '',
            'sec_level': sec.level or sl.NOT_CLASSIFIED, 'sec_reason': sec.reason, 'sec_near': sl.NEAR_MARK if sec.near else '',
            'flag': '; '.join(flags), 'snapshot': snapshot,
        })
    for i, r in enumerate(rows, start=1):
        r['project_id'] = f'S{i:03d}'
    return rows


def name_scan(rows, names):
    """Raise NameWouldLeak if any output cell contains a store project or file name (4+ characters, normalised)."""
    tokens = {_norm(n) for n in names if len(_norm(n)) >= 4}
    for r in rows:
        for col in sl.PROJECT_COLUMNS:
            cell = _norm(r.get(col, ''))
            if not cell:
                continue
            for t in tokens:
                if t in cell:
                    raise NameWouldLeak(f'{r["project_id"]}.{col} would carry a store name; nothing written')


def write_outputs(rows, names, out_dir, map_dir, log, counts_text):
    name_scan(rows, names)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(map_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'Ref_ServiceLevelProjects.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=sl.PROJECT_COLUMNS, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(os.path.join(map_dir, MAP_FILE), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['project_id', 'file_id', 'project_name', 'file_name'])
        for r in rows:
            w.writerow([r['project_id'], r['file_id'], r['project_name'], r['file_name']])
    with open(os.path.join(map_dir, NAMES_FILE), 'w', encoding='utf-8') as fh:
        for n in sorted({n for n in names if n}):
            fh.write(n + '\n')
    with open(os.path.join(out_dir, BUILD_INFO), 'w', encoding='utf-8') as fh:
        fh.write(counts_text + '\n\nExcluded or merged files (store ids only):\n' + '\n'.join('  ' + x for x in log) + '\n')


def summarise(rows, snapshot):
    lines = [f'Built {datetime.datetime.now():%Y-%m-%d %H:%M}; snapshot: {snapshot}', f'projects: {len(rows)}',
             f'with NFA: {sum(1 for r in rows if r["nfa_fee_m2"] != "")}']
    for svc, lvl, src in (('cleaning', 'cln_level', 'cln_source'), ('security', 'sec_level', 'sec_source')):
        cnt = {}
        for r in rows:
            cnt[r[lvl]] = cnt.get(r[lvl], 0) + 1
        form_cls = sum(1 for r in rows if r[src] == sl.SOURCE_FORM and r[lvl] != sl.NOT_CLASSIFIED)
        inf_cls = sum(1 for r in rows if r[src] == sl.SOURCE_COST and r[lvl] != sl.NOT_CLASSIFIED)
        lines.append(f'{svc}: ' + ', '.join(f'{k} {v}' for k, v in sorted(cnt.items())) +
                     f' | form-read classified {form_cls}, inferred classified {inf_cls}')
    nc = [f'{r["project_id"]}: ' + '; '.join(x for x in (r['cln_reason'] and 'cleaning ' + r['cln_reason'],
                                                        r['sec_reason'] and 'security ' + r['sec_reason']) if x)
          for r in rows if r['cln_reason'] or r['sec_reason']]
    lines.append('not classified: ' + ('; '.join(nc) if nc else 'none'))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build the anonymous real-project service-level table.')
    ap.add_argument('--store', required=True)
    ap.add_argument('--levels', required=True)
    ap.add_argument('--out', default=sl.DATA_DIR)
    ap.add_argument('--map', default=None, help='folder for the name map and names list (default: the store folder)')
    ap.add_argument('--thresholds', default=sl.THRESHOLDS_CSV)
    a = ap.parse_args(argv)
    map_dir = a.map or os.path.dirname(os.path.abspath(a.store))
    thresholds = sl.load_thresholds(a.thresholds)
    profile, files, names = read_store(a.store)
    level_rows = read_levels(a.levels)
    snapshot = (f'store {datetime.datetime.fromtimestamp(os.path.getmtime(a.store)):%Y-%m-%d}; '
                f'levels {os.path.basename(a.levels)} {datetime.datetime.fromtimestamp(os.path.getmtime(a.levels)):%Y-%m-%d}')
    log = []
    chosen = select_projects(level_rows, profile, files, names, log)
    rows = build_rows(chosen, thresholds, snapshot)
    all_names = set(names.values()) | {f['file_name'] for f in files.values()} | {p.get('file_name') for p in profile.values()}
    text = summarise(rows, snapshot)
    write_outputs(rows, all_names, a.out, map_dir, log, text)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print(text)
    print(f'written: {os.path.join(a.out, "Ref_ServiceLevelProjects.csv")} | map and names in {map_dir}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
