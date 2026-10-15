"""Run log: one small record per complete run (change add-budget-run-log, spec budget-run-log).

`run.py` calls `write()` once, after the deliverable, the roster and the analysis are written and known to describe the
same project. The record says which project, when, how complete the budget is (Required lines of the AI Guideline
that carry a figure), what the Management Fund brings in and out, and the Savills profit read from the analysis.

Where it writes: `<folder of the input form>/run_log/<yyyymmdd-hhmmss>_<project-slug>.json`, one file per run, never
edited afterwards, so several PCs never write to the same file (design D1).

Failure policy (design D6): nothing here may change a run. Every problem becomes one `Run log:` line; a figure that
could not be read is None (JSON null), never 0.

Figures are read from READ-ONLY TEMPORARY COPIES of the finished workbooks, after Excel has recalculated them
(the workbooks are written by openpyxl, so their totals have no cached values). Excel is optional: without it
the record is still written, with blank figures and status 'excel_unavailable'.

Choices kept in one place (design D4):
- the amount of a line is column G ('Total Price') of its row on the fund sheet, as verification/checks.py reads it;
- a row is a leaf when its G formula is not a SUBTOTAL;
- a zero with a stated reason counts as NOT complete (user's decision, 2026-10-13);
- the Savills profit is the analysis Summary's 'Total Profit Value', read by label.
"""
import csv
import datetime
import json
import os
import re
import shutil
import tempfile
import unicodedata

SCHEMA = 1
FUND_SHEETS = ('2. Budget-Management Fund', '2.2 Common area Fund')
MAIN_SHEET = FUND_SHEETS[0]
CODE_COL, G_COL, REMARK_COL = 25, 7, 20          # Y, G, T on the standard form

# The same two exceptions verification/checks.py applies; verify.py compares both readings on every run (design D7).
_FORM_PLACEHOLDER_REMARKS = {('2.2 Common area Fund', 'RP5'): 'demo'}
_REQUIRED_CODE_DISCLOSED_ON = {'EMA1': 'EMA15', 'EMA2': 'EMA15', 'EMA3': 'EMA15', 'EMA4': 'EMA15'}

# Labels on the analysis workbook's Summary sheet (column A; the figure is in column B)
SUMMARY_SHEET = 'Summary'
PROFIT_LABEL = 'Total Profit Value ='
FEE_LABEL = '(3) Annual Management Fee Revenue'
BASIS_LABEL = 'View:'

_EXCEL_ERROR_LIMIT = -2146826000                  # Excel error values arrive as -2146826xxx through COM Value2


class ExcelUnavailable(Exception):
    pass


def _nfc(s):
    return unicodedata.normalize('NFC', str(s or ''))


def _slug(name, limit=40):
    s = unicodedata.normalize('NFKD', _nfc(name)).replace('đ', 'd').replace('Đ', 'D')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-')
    return (s or 'project')[:limit].strip('-') or 'project'


def _warn(msg):
    print(f'Run log: {msg}')


def _blank_record(now, problems):
    keys_none = ('project_name', 'project_mode', 'stable_operation', 'budget_year', 'deliverable_file', 'vat_basis',
                 'required_total', 'required_filled', 'required_zero_with_reason', 'required_zero_no_reason',
                 'required_missing_from_deliverable', 'required_pct', 'revenue_vnd', 'expense_vnd',
                 'fund_surplus_vnd', 'savills_profit_vnd', 'mgmt_fee_revenue_vnd', 'profit_cost_basis', 'error_cells')
    rec = {'schema': SCHEMA, 'run_id': now.strftime('%Y%m%d-%H%M%S'),
           'run_time_local': now.strftime('%Y-%m-%d %H:%M:%S')}
    rec.update({k: None for k in keys_none})
    rec['status'] = '; '.join(problems) if problems else 'ok'
    return rec


# ---- the input form (openpyxl, read-only) --------------------------------------------------------------------
def _read_input(input_path, problems):
    out = {'project_name': None, 'project_mode': None, 'stable_operation': None}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(input_path, read_only=True, data_only=True)
        try:
            ws = wb['Project Info']
            labels = {}
            for row in ws.iter_rows(min_row=1, max_row=120, max_col=2, values_only=True):
                if row[0] is not None and row[0] not in labels:
                    labels[' '.join(_nfc(row[0]).split()).casefold()] = row[1]

            def get(prefix):
                p = prefix.casefold()
                for k, v in labels.items():
                    if k.startswith(p):
                        return v
                return None
            name = get('Project Name')
            out['project_name'] = str(name).strip() if name not in (None, '') else None
            mode = get('Project Mode')
            out['project_mode'] = str(mode).strip() if mode not in (None, '') else 'New prospect'
            stable = get('Stable Operation')
            out['stable_operation'] = str(stable).strip().casefold() == 'yes' if stable not in (None, '') else False
        finally:
            wb.close()
    except Exception as exc:
        problems.append(f'input_unreadable:{type(exc).__name__}')
    return out


