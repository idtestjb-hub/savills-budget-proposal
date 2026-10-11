"""The operating-project path (change use-operating-project-actuals, task 7.2; verify.py section 9).

Checks a run of the invented operating fixture (fixtures/Sample_Operating_Input.xlsx) against figures
read straight from that fixture, by label: never from read_input(), operating_inputs or the workbooks
under test, so a reader bug cannot hide itself.

- P1: each entered rate x NFA x 12 on the deliverable's RM row and on the analysis 'Management Fee';
  a product without an entered rate keeps the standard sample's comparable figure.
- P3: 100% occupancy on both fill-up sheets, 12 equal months on every RM row, RM.0A = 0.
- P2: RP1 (motorbike) and RP2 (car) = the entered monthly figure x 12, in equal months, and the
  analysis 'Additional Revenue' shows the same monthly figures.
- P4: each collect-on-behalf revenue line = its entered amount x 12, and each paired expense line
  (EEE.A for electricity, EEW.A for water) = the sum of its revenue lines. An amount entered at 0
  writes nothing.

Reading and checking are separate: read_outputs() opens Excel once per workbook and returns plain
values; check_operating() is pure, so a scratch edit of those values proves each check can fail
(task 7.3) without a pipeline run.

The section keeps its own baseline, verification/baselines/operating_baseline.json, recorded only
when every check passes:
    python verification/operating_project.py --record --reason "..."
"""
import os
import shutil
import sys
import tempfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(HERE)
if SOURCE not in sys.path:
    sys.path.insert(0, SOURCE)

import operating_inputs as oi                                      # noqa: E402
from verification import baseline as bl                            # noqa: E402

OPERATING_SAMPLE = os.path.join(HERE, 'fixtures', 'Sample_Operating_Input.xlsx')
OPERATING_BASELINE_PATH = os.path.join(HERE, 'baselines', 'operating_baseline.json')

_FUND = '2. Budget-Management Fund'
_SUMMARY = '1. Summary'
_CODE_COL, _G, _H, _S, _T = 25, 7, 8, 19, 20          # Y code, G year, H:S months, T remark
# Same block as checks._RM_PRODUCT_ROWS: the RM.* per-product rows of the standard form.
RM_PRODUCT_ROWS = {
    'Apartment': 14, 'Officetel': 15, 'Office': 16, 'Shopping Mall': 17, 'Retail': 18,
    'Shop Apartment': 19, 'Shophouse': 20, 'Villas': 21, 'Nursery / Nhà trẻ': 22,
}
_RESIDENT_FILL = ('lấp đầy cư dân', 20, 7)             # sheet name part, row, first month column (G)
_CAR_FILL = ('lấp đầy bãi xe', 9, 6)                   # F
_MOTO_FILL = ('lấp đầy bãi xe', 11, 6)
# PM-2 (a), as approved: electricity collected on behalf pairs with EEE.A, water with EEW.A.
COB_EXPENSE = {'electricity': 'EEE.A', 'water': 'EEW.A'}
# Existing + stable: the utility lines and their '1. Summary' narratives must be untouched (design D3).
_UTILITY_CODES = ('EEW.C', 'EEE.C')
_SUMMARY_UTILITY_ROWS = (38, 39)                       # EEW, EEE narratives in column K
_TOL_LINE = 12.0                                       # VND/year: monthly rounding x 12 months


def _nfc(s):
    return unicodedata.normalize('NFC', str(s or '')).casefold().strip()