def _load_required(csv_path):
    with open(csv_path, encoding='utf-8-sig') as f:
        lines = [ln for ln in f if not ln.startswith('#')]
    return [(r['code'], r['sheet']) for r in csv.DictReader(lines)
            if r['requirement_level'] == 'Required' and r['sheet'] in FUND_SHEETS]


# ---- Excel measurement ----------------------------------------------------------------------------------------
def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _scan_fund_sheet(ws):
    """code -> (row, G value, G formula, remark). Whole used range, as verification/checks.py does."""
    by_code = {}
    last = ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1
    for r in range(1, last + 1):
        code = ws.Cells(r, CODE_COL).Value2
        if not (isinstance(code, str) and code.strip()):
            continue
        by_code[code.strip()] = (r, ws.Cells(r, G_COL).Value2, str(ws.Cells(r, G_COL).Formula or ''),
                                 ws.Cells(r, REMARK_COL).Value2)
    return by_code


def _classify(sheet_name, code, info, scans):
    """'filled' | 'reason' | 'no_reason' | 'header' | 'missing'."""
    if info is None:
        return 'missing'
    _r, g, formula, remark = info
    if 'SUBTOTAL' in formula.upper():
        return 'header'
    gn = _num(g)
    if gn is not None and abs(gn) > 0.5:
        return 'filled'
    disclosed_on = _REQUIRED_CODE_DISCLOSED_ON.get(code)
    if disclosed_on:
        d = scans.get(disclosed_on)
        return 'reason' if d and isinstance(d[3], str) and d[3].strip() else 'no_reason'
    placeholder = isinstance(remark, str) and _FORM_PLACEHOLDER_REMARKS.get((sheet_name, code)) == remark.strip()
    return 'reason' if isinstance(remark, str) and remark.strip() and not placeholder else 'no_reason'


def _count_error_cells(wb):
    n = 0
    for ws in wb.Worksheets:
        vals = ws.UsedRange.Value2
        if vals is None:
            continue
        if not isinstance(vals, tuple):
            vals = ((vals,),)
        for row in vals:
            for v in (row if isinstance(row, tuple) else (row,)):
                if isinstance(v, int) and not isinstance(v, bool) and v < _EXCEL_ERROR_LIMIT:
                    n += 1
    return n