# ---- expected figures, from the fixture ------------------------------------------------------------
def read_expected(sample_path=OPERATING_SAMPLE):
    """The fixture's operating fields and product areas, read by label."""
    import openpyxl

    from input_labels import SheetLabels, normalise

    wb = openpyxl.load_workbook(sample_path, data_only=True)
    try:
        ws = wb['Project Info']
        L = SheetLabels(ws)
        nfa = {p: float(ws.cell(row=L.row_of(p), column=3).value or 0) for p in RM_PRODUCT_ROWS}
        header = L.row_of(oi.PRODUCT_HEADER)
        cols = {normalise(ws.cell(row=header, column=c).value): c
                for c in range(1, (ws.max_column or 1) + 1) if ws.cell(row=header, column=c).value}
        rate_col, vat_col = cols.get(normalise(oi.RATE_HEADER)), cols.get(normalise(oi.VAT_HEADER))
        rates = {}
        if rate_col:
            for p in RM_PRODUCT_ROWS:
                v = ws.cell(row=L.row_of(p), column=rate_col).value
                if isinstance(v, (int, float)) and v:
                    rates[p] = (float(v), ws.cell(row=L.row_of(p), column=vat_col).value)
        stable = L.has(oi.STABLE_LABEL) and str(L.value(oi.STABLE_LABEL) or '').strip().casefold() == 'yes'
        parking = {k: (float(L.value(lbl)) if L.has(lbl) and L.value(lbl) is not None else None)
                   for k, lbl in (('car', oi.PARKING_CAR_LABEL), ('moto', oi.PARKING_MOTO_LABEL))}
        cob = {}
        if L.has(oi.COB_HEADER):
            hrow = L.row_of(oi.COB_HEADER)
            hcols = {normalise(ws.cell(row=hrow, column=c).value): c
                     for c in range(1, (ws.max_column or 1) + 1) if ws.cell(row=hrow, column=c).value}
            ucol = {'water': hcols[normalise(oi.COB_WATER_HEADER)],
                    'electricity': hcols[normalise(oi.COB_ELEC_HEADER)]}
            for p in RM_PRODUCT_ROWS:
                if L.has(oi.COB_ROW_PREFIX + p):
                    r = L.row_of(oi.COB_ROW_PREFIX + p)
                    cob[p] = {u: float(ws.cell(row=r, column=c).value or 0) for u, c in ucol.items()}
        return dict(nfa=nfa, rates=rates, stable=stable, parking=parking, cob=cob)
    finally:
        wb.close()


# ---- reading the outputs (Excel, once per workbook) ------------------------------------------------
def _block(ws, last_col):
    used = ws.UsedRange
    last_row = used.Row + used.Rows.Count - 1
    values = ws.Range(ws.Cells(1, 1), ws.Cells(last_row, last_col)).Value2
    return [list(r) for r in values]


def _find_sheet(wb, *parts):
    for ws in wb.Worksheets:
        if all(_nfc(p) in _nfc(ws.Name) for p in parts):
            return ws
    raise RuntimeError(f"no sheet whose name contains {' + '.join(parts)!r}")


def read_outputs(paths, analysis=True):
    """Recalculate copies in Excel and return the values the checks need:
    fund {code: dict(row, g, months, remark)} (first row per code) and rm {product: same},
    summary_k {row: text}, fills {'resident'|'car'|'moto': [12 values]},
    mgmt_fee {product: monthly} and parking {'car'|'moto': monthly} from the analysis."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise bl.BaselineUnavailable(f'The operating-project checks need Excel ({exc}).') from exc

    tmp = tempfile.mkdtemp(prefix='operating_check_')
    out = dict(fund={}, rm={}, summary_k={}, fills={}, mgmt_fee={}, parking={})
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False

        work = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
        shutil.copy(paths['deliverable'], work)
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        fund = next(ws for ws in wb.Worksheets if _nfc(ws.Name) == _nfc(_FUND))
        rows = _block(fund, _CODE_COL)
        for i, r in enumerate(rows, start=1):
            entry = dict(row=i, g=r[_G - 1], months=r[_H - 1:_S], remark=r[_T - 1])
            code = str(r[_CODE_COL - 1] or '').strip()
            if code and code not in out['fund']:
                out['fund'][code] = entry
        for product, row in RM_PRODUCT_ROWS.items():
            r = rows[row - 1]
            out['rm'][product] = dict(row=row, g=r[_G - 1], months=r[_H - 1:_S], remark=r[_T - 1])
        summary = next(ws for ws in wb.Worksheets if _nfc(ws.Name) == _nfc(_SUMMARY))
        for row in _SUMMARY_UTILITY_ROWS:
            out['summary_k'][row] = summary.Cells(row, 11).Value2
        for key, (part, row, col) in (('resident', _RESIDENT_FILL), ('car', _CAR_FILL), ('moto', _MOTO_FILL)):
            ws = _find_sheet(wb, part)
            out['fills'][key] = list(ws.Range(ws.Cells(row, col), ws.Cells(row, col + 11)).Value2[0])
        wb.Close(SaveChanges=False)
        wb = None

        if analysis:
            work = os.path.join(tmp, 'analysis_' + os.path.basename(paths['analysis']))
            shutil.copy(paths['analysis'], work)
            wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
            xl.CalculateFullRebuild()
            for r in _block(_find_sheet(wb, 'Management Fee'), 5):
                name = r[0].strip() if isinstance(r[0], str) else None
                if name in RM_PRODUCT_ROWS and isinstance(r[4], (int, float)) and isinstance(r[1], (int, float)):
                    out['mgmt_fee'][name] = float(r[4])
            for r in _block(_find_sheet(wb, 'Additional Revenue'), 5):
                name = r[0].strip() if isinstance(r[0], str) else None
                key = {'Car': 'car', 'Motorbike': 'moto'}.get(name)
                if key and key not in out['parking'] and isinstance(r[3], (int, float)):
                    out['parking'][key] = float(r[3])
            wb.Close(SaveChanges=False)
            wb = None
    except bl.BaselineUnavailable:
        raise
    except Exception as exc:
        raise bl.BaselineUnavailable(
            f'Excel could not read the operating-project outputs: {type(exc).__name__}: {exc}') from exc
    finally:
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
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
    return out


# ---- the checks (pure) ------------------------------------------------------------------------------
def _n(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def check_operating(expected, out, standard_full_year=None):
    """(ok, rows, diffs, notes). rows = (label, expected, actual, ok); diffs = (label, message), each
    message naming both values in VND. `standard_full_year` is {product: VND/year} from the standard
    sample's revenue-agreement rows (analysis column): a product with no entered rate must equal it."""
    rows, diffs, notes = [], [], []

    def same(label, exp, act, tol=_TOL_LINE):
        ok = abs(_n(act) - exp) <= tol
        rows.append((label, exp, _n(act), ok))
        if not ok:
            diffs.append((label, f'expected {exp:,.0f} VND, got {_n(act):,.0f} VND '
                                 f'(gap {_n(act) - exp:+,.0f})'))

    def flat(label, months, monthly=None):
        vals = [_n(m) for m in months]
        ok = len(vals) == 12 and max(vals) - min(vals) <= 1.0 and (monthly is None or abs(vals[0] - monthly) <= 1.0)
        rows.append((label, monthly if monthly is not None else vals[0], vals[0], ok))
        if not ok:
            want = f'{monthly:,.0f} VND' if monthly is not None else 'equal months'
            diffs.append((label, f'expected 12 months of {want}, got {min(vals):,.0f} to {max(vals):,.0f} VND'))

    # P1: entered rates on both workbooks.
    for product, (rate, vat) in expected['rates'].items():
        want = rate * expected['nfa'][product] * 12
        same(f'{product} management fee, deliverable G{RM_PRODUCT_ROWS[product]} '
             f'(entered {rate:,.0f} VND/m²/month {vat} x {expected["nfa"][product]:,.0f} m² x 12)',
             want, out['rm'][product]['g'])
        same(f"{product} management fee, analysis 'Management Fee' monthly x 12", want,
             _n(out['mgmt_fee'].get(product)) * 12)
    # P1: a priced product without an entered rate keeps its comparable figure.
    for product, area in expected['nfa'].items():
        if area and product not in expected['rates'] and standard_full_year is not None:
            want = standard_full_year.get(product)
            if want is None:
                notes.append(f'{product}: no standard-sample figure to compare with')
                continue
            same(f'{product} management fee from comparables, deliverable G{RM_PRODUCT_ROWS[product]} '
                 f'(standard sample, full year)', want, out['rm'][product]['g'], tol=max(_TOL_LINE, want * 5e-7))
            same(f"{product} management fee from comparables, analysis 'Management Fee' x 12", want,
                 _n(out['mgmt_fee'].get(product)) * 12, tol=max(_TOL_LINE, want * 5e-7))

    # P3: 100% occupancy, flat RM months, no developer top-up.
    if expected['stable']:
        for key, label in (('resident', 'resident fill-up sheet row 20 G:R'),
                           ('car', 'car parking fill-up row 9 F:Q'), ('moto', 'motorbike parking fill-up row 11 F:Q')):
            vals = [_n(v) for v in out['fills'][key]]
            ok = len(vals) == 12 and all(abs(v - 1.0) < 1e-9 for v in vals)
            rows.append((label, 1.0, min(vals) if vals else 0.0, ok))
            if not ok:
                diffs.append((label, f'expected 100% in all 12 months, got {min(vals):.2%} to {max(vals):.2%}'))
        for product, e in out['rm'].items():
            if _n(e['g']):
                flat(f'{product} management fee G{e["row"]}: 12 equal months', e['months'])
        rm0a = out['fund'].get('RM.0A')
        same('RM.0A developer top-up', 0.0, rm0a['g'] if rm0a else None, tol=0.5)

    # P2: recorded parking.
    for key, code in (('moto', 'RP1'), ('car', 'RP2')):
        monthly = expected['parking'].get(key)
        if monthly is None:
            continue
        line = out['fund'].get(code)
        same(f'{code} ({"motorbike" if key == "moto" else "car"}) = entered {monthly:,.0f} VND/month x 12',
             monthly * 12, line['g'] if line else None)
        if line:
            flat(f'{code} months', line['months'], monthly)
        same(f"{'Motorbike' if key == 'moto' else 'Car'} parking, analysis 'Additional Revenue' monthly",
             monthly, out['parking'].get(key), tol=1.0)

    # P4: collect-on-behalf pairs, grouped by expense code.
    expense_want, expense_from = {}, {}
    for product, amounts in expected['cob'].items():
        for utility, monthly in amounts.items():
            code = f"{oi.COB_REVENUE_PREFIX[utility]}.{oi.COB_SUFFIX[product]}"
            line = out['fund'].get(code)
            if monthly:
                same(f'{code} ({product} {utility} collected) = {monthly:,.0f} VND/month x 12', monthly * 12,
                     line['g'] if line else None)
                expense_want[COB_EXPENSE[utility]] = expense_want.get(COB_EXPENSE[utility], 0.0) + monthly * 12
                expense_from.setdefault(COB_EXPENSE[utility], []).append(code)
            else:
                same(f'{code} ({product} {utility} entered at 0) is 0 or blank', 0.0,
                     line['g'] if line else None, tol=0.5)
    for code, want in expense_want.items():
        line = out['fund'].get(code)
        got = _n(line['g'] if line else None)
        label = f"{code} paid on behalf = {' + '.join(expense_from[code])}"
        rows.append((label, want, got, abs(got - want) <= _TOL_LINE))
        if abs(got - want) > _TOL_LINE:
            diffs.append((label, f'pair unbalanced: {code} is {got:,.0f} VND, '
                                 f"{' + '.join(expense_from[code])} total {want:,.0f} VND (gap {got - want:+,.0f})"))
    return not diffs, rows, diffs, notes