def _excel_measure(deliverable, analysis, required, problems):
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ExcelUnavailable(str(exc))
    tmp = tempfile.mkdtemp(prefix='run_log_')
    out = {}
    pythoncom.CoInitialize()
    xl = dwb = awb = None
    try:
        try:
            xl = win32com.client.DispatchEx('Excel.Application')
            xl.Visible = False
            xl.DisplayAlerts = False
        except Exception as exc:
            raise ExcelUnavailable(f'{type(exc).__name__}')
        dcopy = os.path.join(tmp, 'deliverable.xlsx')
        shutil.copyfile(deliverable, dcopy)
        dwb = xl.Workbooks.Open(dcopy, UpdateLinks=0, ReadOnly=True)
        acopy = None
        if analysis and os.path.exists(analysis):
            acopy = os.path.join(tmp, 'analysis.xlsx')
            shutil.copyfile(analysis, acopy)
            awb = xl.Workbooks.Open(acopy, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()

        sheets = {_nfc(ws.Name): ws for ws in dwb.Worksheets}
        scans = {}
        for name in FUND_SHEETS:
            if _nfc(name) in sheets:
                scans[name] = _scan_fund_sheet(sheets[_nfc(name)])
            else:
                problems.append(f'missing_sheet:{name}')

        counts = {'filled': 0, 'reason': 0, 'no_reason': 0, 'missing': 0}
        for name, scan in scans.items():
            for code, sheet in required:
                if sheet != name:
                    continue
                kind = _classify(name, code, scan.get(code), scan)
                if kind in counts:
                    counts[kind] += 1
        if scans:
            total = counts['filled'] + counts['reason'] + counts['no_reason']
            out.update(required_total=total, required_filled=counts['filled'],
                       required_zero_with_reason=counts['reason'], required_zero_no_reason=counts['no_reason'],
                       required_missing_from_deliverable=counts['missing'],
                       required_pct=(counts['filled'] / total) if total else None)

        main = scans.get(MAIN_SHEET)
        if main is not None:
            rev, exp = main.get('R'), main.get('E')
            r_v, e_v = (_num(rev[1]) if rev else None), (_num(exp[1]) if exp else None)
            if r_v is None:
                problems.append('missing_row:R')
            if e_v is None:
                problems.append('missing_row:E')
            out['revenue_vnd'], out['expense_vnd'] = r_v, e_v
            out['fund_surplus_vnd'] = (r_v - e_v) if r_v is not None and e_v is not None else None
            ws = sheets[_nfc(MAIN_SHEET)]
            switch = ' '.join(str(ws.Range('F7').Value2 or '').split()).upper()
            out['vat_basis'] = 'exclusive' if switch == 'KHOÁN' else 'inclusive'
            year = None
            for c in range(1, 70):
                v = ws.Cells(5, c).Value2
                if isinstance(v, str) and v.strip().casefold().startswith('budget year'):
                    nxt = _num(ws.Cells(5, c + 1).Value2)
                    year = int(nxt) if nxt else None
                    break
            if year is None:
                problems.append('missing_label:Budget Year')
            out['budget_year'] = year
        out['error_cells'] = _count_error_cells(dwb)

        if awb is not None:
            s = next((w for w in awb.Worksheets if _nfc(w.Name) == SUMMARY_SHEET), None)
            found = {}
            if s is not None:
                for r in range(1, 80):
                    a = ' '.join(_nfc(s.Cells(r, 1).Value2).split())
                    for key, label in (('profit', PROFIT_LABEL), ('fee', FEE_LABEL), ('basis', BASIS_LABEL)):
                        if key not in found and a.startswith(label):
                            found[key] = s.Cells(r, 2).Value2
            else:
                problems.append(f'missing_sheet:{SUMMARY_SHEET}')
            out['savills_profit_vnd'] = _num(found.get('profit'))
            out['mgmt_fee_revenue_vnd'] = _num(found.get('fee'))
            out['profit_cost_basis'] = str(found['basis']).strip() if found.get('basis') else None
            for key, label in (('profit', PROFIT_LABEL), ('fee', FEE_LABEL), ('basis', BASIS_LABEL)):
                if s is not None and key not in found:
                    problems.append(f'missing_label:{label.rstrip(" =")}')
        else:
            problems.append('analysis_missing')
    finally:
        for wb in (dwb, awb):
            try:
                if wb is not None:
                    wb.Close(SaveChanges=False)
            except Exception:
                pass
        try:
            if xl is not None:
                xl.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()
        shutil.rmtree(tmp, ignore_errors=True)
    return out


# ---- public ---------------------------------------------------------------------------------------------------
def measure(deliverable, analysis, input_path, classification_csv, now=None):
    """Build the record (a dict). Never raises for a missing or unreadable figure: it leaves None and names the cause."""
    now = now or datetime.datetime.now()
    problems = []
    rec = _blank_record(now, problems)
    rec.update(_read_input(input_path, problems))
    rec['deliverable_file'] = os.path.basename(deliverable) if deliverable else None
    try:
        required = _load_required(classification_csv)
    except OSError as exc:
        problems.append(f'classification_unreadable:{type(exc).__name__}')
        required = []
    try:
        rec.update(_excel_measure(deliverable, analysis, required, problems))
    except ExcelUnavailable:
        problems.append('excel_unavailable')
    except Exception as exc:
        problems.append(f'measure_error:{type(exc).__name__}')
    rec['status'] = '; '.join(dict.fromkeys(problems)) if problems else 'ok'
    return rec


def write_record(record, log_dir):
    """Write the record as its own new file. Returns the path. Never replaces an existing file."""
    os.makedirs(log_dir, exist_ok=True)
    base = f"{record['run_id']}_{_slug(record.get('project_name'))}"
    n = 1
    while True:
        path = os.path.join(log_dir, f'{base}.json' if n == 1 else f'{base}-{n}.json')
        try:
            with open(path, 'x', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
                f.write('\n')
            return path
        except FileExistsError:
            n += 1


def write(deliverable, analysis, input_path, classification_csv, log_dir=None, now=None):
    """The call `run.py` makes. Returns (path or None, record or None); every failure is a warning, never an exception."""
    try:
        log_dir = log_dir or os.path.join(os.path.dirname(os.path.abspath(input_path)), 'run_log')
        rec = measure(deliverable, analysis, input_path, classification_csv, now=now)
    except Exception as exc:
        _warn(f'no record written ({type(exc).__name__}: {exc}).')
        return None, None
    try:
        path = write_record(rec, log_dir)
    except Exception as exc:
        _warn(f'no record written, the folder could not be written ({type(exc).__name__}: {exc}).')
        return None, rec
    if rec['status'] != 'ok':
        _warn(f"record written with blank figures ({rec['status']}).")
    return path, rec