def baseline_figures(out):
    """The operating run's own figures, for operating_baseline.json (added to the analysis figures)."""
    figs = {}
    for product, e in out['rm'].items():
        if _n(e['g']):
            figs[f'op_rm_{product.split(" /")[0].lower().replace(" ", "_")}_year'] = (
                e['g'], f"{_FUND}!G{e['row']}")
    for code in ('RM.0A', 'RP1', 'RP2', 'RO3.A', 'RO3.S', 'RO4.A', 'RO4.S', 'EEE.A', 'EEW.A', 'EEE.C', 'EEW.C'):
        line = out['fund'].get(code)
        if line:
            figs[f'op_{code.lower().replace(".", "_")}_year'] = (_n(line['g']), f"{_FUND}!G{line['row']} ({code})")
    return {name: {'value': float(_n(v)), 'unit': bl.VND, 'where': where} for name, (v, where) in figs.items()}


# ---- Existing + stable: the utility lines do not move -----------------------------------------------
def build_existing_stable(src, out_path):
    """A copy of an Existing-project sample with 'Stable Operation?' = Yes appended below its last row."""
    import openpyxl

    wb = openpyxl.load_workbook(src)
    ws = wb['Project Info']
    r = max(row for row in range(1, (ws.max_row or 1) + 1) if ws.cell(row=row, column=1).value) + 2
    ws.cell(row=r, column=1, value=oi.SECTION_TITLE)
    ws.cell(row=r + 1, column=1, value=oi.STABLE_LABEL)
    ws.cell(row=r + 1, column=2, value='Yes')
    wb.save(out_path)
    return out_path


def compare_existing_stable(plain, stable):
    """(ok, rows, diffs, notes): EEW.C / EEE.C (G, 12 months, T remark) and the '1. Summary' K38/K39
    narratives must be identical with and without the switch (Existing mode wins, design D3)."""
    rows, diffs = [], []
    for code in _UTILITY_CODES:
        a, b = plain['fund'].get(code), stable['fund'].get(code)
        for part in ('g', 'months', 'remark'):
            va, vb = (a or {}).get(part), (b or {}).get(part)
            ok = va == vb and va is not None
            rows.append((f'{code} {part}', va, vb, ok))
            if not ok:
                show = (lambda v: f'{_n(v):,.0f} VND') if part == 'g' else repr
                diffs.append((f'{code} {part}', f'without the switch {show(va)}, with it {show(vb)}'))
    for row in _SUMMARY_UTILITY_ROWS:
        va, vb = plain['summary_k'].get(row), stable['summary_k'].get(row)
        ok = va == vb and bool(va)
        rows.append((f'{_SUMMARY}!K{row}', va, vb, ok))
        if not ok:
            diffs.append((f'{_SUMMARY}!K{row}', f'without the switch {va!r}, with it {vb!r}'))
    return not diffs, rows, diffs, []


# ---- record ----------------------------------------------------------------------------------------
def _record(reason):
    """Run the standard and the operating samples, check, and write operating_baseline.json only if
    every check passes."""
    from verification import checks
    from verification.run_workflow import DEFAULT_SAMPLE, diff_snapshots, run_workflow

    with tempfile.TemporaryDirectory(prefix='operating_record_') as workdir:
        runs = {}
        for name, sample in (('standard', DEFAULT_SAMPLE), ('operating', OPERATING_SAMPLE)):
            d = os.path.join(workdir, name)
            os.makedirs(d)
            outputs, before, after = run_workflow(sample=sample, workdir=d)
            if diff_snapshots(before, after):
                print(f'FAIL  production artefacts changed during the {name} run')
                return 1
            runs[name] = checks.locate_outputs(outputs)
        _ok, rarows, _d, _n2 = checks.check_revenue_agreement(runs['standard'])
        standard = {lbl: a for lbl, _dv, a in rarows}
        paths = runs['operating']
        out = read_outputs(paths)
        results = [('operating path', check_operating(read_expected(), out, standard)),
                   ('revenue agreement', checks.check_revenue_agreement(paths, stable=True)),
                   ('remark content', checks.check_remark_content(paths)),
                   ('summary reconciliation', checks.check_summary_reconciles(paths)),
                   ('Required line items', checks.check_required_line_items(paths))]
        failed = False
        for title, (ok, rows, diffs, _notes) in results:
            print(f'{"OK  " if ok else "FAIL"}  {title} ({len(rows)} check(s))')
            for d in diffs:
                print('        - ' + ' | '.join(str(x) for x in d))
            failed |= not ok
        if failed:
            print('Not recorded: a check failed.')
            return 1
        figures = bl.extract_figures(paths['analysis'])
        figures.update(baseline_figures(out))
        path = bl.save_baseline(figures, reason, path=OPERATING_BASELINE_PATH, sample_path=OPERATING_SAMPLE)
        print(f'Recorded {len(figures)} figures to {path}')
        return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    argv = sys.argv[1:]
    if '--record' not in argv or '--reason' not in argv:
        print('usage: python verification/operating_project.py --record --reason "..."')
        sys.exit(2)
    sys.exit(_record(argv[argv.index('--reason') + 1]))
