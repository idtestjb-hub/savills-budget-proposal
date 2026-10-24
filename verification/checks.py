"""
Structural checks on the workbooks a verification run produces.

These answer "is this workbook shaped the way it should be", not "are the numbers right". Numeric
comparison is a separate concern (see the change's tasks group 4).

WHY THE EXPECTED SHEET SETS ARE HARDCODED HERE rather than read from the template: the point of the
check is to notice when the pipeline stops producing a sheet it used to produce. Deriving the
expectation from the same template the pipeline reads would make the check agree with the pipeline
by construction, and it would notice nothing. So the sets below are a recorded contract, captured
from a real run and verified against the template's own sheet list.

If Savills reshapes the template, this check SHOULD fail — that is the signal, not a false alarm.
Update the constants below deliberately, the same way REDIRECT_PLAN in isolation.py is updated.
"""
import os
import re
import unicodedata


def _nfc(s):
    """Normalise to NFC. Some sheet names in Savills' forms are typed in a mixed Unicode form
    that is neither NFC nor NFD (e.g. 'Tỷ lệ lấp đầy cư dân'), so an exact `==` against a
    hand-written string silently fails. Every sheet-name comparison in this module goes through
    here — the same NFC normalisation the pipeline's own sheet lookups use."""
    return unicodedata.normalize('NFC', s) if isinstance(s, str) else s

# Re-captured 2026-09-10 (change `rebase-output-onto-25-sheet-form`) against the current standard
# form `input/template/2027 Resi Budget Form (IT team).xlsx`: 24 Savills sheets plus 'Comparison',
# which the pipeline appends. Change from the superseded 202608 form: adds 'Tỷ lệ lấp đầy cư dân',
# 'Tiến độ lấp đầy bãi xe', 'B2.6 Rác sinh hoạt (QD67)'; the staff sheets are the form's own
# 'A1. Staff cost 08.2026 (VN)' / 'A1.1 Allowance (From 08.2026)' (was the PM-pasted '1. ...' pair,
# the same calculator); 'Master Info' is not carried (external-workbook links — returns with the
# per-product management-fee change).
# Trailing spaces in two names are real and are preserved deliberately — matching is exact.
EXPECTED_SHEETS = {
    'deliverable': [
        'Cover',
        '0. Info',
        'Tỷ lệ lấp đầy cư dân',
        'Tiến độ lấp đầy bãi xe',
        '1. Summary',
        '2. Budget-Management Fund',
        '2.1 Report-Management Fund',
        '2.2 Common area Fund',
        '2.2.1 Report-Common area Fund',
        '3. Budget-Sinking Fund',
        '3.1 Report-Sinking Fund',
        # Added 2026-10-20 (docs/32, budget adjustment demo): the tool's own sheet, one parent row per fund line
        # with its detail sub-rows, sitting right after the sinking-fund report (check_adjustment_sheet).
        '4. Điều chỉnh',
        'A1. Staff cost 08.2026 (VN)',
        'A1.1 Allowance (From 08.2026)',
        'A2. Bảo vệ - Security',
        'A3. Vệ sinh - Cleaning',
        'A4. Cây xanh - Landscape',
        'A5. Trợ cấp PCCC',
        'B2.6 Rác sinh hoạt (QD67)',
        'B1. Lịch Lễ tân',
        'B2. Mùi hương - Scent',
        'B3. Vật tư vệ sinh - Consumable',
        'B3. Thu gom rác - Garbage coll ',
        'B4. DT Quảng cáo - Elevator adv',
        'B5. Đơn giá gửi xe - Parking pr',
        'Comparison',
    ],
    'analysis': [
        'Summary',
        'Data Flow',
        'Management Fee',
        'Comparison',
        'Staffing Estimate',
        'Staff (Roster)',
        'Service',
        'Capex',
        'OPEX',
        'Additional Revenue',
        'Cost Priority',
        'Year 1 Strategy',
        'Owner Operating Position',
        'Savills Fee Position',
        'Real-Budget Ranges',
        'Service Levels',
    ],
    'roster': [
        'Shift Types',
        'Staffing Demand',
        'Setup',
        'Generated Roster',
        'Cost Summary',
    ],
}


class StructureError(RuntimeError):
    """Raised when a generated workbook is not shaped the way it should be."""


def locate_outputs(outputs):
    """Map run_workflow()'s return value to the three workbook paths.

    The deliverable's filename carries the project name, so it is found by suffix rather than by a
    fixed name. Raises StructureError if it is missing entirely — a workbook that was never written
    cannot be checked, and silently skipping it would defeat the purpose.
    """
    deliverable_dir = outputs['deliverable_dir']
    matches = [f for f in sorted(os.listdir(deliverable_dir))
               if f.endswith('.xlsx') and f.endswith('Sample Consulting Budget.xlsx')]
    if not matches:
        raise StructureError(
            f'No client deliverable was produced in {deliverable_dir}. Expected a file ending '
            f'"Sample Consulting Budget.xlsx"; found: {sorted(os.listdir(deliverable_dir)) or "nothing"}.'
        )
    if len(matches) > 1:
        raise StructureError(
            f'Expected exactly one client deliverable, found {len(matches)}: {matches}. '
            f'A verification run should produce one project, not several.'
        )
    return {
        'deliverable': os.path.join(deliverable_dir, matches[0]),
        'analysis': outputs['analysis'],
        'roster': outputs['roster'],
    }


def _sheet_names(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def check_deliverable_figures(paths):
    """Compare the client deliverable's occupancy-ramped budget lines against their recorded
    baseline (verification/deliverable_baseline.py). A ramped line reverting to a flat 1/12 write,
    or the fill-up curve changing, surfaces here as a named figure difference.

    Returns (ok, figures, differences, notes). Raises the baseline module's own errors if Excel is
    unavailable or a figure is missing.
    """
    from verification import deliverable_baseline as dbl

    figures = dbl.extract_deliverable_figures(paths['deliverable'])
    stored = dbl.load()
    if stored is None:
        return False, figures, [], ['No deliverable baseline recorded yet — run: '
                                    'python verification/deliverable_baseline.py --record --reason "..."']
    ok, differences, notes = dbl.compare(figures, stored=stored)
    return ok, figures, differences, notes


# The nine products both generators can price. Same list in generate_project_budget.py
# (PRODUCT_REVENUE_ROWS) and generate_project_output.py (PRODUCT_ROWS). The row numbers are the
# RM.* per-product revenue block in the standard form's '2. Budget-Management Fund'.
_RM_PRODUCT_ROWS = {
    'Apartment': 14, 'Officetel': 15, 'Office': 16, 'Shopping Mall': 17, 'Retail': 18,
    'Shop Apartment': 19, 'Shophouse': 20, 'Villas': 21, 'Nursery / Nhà trẻ': 22,
}
_RM_DEVELOPER_ROW = 23  # RM.0A — developer top-up on unsold units (info only here)


def parking_prices_in_outputs(paths):
    """({'car': price|None, 'moto': price|None} from the deliverable's helper sheet B5 row 17, the same from the
    analysis's Additional Revenue parking table). A non-numeric cell (no bays, or a recorded revenue) reads None."""
    import openpyxl
    out_d, out_a = {}, {}
    wb = openpyxl.load_workbook(paths['deliverable'], read_only=True)
    try:
        ws = next((wb[n] for n in wb.sheetnames if n.startswith('B5.')), None)
        row = next(ws.iter_rows(min_row=17, max_row=17, max_col=6, values_only=True)) if ws is not None else ()
        out_d['car'] = row[2] if len(row) > 2 and isinstance(row[2], (int, float)) else None
        out_d['moto'] = row[4] if len(row) > 4 and isinstance(row[4], (int, float)) else None
    finally:
        wb.close()
    wa = openpyxl.load_workbook(paths['analysis'], read_only=True)
    try:
        ws = wa['Additional Revenue'] if 'Additional Revenue' in wa.sheetnames else None
        for r in (ws.iter_rows(min_row=1, max_row=40, max_col=2, values_only=True) if ws is not None else ()):
            key = {'Car': 'car', 'Motorbike': 'moto'}.get(r[0] if isinstance(r[0], str) else '')
            if key and key not in out_a:
                out_a[key] = r[1] if isinstance(r[1], (int, float)) else None
    finally:
        wa.close()
    return out_d, out_a


def check_parking_price_agreement(paths):
    """Change price-fee-and-parking-from-portfolio (task 6.1): the monthly parking price per vehicle the deliverable
    quotes on helper sheet B5 equals the one the analysis's Additional Revenue table uses, per vehicle type; both
    blank (no bays, or a recorded revenue) also agrees. Returns (ok, rows, differences, notes)."""
    d, a = parking_prices_in_outputs(paths)
    rows, diffs = [], []
    for key, label in (('car', 'RP2 car price (VND/vehicle/month)'), ('moto', 'RP1 motorbike price (VND/vehicle/month)')):
        dv, av = d.get(key), a.get(key)
        rows.append((label, dv, av))
        if (dv is None) != (av is None) or (dv is not None and abs(float(dv) - float(av)) > 0.5):
            diffs.append((label, dv, av))
    return not diffs, rows, diffs, ['Deliverable: helper sheet B5 row 17; analysis: Additional Revenue parking table.']


def check_revenue_agreement(paths, stable=False):
    """Run the client deliverable and the internal analysis side by side and confirm they price
    management-fee revenue the same way — same full-year total, same figure per product.

    They should agree by construction once both generators rank comparables on the same basis
    (Total building NFA — change `unify-revenue-basis-across-outputs`). This check fails if they
    ever drift apart, which neither workbook's own recorded baseline can see: a baseline catches
    drift from a recorded number, this catches the two reports disagreeing with each other.

    The deliverable's RM rows are occupancy-ramped (a part-year figure); they are un-ramped to a
    full-occupancy year here so the two sides are on the same footing.

    Returns (ok, rows, differences, notes) where `rows` is a list of
    (label, deliverable_vnd, analysis_vnd). Raises BaselineUnavailable if Excel cannot be driven.
    """
    import shutil
    import tempfile

    from verification.baseline import BaselineUnavailable
    from fill_curve import year1_fills

    # A project declared at stable operation is flat at the stable fill (use-operating-project-actuals P3).
    sum_fills = sum(year1_fills(stable))

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            'The cross-generator revenue-agreement check requires Excel — both workbooks store '
            f'these figures as live formulas ({exc}).') from exc

    tmp = tempfile.mkdtemp(prefix='revenue_agree_')
    dwork = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
    awork = os.path.join(tmp, 'analysis_' + os.path.basename(paths['analysis']))
    shutil.copy(paths['deliverable'], dwork)
    shutil.copy(paths['analysis'], awork)

    pythoncom.CoInitialize()
    xl = dwb = awb = None
    deliverable = {}
    analysis = {}
    dev_topup = 0.0
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False

        dwb = xl.Workbooks.Open(dwork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        dfund = next((ws for ws in dwb.Worksheets
                      if _nfc(ws.Name) == _nfc('2. Budget-Management Fund')), None)
        if dfund is None:
            raise RuntimeError("deliverable has no '2. Budget-Management Fund' sheet")
        for product, row in _RM_PRODUCT_ROWS.items():
            g = dfund.Cells(row, 7).Value2 or 0        # col G = SUM(H:S) — ramped year-1 total
            deliverable[product] = float(g) * 12.0 / sum_fills   # un-ramp to a full-occupancy year
        dev_topup = float(dfund.Cells(_RM_DEVELOPER_ROW, 7).Value2 or 0)
        dwb.Close(SaveChanges=False)
        dwb = None

        awb = xl.Workbooks.Open(awork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        amf = next((ws for ws in awb.Worksheets if _nfc(ws.Name) == _nfc('Management Fee')), None)
        if amf is None:
            raise RuntimeError("analysis has no 'Management Fee' sheet")
        used = amf.UsedRange
        for r in range(1, used.Row + used.Rows.Count):
            name = amf.Cells(r, 1).Value2
            nfa = amf.Cells(r, 2).Value2
            monthly = amf.Cells(r, 5).Value2          # col E = per-product monthly revenue (=B*C)
            if (isinstance(name, str) and name.strip() in _RM_PRODUCT_ROWS
                    and isinstance(nfa, (int, float)) and isinstance(monthly, (int, float))):
                analysis[name.strip()] = float(monthly) * 12.0
        awb.Close(SaveChanges=False)
        awb = None
    except Exception as exc:
        raise BaselineUnavailable(
            'Excel could not evaluate the two workbooks for the revenue-agreement check: '
            f'{type(exc).__name__}: {exc}') from exc
    finally:
        for w in (dwb, awb):
            try:
                if w is not None:
                    w.Close(SaveChanges=False)
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

    def _tol(v):
        # rounding across 9 products x 12 ramped monthly cells is ~tens of VND; a real divergence
        # (different comparables) is millions. 0.005% or 5,000 VND, whichever is larger.
        return max(5_000.0, abs(v) * 5e-5)

    rows = []
    differences = []
    d_total = a_total = 0.0
    for product in _RM_PRODUCT_ROWS:
        d = deliverable.get(product, 0.0)
        a = analysis.get(product, 0.0)
        if abs(d) < 1.0 and abs(a) < 1.0:
            continue                                   # product this project does not have
        d_total += d
        a_total += a
        entry = (product, d, a)
        rows.append(entry)
        if abs(d - a) > _tol(max(abs(d), abs(a))):
            differences.append(entry)
    total_entry = ('TOTAL management-fee revenue (full-year, VND)', d_total, a_total)
    rows.append(total_entry)
    if abs(d_total - a_total) > _tol(max(abs(d_total), abs(a_total))):
        differences.append(total_entry)

    notes = [
        f'Deliverable RM rows are occupancy-ramped; un-ramped here (x 12 / {sum_fills:.4f}) to a '
        f'full-occupancy year. RM.0A developer top-up (not compared, info only): {dev_topup:,.0f} VND.',
        'Both columns are VND/year at full occupancy — equal by construction once both generators '
        'rank comparables on Total building NFA. Equal per-product revenue on equal input NFA also '
        'means the two derived the same rate.',
    ]
    return (len(differences) == 0), rows, differences, notes


# The Comparison sheet's PROPOSAL BENCHMARK own-project cells (column B) and the '1. Summary' cell
# each one carries forward. Matched by an ASCII prefix of the row's column-A label (the full labels
# carry an em dash and a curly apostrophe — matching a prefix avoids a brittle exact compare), not a
# fixed row number: the section's position shifts with the address and note rows. See
# generate_project_budget.py add_comparison_sheet() and change benchmark-proposal-against-comparables.
_BENCHMARK_RECONCILE = [
    ('Year-1 management-fee revenue (VND)',   'H14'),
    ('Year-1 total operating income (VND)',   'H13'),
    ('Year-1 total operating cost (VND)',     'H20'),
    ('Year-1 operating surplus (VND)',        'H46'),
]
_BENCHMARK_REVENUE_LABEL = 'Year-1 management-fee revenue (VND)'
# The analysis Comparison sheet's per-comparable rate row: a cell starting 'BLANK' has no real rate.
_PEER_RATE_LABEL = 'Real Apartment rate per comparable'


def comparison_cells_past_column_b(ws):
    """Coordinates of every non-empty cell in column C or beyond on the deliverable's Comparison
    sheet (an openpyxl worksheet). The client sheet carries this project's figures only — the peer
    columns moved to the internal analysis (change apply-head-of-pm-decisions-2026-10, D14) — so
    anything here is a peer figure or name leaking back. Values only: fills, borders and merges are
    ignored."""
    found = []
    for row in ws.iter_rows(min_col=3):
        for cell in row:
            v = cell.value
            if v is not None and not (isinstance(v, str) and not v.strip()):
                found.append(cell.coordinate)
    return found


def check_benchmark_reconciles(paths):
    """Confirm the client deliverable's Comparison-sheet PROPOSAL BENCHMARK section carries the
    deliverable's own '1. Summary' figures forward, rather than restating (and possibly drifting
    from) them, that the client sheet holds nothing past column B, and that the internal analysis
    carries the peer projections.

    The benchmark's own-project revenue / operating income / operating cost / operating surplus
    cells are written as formulas into '1. Summary' (change benchmark-proposal-against-comparables,
    design D1), so this should hold by construction; the check fails if a reference has broken
    (#REF!, wrong cell) or a cell evaluates to an error.

    The "revenue if charged at comparable X's rate" projections live on the analysis's Comparison
    sheet since D14 (change apply-head-of-pm-decisions-2026-10). Each must be a finite positive
    number, one per comparable with a real Apartment rate (none found where a rate exists fails, it
    does not pass empty), and where that comparable's rate equals the derived rate (the formula is
    a bare reference) the projection must equal the analysis's own revenue.

    Returns (ok, rows, differences, notes) where `rows` is [(label, benchmark_vnd, summary_vnd)].
    Raises BaselineUnavailable if Excel cannot be driven.
    """
    import shutil
    import tempfile

    import openpyxl

    from verification.baseline import BaselineUnavailable

    rows, differences, notes = [], [], []

    # -- the client sheet holds this project's column only (openpyxl, values as written) --
    owb = openpyxl.load_workbook(paths['deliverable'], data_only=False)
    try:
        cmp_name = next((n for n in owb.sheetnames if _nfc(n) == _nfc('Comparison')), None)
        if cmp_name is not None:
            extra = comparison_cells_past_column_b(owb[cmp_name])
            if extra:
                differences.append((f'deliverable Comparison has {len(extra)} cell(s) past column B '
                                    f'({", ".join(extra[:6])}{"…" if len(extra) > 6 else ""}) — peer '
                                    'figures belong in the analysis', None, None))
    finally:
        owb.close()

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            'The proposal-benchmark reconciliation check requires Excel — the Comparison sheet and '
            f"'1. Summary' both store these figures as live formulas ({exc}).") from exc

    tmp = tempfile.mkdtemp(prefix='benchmark_recon_')
    dwork = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
    awork = os.path.join(tmp, 'analysis_' + os.path.basename(paths['analysis']))
    shutil.copy(paths['deliverable'], dwork)
    shutil.copy(paths['analysis'], awork)

    def _num(v):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def _labels(ws):
        used = ws.UsedRange
        last_row = used.Row + used.Rows.Count - 1
        col_a = {}
        for rr in range(1, last_row + 1):
            a = ws.Cells(rr, 1).Value2
            if isinstance(a, str) and a.strip():
                col_a.setdefault(rr, a.strip())
        return col_a

    def _row_starting(col_a, prefix):
        return next((rr for rr in sorted(col_a) if col_a[rr].startswith(prefix)), None)

    pythoncom.CoInitialize()
    xl = dwb = awb = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        dwb = xl.Workbooks.Open(dwork, UpdateLinks=0, ReadOnly=True)
        awb = xl.Workbooks.Open(awork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {ws.Name: ws for ws in dwb.Worksheets}
        cmp_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('Comparison')), None)
        sum_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('1. Summary')), None)
        if cmp_ws is None or sum_ws is None:
            raise RuntimeError("deliverable is missing the 'Comparison' or '1. Summary' sheet")

        col_a = _labels(cmp_ws)
        for prefix, summary_cell in _BENCHMARK_RECONCILE:
            rr = _row_starting(col_a, prefix)
            if rr is None:
                differences.append((prefix, None, None))
                notes.append(f'benchmark row not found: {prefix!r}')
                continue
            label = col_a[rr]
            bench = _num(cmp_ws.Cells(rr, 2).Value2)
            summ = _num(sum_ws.Range(summary_cell).Value2)
            rows.append((label, bench, summ))
            if bench is None or summ is None:
                differences.append((label, bench, summ))
            elif abs(bench - summ) > max(5_000.0, abs(summ) * 5e-5):
                differences.append((label, bench, summ))

        # projections: the analysis Comparison sheet's revenue row, columns C.. (one per comparable)
        asheets = {ws.Name: ws for ws in awb.Worksheets}
        acmp = next((asheets[n] for n in asheets if _nfc(n) == _nfc('Comparison')), None)
        if acmp is None:
            raise RuntimeError("analysis is missing the 'Comparison' sheet")
        acol_a = _labels(acmp)
        rate_rr = _row_starting(acol_a, _PEER_RATE_LABEL)
        n_comp = n_rated = 0
        if rate_rr:
            col = 3
            while True:
                raw = acmp.Cells(rate_rr, col).Value2
                if raw is None or (isinstance(raw, str) and not raw.strip()):
                    break
                n_comp += 1
                if not (isinstance(raw, str) and raw.strip().startswith('BLANK')):
                    n_rated += 1
                col += 1
        else:
            differences.append((f'analysis Comparison row not found: {_PEER_RATE_LABEL!r}', None, None))
        rr = _row_starting(acol_a, _BENCHMARK_REVENUE_LABEL)
        own_rev = _num(acmp.Cells(rr, 2).Value2) if rr else None
        if rr is None or own_rev is None:
            if n_rated:
                differences.append(('analysis Comparison has no evaluable year-1 revenue row', own_rev, None))
        else:
            n_proj = 0
            for col in range(3, 3 + n_comp):
                raw = acmp.Cells(rr, col).Value2
                formula = str(acmp.Cells(rr, col).Formula or '')
                if not formula.startswith('='):
                    continue                              # '—': that comparable has no real rate
                n_proj += 1
                proj = _num(raw)
                tail = formula.split('!')[-1]
                bare_ref = ('+' not in tail and '-' not in tail)  # rate == derived rate
                label = f'analysis projection column {col}'
                rows.append((label, proj, own_rev if bare_ref else None))
                if proj is None or proj <= 0:
                    differences.append((label, proj, None))
                elif bare_ref and abs(proj - own_rev) > max(5_000.0, abs(own_rev) * 5e-5):
                    differences.append((label, proj, own_rev))
            if n_proj != n_rated:
                differences.append((f'analysis Comparison has {n_proj} revenue projection(s) for '
                                    f'{n_rated} comparable(s) with a real Apartment rate', None, None))
        dwb.Close(SaveChanges=False)
        dwb = None
        awb.Close(SaveChanges=False)
        awb = None
    except Exception as exc:
        raise BaselineUnavailable(
            'Excel could not evaluate the deliverable for the proposal-benchmark reconciliation '
            f'check: {type(exc).__name__}: {exc}') from exc
    finally:
        for wbk in (dwb, awb):
            try:
                if wbk is not None:
                    wbk.Close(SaveChanges=False)
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

    notes.append("PROPOSAL BENCHMARK own-project cells are formulas into '1. Summary' — this "
                 'confirms none has broken (#REF!, wrong cell); the client sheet has nothing past '
                 'column B; the analysis carries one evaluable projection per rated comparable.')
    return (len(differences) == 0), rows, differences, notes


# '1. Summary' PART-1 rows this check reconciles against '2. Budget-Management Fund' — mirrors
# generate_project_budget._SUMMARY_PART1, recorded here independently (the same way
# _BENCHMARK_RECONCILE above is its own contract) so this check notices if the generator's own
# table drifts from what it actually wrote, rather than agreeing with it by construction. matcher
# 'X' = any fund code starting with X; '=X' = exactly X. Change reconcile-summary-with-detail-sheets.
_SUMMARY_RECONCILE_ROWS = [
    (14, 'RM',    ('RM.',)),
    (15, 'RPa',   ('RP1', 'RP2', 'RP3')),
    (18, 'RO',    ('RO',)),
    (19, 'RI',    ('RI',)),
    (22, 'EMH',   ('EMH',)),
    (23, 'EMA',   ('EMA',)),
    (24, 'EMB',   ('EMB',)),
    (27, 'ESC',   ('ESC',)),
    (29, 'ESS1',  ('=ESS1',)),
    (30, 'ESS4',  ('=ESS4',)),
    # Was ('=ESS16',) — corrected 2026-09-21 (change complete-ai-guideline-remark-coverage). The
    # real formula (H31 = '2. Fund'!AK144 - H29 - H30) is "everything in the ESS section except
    # ESS1 (Security, its own row 29) and ESS4 (Cleaning, its own row 30)" — matching only ESS16
    # was an approximation that happened to total correctly only because every other code in that
    # bucket (including ESS9) was zero. Pricing ESS9 (waste collection) broke that coincidence and
    # surfaced this — see docs/05-decisions.md.
    (31, 'ESS16', ('ESS', '!=ESS1', '!=ESS4')),
    (32, 'ESI1',  ('ESI',)),
    (33, 'ESM',   ('ESM',)),
    (34, 'ESA6',  ('ESA', 'ESL')),
    (36, 'EN',    ('EN',)),
    (38, 'EEW',   ('EEW',)),
    (39, 'EEE',   ('EEE',)),
    (40, 'EED',   ('EED',)),
    (43, 'ER',    ('ER',)),
]
_FUND_LEAF_FIRST_ROW = 12
_FUND_LEAF_LAST_ROW = 494
_ERR_VALUES = {-2146826281, -2146826246, -2146826273, -2146826288, -2146826252, -2146826259}


def _fund_code_match(code, matchers):
    """'X' = code starts with X; '=X' = code equals X exactly; '!X'/'!=X' = the same two forms,
    but as an EXCLUSION that overrides any include below — added 2026-09-21 (change
    complete-ai-guideline-remark-coverage) for row 31 (see _SUMMARY_RECONCILE_ROWS): its real
    Excel formula is 'ESS section total - ESS1 - ESS4', not "ESS16 alone" as the matcher used to
    say, which just happened to produce the same total while every other ESS code was zero."""
    for m in matchers:
        if m.startswith('!'):
            excl = m[1:]
            if excl.startswith('='):
                if code == excl[1:]:
                    return False
            elif code.startswith(excl):
                return False
    for m in matchers:
        if m.startswith('!'):
            continue
        if m.startswith('='):
            if code == m[1:]:
                return True
        elif code.startswith(m):
            return True
    return False


def check_summary_reconciles(paths):
    """Confirm '1. Summary' ties to '2. Budget-Management Fund' end to end (change
    reconcile-summary-with-detail-sheets, design D5):

      (a) every PART-1 code's 'H' total on Summary == the sum of 'AK' over the fund leaves that
          roll up into it (matched the same way _compose_summary_narratives matches them);
      (b) every fund leaf row's own 'G' (Total Price) == 'AK' (=SUM(AQ:BB), what Summary reads);
      (c) H46 == H13 - H20, and H54 == H46 - H48 (the surplus derivation);
      (d) EMH (H22) == 'A1. Staff cost 08.2026 (VN)'!AC96 + the top-up baked into EMH2's own
          formula string (row 83, col F) — read back from the formula text, not re-derived, so
          this fails loudly if that formula ever stops matching the shape the pipeline writes —
          PLUS every other EMH-family leaf's own G (EMH4's PCCC allowance since change
          fill-guideline-required-line-items, 2026-09-14; EMH1/EMH3 are currently always zero but
          would count here too if either is ever priced) — the EMH *section* subtotal is EMH2's
          derivation plus whatever else in the family carries a real figure, not EMH2 alone;
      (e) the deliverable's own Excel-error-value cell count against a recorded ceiling
          (verification/baselines/error_cell_ceiling.json), which only ever ratchets down.

    Returns (ok, rows, differences, notes). Raises BaselineUnavailable if Excel cannot be driven.
    """
    import json
    import re
    import shutil
    import tempfile

    from verification.baseline import BaselineUnavailable

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            "The summary-reconciliation check requires Excel — '1. Summary' and '2. Budget-"
            f"Management Fund' both store these figures as live formulas ({exc}).") from exc

    tmp = tempfile.mkdtemp(prefix='summary_recon_')
    dwork = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], dwork)

    def _num(v):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def _tol(v):
        return max(5_000.0, abs(v) * 5e-5)

    pythoncom.CoInitialize()
    xl = dwb = None
    rows, differences, notes = [], [], []
    error_cell_count = 0
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        dwb = xl.Workbooks.Open(dwork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {ws.Name: ws for ws in dwb.Worksheets}
        fund_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('2. Budget-Management Fund')), None)
        sum_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('1. Summary')), None)
        a1_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('A1. Staff cost 08.2026 (VN)')), None)
        if fund_ws is None or sum_ws is None or a1_ws is None:
            raise RuntimeError("deliverable is missing '2. Budget-Management Fund', '1. Summary', "
                                "or 'A1. Staff cost 08.2026 (VN)'")

        # ---- read every fund row once: code (Y=25), G (7), AK (37), and whether G is a section
        # SUBTOTAL rather than a leaf. Every section-header row's own G formula is
        # '=SUBTOTAL(9,G<first>:G<last>)'; every leaf row's is
        # '=IF($C<r>="Schedule",SUM(H<r>:S<r>),F<r>*E<r>)' — a structural signal read straight off
        # the template, not a guess at which code strings are "header" text (some families nest,
        # e.g. RO > RO2/RO3/RO4 > RO2a/RO2b, so a header's code is not always the summary's code).
        leaf_rows = []
        for r in range(_FUND_LEAF_FIRST_ROW, _FUND_LEAF_LAST_ROW + 1):
            code = fund_ws.Cells(r, 25).Value2
            if not (isinstance(code, str) and code.strip()):
                continue
            g = fund_ws.Cells(r, 7).Value2
            ak = fund_ws.Cells(r, 37).Value2
            g_formula = str(fund_ws.Cells(r, 7).Formula or '')
            is_header = 'SUBTOTAL' in g_formula.upper()
            leaf_rows.append((r, code.strip(), g, ak, is_header))

        # (b) every fund row (header subtotals included — they should agree with AK too): G vs AK
        for r, code, g, ak, _is_header in leaf_rows:
            gn, akn = _num(g), _num(ak)
            label = f"'2. Fund' row {r} ({code}) G vs AK"
            if gn is None or akn is None:
                continue   # an Excel error here is counted by the error-cell check (e), not this one
            rows.append((label, gn, akn))
            if abs(gn - akn) > _tol(max(abs(gn), abs(akn))):
                differences.append((label, gn, akn))

        # (a) every PART-1 code: Summary H vs sum of fund AK for its children — header/subtotal
        # rows excluded (their own AK already equals the sum of their descendants; including them
        # too would double-count).
        for srow, code, matchers in _SUMMARY_RECONCILE_ROWS:
            leaves = [(c, ak) for _r, c, _g, ak, is_header in leaf_rows
                      if _fund_code_match(c, matchers) and not is_header]
            child_ak_sum = sum(_num(ak) or 0.0 for _c, ak in leaves)
            summary_h = _num(sum_ws.Cells(srow, 8).Value2)
            label = f"'1. Summary'!H{srow} ({code}) vs fund children"
            rows.append((label, summary_h, child_ak_sum))
            if summary_h is None:
                differences.append((label, summary_h, child_ak_sum))
            elif abs(summary_h - child_ak_sum) > _tol(max(abs(summary_h), abs(child_ak_sum))):
                differences.append((label, summary_h, child_ak_sum))

        # (c) surplus derivation
        h13 = _num(sum_ws.Cells(13, 8).Value2)
        h20 = _num(sum_ws.Cells(20, 8).Value2)
        h46 = _num(sum_ws.Cells(46, 8).Value2)
        h48 = _num(sum_ws.Cells(48, 8).Value2)
        h54 = _num(sum_ws.Cells(54, 8).Value2)
        for label, left, right in [
            ('H46 vs H13-H20', h46, None if h13 is None or h20 is None else h13 - h20),
            ('H54 vs H46-H48', h54, None if h46 is None or h48 is None else h46 - h48),
        ]:
            rows.append((label, left, right))
            if left is None or right is None or abs(left - right) > _tol(max(abs(left), abs(right))):
                differences.append((label, left, right))

        # (d) EMH vs A1's own grand total + top-up. A1's total is found by its own "Total cost/
        # year ... Savills" label (design D5) rather than a bare 'AC96' reference: the pipeline's
        # EMH2 formula (D2) itself hardcodes that cell, so if A1 is ever reshaped, an independent
        # label-based read here is what actually catches the drift — a bare-cell read on both sides
        # would agree by construction even while pointing at the wrong cell.
        a1_total = None
        a1_used = a1_ws.UsedRange
        for rr in range(1, a1_used.Row + a1_used.Rows.Count):
            for cc in range(1, min(a1_used.Column + a1_used.Columns.Count, 40)):
                txt = a1_ws.Cells(rr, cc).Value2
                if not isinstance(txt, str):
                    continue
                low = txt.lower()
                if 'total cost' in low and 'year' in low and 'savills' in low:
                    for offset in range(1, 8):
                        v = _num(a1_ws.Cells(rr, cc + offset).Value2)
                        if v is not None:
                            a1_total = v
                            break
                    break
            if a1_total is not None:
                break
        # Top-up: EMH2's formula references A1's own unplaced-position row(s) LIVE — e.g.
        # "...AC96+SUM('A1...'!AC98:AC99)*12)/12" (2+ rows), "...AC96+'A1...'!AC98*12)/12" (1 row),
        # or a bare "...AC96/12" when every position has a row-group (no top-up at all). Read
        # those cells' actual values via COM rather than assuming a constant, so this
        # independently verifies what the formula computes, not just that it parses. A legacy
        # "AC96+<number>" constant (pre this row-based design) is still accepted for robustness.
        emh2_formula = str(fund_ws.Cells(83, 6).Formula or '')
        # docs/32 (2026-10-20): the adjustment sheet wraps a fund cell that was already a formula as
        # "=(<old formula>)*IF('4. Điều chỉnh'!$I$r=0,1,'4. Điều chỉnh'!$M$r/'4. Điều chỉnh'!$I$r)"; the
        # top-up is read from the old formula inside the wrap.
        unwrapped = unwrap_adjustment_formula(emh2_formula)
        if unwrapped != emh2_formula:
            notes.append("EMH2's formula (row 83, col F) is wrapped by '4. Điều chỉnh'; the wrap was removed before "
                         'reading the top-up')
            emh2_formula = unwrapped
        # Existing-project mode (change carry-forward-staffing, design D8/D10): EMH2 either leaves
        # A1's night/holiday allowance (AC90) out because EMH3 carries it, or is the carried /
        # overridden amount itself (a number, no formula).
        allowance_out = re.search(r"AC96-'A1[^!]*'!AC90\*'A1[^!]*'!AC95", emh2_formula)
        emh2_is_amount = not emh2_formula.lstrip().startswith('=')
        top_up = None
        range_m = re.search(r"AC(\d+):AC(\d+)\)\*12", emh2_formula)
        single_m = re.search(r"!AC(\d+)\*12", emh2_formula)
        const_m = re.search(r"AC96\s*\+\s*(-?\d+(?:\.\d+)?)\)", emh2_formula)
        if range_m:
            r1, r2 = int(range_m.group(1)), int(range_m.group(2))
            top_up = sum(_num(a1_ws.Cells(r, 29).Value2) or 0.0 for r in range(r1, r2 + 1)) * 12
        elif single_m:
            top_up = (_num(a1_ws.Cells(int(single_m.group(1)), 29).Value2) or 0.0) * 12
        elif const_m:
            top_up = float(const_m.group(1))
        elif re.search(r"=\s*'A1[^!]*'!AC96/12\s*$", emh2_formula.strip()):
            top_up = 0.0
        elif allowance_out and re.search(r"AC95\)/12\s*$", emh2_formula.strip()):
            top_up = 0.0          # =(AC96-AC90*AC95)/12: no unplaced rows (group 5, D5)
        # EMH2's own derivation (a1_total + top_up) is only PART of the EMH section once any other
        # EMH-family code carries a real figure of its own (EMH4 — PCCC allowance — since change
        # fill-guideline-required-line-items, 2026-09-14). Add every other EMH leaf's own G from
        # the already-scanned `leaf_rows` — this is what makes the assertion track H22 correctly
        # if EMH1/EMH3 (both currently zero-by-design) are ever priced too, not just EMH4 today.
        other_emh_total = sum(
            g for r, code, g, ak, is_header in leaf_rows
            if code != 'EMH2' and code.startswith('EMH') and not is_header and isinstance(g, (int, float))
        )
        h22 = _num(sum_ws.Cells(22, 8).Value2)
        label = "'1. Summary'!H22 (EMH) vs A1!AC96 + top-up + other EMH-family leaves"
        if allowance_out and a1_total is not None:
            a1_total -= (_num(a1_ws.Cells(90, 29).Value2) or 0.0) * (_num(a1_ws.Cells(95, 29).Value2) or 0.0)
            label = "'1. Summary'!H22 (EMH) vs A1!AC96 - allowance (in EMH3) + top-up + other EMH leaves"
        if emh2_is_amount:
            a1_total = next((g for r, code, g, ak, is_header in leaf_rows
                             if code == 'EMH2' and not is_header and isinstance(g, (int, float))), None)
            top_up = 0.0
            label = "'1. Summary'!H22 (EMH) vs EMH2 carried amount + other EMH-family leaves"
        if a1_total is None or top_up is None:
            rows.append((label, h22, None))
            differences.append((label, h22, None))
            notes.append(f"could not parse EMH2's formula for a top-up figure: {emh2_formula!r}")
        else:
            expected = a1_total + top_up + other_emh_total
            rows.append((label, h22, expected))
            if h22 is None or abs(h22 - expected) > _tol(max(abs(h22), abs(expected))):
                differences.append((label, h22, expected))

        # (e) error-cell count across the whole deliverable
        for ws in dwb.Worksheets:
            vals = ws.UsedRange.Value2
            if vals is None:
                continue
            rvals = (vals if isinstance(vals, tuple) and vals and isinstance(vals[0], tuple)
                     else ((vals,) if not isinstance(vals, tuple) else (vals,)))
            for row in rvals:
                if not isinstance(row, tuple):
                    row = (row,)
                for v in row:
                    if isinstance(v, int) and v in _ERR_VALUES:
                        error_cell_count += 1

        dwb.Close(SaveChanges=False)
        dwb = None
    except Exception as exc:
        raise BaselineUnavailable(
            'Excel could not evaluate the deliverable for the summary-reconciliation check: '
            f'{type(exc).__name__}: {exc}') from exc
    finally:
        try:
            if dwb is not None:
                dwb.Close(SaveChanges=False)
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

    ceiling_path = os.path.join(os.path.dirname(__file__), 'baselines', 'error_cell_ceiling.json')
    ceiling = None
    if os.path.exists(ceiling_path):
        with open(ceiling_path, encoding='utf-8') as f:
            ceiling = json.load(f).get('deliverable_error_cells')
    label = f'deliverable error-cell count ({error_cell_count}) vs recorded ceiling'
    rows.append((label, error_cell_count, ceiling))
    if ceiling is None:
        differences.append((label, error_cell_count, ceiling))
        notes.append(f'no recorded ceiling at {ceiling_path} — write {{"deliverable_error_cells": N}} '
                     'there (see task 4.3) to set the initial ceiling')
    elif error_cell_count > ceiling:
        differences.append((label, error_cell_count, ceiling))

    notes.append("EMH2's formula string is the source of truth for its top-up — this check reads "
                 "it back rather than recomputing it, so it fails loudly if the pipeline's formula "
                 'shape ever changes without this check being updated too.')
    return (len(differences) == 0), rows, differences, notes


# Recipe-driven '1. Summary' rows: tokens that MUST appear in the composed K narrative. This is a
# "presence of parts" check (design.md D5 / the change's risk note) — not exact phrasing, which the
# Head of PM reviews (tasks.md 5.2). Keyed by the summary code in generate_project_budget._SUMMARY_PART1.
_REMARK_RECIPE_ANCHORS = {
    'RM':   ['m2', '/m2/', 'lấp đầy cư dân'],
    'RPa':  ['lấp đầy bãi xe'],
    'RI':   ['Common area Fund'],
    'EMH':  ['Công Ty Quản lý', 'A1. Staff cost', 'A5'],
    'ESS1': ['vị trí', 'A2. Bảo vệ'],
    'ESS4': ['vệ sinh', 'A3. Vệ sinh'],
    'EN':   ['khấu hao', '24 tháng'],
    # Units are the Vietnamese labels (change explain-common-area-fund-zero-lines); 'kWh' alone
    # would also match the English "kWh/month", so EEE anchors on the full 'kWh/tháng'.
    'EEW':  ['m3/tháng', 'PBVMT', 'lấp đầy cư dân'],
    'EEE':  ['kWh/tháng', '1279', '40%'],
    'EED':  ['lít/tháng', 'DO 0,05S', 'test', 'backup'],
}

# A line-level remark naming any of these is citing an internal engineering artifact rather than
# explaining the figure in terms a client can act on (change localize-line-level-remarks, spec
# deliverable-remarks — "SHALL NOT name an internal source file or other engineering artifact").
# Matched as a plain substring, case-sensitive — these are proper names/extensions, not prose words
# that could collide with real remark text. '.md'/'docs/'/the change name cover task 5.1's own
# verification text (docs/14-required-line-item-gaps.md, complete-ai-guideline-remark-coverage),
# which '.csv'/'.py' alone would miss.
_INTERNAL_ARTIFACT_DENYLIST = [
    '.csv', '.py', '.md', 'docs/', 'Costing_Method_Catalogue', 'generate_project_budget',
    'estimate_opex', 'complete-ai-guideline-remark-coverage',
]

# Internal wording on ANY sheet of the client deliverable (change fix-deliverable-remark-wording,
# spec deliverable-remarks): the artifact names above plus the tool's own vocabulary, a function
# name, the language it is written in, change-process phrasing, the internal guideline's name,
# statistical shorthand, and the two placeholders the template ships. One list, one place.
_INTERNAL_WORDING_DENYLIST = _INTERNAL_ARTIFACT_DENYLIST + [
    'derive_', 'master_comparables', 'generate_project_output', 'Python', 'thay đổi này',
    'AI Guideline', 'n=1', 'demo', '[Lưu ý nội bộ',
]

# Cells whose text comes from Savills' standard form, not from this pipeline, and so may contain a
# word above. Listed explicitly, never by pattern. The scan compares each one with the template's own
# text, so a cell the pipeline overwrote cannot hide behind this list. Reported to the template owner
# (docs/23 A1, A2); not ours to edit. RP5's remark (T15, the form's "demo") is no longer here: the
# pipeline now writes its own reason there (change fix-verify-hand-check-and-rp5-remark), so the
# cell is scanned like any other pipeline remark.
_TEMPLATE_OWNED_TEXT_CELLS = {
    ('2.2 Common area Fund', 'T460'),     # VAT1  "[Lưu ý nội bộ: ...]"
    ('2.2 Common area Fund', 'T461'),     # VAT2
    ('2.2 Common area Fund', 'T462'),     # CIT1
    ('2.2 Common area Fund', 'T463'),     # CIT1a
    ('2.2 Common area Fund', 'T464'),     # CIT1b
    ('2.2 Common area Fund', 'T465'),     # CIT2
}


# Other projects' names (decision D3: the client deliverable names no other project; change
# apply-head-of-pm-decisions-2026-10, task 9.3). The list is built from the data each run, never written into the
# repo: (data file under Budget_Agent/data, name column). A name made only of these generic words is left out, since it
# would match ordinary text (the user's choice, 2026-10-19).
_PROJECT_NAME_SOURCES = (
    ('master_list_verified/Dim_Property_Residential.csv', 'Name'),
    ('master_list_verified/Dim_Property_Commercial.csv', 'Name'),
    ('master_list_verified/Fact_ProjectLocation.csv', 'asset_name'),
    ('master_list_verified/Ref_ComparableVATBasis.csv', 'project_key'),
    ('generation_A_star_schema/Dim_Project.csv', 'ProjectName'),
    ('generation_A_star_schema/Fact_OPEX.csv', 'Project'),
    ('generation_A_star_schema/Fact_Capex_Rescanned.csv', 'Project'),
    ('generation_A_star_schema/Fact_CapexReserve.csv', 'Project'),
    ('generation_B_verified/Dim_Property_v2_verified.csv', 'ProjectName'),
)
_GENERIC_NAME_WORDS = {'parking', 'building', 'tower', 'towers', 'block', 'residence', 'residences', 'apartment',
                       'apartments', 'project', 'office', 'area', 'lot', 'house', 'the', 'and'}
_MIN_NAME_LENGTH = 4


def _norm_name_text(s):
    return ' '.join(unicodedata.normalize('NFC', str(s)).casefold().split())


def project_names_from_data(data_dir=None):
    """Every project name the reference data carries (the comparables' master list, the hand-verified comparables,
    locations, VAT bases, the cost and capital-expenditure tables), normalised (NFC, case-folded, single spaces).
    Names shorter than four characters, and names made only of generic words, are left out."""
    import csv
    data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                        'data')
    raw = set()
    for rel, col in _PROJECT_NAME_SOURCES:
        try:
            with open(os.path.join(data_dir, *rel.split('/')), encoding='utf-8-sig') as fh:
                for rec in csv.DictReader(ln for ln in fh if not ln.startswith('#')):
                    if rec.get(col):
                        raw.add(rec[col])
        except OSError:
            continue
    try:
        import master_comparables
        raw.update(c['name'] for c in master_comparables.HAND_VERIFIED_COMPARABLES if c.get('name'))
    except Exception:
        pass
    names = set()
    for n in raw:
        n = _norm_name_text(n)
        words = re.findall(r'\w+', n)
        if len(n) >= _MIN_NAME_LENGTH and words and not all(w in _GENERIC_NAME_WORDS for w in words):
            names.add(n)
    return names


def _other_project_pattern(names, own_name):
    """One word-bounded pattern over `names`, minus this project's own name (either contains the other)."""
    own = _norm_name_text(own_name or '')
    keep = sorted((n for n in names if not (own and (n in own or own in n))), key=len, reverse=True)
    if not keep:
        return None
    return re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(n) for n in keep) + r')(?!\w)')


def scan_internal_wording(wb, template_wb=None, project_names=None, own_name=None):
    """Scan every text cell of every sheet of `wb` (the generated client deliverable) for
    `_INTERNAL_WORDING_DENYLIST`, and every text and formula cell for another project's name from `project_names`
    (normalised, project_names_from_data) other than `own_name`. Returns (cells_scanned, exempt_cells, failures)
    where failures are (sheet, coordinate, reason). The word list skips formula cells; a text cell that merely starts
    with "=" (many remarks do) is still text and is scanned.
    """
    pattern = _other_project_pattern(project_names or (), own_name)
    scanned, hits, name_hits = 0, [], []
    for ws in wb.worksheets:
        for row in ws.iter_rows(max_col=min(ws.max_column, 120)):
            for c in row:
                v = c.value
                if not isinstance(v, str) or not v.strip():
                    continue
                if pattern is not None:
                    m = pattern.search(_norm_name_text(v))
                    if m:
                        name_hits.append((ws.title, c.coordinate, 'formula' if c.data_type == 'f' else 'text'))
                if c.data_type == 'f':
                    continue
                scanned += 1
                word = next((w for w in _INTERNAL_WORDING_DENYLIST if w in v), None)
                if word:
                    hits.append((ws.title, c.coordinate, word, v))
    failures, exempt = [], []
    for sheet, coord, where in name_hits:
        # The name itself is not repeated in the report: the run log and verify output stay free of it too.
        failures.append((sheet, coord, f"another project's name in client-facing {where}"))
    for sheet, coord, word, text in hits:
        if (sheet, coord) not in _TEMPLATE_OWNED_TEXT_CELLS:
            failures.append((sheet, coord, f'internal wording {word!r} in client-facing text'))
            continue
        if template_wb is not None and template_wb[sheet][coord].value != text:
            failures.append((sheet, coord, 'exempt template cell differs from the template'))
            continue
        exempt.append((sheet, coord))
    return scanned, exempt, failures

# Template-authored T-cell content this pipeline never writes to and must not edit (the project's
# standing "keep the template file" boundary) — an EXCLUSION list, not an inclusion list. The
# comprehensive T-remark loop below scans every non-blank coded row on both fund sheets by DEFAULT
# and skips only these; a genuinely new template note, or a future pipeline regression that starts
# touching one of these rows, still gets scanned rather than silently agreeing with whatever the
# pipeline currently claims to own (the same reason EXPECTED_SHEETS above is a hardcoded contract,
# not read from the template). Two earlier designs failed here and are deliberately not repeated:
# "non-blank + has a code" (caught these 11 template-default rows as false positives) and "T starts
# with '=' or 'Để ở mức 0:'" (silently missed most pipeline-written rows instead, because
# generate_project_output._fix_fake_formula_strings strips a leading '=' from any matching cell late
# in the pipeline — so the prefix this dict's own writers use in source is gone by the time this
# check reads the deliverable).
#
# Recorded 2026-09-15 (change localize-line-level-remarks) by scanning every non-blank coded T cell
# on both fund sheets with NO exclusions at all and checking each against every rule below (VAT
# sentence, Vietnamese content, denylist) — these 11 were the only rows that failed, and every one
# was confirmed template-owned by its F/G columns: F is either blank or a template-native absolute-
# reference formula (e.g. '=$AH$456*10%'), and G is always the template's own pass-through formula
# (IF($C=...,SUM(...),F*E) or SUBTOTAL) — never a literal value, which is what every pipeline write
# looks like. Re-run scripts/scratchpad `g6_full_scan2.py`'s method (no filtering, check all three
# rules, inspect F/G on anything that fails) if the template changes and this set needs revisiting.
_TEMPLATE_OWNED_T_ROWS = {
    ('2. Budget-Management Fund', 'ESA6'),   # elevator maintenance-fund guidance, already Vietnamese
    ('2. Budget-Management Fund', 'ESA11'),  # equipment maintenance-fund guidance, already Vietnamese
    ('2. Budget-Management Fund', 'ESA12'),  # equipment maintenance-fund guidance, already Vietnamese
    ('2. Budget-Management Fund', 'ESA16'),  # water-meter maintenance-fund guidance, already Vietnamese
    # RP5 ("demo") was the 11th row here until change fix-verify-hand-check-and-rp5-remark: the
    # pipeline now writes RP5's own reason, so that row is scanned like the rest.
    ('2.2 Common area Fund', 'VAT1'),        # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'VAT2'),        # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT1'),        # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT1a'),       # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT1b'),       # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT2'),        # "[Lưu ý nội bộ: ...]" internal accounting note
}


# Required parts of the Existing-project EEE / EEW summary narrative (existing_utilities.narrative_vi).
_EXISTING_UTILITY_ANCHORS = {'EEE': ['kWh/tháng', 'đ/kWh', 'x 12 tháng'], 'EEW': ['m3/tháng', 'đ/m3', 'x 12 tháng']}


def k14_revenue_sentence_problem(k, year, vat_vi):
    """None when the '1. Summary' K14 fee narrative ends with "Doanh thu hạng mục này dự ước tại năm <year>." and does
    not carry the generic VAT sentence (Head of PM decision K14-a, change apply-head-of-pm-decisions-2026-10, group 7);
    else what is wrong. The rates in the narrative state their own VAT basis, so the generic sentence is not wanted."""
    import operating_inputs
    if not k.rstrip().endswith(operating_inputs.entered_rate_year_vi(year)):
        return 'the management-fee narrative must end with the revenue sentence (decision K14-a)'
    if vat_vi and vat_vi in k:
        return 'the management-fee narrative carries the generic VAT sentence (decision K14-a)'
    return None


def check_remark_content(paths):
    """Confirm the client deliverable's remarks say what the AI Guideline instructs (change
    apply-guideline-remark-model). For the generated deliverable:

      1. every non-zero PART-1 total on '1. Summary' has a composed K narrative;
      2. an aggregate total's narrative names every child line the pipeline gave a figure;
      3. a recipe-driven total's narrative carries each part its catalogue recipe lists
         (presence of parts — anchor tokens above — not exact phrasing);
      4. on an inclusive-of-VAT run the VAT-treatment sentence is in every non-empty composed K
         cell and in every non-blank `T` remark on both fund sheets;
      5. each composed K narrative is Vietnamese (2026-09-11, user direction — no English);
      6. every non-blank line-level `T` remark on '2. Budget-Management Fund' and '2.2 Common area
         Fund' is Vietnamese, not just the sampled few (change localize-line-level-remarks,
         2026-09-15 — was English throughout, checked against 8 rows of one sheet only);
      7. no line-level `T` remark names an internal source file or engineering artifact
         (`_INTERNAL_ARTIFACT_DENYLIST`) — a client reads this column, not an engineer.

    Read with openpyxl, not COM: every cell this inspects — the composed K text, the line `T`
    remarks, and the fund leaves the pipeline filled (C / F / H:S / Y / Z) — is a literal the
    pipeline wrote, so Excel evaluation adds nothing. "Non-zero PART-1 total" is read from the same
    written-leaf set the composer used (generate_project_budget._collect_written), which is exactly
    the composer's own contract: it must compose for everything it funded. A broken '1. Summary'
    VLOOKUP that zeroes a funded row is a *figure* fault owned by check_summary_reconciles, not here.

    Returns (ok, rows, differences, notes) — `rows` is [(label, status)], `differences` the failures.
    """
    import openpyxl
    from generate_project_budget import (
        _SUMMARY_PART1, _SUMMARY_K_COL, _collect_written, _catalogue_vat_rule, _budget_year,
        _ACCREDITATION_SENTENCE, _children_for,
    )

    wb = openpyxl.load_workbook(paths['deliverable'], data_only=False)
    # Existing-project utilities run: the analysis workbook carries the Utility Bridge.
    import existing_utilities
    existing_utilities_run = bool(paths.get('analysis')) and (
        existing_utilities.BRIDGE_SHEET in _sheet_names(paths['analysis']))
    summ = wb['1. Summary']
    fund = wb['2. Budget-Management Fund']
    common_fund = wb['2.2 Common area Fund']

    written = _collect_written(wb)
    common_area_active = any(c in written for c in ('RA1.A', 'RA2'))
    year = _budget_year(wb, None)
    _sheet, _cell, vi_tmpl = _catalogue_vat_rule()
    switch = ' '.join(str(fund['F7'].value or '').split()).upper()
    incl_vat = switch != 'KHOÁN'
    vat_vi = vi_tmpl.replace('<year>', year)

    rows, differences, notes = [], [], []

    def fail(label, msg):
        differences.append((label, msg))
        rows.append((label, f'FAIL — {msg}'))

    def ok(label):
        rows.append((label, 'ok'))

    for srow, kind, code, prefixes in _SUMMARY_PART1:
        children = _children_for(prefixes, written)
        expected = bool(children) or (code == 'RI' and common_area_active)
        k = summ.cell(row=srow, column=_SUMMARY_K_COL).value
        k = k if isinstance(k, str) else ''
        label = f"1. Summary K{srow} ({code})"

        if not expected:
            continue
        if not k.strip() or k.lstrip().startswith('='):
            fail(label, 'non-zero PART-1 total has no composed narrative (K blank or a formula pull)')
            continue

        # Vietnamese only (2026-09-11, user direction) — a diacritic marker confirms it wasn't left
        # as English or blank-of-content; it does not require any particular phrasing.
        has_vi = any(ch in k for ch in 'ạảấầẩẫậắằẳẵặẹẻẽếềểễệọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ')
        if not has_vi:
            fail(label, 'narrative has no Vietnamese content')

        # VAT sentence. K14 (management-fee revenue) ends with the revenue sentence instead, on every run (K14-a).
        if code == 'RM':
            problem = k14_revenue_sentence_problem(k, year, vat_vi)
            if problem:
                fail(label, problem)
        elif incl_vat and vat_vi not in k:
            fail(label, 'inclusive-of-VAT run but the K narrative has no VAT-treatment sentence')

        if kind == 'rollup':
            missing = [w['name_vi'] for _c, w in children if w['name_vi'] not in k and w['name_en'] not in k]
            if missing:
                fail(label, f'aggregate narrative omits funded child line(s): {", ".join(missing)}')
            else:
                ok(label)
            if srow == 34 and _ACCREDITATION_SENTENCE not in k:
                fail(label, 'accreditation narrative is missing the fixed Điều 150 Luật Nhà ở 2023 sentence')
        else:  # recipe
            anchors = _REMARK_RECIPE_ANCHORS.get(code, [])
            if existing_utilities_run and code in _EXISTING_UTILITY_ANCHORS:
                # Existing-project EEE/EEW (change carry-forward-common-utilities): the project's own actual
                # consumption, so the new-building parts (fill-up curve, 40% floor, guideline price build-up)
                # are replaced, and the curve must not be described (spec occupancy-ramp).
                anchors = _EXISTING_UTILITY_ANCHORS[code]
                if 'lấp đầy' in k:
                    fail(label, 'Existing-project narrative still describes the fill-up curve')
            missing = [a for a in anchors if a not in k]
            if missing:
                fail(label, f'recipe narrative is missing required part(s): {", ".join(missing)}')
            else:
                ok(label)

    # ---- Line-level T remarks, EVERY non-blank cell on BOTH fund sheets (change
    # localize-line-level-remarks, 2026-09-15 — was a same-sheet 8-row VAT-only sample; the new
    # scope is comprehensive on both sheets and also checks Vietnamese content and internal-filename
    # leakage, so this replaces rather than supplements the old sample). Read by CODE + T column
    # directly, not through `written` — `written` is the composer's funded-lines contract (non-zero
    # figures only), so it never includes the ~26 flagged-zero disclosure remarks (EMH1 when unset,
    # RP3, ESC1, ...), which are exactly the remarks most likely to regress to English since nothing
    # else exercises them. In scope by default; `_TEMPLATE_OWNED_T_ROWS` above is the only exclusion.
    #
    # All three rules run independently per row (no short-circuit) so a row that is wrong two ways
    # reports both, the same pattern the '1. Summary' K-cell loop above already uses.
    for sheet_label, sheet in (('2. Budget-Management Fund', fund), ('2.2 Common area Fund', common_fund)):
        for r in range(1, sheet.max_row + 1):
            code = sheet.cell(row=r, column=25).value
            code = code.strip() if isinstance(code, str) else code
            # A real leaf code never contains a newline; the header row's own code CELL literally
            # holds "CODE\nMã" (the template's two-line column heading) and would otherwise read as
            # a truthy, non-blank "code" and get scanned as if it were a cost line.
            if not code or not isinstance(code, str) or '\n' in code:
                continue
            if (sheet_label, code) in _TEMPLATE_OWNED_T_ROWS:
                continue
            t = sheet.cell(row=r, column=20).value
            t = t if isinstance(t, str) else ''
            if not t.strip():
                continue
            label = f"{sheet_label} T{r} ({code})"

            row_failed = False
            # Change price-fee-and-parking-from-portfolio (spec deliverable-remarks): a revenue unit rate names its
            # source — the portfolio median (with the number of Savills-managed projects), the PM's entered figure,
            # the PM's recorded revenue, or the reference-project fallback — and never a project.
            if sheet_label == '2. Budget-Management Fund' and code in ('RM.AP', 'RP1', 'RP2'):
                if not any(w in t for w in ('trung vị', 'PM nhập', 'PM ghi nhận', 'dự án tham chiếu', 'DỰ PHÒNG')):
                    fail(label, 'revenue unit rate states no source (portfolio median, PM figure or reference fallback)')
                    row_failed = True
                if 'trung vị' in t and 'dự án do Savills quản lý' not in t:
                    fail(label, 'portfolio-median wording must give the number of Savills-managed projects')
                    row_failed = True
            entered_rate_line = 'thực tế do PM nhập' in t and code.startswith('RM.')
            if entered_rate_line:
                # W3 (2026-10-11): a line priced from an entered rate states its own VAT basis and ends
                # with the revenue sentence; the generic "Chi phí … đã bao gồm VAT" must not follow it.
                if 'Doanh thu hạng mục này dự ước tại năm' not in t or vat_vi in t:
                    fail(label, 'entered-rate line must end with the revenue sentence and not the generic '
                                'VAT sentence')
                    row_failed = True
            elif incl_vat and vat_vi not in t:
                fail(label, 'inclusive-of-VAT run but this written T remark has no VAT-treatment sentence')
                row_failed = True
            t_has_vi = any(ch in t for ch in 'ạảấầẩẫậắằẳẵặẹẻẽếềểễệọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ')
            if not t_has_vi:
                fail(label, 'line-level remark has no Vietnamese content')
                row_failed = True
            # Internal wording is no longer checked here: scan_internal_wording() below covers this
            # column and every other text cell of every sheet.
            if not row_failed:
                ok(label)

    # ---- Internal wording, every text cell of every sheet (change fix-deliverable-remark-wording).
    # The template is loaded to confirm each exempt cell still holds the template's own text.
    import openpyxl as _opx
    template_wb = _opx.load_workbook(_template_path(), data_only=False)
    scanned, exempt_cells, wording_failures = scan_internal_wording(
        wb, template_wb, project_names_from_data(), wb['2. Budget-Management Fund']['AH5'].value)
    for sheet, coord, reason in wording_failures:
        fail(f"{sheet}!{coord}", reason)
    if not wording_failures:
        ok('whole-workbook internal-wording scan')
    notes.append(f"internal-wording scan: {scanned:,} text cells on {len(wb.worksheets)} sheets, "
                 f"{len(exempt_cells)} exempt template cell(s)")

    # ---- '0. Info' per-product area-basis remark (change complete-ai-guideline-remark-coverage) ----
    # Recorded independently, matching generate_project_budget.py's own local `_INFO_FEE_ROWS` — not
    # imported, so a template reshape there is caught here too, not silently agreed with.
    _INFO_FEE_ROWS = {'Apartment': 8, 'Officetel': 9, 'Office': 10, 'Shophouse': 11}
    info = wb['0. Info']
    for prod, r in _INFO_FEE_ROWS.items():
        nfa = info.cell(row=r, column=4).value      # D = NFA, written only when the product is priced
        if not nfa:
            continue
        label = f"0. Info!G{r} ({prod})"
        g = info.cell(row=r, column=7).value         # G = 'Ghi chú' remark
        if not (isinstance(g, str) and g.strip()):
            fail(label, 'priced product has no area-basis remark')
        else:
            ok(label)

    # ---- ESS9 (B2.6 / waste-collection-costing track, change complete-ai-guideline-remark-
    # coverage): a real figure must not appear without its remark. Recorded independently, matching
    # generate_project_budget.py's own MGMT_FUND_ROWS['waste_collection'] — not imported, so a
    # template reshape there is caught here too, not silently agreed with. ----
    _ess9_row = 153
    _ess9_code = fund.cell(row=_ess9_row, column=25).value
    _ess9_code = _ess9_code.strip() if isinstance(_ess9_code, str) else _ess9_code
    if _ess9_code == 'ESS9':
        # The months are literals the pipeline wrote directly — G is a formula over them, unevaluated under
        # this function's own data_only=False load (see the docstring above) — or, once '4. Điều chỉnh' has
        # linked them, the originals that sheet holds (fund_months_as_written).
        _ess9_year = sum(fund_months_as_written(wb, '2. Budget-Management Fund', _ess9_row))
        if abs(_ess9_year) >= 1:
            label = f"2. Budget-Management Fund T{_ess9_row} (ESS9)"
            _ess9_t = fund.cell(row=_ess9_row, column=20).value
            if not (isinstance(_ess9_t, str) and _ess9_t.strip()):
                fail(label, 'priced waste-collection line has no remark')
            else:
                ok(label)

    # ---- 'A2'/'A3' canonical position descriptions still present (design.md D2 — the template
    # ships these itself; the pipeline neither writes nor should need to write them, so the only
    # real risk is a future Savills template revision silently dropping one). ----
    # verification/checks.py -> verification/ -> source_code/ -> Budget_Agent/ (same depth
    # generate_project_budget.py's own BUDGET_AGENT constant resolves to).
    _budget_agent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    canon_path = os.path.join(_budget_agent_dir, 'data', 'master_list_verified',
                              'AI_Guideline_Canonical_Positions.csv')
    _CANON_SHEET_COL = {'Security': ('A2. Bảo vệ - Security', 9), 'Cleaning': ('A3. Vệ sinh - Cleaning', 12)}
    try:
        with open(canon_path, encoding='utf-8-sig') as f:
            canon_lines = [ln for ln in f if not ln.startswith('#')]
        import csv as _csv
        canon_rows = list(_csv.DictReader(canon_lines))
    except OSError:
        canon_rows = []
        notes.append(f'canonical-position reference not found at {canon_path!r} — A2/A3 check skipped')
    for crow in canon_rows:
        cat = crow['category']
        sheet_name, col = _CANON_SHEET_COL.get(cat, (None, None))
        if sheet_name is None or sheet_name not in wb.sheetnames:
            continue
        r = int(crow['row'])
        label = f"{sheet_name}!row {r} ({cat} {crow['code']} {crow['name_en'] or crow['name_vi']})"
        val = wb[sheet_name].cell(row=r, column=col).value
        if not (isinstance(val, str) and val.strip()):
            fail(label, 'canonical position is missing its duty description')
        else:
            ok(label)

    # Unique labels, not row-entry counts: a label can now appear more than once in `rows` (a cell
    # failing two ways reports both — see the T-remark loop above), so summing entries would inflate
    # these past the real number of narratives/remarks checked.
    composed = len({lbl for lbl, _s in rows if lbl.startswith('1. Summary K')})
    notes.append(f"VAT model (2. Budget-Management Fund!F7): {switch or '(blank)'} — "
                 f"{'inclusive' if incl_vat else 'exclusive'} of VAT; budget year {year}.")
    t_checked = len({lbl for lbl, _s in rows if ' T' in lbl and lbl.startswith('2.')})
    notes.append(f"{sum(1 for _l, s in rows if s == 'ok')} assertions passed across "
                 f"{composed} composed '1. Summary' narrative(s), {t_checked} line-level T remark(s) "
                 f"on both fund sheets, '0. Info' area-basis remarks, and {len(canon_rows)} "
                 f"canonical A2/A3 positions.")
    return (len(differences) == 0), rows, differences, notes


_REQUIRED_CLASSIFICATION_FUND_SHEETS = ('2. Budget-Management Fund', '2.2 Common area Fund')

# The sheet(s) a zero-with-no-reason Required code FAILs the run on. Both fund sheets since change
# explain-common-area-fund-zero-lines: each '2.2 Common area Fund' line that is a share of a zero
# '2. Budget-Management Fund' line now carries that line's own reason
# (generate_project_budget._write_common_area_zero_reasons), and EMA1-EMA4 are disclosed on '2.2''s
# own EMA15 line, as on '2. Fund'. Until then the 32 such '2.2' lines (EMH1, EMH3, EMA1-4, EMB1,
# EMB4, EMO2, EMO6, EM#, ESC1/2/4/5, ESS10/12/17/18/19/23, ESI1/2, ESM6/7/9/10/12/13, ESR, ES#,
# EE#) were correct zeros with no remark, so this sheet was only reported, not enforced.
_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS = ('2. Budget-Management Fund', '2.2 Common area Fund')

# EMA1-4 are Required but have no itemized comparable source anywhere in this repo (change
# fill-guideline-required-line-items, design D3, task 3.2) — they stay folded into EMA15's
# catch-all, and D3's own fallback puts the "stated reason" on EMA15's remark, not on EMA1-4's own
# (blank) remark cells. Recorded here as the one documented exception, not inferred at check time.
_REQUIRED_CODE_DISCLOSED_ON = {'EMA1': 'EMA15', 'EMA2': 'EMA15', 'EMA3': 'EMA15', 'EMA4': 'EMA15'}

# Remarks the standard form ships that explain nothing, so a zero Required line holding only one of
# these has NO stated reason: (sheet, code) -> the placeholder's exact text. Matched on the whole
# trimmed text of that one cell, never on the word, in the same spirit as the explicit cell lists
# above (change fix-verify-hand-check-and-rp5-remark). Until that change the check accepted RP5's
# "demo" as a reason and passed on a word that explains nothing.
_FORM_PLACEHOLDER_REMARKS = {('2.2 Common area Fund', 'RP5'): 'demo'}


def check_required_line_items(paths):
    """Confirm every code the AI Guideline classifies 'Bắt buộc/Required' on
    '2. Budget-Management Fund' or '2.2 Common area Fund' carries a non-zero figure, or a stated
    reason for staying zero (change fill-guideline-required-line-items, spec
    guideline-required-line-items; '2.2' enforced since explain-common-area-fund-zero-lines — see
    _REQUIRED_CLASSIFICATION_ENFORCED_SHEETS).

    Reads `data/master_list_verified/AI_Guideline_Required_Classification.csv` (task 1's own
    transcribed reference — NFC-normalised at extraction time, see that CSV's own header). For
    each Required leaf code on an enforced sheet (SUBTOTAL/header rows excluded, the same
    'SUBTOTAL' in the G-formula signal check_summary_reconciles uses):

      - non-zero G -> pass;
      - zero G, but the code's own T (Remarks) cell is non-empty -> pass (a stated reason), unless
        the text is exactly a form placeholder listed in _FORM_PLACEHOLDER_REMARKS (RP5's "demo"),
        which explains nothing and so counts as no reason;
      - zero G, and the code is one of EMA1-4 (see _REQUIRED_CODE_DISCLOSED_ON) -> check the named
        code's remark instead (EMA15's catch-all disclosure covers all four);
      - zero G with no remark anywhere applicable -> FAIL, naming the code.

    A Required code with no matching Y-column row on the deliverable at all (a template-version
    mismatch between the reference file and the live form) is reported as a note, not a failure.
    PL1/PL2/PL2CA/ERCS/ERCS1, listed here until 2026-10-04, were not mismatches: they sit below the
    fixed row cut-off this check used to stop at; it now scans each sheet's whole used range.

    Returns (ok, rows, differences, notes). Raises BaselineUnavailable if Excel cannot be driven or
    the reference CSV is missing (this check has nothing to verify against without it).
    """
    import csv
    import shutil
    import tempfile

    from verification.baseline import BaselineUnavailable

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            "The required-line-item check requires Excel — the fund sheets' G totals are live "
            f"formulas ({exc}).") from exc

    _budget_agent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ref_path = os.path.join(_budget_agent_dir, 'data', 'master_list_verified',
                             'AI_Guideline_Required_Classification.csv')
    try:
        with open(ref_path, encoding='utf-8-sig') as f:
            ref_lines = [ln for ln in f if not ln.startswith('#')]
        ref_rows = list(csv.DictReader(ref_lines))
    except OSError as exc:
        raise BaselineUnavailable(
            f"The required-line-item check needs {ref_path!r} (task 1's transcribed reference), "
            f"which is missing ({exc}).") from exc

    required = [r for r in ref_rows if r['requirement_level'] == 'Required'
                and r['sheet'] in _REQUIRED_CLASSIFICATION_FUND_SHEETS]

    tmp = tempfile.mkdtemp(prefix='required_lines_')
    dwork = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], dwork)

    pythoncom.CoInitialize()
    xl = dwb = None
    rows, differences, notes = [], [], []
    not_found = []
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        dwb = xl.Workbooks.Open(dwork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {_nfc(ws.Name): ws for ws in dwb.Worksheets}

        for sheet_name in _REQUIRED_CLASSIFICATION_FUND_SHEETS:
            ws = sheets.get(_nfc(sheet_name))
            if ws is None:
                notes.append(f"'{sheet_name}' not found on the deliverable — required-line-item "
                              f"check skipped for that sheet")
                continue
            # Whole used range. A fixed 495/300 cut-off hid PL2 ('2. Fund' r505) and ERCS/ERCS1/
            # PL1/PL2CA ('2.2' r440-466), which were then reported as "no matching row" although
            # they exist (found while enforcing '2.2', change explain-common-area-fund-zero-lines).
            maxr = ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1
            enforced = sheet_name in _REQUIRED_CLASSIFICATION_ENFORCED_SHEETS

            # one scan per sheet: row -> (code, G, T remark, is_header) — same structural signal
            # check_summary_reconciles uses for header vs leaf.
            by_code = {}
            for r in range(1, maxr + 1):
                code = ws.Cells(r, 25).Value2
                if not (isinstance(code, str) and code.strip()):
                    continue
                code = code.strip()
                g_formula = str(ws.Cells(r, 7).Formula or '')
                is_header = 'SUBTOTAL' in g_formula.upper()
                g = ws.Cells(r, 7).Value2
                t = ws.Cells(r, 20).Value2
                by_code[code] = (r, g, t, is_header)

            sheet_pending = []
            for rrow in [x for x in required if x['sheet'] == sheet_name]:
                code = rrow['code']
                info = by_code.get(code)
                label = f"'{sheet_name}' ({code})"
                if info is None:
                    not_found.append(label)
                    continue
                r, g, t, is_header = info
                if is_header:
                    continue  # section header / subtotal — not a leaf pricing target
                gn = g if isinstance(g, (int, float)) and not isinstance(g, bool) else None
                if gn is not None and abs(gn) > 0.5:
                    rows.append((label, 'ok — non-zero'))
                    continue

                # zero (or an Excel error, treated as zero here — check_summary_reconciles' §e
                # error-cell check is the one that owns Excel-error failures) — needs a stated
                # reason, either on this code's own remark or (EMA1-4) on the catch-all's.
                disclosed_on = _REQUIRED_CODE_DISCLOSED_ON.get(code)
                if disclosed_on:
                    disc_info = by_code.get(disclosed_on)
                    disc_t = disc_info[2] if disc_info else None
                    if isinstance(disc_t, str) and disc_t.strip():
                        rows.append((label, f'ok — zero, reason stated on {disclosed_on}'))
                    else:
                        msg = (f"zero with no reason stated on '{disclosed_on}' (its own "
                               f"designated disclosure row)")
                        if enforced:
                            differences.append((label, msg))
                            rows.append((label, 'FAIL — zero, no disclosure on its designated row'))
                        else:
                            sheet_pending.append(label)
                    continue

                is_placeholder = (isinstance(t, str)
                                  and _FORM_PLACEHOLDER_REMARKS.get((sheet_name, code)) == t.strip())
                if isinstance(t, str) and t.strip() and not is_placeholder:
                    rows.append((label, 'ok — zero, reason stated'))
                elif enforced:
                    if is_placeholder:
                        differences.append((label, "Required code is zero and its only remark is the "
                                                   "standard form's placeholder text"))
                        rows.append((label, 'FAIL — zero, only the form placeholder remark'))
                    else:
                        differences.append((label, 'Required code is zero with no stated reason'))
                        rows.append((label, 'FAIL — zero, no stated reason'))
                else:
                    sheet_pending.append(label)

            if sheet_pending:
                notes.append(
                    f"'{sheet_name}' — {len(sheet_pending)} Required code(s) zero with no stated "
                    f"reason, reported only (this sheet is not in "
                    f"_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS): "
                    f"{', '.join(c for c in sheet_pending)}")

        dwb.Close(SaveChanges=False)
    finally:
        try:
            if dwb is not None:
                dwb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            if xl is not None:
                xl.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()
        shutil.rmtree(tmp, ignore_errors=True)

    if not_found:
        notes.append(f"{len(not_found)} Required code(s) have no matching row on the deliverable "
                     f"(template-version mismatch, not this check's concern — see "
                     f"docs/14-required-line-item-gaps.md): {', '.join(not_found)}")
    notes.append(f"{len(required)} Required codes checked across "
                 f"{', '.join(_REQUIRED_CLASSIFICATION_FUND_SHEETS)}; "
                 f"{sum(1 for _l, s in rows if s.startswith('ok'))} pass, "
                 f"{len(differences)} fail, {len(not_found)} not found on this deliverable.")
    return (len(differences) == 0), rows, differences, notes


def check_sheets(paths, expected=None):
    """Assert every expected sheet is present in each workbook.

    Missing sheets are a failure, named individually. Unexpected extra sheets are reported but do
    not fail — an added sheet is a change worth seeing, while a dropped sheet is a regression.

    Returns a dict of {label: {'path','present','missing','unexpected'}}. Raises StructureError
    naming every missing sheet across all workbooks at once, so one run tells you everything that
    is wrong rather than only the first thing.
    """
    expected = expected or EXPECTED_SHEETS
    results = {}
    failures = []

    for label, want in expected.items():
        path = paths.get(label)
        if not path or not os.path.exists(path):
            failures.append(f'{label}: workbook not found at {path!r}')
            results[label] = {'path': path, 'present': [], 'missing': list(want), 'unexpected': []}
            continue

        actual = _sheet_names(path)
        actual_nfc = {_nfc(s) for s in actual}
        want_nfc = {_nfc(s) for s in want}
        missing = [s for s in want if _nfc(s) not in actual_nfc]
        unexpected = [s for s in actual if _nfc(s) not in want_nfc]
        results[label] = {
            'path': path, 'present': actual, 'missing': missing, 'unexpected': unexpected,
        }
        if missing:
            failures.append(
                f'{label} ({os.path.basename(path)}) is missing {len(missing)} of {len(want)} '
                f'expected sheet(s): ' + ', '.join(repr(s) for s in missing)
            )

    if failures:
        raise StructureError(
            'Generated workbooks are missing expected sheets:\n  - '
            + '\n  - '.join(failures)
            + '\nEither the pipeline stopped producing them, or the template was reshaped. If the '
              'template changed deliberately, update EXPECTED_SHEETS in verification/checks.py to '
              'match the new shape.'
        )
    return results


class CorruptionArtifact(RuntimeError):
    """Raised when a generated file carries something that triggers Excel's repair prompt."""


# Every artifact class below actually occurred in this project and reached delivered files. Each is
# checked at the zip/XML level rather than through openpyxl, because openpyxl silently repairs or
# ignores most of them on load — which is exactly why they went unnoticed the first time.
def scan_artifacts(path):
    """Return a list of human-readable corruption findings for one .xlsx. Empty means clean."""
    import re
    import zipfile

    findings = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()

        # 1. OneDrive / SharePoint sync injects these into files inside a synced folder. Excel
        #    reports "unreadable content" and offers to repair. Hit 3 delivered files this project.
        trash = [n for n in names if 'trash' in n.lower() or n.lower().endswith('.dat')]
        if trash:
            findings.append(
                f'{len(trash)} OneDrive-injected zip artifact(s): {trash[:5]}'
                + (' ...' if len(trash) > 5 else '')
            )

        # 2. Stale external links. A copied sheet can leave references to [1]'Sheet Name', which
        #    Excel reports as a broken link on open.
        ext = [n for n in names if n.startswith('xl/externalLinks/')]
        if ext:
            findings.append(f'{len(ext)} external-link part(s) present: {ext[:3]}')

        # 3. Prose written into a cell that begins with "=" is serialised as a real <f> formula.
        #    Excel then reports "Removed Records: Formula" and strips it. openpyxl writes "=foo" as
        #    <f>foo</f>, so prose like "= 1,234,567 VND x 12" lands as <f> 1,234,567 ...</f> —
        #    a formula whose body starts with whitespace, which no real formula ever does.
        for sheet_part in [n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml$', n)]:
            xml = z.read(sheet_part).decode('utf-8', errors='replace')
            fake = re.findall(r'<f[^>]*>(\s[^<]{0,60})', xml)
            if fake:
                findings.append(
                    f'{sheet_part}: {len(fake)} cell(s) hold prose in formula position, e.g. '
                    f'"={fake[0][:50]}..." — Excel will strip these on open'
                )
            if "[1]'" in xml:
                findings.append(f'{sheet_part}: contains a stale external reference [1]\'...\'')
    return findings


def check_artifacts(paths):
    """Assert no generated workbook carries a corruption artifact.

    Returns {label: []} on success. Raises CorruptionArtifact naming the affected file and what was
    found in it.
    """
    results = {}
    failures = []
    for label, path in paths.items():
        if not path or not os.path.exists(path):
            continue
        findings = scan_artifacts(path)
        results[label] = findings
        if findings:
            failures.append(
                f'{label} ({os.path.basename(path)}):\n      ' + '\n      '.join(findings)
            )
    if failures:
        raise CorruptionArtifact(
            'Generated files carry artifacts that make Excel prompt for repair:\n  - '
            + '\n  - '.join(failures)
            + '\nThe generators already strip OneDrive artifacts and fix prose-in-formula cells '
              '(see _strip_onedrive_zip_artifacts and _fix_fake_formula_strings). If this fires, '
              'either a new write path bypasses them or a new artifact class has appeared.'
        )
    return results


class FormulaError(RuntimeError):
    """Raised when a generated workbook contains cells resolving to an Excel error value."""


# The strings Excel shows for an error cell. #N/A is included deliberately: in this pipeline's
# outputs it has always indicated a broken lookup, not an intentional "not applicable".
EXCEL_ERROR_VALUES = {
    '#NULL!', '#DIV/0!', '#VALUE!', '#REF!', '#NAME?', '#NUM!', '#N/A',
    '#GETTING_DATA', '#SPILL!', '#CALC!', '#FIELD!', '#BLOCKED!', '#CONNECT!', '#UNKNOWN!',
}

METHOD_FULL = 'excel-recalculation'
METHOD_DEGRADED = 'cached-values-only'

# Excel returns an error cell through Value2 as one of these negative ints, not as a string.
# Verified empirically on this machine against Excel 16.0 by building a workbook with one of each.
ERROR_CODES = {
    -2146826288: '#NULL!',
    -2146826281: '#DIV/0!',
    -2146826273: '#VALUE!',
    -2146826265: '#REF!',
    -2146826259: '#NAME?',
    -2146826252: '#NUM!',
    -2146826246: '#N/A',
}


def _scan_errors_via_excel(path):
    """Open a COPY in Excel, force a full rebuild, and return every error cell.

    Returns a list of (sheet, address, displayed_text). Raises RuntimeError if Excel cannot be
    driven at all, so the caller can fall back and SAY that it fell back.

    Never opens the original file: Excel can rewrite a workbook merely by opening it, and these
    outputs are the thing under test.
    """
    import shutil
    import tempfile

    import pythoncom
    import win32com.client

    work = os.path.join(tempfile.mkdtemp(prefix='recalc_'), os.path.basename(path))
    shutil.copy(path, work)

    pythoncom.CoInitialize()
    xl = None
    wb = None
    errors = []
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        xl.AskToUpdateLinks = False
        # UpdateLinks=0 stops a stale external reference from blocking on a modal prompt.
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()

        from openpyxl.utils import get_column_letter

        # Read values rather than using SpecialCells(xlErrors). SpecialCells refuses to run on a
        # protected sheet, and 9 of the deliverable's 22 sheets are protected — using it would have
        # meant either modifying the workbook to unprotect it, or silently skipping those sheets.
        # Value2 reads fine on a protected sheet, returns the whole used range in one call, and
        # surfaces error cells as specific negative ints (verified empirically, see ERROR_CODES).
        for ws in wb.Worksheets:
            used = ws.UsedRange
            values = used.Value2
            if values is None:
                continue
            if not isinstance(values, tuple):          # single-cell used range
                values = ((values,),)
            elif values and not isinstance(values[0], tuple):
                values = (values,)

            r0, c0 = used.Row, used.Column
            for ri, row in enumerate(values):
                for ci, v in enumerate(row):
                    if isinstance(v, int) and v in ERROR_CODES:
                        addr = f'{get_column_letter(c0 + ci)}{r0 + ri}'
                        errors.append((ws.Name, addr, ERROR_CODES[v]))
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
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)
    return errors


def _scan_errors_via_openpyxl(path):
    """Weaker fallback: read the values Excel cached at write time.

    This CANNOT see an error that only appears once formulas are recalculated, which is the most
    common kind in this pipeline. Its result is not equivalent to the Excel path, and every caller
    must report which one ran.
    """
    import openpyxl
    errors = []
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    v = cell.value
                    if isinstance(v, str) and v.strip() in EXCEL_ERROR_VALUES:
                        errors.append((ws.title, cell.coordinate, v.strip()))
    finally:
        wb.close()
    return errors


def _template_path():
    """The template the pipeline itself reads.

    Imported from generate_project_budget rather than recomputed from __file__. Recomputing it here
    is how this first went wrong — the path was one directory too deep, the template was not found,
    and the baseline came back empty, which silently reclassified every inherited error as new.
    Deriving it from the module that actually opens the file cannot drift out of step.
    """
    import generate_project_budget as gpb
    return gpb.TEMPLATE_PATH


def _baseline_error_locations(template_path=None):
    """The (sheet, cell) locations that already hold an error in the BLANK template.

    Measured, not assumed: the untouched 2026-08 Resi template carries ~2,033 error cells, almost
    all #DIV/0! in the far-right variance columns (BJ/BK/BM/BN) that divide by an empty prior-year
    figure. Filling the budget resolves most of them.

    Read live rather than hardcoded so that a template change moves the baseline with it. What this
    check owns is "did the PIPELINE introduce an error", not "is the template clean" — the latter is
    Savills' to answer about their own template.
    """
    path = template_path or _template_path()
    if not os.path.exists(path):
        # Deliberately fatal. An empty baseline silently reclassifies every inherited error as one
        # the pipeline introduced, turning a passing check into a flood of false failures — or, if
        # the comparison were inverted, hiding real ones.
        raise FileNotFoundError(
            f'Cannot establish the formula-error baseline: the template is not at {path!r}. '
            f'Without it there is no way to tell an error the pipeline introduced from one the '
            f'template already had.'
        )
    errs = _scan_errors_via_excel(path)
    return {(s, a) for s, a, _ in errs}, len(errs)


def check_formula_errors(paths, force_degraded=False, baseline=None, template_path=None):
    """Assert the pipeline introduces no Excel error values.

    Errors at a location that already errors in the blank template are reported as INHERITED and do
    not fail. Errors anywhere else are NEW and do fail, naming the sheet and cell of the first one.

    Returns a dict stating which method actually ran. Per design D5 the reduced check is never
    substituted silently: a degraded run says explicitly what it could not see.
    """
    method, reason = METHOD_FULL, None
    if force_degraded:
        method, reason = METHOD_DEGRADED, 'degraded path forced by the caller'

    scan = _scan_errors_via_openpyxl if method == METHOD_DEGRADED else _scan_errors_via_excel
    results = {}
    for label, path in paths.items():
        if not path or not os.path.exists(path):
            continue
        try:
            results[label] = scan(path)
        except Exception as exc:
            # One failure downgrades the whole run, so every workbook is judged the same way.
            method = METHOD_DEGRADED
            reason = f'Excel automation unavailable: {type(exc).__name__}: {str(exc)[:160]}'
            scan = _scan_errors_via_openpyxl
            results[label] = scan(path)

    if baseline is None:
        baseline = set() if method == METHOD_DEGRADED else _baseline_error_locations(template_path)[0]

    inherited, introduced = {}, {}
    for label, errs in results.items():
        inherited[label] = [e for e in errs if (e[0], e[1]) in baseline]
        introduced[label] = [e for e in errs if (e[0], e[1]) not in baseline]

    degraded_note = (
        '\nNOTE: this ran the REDUCED check (cached values only). Errors that appear only after a '
        'full recalculation were NOT detectable in this run, so a clean result here is weaker '
        f'evidence than a clean {METHOD_FULL} result. Reason: {reason}'
    ) if method == METHOD_DEGRADED else ''

    failures = []
    for label, errs in introduced.items():
        if errs:
            sheet, addr, text = errs[0]
            failures.append(
                f'{label} ({os.path.basename(paths[label])}): {len(errs)} error cell(s) not present '
                f"in the blank template. First: sheet '{sheet}' cell {addr} = {text}"
            )
    if failures:
        raise FormulaError(
            f'The pipeline introduced Excel error values (method: {method}):\n  - '
            + '\n  - '.join(failures) + degraded_note
        )

    return {
        'method': method, 'degraded': method == METHOD_DEGRADED, 'reason': reason,
        'results': results, 'inherited': inherited, 'introduced': introduced,
        'baseline_size': len(baseline), 'note': degraded_note.strip(),
    }


def check_method_coverage(paths):
    """Coverage and method fidelity (change report-method-coverage-in-verification).

    Answers what check_summary_reconciles and the baseline comparison never ask: do we fill the
    line at all, and do we use the method the costing spec states for it. Coverage is measured
    against real reference budgets (verification/method_coverage.py's REFERENCE_BUDGETS), never
    against this run's own output (design.md D4). Fidelity is a value-weighted share, read from
    this run's own generated deliverable.

    Fails only when a write site has no recorded verdict, or a verdict is recorded for a code no
    longer written (design.md D2) — never on a low coverage or fidelity score (D3). No figure,
    method or cost code is touched here; this function only measures.

    Returns (ok, rows, differences, notes). Raises BaselineUnavailable if Excel cannot be driven,
    or if a reference budget file is missing.
    """
    import shutil
    import tempfile

    from verification import method_coverage as mc
    from verification.baseline import BaselineUnavailable

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            "The method-coverage check requires Excel — the fund sheet's G totals are live "
            f"formulas ({exc}).") from exc

    rows, differences, notes = [], [], []

    # ---- 3.3/3.4/3.5: cross-check verdicts against the pipeline's own write sites first — a
    # missing or orphaned verdict is the one thing this check fails a run for. ----
    verdicts_ok, missing_verdicts, orphaned_verdicts = mc.check_method_verdicts()
    rows.append(('method verdict cross-check', verdicts_ok, True))
    if not verdicts_ok:
        differences.append((
            'method verdict cross-check', verdicts_ok, True,
        ))
        detail = []
        if missing_verdicts:
            detail.append(f"written with no recorded verdict: {missing_verdicts}")
        if orphaned_verdicts:
            detail.append(f"verdict recorded for a code no longer written: {orphaned_verdicts}")
        notes.append("FAIL  method-coverage verdict cross-check: " + '; '.join(detail))
        # No point computing fidelity/coverage against a registry known to be out of sync —
        # report the structural failure and stop, same as check_summary_reconciles does when it
        # cannot read its own anchor input.
        return False, rows, differences, notes

    # ---- read every write-site code's own G value off this run's freshly generated deliverable ----
    tmp = tempfile.mkdtemp(prefix='method_coverage_')
    dwork = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], dwork)

    pythoncom.CoInitialize()
    xl = dwb = None
    code_to_value = {}
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        dwb = xl.Workbooks.Open(dwork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        fund_ws = next((ws for ws in dwb.Worksheets if _nfc(ws.Name) == _nfc('2. Budget-Management Fund')), None)
        if fund_ws is None:
            raise BaselineUnavailable("'2. Budget-Management Fund' not found on the deliverable.")

        written_codes = mc.write_site_codes()
        # Codes written only when the PM enters them (collect-on-behalf pairs) carry their verdict in
        # the catalogue (approved departures); they count only when this run wrote a figure on them.
        departure_codes = set(mc.departure_verdicts())
        for r in range(1, 495):
            code = fund_ws.Cells(r, 25).Value2  # Y — cost code
            if not (isinstance(code, str) and code.strip()):
                continue
            code = code.strip()
            if code not in written_codes and code not in departure_codes:
                continue
            g = fund_ws.Cells(r, 7).Value2  # G — Total Price
            if isinstance(g, (int, float)) and g:
                code_to_value[code] = float(g)
        dwb.Close(SaveChanges=False)
        dwb = None
    finally:
        try:
            if dwb is not None:
                dwb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            if xl is not None:
                xl.Quit()
        except Exception:
            pass

    # ---- 4.3/4.4: method fidelity, value-weighted, by verdict bucket ----
    fidelity = mc.compute_fidelity(code_to_value)
    for bucket in ('matches', 'partial', 'mismatch'):
        b = fidelity[bucket]
        rows.append((f'fidelity: {bucket}', b['share'], None))
    notes.append(
        f"method fidelity (by written VND, {len(code_to_value)} written codes, "
        f"{fidelity['total_value']:,.0f} total): "
        f"matches {fidelity['matches']['share']*100:.1f}% "
        f"({', '.join(fidelity['matches']['codes'])}); "
        f"partial {fidelity['partial']['share']*100:.1f}%"
        + (f" ({', '.join(fidelity['partial']['codes'])})" if fidelity['partial']['codes'] else '')
        + f"; mismatch {fidelity['mismatch']['share']*100:.1f}%"
        + (f" ({', '.join(fidelity['mismatch']['codes'])})" if fidelity['mismatch']['codes'] else '')
    )

    # ---- 4.1/4.2: coverage against each reference budget, reported separately, never averaged ----
    written_codes = mc.write_site_codes()
    for name in mc.REFERENCE_BUDGETS:
        cov = mc.compute_coverage(name, written_codes)
        rows.append((f'coverage: {name}', cov['filled_share'], None))
        notes.append(
            f"coverage against {name} (real reference budget): "
            f"{cov['filled_share']*100:.1f}% of its value is on codes this pipeline fills; "
            f"{cov['unfilled_share']*100:.1f}% ({len(cov['unfilled_codes'])} codes) is on lines "
            f"left blank: {', '.join(cov['unfilled_codes'])}"
        )

    return True, rows, differences, notes


def check_input_form_guard():
    """The input-form builder must not replace an existing project input workbook unless forced, and
    a forced rebuild must keep a backup (change guard-input-file-overwrite, spec input-form-protection).

    Everything happens in a temporary folder: the builder's three path globals are rebound there for
    the duration and restored afterwards, and the live input workbook is fingerprinted before and
    after so a path the rebinding missed would be caught. A stand-in file, not a real form, plays the
    "existing project input".

    Returns (ok, rows, differences, notes): rows are (label, 'ok' or 'fail: reason'), differences
    the failing ones as (label, reason).
    """
    import contextlib
    import hashlib
    import io
    import sys
    import tempfile

    src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if src not in sys.path:
        sys.path.insert(0, src)
    import build_project_input_form as bpf

    def fingerprint(path):
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as fh:
            return hashlib.sha256(fh.read()).hexdigest(), os.path.getmtime(path)

    def listing(folder):
        return {n: (os.path.getsize(os.path.join(folder, n)), os.path.getmtime(os.path.join(folder, n)))
                for n in sorted(os.listdir(folder))}

    rows, differences = [], []

    def record(label, passed, reason=''):
        rows.append((label, 'ok' if passed else f'fail: {reason}'))
        if not passed:
            differences.append((label, reason))

    live_path = bpf.FINAL_OUT
    live_before = fingerprint(live_path)
    saved = (bpf.OUT_DIR, bpf.FINAL_OUT, bpf.OUT)
    stand_in = b'stand-in project input for verification - not a real workbook'
    try:
        with tempfile.TemporaryDirectory(prefix='form_guard_') as td:
            bpf.OUT_DIR = td
            bpf.FINAL_OUT = os.path.join(td, 'Project_Budget_Input.xlsx')
            bpf.OUT = os.path.join(td, '_form_build_tmp.xlsx')
            with open(bpf.FINAL_OUT, 'wb') as fh:
                fh.write(stand_in)
            os.utime(bpf.FINAL_OUT, (1_700_000_000, 1_700_000_000))
            before = listing(td)

            # ---- unforced build over an existing file must be refused and change nothing ----
            refused, message = False, ''
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    bpf.main()
                except bpf.LiveInputExists as exc:
                    refused, message = True, str(exc)
            record('unforced build over an existing input is refused', refused,
                   'the build ran and did not raise LiveInputExists')
            record('the refusal names the file and the --force option',
                   refused and bpf.FINAL_OUT in message and '--force' in message,
                   'message does not name the file and --force')
            record('the refused build left the existing file and the folder unchanged',
                   listing(td) == before and open(bpf.FINAL_OUT, 'rb').read() == stand_in,
                   'the stand-in input was altered, or a file was added')

            # ---- forced build: backup equal to the old file, then replaced ----
            with contextlib.redirect_stdout(io.StringIO()):
                bpf.main(force=True)
            backups = [n for n in os.listdir(td) if n.startswith(bpf.BACKUP_PREFIX)]
            record('a forced build leaves exactly one backup', len(backups) == 1,
                   f'found {len(backups)} backup file(s)')
            record('the backup holds the content the input had before the build',
                   len(backups) == 1 and open(os.path.join(td, backups[0]), 'rb').read() == stand_in,
                   'backup missing or different from the earlier content')
            with open(bpf.FINAL_OUT, 'rb') as fh:
                head = fh.read(2)
            record('the forced build replaced the input with a new workbook', head == b'PK',
                   'the input was not replaced by an .xlsx')
    finally:
        bpf.OUT_DIR, bpf.FINAL_OUT, bpf.OUT = saved

    live_after = fingerprint(live_path)
    record('the live input workbook is byte-identical and unchanged in timestamp',
           live_before == live_after, 'the live input workbook changed during the guard check')
    return not differences, rows, differences, []


# ---- Existing-project mode (change carry-forward-staffing, task 7.1) ---------------------------
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _bridge_reason_records(ws):
    """The 'CHANGED LINES AND REASONS' table of a Staff Bridge sheet, as dicts keyed by header."""
    import existing_staffing as es
    title_row = next((r for r in range(1, (ws.max_row or 0) + 1)
                      if str(ws.cell(row=r, column=1).value or '').strip() == es.REASONS_TITLE), None)
    if title_row is None:
        raise StructureError(f"'{es.BRIDGE_SHEET}' has no '{es.REASONS_TITLE}' table.")
    headers = {str(ws.cell(row=title_row + 1, column=c).value or '').strip(): c
               for c in range(1, (ws.max_column or 1) + 1)}
    missing = [h for h in es.REASON_HEADERS if h not in headers]
    if missing:
        raise StructureError(f"'{es.BRIDGE_SHEET}' reason table lacks columns {missing}.")
    records = []
    for r in range(title_row + 2, (ws.max_row or 0) + 1):
        if ws.cell(row=r, column=1).value in (None, ''):
            break
        rec = {h: ws.cell(row=r, column=headers[h]).value for h in es.REASON_HEADERS}
        if str(rec['Line']).startswith('No staffing line changed'):
            break
        rec['_row'] = r
        records.append(rec)
    return records


def check_staffing_reasons(analysis_path):
    """Every changed staffing line listed on the Staff Bridge carries a reason, and the code "Khác"
    carries a note (spec budget-workflow-verification). Re-derives the rule from the records'
    own fields rather than trusting their Status column.

    Returns (ok, rows, differences, notes); a workbook without a Staff Bridge (New prospect) passes
    with a note.
    """
    import openpyxl
    import existing_staffing as es
    from input_labels import normalise

    wb = openpyxl.load_workbook(analysis_path, read_only=False)
    if es.BRIDGE_SHEET not in wb.sheetnames:
        return True, [], [], ['no Staff Bridge in this workbook (New-prospect mode): nothing to check']
    rows, differences = [], []
    codes = {normalise(c): c for c in es.REASON_CODES}
    for rec in _bridge_reason_records(wb[es.BRIDGE_SHEET]):
        label = f"{rec['Line']} — {rec['Item']} (row {rec['_row']})"
        text = str(rec['Reason'] or '').strip()
        source = str(rec['Source'] or '').strip()
        code = str(rec['Reason code'] or '').strip()
        note = str(rec['Reason note'] or '').strip()
        problem = None
        if not text:
            problem = 'changed with no reason'
        elif source == es.SOURCE_PM and normalise(code) not in codes:
            problem = f'reason code {code!r} is not on the approved list'
        elif source == es.SOURCE_PM and codes.get(normalise(code)) == es.REASON_OTHER and not note:
            problem = 'reason code "Khác" without a note'
        rows.append((label, 'ok' if problem is None else f'FAIL: {problem}'))
        if problem:
            differences.append((label, problem))
    return not differences, rows, differences, []


def _deliverable_staff_lines(deliverable_path):
    """EMH2/EMH3/EMH4 column G of the deliverable's fund sheet, after Excel recalculates a copy."""
    import shutil
    import tempfile
    import openpyxl
    from verification.baseline import BaselineUnavailable

    fund = openpyxl.load_workbook(deliverable_path, read_only=True)['2. Budget-Management Fund']
    where = {}
    for r, row in enumerate(fund.iter_rows(min_row=1, max_row=200, min_col=25, max_col=25,
                                           values_only=True), start=1):
        code = str(row[0] or '').strip()
        if code in ('EMH2', 'EMH3', 'EMH4') and code not in where:
            where[code] = r
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(f'The Staff Bridge tie needs Excel ({exc}).') from exc
    work = os.path.join(tempfile.mkdtemp(prefix='bridge_tie_'), os.path.basename(deliverable_path))
    shutil.copy(deliverable_path, work)
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        ws = wb.Worksheets('2. Budget-Management Fund')
        return {code: _num(ws.Cells(r, 7).Value2) for code, r in where.items()}
    except Exception as exc:
        raise BaselineUnavailable(f'Excel could not evaluate the deliverable: {type(exc).__name__}: {exc}') from exc
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
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)


def check_staff_bridge(paths, existing_mode, deliverable_values=None):
    """Existing-project mode: the Staff Bridge's budget-year total of EMH2, EMH3 and EMH4 equals the
    same lines of the client deliverable as Excel recalculates it, and the deliverable carries no
    bridge. New-prospect mode: neither workbook carries a bridge.

    Returns (ok, rows, differences, notes). `deliverable_values` ({code: VND/year}) skips Excel (tests).
    """
    import openpyxl
    import existing_staffing as es

    rows, differences, notes = [], [], []
    deliverable_sheets = _sheet_names(paths['deliverable'])
    label = 'client deliverable carries no Staff Bridge'
    ok_here = es.BRIDGE_SHEET not in deliverable_sheets
    rows.append((label, 'ok' if ok_here else 'FAIL'))
    if not ok_here:
        differences.append((label, 'present', 'absent'))
    analysis = openpyxl.load_workbook(paths['analysis'], read_only=False)
    has_bridge = es.BRIDGE_SHEET in analysis.sheetnames
    if not existing_mode:
        label = 'New-prospect run produces no Staff Bridge'
        rows.append((label, 'ok' if not has_bridge else 'FAIL'))
        if has_bridge:
            differences.append((label, 'present', 'absent'))
        return not differences, rows, differences, notes
    if not has_bridge:
        differences.append(('Staff Bridge in the analysis workbook', 'absent', 'present'))
        return False, rows, differences, notes
    ws = analysis[es.BRIDGE_SHEET]
    total_row = next((r for r in range(1, (ws.max_row or 0) + 1)
                      if str(ws.cell(row=r, column=1).value or '').strip() == es.BRIDGE_TOTAL_LABEL), None)
    header_row = next((r for r in range(1, total_row or 0)
                       if str(ws.cell(row=r, column=1).value or '').strip() == 'Step'), None)
    if total_row is None or header_row is None:
        differences.append((f"'{es.BRIDGE_SHEET}' row '{es.BRIDGE_TOTAL_LABEL}'", 'missing', 'present'))
        return False, rows, differences, notes
    cols = {str(ws.cell(row=header_row, column=c).value or '').strip(): c for c in range(1, 8)}
    values = deliverable_values if deliverable_values is not None else _deliverable_staff_lines(paths['deliverable'])
    bridge_sum = deliverable_sum = 0.0
    for code in es.STAFF_LINES:
        b = _num(ws.cell(row=total_row, column=cols[code]).value)
        d = values.get(code)
        label = f'Staff Bridge {code} = deliverable {code}'
        rows.append((label, b, d))
        if b is None or d is None or abs(b - d) > 1:
            differences.append((label, b, d))
        bridge_sum += b or 0
        deliverable_sum += d or 0
    rows.append(('Staff Bridge total = EMH2 + EMH3 + EMH4', bridge_sum, deliverable_sum))
    if abs(bridge_sum - deliverable_sum) > 1:
        differences.append(('Staff Bridge total = EMH2 + EMH3 + EMH4', bridge_sum, deliverable_sum))
    return not differences, rows, differences, notes


_UTILITY_FUND_ROWS = {'EEE.C': 240, 'EEW.C': 230}   # MGMT_FUND_ROWS 'electricity' / 'water'


def _deliverable_utility_lines(deliverable_path):
    """{'EEE.C': VND/year, 'EEW.C': VND/year}: the sum of the twelve month cells H:S the generator writes
    (constants, so no recalculation is needed; once '4. Điều chỉnh' has linked them, the originals it holds —
    fund_months_as_written). Also checks that the row really carries that code."""
    import openpyxl
    wb = openpyxl.load_workbook(deliverable_path, read_only=True, data_only=False)
    try:
        ws = wb['2. Budget-Management Fund']
        out = {}
        for code, row in _UTILITY_FUND_ROWS.items():
            cells = next(ws.iter_rows(min_row=row, max_row=row, values_only=True))
            if str(cells[24] or '').strip() != code:       # column Y holds the code
                raise ValueError(f"'2. Budget-Management Fund' row {row} is {cells[24]!r}, expected {code}")
            out[code] = sum(fund_months_as_written(wb, '2. Budget-Management Fund', row))
        return out
    finally:
        wb.close()


def check_utility_bridge(paths, existing_mode, deliverable_values=None):
    """Existing-project mode (change carry-forward-common-utilities): the Utility Bridge's budget-year figure
    of EEE.C and EEW.C equals the twelve months of the same line on the client deliverable, within 1 VND,
    and the deliverable carries no bridge. New-prospect mode: neither workbook carries one.

    Returns (ok, rows, differences, notes). `deliverable_values` ({code: VND/year}) skips reading (tests).
    """
    import openpyxl
    import existing_utilities as eu

    rows, differences, notes = [], [], []
    label = 'client deliverable carries no Utility Bridge'
    ok_here = eu.BRIDGE_SHEET not in _sheet_names(paths['deliverable'])
    rows.append((label, 'ok' if ok_here else 'FAIL'))
    if not ok_here:
        differences.append((label, 'present', 'absent'))
    analysis = openpyxl.load_workbook(paths['analysis'], read_only=True, data_only=True)
    try:
        has_bridge = eu.BRIDGE_SHEET in analysis.sheetnames
        if not existing_mode:
            label = 'New-prospect run produces no Utility Bridge'
            rows.append((label, 'ok' if not has_bridge else 'FAIL'))
            if has_bridge:
                differences.append((label, 'present', 'absent'))
            return not differences, rows, differences, notes
        if not has_bridge:
            differences.append(('Utility Bridge in the analysis workbook', 'absent', 'present'))
            return False, rows, differences, notes
        table = list(analysis[eu.BRIDGE_SHEET].iter_rows(values_only=True))
    finally:
        analysis.close()
    header = next((r for r in table if str(r[0] or '').strip() == 'Step'), None)
    total = next((r for r in table if str(r[0] or '').strip() == eu.BRIDGE_TOTAL_LABEL), None)
    if header is None or total is None:
        differences.append((f"'{eu.BRIDGE_SHEET}' row '{eu.BRIDGE_TOTAL_LABEL}'", 'missing', 'present'))
        return False, rows, differences, notes
    cols = {str(v or '').strip(): i for i, v in enumerate(header)}
    values = deliverable_values if deliverable_values is not None else _deliverable_utility_lines(paths['deliverable'])
    for code in eu.LINES:
        b = _num(total[cols[code]]) if code in cols else None
        d = values.get(code)
        label = f'Utility Bridge {code} = deliverable {code} (sum of 12 months)'
        rows.append((label, b, d))
        if b is None or d is None or abs(b - d) > 1:
            differences.append((label, b, d))
    return not differences, rows, differences, notes


_FUND_SHEET = '2. Budget-Management Fund'
_STAFF_DETAIL_SHEETS = {'EMH2': 'A1. Staff cost 08.2026 (VN)', 'EMH3': 'A1.1 Allowance (From 08.2026)',
                        'EMH4': 'A5. Trợ cấp PCCC'}


def existing_detail_ties(cell, fund_rows):
    """Pure core of check_existing_detail_ties (change carry-forward-staffing, design D15).

    `cell(sheet, row, col)` -> (value, formula or None) after Excel recalculation; `fund_rows` maps
    EMH2/EMH3/EMH4 to their row on the fund sheet. Each line's VND/year is recomputed from its detail
    sheet without reading the line's own formula:
      EMH2 = A1!AC96 - AC90*AC95 + 12 * every AC value from row 98 down (overflow, carried, adjustment);
      EMH3 = 12 * A1.1!S13 + every S below row 13 (VND/year: Existing's typed carried / adjustment rows, and a new
             prospect's formula rows for a qualifying code with no template row; the template has no S there);
      EMH4 = A5!H8 + every typed H below row 8.
    The line must be a formula naming its detail sheet. A line left at zero with a "Để ở mức 0" remark
    (EMH3 with no duty data and no approved amount) is not priced and passes."""
    rows, differences, notes = [], [], []

    def num(sheet, r, c):
        v = _num(cell(sheet, r, c)[0])
        return v or 0.0

    a1, a11, a5 = (_STAFF_DETAIL_SHEETS[k] for k in ('EMH2', 'EMH3', 'EMH4'))
    expected = {
        'EMH2': (num(a1, 96, 29) - num(a1, 90, 29) * num(a1, 95, 29)
                 + 12 * sum(num(a1, r, 29) for r in range(98, 141))),
        'EMH3': 12 * num(a11, 13, 19) + sum(num(a11, r, 19) for r in range(14, 41)),
        'EMH4': num(a5, 8, 8) + sum(num(a5, r, 8) for r in range(9, 41) if cell(a5, r, 8)[1] is None),
    }
    for code in ('EMH2', 'EMH3', 'EMH4'):
        r = fund_rows.get(code)
        label = f"'{_FUND_SHEET}' {code} = '{_STAFF_DETAIL_SHEETS[code]}'"
        if r is None:
            differences.append((label, 'row not found', ''))
            continue
        formula = cell(_FUND_SHEET, r, 6)[1]
        g = _num(cell(_FUND_SHEET, r, 7)[0])
        remark = str(cell(_FUND_SHEET, r, 20)[0] or '')
        if formula is None:
            if not g and remark.startswith('Để ở mức 0'):
                rows.append((label, 'ok — zero, reason stated'))
            else:
                differences.append((label, f'typed amount {g}', 'a formula into its detail sheet'))
            continue
        if _nfc(f"'{_STAFF_DETAIL_SHEETS[code]}'!") not in _nfc(formula):
            differences.append((label, formula, f"a formula into '{_STAFF_DETAIL_SHEETS[code]}'"))
            continue
        rows.append((label, g, expected[code]))
        if g is None or abs(g - expected[code]) > 1:
            differences.append((label, g, expected[code]))
    return not differences, rows, differences, notes


def check_existing_detail_ties(paths):
    """Existing-project mode: EMH2, EMH3 and EMH4 on the fund sheet are formulas into A1 / A1.1 / A5
    and equal those sheets as Excel recalculates them (existing_detail_ties). Returns
    (ok, rows, differences, notes)."""
    import shutil
    import tempfile
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(f'The detail-sheet tie needs Excel ({exc}).') from exc
    work = os.path.join(tempfile.mkdtemp(prefix='detail_tie_'), os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], work)
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {_nfc(ws.Name): ws for ws in wb.Worksheets}

        def cell(sheet, r, c):
            ws = sheets.get(_nfc(sheet))
            if ws is None:
                raise BaselineUnavailable(f"'{sheet}' not found on the deliverable.")
            x = ws.Cells(r, c)
            return x.Value2, (str(x.Formula) if x.HasFormula else None)

        fund = sheets[_nfc(_FUND_SHEET)]
        fund_rows = {}
        for r in range(1, 201):
            code = str(fund.Cells(r, 25).Value2 or '').strip()
            if code in _STAFF_DETAIL_SHEETS and code not in fund_rows:
                fund_rows[code] = r
        return existing_detail_ties(cell, fund_rows)
    except BaselineUnavailable:
        raise
    except Exception as exc:
        raise BaselineUnavailable(f'Excel could not evaluate the deliverable: {type(exc).__name__}: {exc}') from exc
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
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)


# ---- Contingency lines EM#, ES#, EE# (change apply-head-of-pm-decisions-2026-10, group 6) ------------------------
_CONTINGENCY_FORMULA = None


def contingency_ties(lines_by_sheet, cell, analysis=None):
    """Hold each contingency line of both fund sheets to its rule (design D9), as Excel evaluated it.

    `lines_by_sheet` is {sheet: contingency.layout(...)}; `cell(sheet, row, col)` returns (value, formula or None).
    Each month is either the live formula `=ROUND(rate*(SUBTOTAL(9,<col><first>:<col><last>)-<excluded>),0)` over
    exactly the line's own leaves and exclusions, with `last` above the line itself (a range reaching the line would
    make it depend on itself), and equal to ROUND(rate x (the plain sum of the leaf rows - the excluded rows)); or, at
    a rate of 0, the six lines stay 0 with a "Để ở mức 0" remark. One rate on every line. `analysis`, when given, is
    dict(rate=, bases={label: (contingency, in-house staff, OPEX less repairs)}) from the analysis's Cost Priority
    sheet: same rate, and contingency = ROUND(rate x (staff + OPEX)). Returns (ok, rows, differences, notes)."""
    import re
    import contingency as ct
    global _CONTINGENCY_FORMULA
    if _CONTINGENCY_FORMULA is None:
        _CONTINGENCY_FORMULA = re.compile(
            r'^=ROUND\(([0-9.]+)\*\(SUBTOTAL\(9,([A-Z]+)(\d+):\2(\d+)\)((?:-[A-Z]+\d+)*)\),0\)$')
    from openpyxl.utils import get_column_letter
    rows, differences, rates = [], [], set()

    def record(label, passed, reason=''):
        rows.append((label, 'ok' if passed else f'fail: {reason}'))
        if not passed:
            differences.append((label, reason))

    def num(v):
        return float(v) if isinstance(v, (int, float)) else 0.0

    for sheet, lines in lines_by_sheet.items():
        for line in lines:
            label = f"{sheet} {line['code']}"
            row = line['row']
            formulas = [cell(sheet, row, 8 + m)[1] for m in range(12)]
            if all(f is None for f in formulas):
                g = num(cell(sheet, row, 7)[0])
                remark = str(cell(sheet, row, 20)[0] or '')
                rates.add(0.0)
                record(f'{label} at rate 0', abs(g) < 0.5 and remark.startswith('Để ở mức 0'),
                       f'G {g:,.0f}, remark {remark[:60]!r}')
                continue
            leaves = [r for r in range(line['first'], line['last'] + 1)
                      if 'SUBTOTAL' not in str(cell(sheet, r, 7)[1] or '').upper()]
            excluded = sorted(r for _c, r in line['excluded'])
            problems = []
            for m, f in enumerate(formulas):
                col = get_column_letter(ct.MONTH_BASE_COL[sheet] + m)
                hit = _CONTINGENCY_FORMULA.match(str(f or '').replace(' ', ''))
                if not hit:
                    problems.append(f'month {m + 1}: {f!r} is not the contingency formula')
                    continue
                rate, fcol, first, last = float(hit.group(1)), hit.group(2), int(hit.group(3)), int(hit.group(4))
                minus = sorted(int(x[len(fcol):]) for x in hit.group(5).split('-') if x)
                rates.add(rate)
                if last >= row or first <= row <= last or row in minus:
                    problems.append(f'month {m + 1}: the range {first}-{last} reaches the line itself (row {row})')
                if (fcol, first, last, minus) != (col, line['first'], line['last'], excluded):
                    problems.append(f'month {m + 1}: reads {fcol}{first}:{fcol}{last} less {minus}, expected '
                                    f'{col}{line["first"]}:{col}{line["last"]} less {excluded}')
                c = ct.MONTH_BASE_COL[sheet] + m
                want = round(rate * (sum(num(cell(sheet, r, c)[0]) for r in leaves)
                                     - sum(num(cell(sheet, r, c)[0]) for r in excluded)))
                got = num(cell(sheet, row, 8 + m)[0])
                if abs(got - want) > 0.5:
                    problems.append(f'month {m + 1}: {got:,.0f}, but rate x its leaves = {want:,.0f}')
            record(f'{label} = rate x its own leaves, each month', not problems, '; '.join(problems[:3]))
    record('one contingency rate on every line', len(rates) == 1, f'rates {sorted(rates)}')
    notes = [f"contingency rate {sorted(rates)[0]:.4g} on {sum(len(v) for v in lines_by_sheet.values())} lines"
             if len(rates) == 1 else 'more than one contingency rate']
    if analysis is not None and len(rates) == 1:
        rate = next(iter(rates))
        record('the analysis uses the deliverable\'s contingency rate', abs(analysis['rate'] - rate) < 1e-9,
               f"analysis {analysis['rate']}, deliverable {rate}")
        for basis, (cont, staff, opex) in analysis['bases'].items():
            want = round(rate * (staff + opex))
            record(f'analysis contingency ({basis}) = rate x (in-house staff + OPEX less repairs)',
                   abs(cont - want) < 0.5, f'{cont:,.0f} vs {want:,.0f}')
    return (not differences), rows, differences, notes


def check_contingency(paths):
    """The contingency lines on the generated deliverable and the analysis, read through Excel after a full
    recalculation (contingency_ties), plus Excel's own circular-reference flag on both fund sheets and
    '1. Summary'. The lines and their leaves come from contingency.layout on the deliverable itself, with the
    catalogue's collect-on-behalf expense lines as exclusions. Returns (ok, rows, differences, notes).
    False negative: Excel's CircularReference names only the first loop it finds on a sheet."""
    import shutil
    import tempfile

    import openpyxl
    import contingency as ct
    import generate_project_budget as gpb
    import operating_inputs
    from verification.baseline import BaselineUnavailable
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(f'The contingency check needs Excel ({exc}).') from exc
    paired = set(operating_inputs.cob_pairing(gpb.CATALOGUE_PATH).values())
    owb = openpyxl.load_workbook(paths['deliverable'])
    lines_by_sheet = {s: ct.layout(owb[s], s, extra_exclusions=paired) for s in (ct.FUND_SHEET, ct.COMMON_SHEET)}
    tmp = tempfile.mkdtemp(prefix='contingency_')
    pythoncom.CoInitialize()
    xl = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(shutil.copy(paths['deliverable'], os.path.join(tmp, 'd.xlsx')), UpdateLinks=0)
        xl.CalculateFullRebuild()
        grids, circular = {}, []
        for ws in wb.Worksheets:
            name = _nfc(ws.Name)
            if name in (_nfc(ct.FUND_SHEET), _nfc(ct.COMMON_SHEET), _nfc('1. Summary')):
                if ws.CircularReference is not None:
                    circular.append(f'{ws.Name}!{ws.CircularReference.Address}')
                if name != _nfc('1. Summary'):
                    rng = ws.Range('A1:BB500')
                    grids[name] = (rng.Value2, rng.Formula)
        wb.Close(SaveChanges=False)

        def cell(sheet, r, c):
            values, formulas = grids[_nfc(sheet)]
            f = formulas[r - 1][c - 1]
            return values[r - 1][c - 1], (f if isinstance(f, str) and f.startswith('=') else None)

        analysis = None
        if paths.get('analysis') and os.path.exists(paths['analysis']):
            wa = xl.Workbooks.Open(shutil.copy(paths['analysis'], os.path.join(tmp, 'a.xlsx')), UpdateLinks=0)
            xl.CalculateFullRebuild()
            cp = next((ws for ws in wa.Worksheets if ws.Name == 'Cost Priority'), None)
            if cp is not None:
                vals = cp.UsedRange.Value2
                at = next((i + 1 for i, r in enumerate(vals) if isinstance(r[0], str)
                           and r[0].startswith('Contingency Rate')), None)
                if at is not None:
                    get = lambda r, c: float(cp.Cells(r, c).Value2 or 0)
                    analysis = dict(rate=get(at, 2), bases={
                        'Must-Have': (get(at + 3, 2), get(at + 1, 2), get(at + 2, 2)),
                        'Full Cost': (get(at + 3, 3), get(at + 1, 3), get(at + 2, 3))})
            wa.Close(SaveChanges=False)
        ok, rows, differences, notes = contingency_ties(lines_by_sheet, cell, analysis)
        rows.append(('no circular reference on the fund sheets or 1. Summary', 'ok' if not circular else 'fail'))
        if circular:
            differences.append(('circular reference', ', '.join(circular)))
        if analysis is None:
            notes.append('the analysis has no contingency section on Cost Priority; its rate was not compared')
        return (not differences), rows, differences, notes
    except BaselineUnavailable:
        raise
    except Exception as exc:
        raise BaselineUnavailable(f'Excel could not evaluate the contingency lines: {type(exc).__name__}: {exc}') from exc
    finally:
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


# The deliverable's helper sheets that explain a fund line (change apply-head-of-pm-decisions-2026-10, D15): each
# sheet's monthly total cell x 12 equals the line(s) on the fund sheet named. ESS9 is compared before VAT, as the
# garbage sheet prices it; the fund line carries each month's VAT when the financial model includes it.
_COMMON_AREA_SHEET = '2.2 Common area Fund'
_HELPER_TIES = (
    ('A2. Bảo vệ - Security', 31, 8, _FUND_SHEET, ('ESS1',)),
    ('A3. Vệ sinh - Cleaning', 23, 11, _FUND_SHEET, ('ESS4',)),
    ('A4. Cây xanh - Landscape', 11, 11, _FUND_SHEET, ('ESS16',)),
    ('B3. Thu gom rác - Garbage coll ', 11, 12, _FUND_SHEET, ('ESS9',)),
    ('B4. DT Quảng cáo - Elevator adv', 7, 12, _COMMON_AREA_SHEET, ('RA1.A', 'RA2')),
)
HELPER_TIE_TOLERANCE = 12      # VND a year: the fund lines are written month by month, rounded


def helper_sheet_ties(cell, line_rows):
    """Pure core of check_helper_sheet_ties. `cell(sheet, row, col)` -> (value, formula or None) after Excel
    recalculation; `line_rows` maps (sheet, code) to the line's row. A line's VND/year is its column G; ESS9's is
    taken back to before VAT month by month (H:S over 1 + that month's general VAT, from the dated tariff file and
    the period starting at the fund sheet's AH6) unless the model switch F7 says KHOÁN."""
    import datetime as _dt
    import budget_period
    import utility_tariffs
    rows, differences, notes = [], [], []

    def num(sheet, r, c):
        return _num(cell(sheet, r, c)[0]) or 0.0

    incl_vat = ' '.join(str(cell(_FUND_SHEET, 7, 6)[0] or '').split()).upper() != 'KHOÁN'
    start = cell(_FUND_SHEET, 6, 34)[0]
    if isinstance(start, (int, float)) and not isinstance(start, bool):
        start = _dt.datetime(1899, 12, 30) + _dt.timedelta(days=start)
    period = budget_period.from_value(start)
    tariff_rows = utility_tariffs.load_rows()
    vat = [utility_tariffs.vat_rate(y, m, rows=tariff_rows) for y, m in period.months]
    for sheet, r, c, line_sheet, codes in _HELPER_TIES:
        label = f"'{sheet}'!{chr(64 + c)}{r} x 12 = " + ' + '.join(codes)
        missing = [code for code in codes if (line_sheet, code) not in line_rows]
        if missing:
            differences.append((label, 'row not found: ' + ', '.join(missing), ''))
            continue
        expected = 0.0
        for code in codes:
            lr = line_rows[(line_sheet, code)]
            if code == 'ESS9':
                months = [num(line_sheet, lr, 8 + i) for i in range(12)]
                expected += sum(v / (1 + vat[i] / 100) if incl_vat else v for i, v in enumerate(months))
            else:
                expected += num(line_sheet, lr, 7)
        got = num(sheet, r, c) * 12
        rows.append((label, got, expected))
        if abs(got - expected) > HELPER_TIE_TOLERANCE:
            differences.append((label, got, expected))
    notes.append(f'{len(rows)} helper-sheet total(s) tied to their fund lines (tolerance {HELPER_TIE_TOLERANCE} '
                 f'VND a year; ESS9 before VAT, model {"incl." if incl_vat else "excl."} VAT).')
    return not differences, rows, differences, notes


def check_helper_sheet_ties(paths):
    """A2/A3/A4 = ESS1/ESS4/ESS16, the B3 garbage sheet = ESS9 before VAT, B4 = RA1.A + RA2, on the deliverable as
    Excel recalculates it (helper_sheet_ties). Returns (ok, rows, differences, notes)."""
    import shutil
    import tempfile

    from verification.baseline import BaselineUnavailable
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(f'The helper-sheet tie needs Excel ({exc}).') from exc
    work = os.path.join(tempfile.mkdtemp(prefix='helper_tie_'), os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], work)
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {_nfc(ws.Name): ws for ws in wb.Worksheets}

        def cell(sheet, r, c):
            ws = sheets.get(_nfc(sheet))
            if ws is None:
                raise BaselineUnavailable(f"'{sheet}' not found on the deliverable.")
            x = ws.Cells(r, c)
            return x.Value2, (str(x.Formula) if x.HasFormula else None)

        wanted = {(s, code) for _h, _r, _c, s, codes in _HELPER_TIES for code in codes}
        line_rows = {}
        for s in {s for s, _code in wanted}:
            ws = sheets[_nfc(s)]
            codes = ws.Range('Y1:Y700').Value
            for i, (y,) in enumerate(codes, start=1):
                key = (s, str(y or '').strip())
                if key in wanted and key not in line_rows:
                    line_rows[key] = i
        return helper_sheet_ties(cell, line_rows)
    except BaselineUnavailable:
        raise
    except Exception as exc:
        raise BaselineUnavailable(f'Excel could not evaluate the deliverable: {type(exc).__name__}: {exc}') from exc
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
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)


# The adjustment sheet (docs/32, 2026-10-20): '4. Điều chỉnh' carries one parent row per fund line the tool wrote
# (code in A, 'Tổng' in C) followed by its detail sub-rows ('Chi tiết' in C). Column letters below follow the layout
# in docs/32 section 3. The fund line's month cells (H:S, and F on a Monthly line) are formulas back into this sheet,
# so an untouched deliverable must show every figure unchanged: M = I, N = 0, and I = the fund line's AK.
ADJUSTMENT_SHEET = '4. Điều chỉnh'
_ADJUSTMENT_AFTER = '3.1 Report-Sinking Fund'
_ADJUSTMENT_FIRST_ROW = 5
_ADJ_COL = {'code': 1, 'name': 2, 'kind': 3, 'choice': 4, 'desc': 5, 'unit': 6, 'qty': 7, 'price': 8, 'amount': 9,
            'new_qty': 10, 'new_price': 11, 'escalation': 12, 'new_amount': 13, 'delta': 14, 'delta_pct': 15,
            'fund_sheet': 16, 'fund_row': 17, 'freq': 18, 'month1': 19}
_ADJ_KIND_PARENT, _ADJ_KIND_DETAIL = 'Tổng', 'Chi tiết'
_ADJ_FUND_SHEETS = (_FUND_SHEET, _COMMON_AREA_SHEET)
_ADJ_FUND_FIRST_ROW = 12
_ADJ_TAX_BLOCK_CODE = 'PL1'                         # first code of PART 2 on both fund sheets (rows 495 / 456)
# The year total the parent's I is held to: AK (=SUM(AQ:BB), what '1. Summary' reads) on the management fund;
# the common-area fund has no AK, so its own G (the form's year total).
_ADJ_TOTAL_COL = {_FUND_SHEET: 37, _COMMON_AREA_SHEET: 7}
ADJUSTMENT_TIE_TOLERANCE = HELPER_TIE_TOLERANCE   # VND a year: the fund lines are written month by month, rounded
_ADJ_DETAIL_TOLERANCE = 1.0                         # VND: the detail invariants of docs/32 section 2


def adjustment_original_months(wb, code, fund_sheet=None):
    """The 12 original months (S:AD) of `code`'s parent row on '4. Điều chỉnh' of an openpyxl workbook, or None
    when the sheet or the code is not there. `fund_sheet` narrows the match to the parent whose column P names it
    (a code can sit on both fund sheets)."""
    name = next((n for n in wb.sheetnames if _nfc(n) == _nfc(ADJUSTMENT_SHEET)), None)
    if name is None:
        return None
    A = _ADJ_COL
    for row in wb[name].iter_rows(min_row=_ADJUSTMENT_FIRST_ROW, max_col=A['month1'] + 11, values_only=True):
        if _nfc(str(row[A['kind'] - 1] or '').strip()) != _ADJ_KIND_PARENT:
            continue
        if str(row[A['code'] - 1] or '').strip() != code:
            continue
        if fund_sheet is not None and _nfc(str(row[A['fund_sheet'] - 1] or '').strip()) != _nfc(fund_sheet):
            continue
        return [float(_num(v) or 0.0) for v in row[A['month1'] - 1:A['month1'] + 11]]
    return None


def fund_months_as_written(wb, sheet, row):
    """The 12 month figures (H:S) of a fund line as the generator wrote them, from an openpyxl workbook loaded
    without data_only: plain numbers as they are; once '4. Điều chỉnh' has turned them into formulas back into
    itself (docs/32), the originals from that sheet's parent row (matched by the line's code on column Y and the
    sheet). Blanks are 0. Raises ValueError when a month is a formula into the sheet and no parent row carries the
    code, so a check never silently reads 0 for a linked line."""
    ws = wb[next(n for n in wb.sheetnames if _nfc(n) == _nfc(sheet))]
    cells = next(ws.iter_rows(min_row=row, max_row=row, max_col=25, values_only=True))
    months = list(cells[7:19])
    if not any(_formula_names_sheet(v, ADJUSTMENT_SHEET) for v in months):
        return [float(_num(v) or 0.0) for v in months]
    code = str(cells[24] or '').strip()
    original = adjustment_original_months(wb, code, sheet)
    if original is None:
        raise ValueError(f"'{sheet}' row {row} ({code!r}) is linked to '{ADJUSTMENT_SHEET}' but that sheet has no "
                         f'parent row for it')
    return original


_ADJ_WRAP = None


def unwrap_adjustment_formula(formula):
    """The formula a fund cell had before '4. Điều chỉnh' wrapped it: "=(<old>)*IF('4. Điều chỉnh'!...)" gives
    "=<old>"; anything else is returned unchanged."""
    global _ADJ_WRAP
    if _ADJ_WRAP is None:
        _ADJ_WRAP = re.compile(r"^=\((.*)\)\*IF\('4\. Điều chỉnh'!.*\)$", re.DOTALL)
    if not isinstance(formula, str):
        return formula
    m = _ADJ_WRAP.match(_nfc(formula.strip()))
    return '=' + m.group(1) if m else formula


def _formula_names_sheet(formula, sheet):
    """True when `formula` references `sheet` (quoted or bare, in either Unicode form): the plain link of docs/32
    section 3 and the wrapped form "=(<old formula>)*IF('4. Điều chỉnh'!...)" alike."""
    if not isinstance(formula, str):
        return False
    return _nfc(sheet) in _nfc(formula)


def adjustment_sheet_ties(sheet_names, cell, last_row):
    """Pure core of check_adjustment_sheet. `sheet_names` is the deliverable's sheet order; `cell(sheet, r, c)` ->
    (value, formula or None) after Excel recalculation; `last_row(sheet)` -> the last used row of a sheet.

    Holds the untouched deliverable to docs/32 section 4: the sheet sits right after '3.1 Report-Sinking Fund'; each
    parent row's I equals the sum of its detail rows, M equals I, N is 0, and the 12 original months (S:AD) add up to
    I; each detail row's G x H equals I; the parent's I equals AK of the fund line its code names (located by the
    code on column Y, and column Q must agree: AK on the management fund, G on the common-area fund, which has
    no AK); that fund line's month cells (H:S, plus F on a Monthly line) are
    formulas into this sheet; and no fund leaf with a non-zero total whose months are plain values is left off the
    sheet (the PART 2 block from PL1 down is not lines). A leaf whose months are formulas of their own (a pass-through share, a staff-sheet link, a contingency
    line) is derived rather than written, so it is reported in the notes, not failed.
    Returns (ok, rows, differences, notes)."""
    rows, differences, notes = [], [], []
    names = [_nfc(n) for n in sheet_names]
    if _nfc(ADJUSTMENT_SHEET) not in names:
        differences.append((f"'{ADJUSTMENT_SHEET}'", 'sheet missing from the deliverable', ''))
        return False, rows, differences, notes
    pos = names.index(_nfc(ADJUSTMENT_SHEET))
    want_pos = names.index(_nfc(_ADJUSTMENT_AFTER)) + 1 if _nfc(_ADJUSTMENT_AFTER) in names else None
    rows.append((f"'{ADJUSTMENT_SHEET}' position", pos, want_pos))
    if pos != want_pos:
        differences.append((f"'{ADJUSTMENT_SHEET}' position (0-based)", pos,
                            f"{want_pos} (right after '{_ADJUSTMENT_AFTER}')"))

    def val(sheet, r, c):
        return cell(sheet, r, c)[0]

    def num(sheet, r, c):
        return _num(val(sheet, r, c)) or 0.0

    def text(sheet, r, c):
        v = val(sheet, r, c)
        return _nfc(str(v).strip()) if isinstance(v, str) else ''

    # ---- the fund lines: every leaf row by (sheet, code) -------------------------------------
    fund_rows, leaves = {}, []
    for sheet in _ADJ_FUND_SHEETS:
        if _nfc(sheet) not in names:
            differences.append((f"'{sheet}'", 'fund sheet missing from the deliverable', ''))
            continue
        for r in range(_ADJ_FUND_FIRST_ROW, last_row(sheet) + 1):
            code = text(sheet, r, 25)
            if code == _ADJ_TAX_BLOCK_CODE:
                break                                      # PART 2 (profit, VAT, CIT) starts here: not lines
            if not code:
                continue
            g_formula = cell(sheet, r, 7)[1] or ''
            if g_formula.upper().startswith('=SUBTOTAL'):
                continue                                   # a section subtotal, not a line
            fund_rows.setdefault((sheet, code), r)
            leaves.append((sheet, code, r))

    # ---- the adjustment sheet: parents and their details -------------------------------------
    A = _ADJ_COL
    parents, r, last = [], _ADJUSTMENT_FIRST_ROW, last_row(ADJUSTMENT_SHEET)
    while r <= last:
        if text(ADJUSTMENT_SHEET, r, A['kind']) != _ADJ_KIND_PARENT:
            r += 1
            continue
        details = []
        d = r + 1
        while d <= last and text(ADJUSTMENT_SHEET, d, A['kind']) == _ADJ_KIND_DETAIL:
            details.append(d)
            d += 1
        parents.append((r, details))
        r = d

    covered = set()
    n_details = 0
    for pr, details in parents:
        code = text(ADJUSTMENT_SHEET, pr, A['code'])
        label = f'{code} (row {pr})'
        amount = num(ADJUSTMENT_SHEET, pr, A['amount'])
        new_amount = num(ADJUSTMENT_SHEET, pr, A['new_amount'])
        delta = num(ADJUSTMENT_SHEET, pr, A['delta'])
        if not details:
            differences.append((f'{label}: detail rows', 0, 'at least 1'))
        detail_sum = sum(num(ADJUSTMENT_SHEET, d, A['amount']) for d in details)
        rows.append((f'{label}: I = sum of detail I', amount, detail_sum))
        if abs(amount - detail_sum) > _ADJ_DETAIL_TOLERANCE:
            differences.append((f'{label}: parent I vs sum of detail I', amount, detail_sum))
        rows.append((f'{label}: M = I (untouched)', new_amount, amount))
        if abs(new_amount - amount) > _ADJ_DETAIL_TOLERANCE:
            differences.append((f'{label}: M (new amount) vs I (original) on an untouched sheet', new_amount, amount))
        if abs(delta) > _ADJ_DETAIL_TOLERANCE:
            differences.append((f'{label}: N (difference) on an untouched sheet', delta, 0))
        months = [num(ADJUSTMENT_SHEET, pr, A['month1'] + i) for i in range(12)]
        rows.append((f'{label}: original months S:AD = I', sum(months), amount))
        if abs(sum(months) - amount) > ADJUSTMENT_TIE_TOLERANCE:
            differences.append((f'{label}: original months S:AD vs I', sum(months), amount))
        for d in details:
            n_details += 1
            q, p, a = (num(ADJUSTMENT_SHEET, d, A[k]) for k in ('qty', 'price', 'amount'))
            if abs(q * p - a) > _ADJ_DETAIL_TOLERANCE:
                differences.append((f'{label}: detail row {d} G x H vs I', q * p, a))
        # the fund line
        fund_sheet = text(ADJUSTMENT_SHEET, pr, A['fund_sheet'])
        key = (next((s for s in _ADJ_FUND_SHEETS if _nfc(s) == fund_sheet), fund_sheet), code)
        if key not in fund_rows:
            differences.append((f'{label}: fund line', f"'{fund_sheet}' has no leaf with code {code!r}", ''))
            continue
        covered.add(key)
        fr = fund_rows[key]
        q_row = num(ADJUSTMENT_SHEET, pr, A['fund_row'])
        if int(q_row) != fr:
            differences.append((f'{label}: column Q (fund row) vs the row code {code!r} is on', int(q_row), fr))
        tcol = _ADJ_TOTAL_COL[key[0]]
        total = num(key[0], fr, tcol)
        rows.append((f"{label}: I = '{key[0]}'!{_col_letter(tcol)}{fr}", amount, total))
        if abs(amount - total) > ADJUSTMENT_TIE_TOLERANCE:
            differences.append((f"{label}: parent I vs '{key[0]}'!{_col_letter(tcol)}{fr}", amount, total))
        freq = text(ADJUSTMENT_SHEET, pr, A['freq']).lower()
        month_cols = list(range(8, 20)) + ([6] if freq == 'monthly' else [])
        unlinked = [c for c in month_cols if not _formula_names_sheet(cell(key[0], fr, c)[1], ADJUSTMENT_SHEET)]
        rows.append((f"{label}: '{key[0]}' row {fr} month cells linked", len(month_cols) - len(unlinked),
                     len(month_cols)))
        if unlinked:
            differences.append((f"{label}: '{key[0]}' row {fr} month cell(s) not a formula into "
                                f"'{ADJUSTMENT_SHEET}'", ', '.join(_col_letter(c) for c in unlinked), 'formula'))

    # ---- every written fund leaf is on the sheet -----------------------------------------------
    derived = []
    for sheet, code, fr in leaves:
        total = num(sheet, fr, _ADJ_TOTAL_COL[sheet])
        if (sheet, code) in covered or abs(total) < 1:
            continue
        freq = text(sheet, fr, 3).lower()
        primary = 6 if freq == 'monthly' else 8
        if cell(sheet, fr, primary)[1]:
            derived.append((sheet, f'{code} (row {fr})'))
        else:
            differences.append((f"'{sheet}' row {fr} code {code}: non-zero {_col_letter(_ADJ_TOTAL_COL[sheet])}, "
                                f"written as values, missing from '{ADJUSTMENT_SHEET}'", total, 'on the sheet'))
    notes.append(f"'{ADJUSTMENT_SHEET}': {len(parents)} parent row(s), {n_details} detail row(s), "
                 f'{len(covered)} fund line(s) linked (tolerance {ADJUSTMENT_TIE_TOLERANCE} VND a year on the '
                 f'fund ties, {_ADJ_DETAIL_TOLERANCE:.0f} VND on the detail rows).')
    if derived:
        by_sheet = {}
        for sheet, what in derived:
            by_sheet.setdefault(sheet, []).append(what)
        notes.append(f'{len(derived)} non-zero fund line(s) are formulas of their own and stay off the sheet: '
                     + '; '.join(f"'{sheet}': " + (', '.join(whats) if sheet == _FUND_SHEET
                                                     else f'{len(whats)} pass-through share(s) of the form')
                                 for sheet, whats in by_sheet.items()))
    return not differences, rows, differences, notes


def _col_letter(c):
    s = ''
    while c:
        c, rem = divmod(c - 1, 26)
        s = chr(65 + rem) + s
    return s


def _read_sheet_block(ws, first_row, last_col):
    """Read a sheet's rows `first_row`..last used row, columns 1..`last_col`, in two bulk reads (values and
    formulas). Returns (last_row, lookup) where lookup(r, c) -> (value, formula or None)."""
    used = ws.UsedRange
    last_row = used.Row + used.Rows.Count - 1
    if last_row < first_row:
        return last_row, (lambda r, c: (None, None))
    rng = ws.Range(ws.Cells(first_row, 1), ws.Cells(last_row, last_col))
    values, formulas = rng.Value2, rng.Formula
    if not isinstance(values, tuple):           # a single cell comes back bare
        values, formulas = ((values,),), ((formulas,),)

    def lookup(r, c):
        i, j = r - first_row, c - 1
        if i < 0 or i >= len(values) or j < 0 or j >= len(values[0]):
            return None, None
        f = formulas[i][j]
        return values[i][j], (f if isinstance(f, str) and f.startswith('=') else None)
    return last_row, lookup


def adjustment_cells_from_workbook(wb):
    """From an open, recalculated Excel COM workbook, the (sheet_names, cell, last_row) triple adjustment_sheet_ties
    reads: the adjustment sheet from row 1 to AD and both fund sheets from row 12 to AK, read in bulk once."""
    sheets = {_nfc(ws.Name): ws for ws in wb.Worksheets}
    sheet_names = [ws.Name for ws in wb.Worksheets]
    blocks = {}
    for name, first in ((ADJUSTMENT_SHEET, 1), (_FUND_SHEET, _ADJ_FUND_FIRST_ROW),
                        (_COMMON_AREA_SHEET, _ADJ_FUND_FIRST_ROW)):
        ws = sheets.get(_nfc(name))
        if ws is not None:
            blocks[_nfc(name)] = _read_sheet_block(ws, first, 37)

    def cell(sheet, r, c):
        block = blocks.get(_nfc(sheet))
        return block[1](r, c) if block else (None, None)

    def last_row(sheet):
        block = blocks.get(_nfc(sheet))
        return block[0] if block else 0
    return sheet_names, cell, last_row


def check_adjustment_sheet(paths):
    """'4. Điều chỉnh' on the deliverable as Excel recalculates it (adjustment_sheet_ties): in place, parents equal
    their details and their fund lines, nothing moved, every written line covered and linked.
    Returns (ok, rows, differences, notes)."""
    import shutil
    import tempfile

    from verification.baseline import BaselineUnavailable
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(f'The adjustment-sheet check needs Excel ({exc}).') from exc
    work = os.path.join(tempfile.mkdtemp(prefix='adjust_tie_'), os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], work)
    pythoncom.CoInitialize()
    xl = wb = None
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheet_names, cell, last_row = adjustment_cells_from_workbook(wb)
    except Exception as exc:
        raise BaselineUnavailable(f'Excel could not evaluate the deliverable: {type(exc).__name__}: {exc}') from exc
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
        shutil.rmtree(os.path.dirname(work), ignore_errors=True)
    return adjustment_sheet_ties(sheet_names, cell, last_row)


def check_run_log(paths, input_path, required_rows):
    """The run log (change add-budget-run-log, spec budget-run-log), exercised on the synthetic project.

    Writes a record into a TEMPORARY folder (never the live reports/run_log/) and asserts:
      - the record exists, parses, and its three Required-line counts add up to its total;
      - surplus equals revenue minus expense;
      - its Required counts equal the independent reading `required_rows` (the rows check_required_line_items
        returned for the same deliverable), and its revenue / expense equal G of the R and E rows read straight
        through Excel;
      - a log folder that cannot be created gives a warning and no exception;
      - a PC without Excel gives a record with blank figures and status excel_unavailable;
      - the live reports/run_log/ folder is exactly as it was.

    Returns (ok, rows, differences, notes); rows are (label, 'ok' | 'FAIL — ...').
    """
    import contextlib
    import io
    import json
    import shutil
    import sys
    import tempfile

    from verification.baseline import BaselineUnavailable

    _src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    import run_log

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(f'The run-log check requires Excel ({exc}).') from exc

    live_dir = os.path.join(os.path.dirname(_src), 'reports', 'run_log')
    live_before = sorted(os.listdir(live_dir)) if os.path.isdir(live_dir) else None
    csv_path = os.path.join(os.path.dirname(_src), 'data', 'master_list_verified',
                            'AI_Guideline_Required_Classification.csv')
    rows, differences, notes = [], [], []

    def check(label, ok, msg=''):
        rows.append((label, 'ok' if ok else f'FAIL — {msg}'))
        if not ok:
            differences.append((label, msg))

    tmp = tempfile.mkdtemp(prefix='run_log_check_')
    try:
        log_dir = os.path.join(tmp, 'run_log')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            path, rec = run_log.write(paths['deliverable'], paths['analysis'], input_path, csv_path, log_dir=log_dir)
        check('a record is written', bool(path) and os.path.exists(path or ''), 'no file was written')
        if not path:
            return False, rows, differences, notes
        rec_file = json.load(open(path, encoding='utf-8'))
        check('the record parses back unchanged', rec_file == rec, 'the file differs from the record in memory')
        check('the status is ok', rec['status'] == 'ok', f"status is {rec['status']!r}")
        total = rec['required_total']
        parts = (rec['required_filled'], rec['required_zero_with_reason'], rec['required_zero_no_reason'])
        check('Required counts add up to the total', total is not None and sum(parts) == total,
              f'{parts} do not add up to {total}')
        if None not in (rec['revenue_vnd'], rec['expense_vnd'], rec['fund_surplus_vnd']):
            check('surplus equals revenue minus expense',
                  abs(rec['fund_surplus_vnd'] - (rec['revenue_vnd'] - rec['expense_vnd'])) < 0.5,
                  f"{rec['fund_surplus_vnd']} vs {rec['revenue_vnd']} - {rec['expense_vnd']}")
        else:
            check('surplus equals revenue minus expense', False, 'a money figure is blank')

        # independent reading 1: the rows of check_required_line_items
        f_n = sum(1 for _l, s in required_rows if s == 'ok — non-zero')
        r_n = sum(1 for _l, s in required_rows if s.startswith('ok — zero'))
        z_n = sum(1 for _l, s in required_rows if s.startswith('FAIL'))
        check('Required counts equal the independent reading (check_required_line_items)',
              parts == (f_n, r_n, z_n), f'run log {parts} vs independent {(f_n, r_n, z_n)}')

        # independent reading 2: G of the R and E rows straight through Excel
        pythoncom.CoInitialize()
        xl = wb = None
        try:
            xl = win32com.client.DispatchEx('Excel.Application')
            xl.Visible = False
            xl.DisplayAlerts = False
            work = os.path.join(tmp, 'deliverable_copy.xlsx')
            shutil.copy(paths['deliverable'], work)
            wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
            xl.CalculateFullRebuild()
            ws = next(w for w in wb.Worksheets if _nfc(w.Name) == _nfc('2. Budget-Management Fund'))
            direct = {}
            for r in range(1, ws.UsedRange.Row + ws.UsedRange.Rows.Count):
                c = ws.Cells(r, 25).Value2
                if isinstance(c, str) and c.strip() in ('R', 'E') and c.strip() not in direct:
                    direct[c.strip()] = ws.Cells(r, 7).Value2
        finally:
            for obj in (wb,):
                try:
                    if obj is not None:
                        obj.Close(SaveChanges=False)
                except Exception:
                    pass
            try:
                if xl is not None:
                    xl.Quit()
            except Exception:
                pass
            pythoncom.CoUninitialize()
        check('revenue and expense equal G of the R and E rows read through Excel',
              abs((direct.get('R') or 0) - (rec['revenue_vnd'] or -1)) < 0.5
              and abs((direct.get('E') or 0) - (rec['expense_vnd'] or -1)) < 0.5,
              f"run log {rec['revenue_vnd']} / {rec['expense_vnd']} vs Excel {direct}")

        # a log folder that cannot be created: a warning, never an exception
        blocker = os.path.join(tmp, 'a_file')
        open(blocker, 'w').close()
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                bad_path, _bad_rec = run_log.write(paths['deliverable'], paths['analysis'], input_path, csv_path,
                                                   log_dir=os.path.join(blocker, 'run_log'))
            check('an unwritable log folder gives a warning and no exception',
                  bad_path is None and 'Run log:' in out.getvalue(), 'no warning, or a record was claimed')
        except Exception as exc:
            check('an unwritable log folder gives a warning and no exception', False,
                  f'raised {type(exc).__name__}: {exc}')

        # a PC without Excel: blank figures, a named status
        real_measure = run_log._excel_measure

        def _no_excel(*_a, **_k):
            raise run_log.ExcelUnavailable('simulated')
        run_log._excel_measure = _no_excel
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                p2, r2 = run_log.write(paths['deliverable'], paths['analysis'], input_path, csv_path,
                                       log_dir=os.path.join(tmp, 'run_log_noexcel'))
        finally:
            run_log._excel_measure = real_measure
        check('without Excel the record has blank figures and status excel_unavailable',
              bool(p2) and r2['status'] == 'excel_unavailable' and r2['revenue_vnd'] is None
              and r2['required_total'] is None and r2['project_name'], f'record: {r2}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    live_after = sorted(os.listdir(live_dir)) if os.path.isdir(live_dir) else None
    check('the live run log folder is exactly as it was', live_before == live_after,
          f'before {live_before}, after {live_after}')
    notes.append(f"run log: {sum(1 for _l, s in rows if s == 'ok')} of {len(rows)} assertions passed "
                 f"(synthetic project, temporary folder only).")
    return (len(differences) == 0), rows, differences, notes


_SERVICE_LEVEL_NAMES_DEFAULT = os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-agent', 'scan-2026-10-07',
                                            'final_v2', 'service_levels_names.txt')


def check_service_levels(paths, input_path, names_list=None):
    """The Service Levels sheet and its two data tables (change add-service-level-table, spec
    budget-workflow-verification). Asserts, on the given run:
      - the analysis workbook carries the sheet and the client deliverable does not;
      - the sheet's people on duty, roster headcount and 24-hour posts equal an independent count of the input's
        Staffing Demand rows (24H = 24 h, other shifts 8 h; roster = ceil x 7/6 for 7-day rows);
      - its NFA equals the Management Fee sheet's total NFA; its measures, levels and 'sát ngưỡng' marks equal an
        independent recomputation from Ref_ServiceLevelThresholds.csv (a value on a cut-off in the higher band, a
        value outside the bounds not classified);
      - the comparison counts equal the form-read, classified rows of Ref_ServiceLevelProjects.csv with the project
        itself left out, and the inferred count is shown apart;
      - no two rows of the real-project table share a fee-paying NFA;
      - neither data table contains a store project or file name (the names list is the build step's own output,
        kept outside the repository; absent on this PC -> noted, not failed).
    Every other sheet and the deliverable are compared with their baselines by the sections before this one.
    Returns (ok, rows, differences, notes); rows are (label, 'ok' | 'FAIL — ...').
    """
    import csv
    import hashlib
    import math
    import sys
    import unicodedata

    import openpyxl

    _src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    import service_levels as sl

    rows, differences, notes = [], [], []

    def check(label, ok, msg=''):
        rows.append((label, 'ok' if ok else f'FAIL — {msg}'))
        if not ok:
            differences.append((label, msg))

    def close(a, b, tol=1e-6):
        return a is not None and b is not None and abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))

    sheet = sl.SHEET_NAME
    check('client deliverable carries no Service Levels sheet', sheet not in _sheet_names(paths['deliverable']), 'present')
    if sheet not in _sheet_names(paths['analysis']):
        check('Service Levels sheet in the analysis workbook', False, 'absent')
        return False, rows, differences, notes

    # ---- the sheet ----------------------------------------------------------------------------
    wb = openpyxl.load_workbook(paths['analysis'], read_only=True, data_only=True)
    try:
        table = list(wb[sheet].iter_rows(values_only=True))
        mf = {str(r[0]).strip(): r[1] for r in wb['Management Fee'].iter_rows(max_col=2, values_only=True) if r and r[0]}
    finally:
        wb.close()
    hdr_i = next((i for i, r in enumerate(table) if r and str(r[0] or '').strip() == 'Service'), None)
    if hdr_i is None:
        check('Service Levels table header', False, 'no header row')
        return False, rows, differences, notes
    cols = {str(v or '').strip(): i for i, v in enumerate(table[hdr_i])}
    svc = {}
    for r in table[hdr_i + 1:hdr_i + 4]:
        if r and r[0] in ('Cleaning', 'Security', 'Landscape'):
            svc[str(r[0]).lower()] = {k: r[i] for k, i in cols.items()}
    check('three service rows on the sheet', set(svc) == {'cleaning', 'security', 'landscape'}, f'found {sorted(svc)}')
    if set(svc) != {'cleaning', 'security', 'landscape'}:
        return False, rows, differences, notes
    check('landscape has no level', 'chưa đặt ngưỡng' in str(svc['landscape'].get('Level', '')), str(svc['landscape'].get('Level')))

    # ---- independent count of the roster's Staffing Demand -------------------------------------------
    # The roster workbook's 'Staffing Demand' is the input's sheet after the tool filled the ratio-driven rows
    # (blank 'Staff On Duty / Day' in the input form), so it is the roster the sheet must tie to. The input form
    # gives only the project name, for the leave-one-out key.
    wi = openpyxl.load_workbook(input_path, read_only=True, data_only=True)
    try:
        proj_name = next((r[1] for r in wi['Project Info'].iter_rows(values_only=True)
                          if r and str(r[0] or '').strip().casefold() == 'project name'), None)
    finally:
        wi.close()
    wr = openpyxl.load_workbook(paths['roster'], read_only=True, data_only=True)
    try:
        sd = list(wr['Staffing Demand'].iter_rows(values_only=True))
    finally:
        wr.close()
    h = next(i for i, r in enumerate(sd) if r and str(r[0] or '').strip() == 'Position')
    hc = {str(v or '').strip(): i for i, v in enumerate(sd[h])}
    ci = {'pos': hc['Position'], 'shift': hc['Shift Code'], 'spd': hc['Staff On Duty / Day'], 'cov': hc['Coverage Days / Week']}
    mine = {'cleaning': {'on_duty': 0.0, 'roster': 0, 'hours': 0.0}, 'security': {'on_duty': 0.0, 'roster': 0, 'hours': 0.0}}
    for r in sd[h + 1:]:
        if not r or not r[ci['pos']]:
            continue
        pos = str(r[ci['pos']]).lower()
        for s in mine:
            if s in pos:
                spd = float(r[ci['spd']] or 0)
                cov = float(r[ci['cov']] or 0)
                mine[s]['on_duty'] += spd
                mine[s]['roster'] += math.ceil(spd * 7 / 6) if cov >= 7 else spd
                mine[s]['hours'] += spd * (24.0 if str(r[ci['shift']] or '').strip().upper() == '24H' else 8.0)
    for s in ('cleaning', 'security'):
        check(f'{s}: people on duty / day equals Staffing Demand', close(svc[s].get('People on duty / day'), mine[s]['on_duty']),
              f"sheet {svc[s].get('People on duty / day')} vs input {mine[s]['on_duty']}")
        check(f'{s}: roster headcount equals the roster rule on Staffing Demand', close(svc[s].get('Roster headcount'), mine[s]['roster']),
              f"sheet {svc[s].get('Roster headcount')} vs input {mine[s]['roster']}")
    check('security: 24h-equivalent posts equal hours / 24', close(svc['security'].get('24h-equivalent posts'), mine['security']['hours'] / 24),
          f"sheet {svc['security'].get('24h-equivalent posts')} vs input {mine['security']['hours'] / 24}")
    nfa_mf = next((v for k, v in mf.items() if k.startswith('Total NFA')), None)
    nfa_sheet = svc['cleaning'].get('Fee-paying NFA (m²)')
    check('fee-paying NFA equals the Management Fee sheet total NFA', close(nfa_sheet, nfa_mf) or (not nfa_sheet and not nfa_mf),
          f'sheet {nfa_sheet} vs Management Fee {nfa_mf}')

    # ---- independent recomputation from the threshold table -----------------------------------------
    with open(sl.THRESHOLDS_CSV, encoding='utf-8-sig', newline='') as fh:
        th = {r['service']: r for r in csv.DictReader(fh)}

    def level_of(v, t):
        if v is None or v <= 0:
            return None, False
        if (t['bound_low'] and v < float(t['bound_low'])) or (t['bound_high'] and v > float(t['bound_high'])):
            return None, False
        c1, c2 = float(t['cutoff_1']), float(t['cutoff_2'])
        lvl = t['level_below_cutoff_1'] if v < c1 else t['level_between'] if v < c2 else t['level_from_cutoff_2']
        return lvl, any(c * 0.9 <= v < c * 1.1 for c in (c1, c2))

    nfa_v = float(nfa_mf or 0)
    expect = {'cleaning': (nfa_v / mine['cleaning']['on_duty']) if nfa_v > 0 and mine['cleaning']['on_duty'] > 0 else None,
              'security': ((mine['security']['hours'] / 24) / (nfa_v / 1e4)) if nfa_v > 0 and mine['security']['hours'] > 0 else None}
    for s in ('cleaning', 'security'):
        lvl, near = level_of(expect[s], th[s])
        got_lvl, got_near = str(svc[s].get('Level') or ''), str(svc[s].get('Near cut-off') or '')
        check(f'{s}: measure recomputed', close(svc[s].get('Measure'), expect[s]) or (svc[s].get('Measure') in (None, '') and expect[s] is None),
              f"sheet {svc[s].get('Measure')} vs {expect[s]}")
        check(f'{s}: level recomputed from the threshold table',
              (got_lvl == lvl) if lvl else got_lvl.startswith('chưa phân loại'), f'sheet {got_lvl!r} vs {lvl!r}')
        check(f'{s}: sát ngưỡng mark recomputed', (got_near == 'sát ngưỡng') == near, f'sheet {got_near!r} vs {near}')
    thr = sl.load_thresholds()
    edges = [('cleaning', 2500, th['cleaning']['level_between']), ('cleaning', 4000, th['cleaning']['level_from_cutoff_2']),
             ('security', float(th['security']['cutoff_1']), th['security']['level_between']),
             ('security', float(th['security']['cutoff_2']), th['security']['level_from_cutoff_2'])]
    for s, v, want in edges:
        got = sl.classify(s, v, thr).level
        check(f'{s}: a value exactly on {v:g} falls in the higher band ({want})', got == want, f'got {got!r}')
    oob = sl.classify('security', 0.08, thr)
    check('security 0.08 is kept, not classified', oob.level is None and oob.value == 0.08 and oob.reason == sl.REASON_OUT_OF_BOUNDS, oob.label)

    # ---- the comparison set ---------------------------------------------------------------------
    projects = sl.load_projects()
    self_key = sl.name_key(proj_name)
    for s in ('cleaning', 'security'):
        values, n_inf = sl.comparison_set(s, projects, self_key, nfa_v if nfa_v > 0 else None)
        check(f'{s}: projects compared = form-read classified rows, project left out',
              close(svc[s].get('Projects compared (form-read)'), len(values)),
              f"sheet {svc[s].get('Projects compared (form-read)')} vs table {len(values)}")
        check(f'{s}: inferred rows shown apart', close(svc[s].get('Inferred rows (reference only, not compared)'), n_inf),
              f"sheet {svc[s].get('Inferred rows (reference only, not compared)')} vs table {n_inf}")
        src_col = 'cln_source' if s == 'cleaning' else 'sec_source'
        lvl_col = 'cln_level' if s == 'cleaning' else 'sec_level'
        n_form = sum(1 for p in projects if p.get(src_col) == sl.SOURCE_FORM and p.get(lvl_col) != sl.NOT_CLASSIFIED)
        check(f'{s}: no inferred row inside the comparison set', len(values) <= n_form, f'{len(values)} compared, {n_form} form-read')
    nfas = [p['nfa_fee_m2'] for p in projects if p.get('nfa_fee_m2')]
    dup = sorted({v for v in nfas if nfas.count(v) > 1})
    check('no two real projects share a fee-paying NFA', not dup,
          'duplicate NFA: ' + ', '.join(p['project_id'] for p in projects if p.get('nfa_fee_m2') in dup))
    notes.append(f'real-project table: {len(projects)} rows, {len(nfas)} with NFA; '
                 + '; '.join(f'{s} {len(sl.comparison_set(s, projects)[0])} form-read compared' for s in ('cleaning', 'security')))

    # ---- the name scan --------------------------------------------------------------------------
    names_path = names_list or os.environ.get('SERVICE_LEVEL_NAMES') or _SERVICE_LEVEL_NAMES_DEFAULT
    if os.path.exists(names_path):
        def norm(x):
            return ''.join(ch for ch in unicodedata.normalize('NFC', str(x or '')).casefold() if ch.isalnum())
        with open(names_path, encoding='utf-8') as fh:
            tokens = {norm(line) for line in fh if len(norm(line)) >= 4}
        leaked = []
        for path in (sl.THRESHOLDS_CSV, sl.PROJECTS_CSV):
            with open(path, encoding='utf-8-sig', newline='') as fh:
                for i, r in enumerate(csv.reader(fh)):
                    for cell in r:
                        c = norm(cell)
                        if c and any(t in c for t in tokens):
                            leaked.append(f'{os.path.basename(path)} row {i}')
        check(f'no store project or file name in either data table ({len(tokens)} names scanned)', not leaked, '; '.join(leaked[:5]))
    else:
        notes.append('name scan skipped: the names list from the build step is not on this PC '
                     f'({names_path}); set SERVICE_LEVEL_NAMES to run it')
    _ = hashlib  # the key function lives in service_levels; kept importable here for a manual check
    return not differences, rows, differences, notes


_REAL_BUDGET_NAMES_DEFAULT = os.path.join(os.path.expanduser('~'), 'Savills-local', 'budget-agent', 'scan-2026-10-07',
                                          'final_v4', 'real_budget_ranges_names.txt')   # store v4 (2026-10-22)


def read_real_budget_ranges_sheet(analysis_path):
    """The 'Real-Budget Ranges' sheet as (info {label: value}, summary [{header: value}], used {code: [ids]}),
    or None when the sheet is absent."""
    import openpyxl
    import real_budget_ranges as rbr
    from generate_project_output import RBR_HEADERS
    wb = openpyxl.load_workbook(analysis_path, read_only=True, data_only=True)
    try:
        if rbr.SHEET_NAME not in wb.sheetnames:
            return None
        table = [tuple(r) for r in wb[rbr.SHEET_NAME].iter_rows(values_only=True)]
    finally:
        wb.close()
    info, summary, used = {}, [], {}
    hdr = next(i for i, r in enumerate(table) if r and r[0] == RBR_HEADERS[0] and r[1] == RBR_HEADERS[1])
    for r in table[3:hdr]:
        if r and r[0]:
            info[str(r[0]).strip()] = r[1]
    for r in table[hdr + 1:]:
        if not r or not r[0]:
            break
        summary.append(dict(zip(RBR_HEADERS, r)))
    code = None
    for r in table[hdr + len(summary) + 1:]:
        first = str(r[0] or '') if r else ''
        if ' — ' in first and first.endswith('every project with a value'):
            code = first.split(' — ')[0].strip()
            used[code] = []
        elif code and re.fullmatch(r'P\d{3,}', first) and r[5] == 'used':
            used[code].append(first)
    return info, summary, used


def name_leaks(names_path, data_paths):
    """(names scanned, ['<file> row <i>', ...]): the rows of the data files holding any name of the names list
    (one per line, compared NFC, case-folded, letters and digits only; names under 4 characters are skipped)."""
    import csv

    def norm(x):
        return ''.join(ch for ch in unicodedata.normalize('NFC', str(x or '')).casefold() if ch.isalnum())
    with open(names_path, encoding='utf-8') as fh:
        tokens = {norm(line) for line in fh if len(norm(line)) >= 4}
    leaked = []
    for path in data_paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8-sig', newline='') as fh:
            for i, r in enumerate(csv.reader(fh)):
                if any(norm(c) and any(t in norm(c) for t in tokens) for c in r):
                    leaked.append(f'{os.path.basename(path)} row {i}')
    return len(tokens), leaked


def real_budget_ranges_problems(info, summary, used, fund_sums, values_rows):
    """Pure check of the 'Real-Budget Ranges' sheet against the deliverable (spec budget-workflow-verification).
    fund_sums is {code: the sum of its twelve month cells on '2. Budget-Management Fund'}; values_rows is
    real_budget_ranges.load_values(). Returns [(label, message)] for every problem; [] when the sheet ties."""
    import real_budget_ranges as rbr
    probs = []
    name, nfa = info.get('Project'), info.get('Fee-paying NFA (m²)')
    keys = rbr.self_keys(name)
    by_id = {}
    for x in values_rows or []:
        by_id.setdefault(x['project_id'], x)
    for s in summary:
        code, role = s['Code'], s['Role']
        if role == 'Cross-check':
            if s['Written to the deliverable (VND/year)'] not in (None, ''):
                probs.append((code, 'a cross-check code carries a figure written to the deliverable'))
            continue
        sheet = float(s['Written to the deliverable (VND/year)'] or 0)
        got = float(fund_sums.get(code) or 0)
        if abs(sheet - got) > 0.5:
            probs.append((code, f'Real-Budget Ranges {sheet:,.0f} vs 2. Budget-Management Fund {got:,.0f}'))
        if sheet and (s['Projects used'] or 0) < rbr.MIN_PROJECTS:
            probs.append((code, f"priced from {s['Projects used']} projects, under the floor of {rbr.MIN_PROJECTS}"))
        if len(used.get(code, [])) != (s['Projects used'] or 0):
            probs.append((code, f"{len(used.get(code, []))} ids marked used vs {s['Projects used']} in the summary"))
        for pid in used.get(code, []):
            x = by_id.get(pid)
            if x and rbr.is_self(x, keys, nfa):
                probs.append((code, f'{pid} is the project itself but is among the values used'))
    return probs


def check_real_budget_ranges(paths, names_list=None):
    """The 'Real-Budget Ranges' sheet (change use-real-budget-ranges, spec budget-workflow-verification):
      - the analysis carries it and the client deliverable does not;
      - every priced code's figure on the sheet equals the sum of its twelve months on '2. Budget-Management
        Fund', and a cross-check code writes nothing;
      - a priced code uses at least 10 projects, and none of them is the project itself (name or NFA within 0.5%);
      - a negative probe: the same check on the deliverable with ESS12 1,000 VND off fails and names ESS12;
      - the values file and its README carry no store project or file name (names list kept outside the
        repository; absent on this PC -> noted, not failed).
    Returns (ok, rows, differences, notes)."""
    import csv
    import sys
    import unicodedata

    import openpyxl

    _src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    import real_budget_ranges as rbr

    rows, differences, notes = [], [], []

    def check(label, ok, msg=''):
        rows.append((label, 'ok' if ok else f'FAIL — {msg}'))
        if not ok:
            differences.append((label, msg))

    check('client deliverable carries no Real-Budget Ranges sheet',
          rbr.SHEET_NAME not in _sheet_names(paths['deliverable']), 'present')
    got = read_real_budget_ranges_sheet(paths['analysis'])
    if got is None:
        check('Real-Budget Ranges sheet in the analysis workbook', False, 'absent')
        return False, rows, differences, notes
    info, summary, used = got
    check('every code in scope on the sheet', [s['Code'] for s in summary] == list(rbr.ALL_CODES),
          f"found {[s['Code'] for s in summary]}")

    wb = openpyxl.load_workbook(paths['deliverable'], read_only=True, data_only=False)
    try:
        fund_sums = {}
        for i, r in enumerate(wb['2. Budget-Management Fund'].iter_rows(min_row=79, max_row=494, max_col=25,
                                                                         values_only=True), start=79):
            code = str(r[24] or '').strip()
            if code in rbr.ALL_CODES:
                # the months as written, or their originals once '4. Điều chỉnh' has linked them (docs/32)
                fund_sums[code] = sum(fund_months_as_written(wb, '2. Budget-Management Fund', i))
    finally:
        wb.close()
    values_rows = rbr.load_values()
    probs = real_budget_ranges_problems(info, summary, used, fund_sums, values_rows)
    for code, msg in probs:
        check(f'{code} ties, floor and leave-one-out', False, msg)
    priced = [s['Code'] for s in summary if s['Role'] != 'Cross-check' and s['Written to the deliverable (VND/year)']]
    check(f'{len(priced)} priced code(s) tie to the deliverable, use 10+ projects, leave the project out', not probs,
          f'{len(probs)} problem(s)')
    probe = dict(fund_sums, ESS12=(fund_sums.get('ESS12') or 0) + 1000)
    caught = [p for p in real_budget_ranges_problems(info, summary, used, probe, values_rows) if p[0] == 'ESS12']
    check('negative probe: ESS12 1,000 VND off fails and names ESS12', bool(caught), 'not caught')
    notes.append('Real-Budget Ranges: ' + ', '.join(
        f"{s['Code']} {float(s['Written to the deliverable (VND/year)'] or 0):,.0f}" for s in summary
        if s['Role'] != 'Cross-check'))

    names_path = names_list or os.environ.get('REAL_BUDGET_NAMES') or _REAL_BUDGET_NAMES_DEFAULT
    if os.path.exists(names_path) and os.path.exists(rbr.VALUES_CSV):
        n_names, leaked = name_leaks(names_path, (rbr.VALUES_CSV, os.path.join(rbr.DATA_DIR, 'README.txt')))
        check(f'no store project or file name in the values file ({n_names} names scanned)', not leaked,
              '; '.join(leaked[:5]))
    else:
        notes.append('real-budget name scan skipped: the names list from the build step is not on this PC '
                     f'({names_path}); set REAL_BUDGET_NAMES to run it')
    return not differences, rows, differences, notes


def _main():
    import sys
    import tempfile

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from verification.run_workflow import run_workflow

    with tempfile.TemporaryDirectory(prefix='budget_checks_') as workdir:
        print('running both generators against the sample...\n')
        outputs, _, _ = run_workflow(workdir=workdir)
        paths = locate_outputs(outputs)

        results = check_sheets(paths)
        print('sheet-presence check:')
        for label, r in results.items():
            want = len(EXPECTED_SHEETS[label])
            extra = f'  (+{len(r["unexpected"])} unexpected: {r["unexpected"]})' if r['unexpected'] else ''
            print(f'  OK    {label:12} {want}/{want} expected sheets present{extra}')

        # Prove the check actually fails, and names the sheet — a check that has never been seen to
        # fail is not known to work.
        print('\nnegative test — asserting against a sheet the pipeline does not produce:')
        probe = dict(EXPECTED_SHEETS)
        probe['analysis'] = list(EXPECTED_SHEETS['analysis']) + ['Sheet That Does Not Exist']
        try:
            check_sheets(paths, expected=probe)
        except StructureError as exc:
            named = 'Sheet That Does Not Exist' in str(exc)
            print(f'  {"OK  " if named else "FAIL"}  raised StructureError and named the missing sheet')
            print(f'  message: {str(exc).splitlines()[1].strip()[:120]}')
        else:
            print('  FAIL  no error raised — the check does not actually check anything')
            return 1

        # ---- corruption artifacts ----
        print('\ncorruption-artifact scan:')
        artifacts = check_artifacts(paths)
        for label in artifacts:
            print(f'  OK    {label:12} no repair-triggering artifacts')

        # Negative test: inject a real OneDrive-style artifact into a copy and confirm detection.
        print('\nnegative test — injecting a [trash] artifact into a copy of the deliverable:')
        import shutil
        import zipfile
        probe_path = os.path.join(workdir, 'probe_corrupted.xlsx')
        shutil.copy(paths['deliverable'], probe_path)
        with zipfile.ZipFile(probe_path, 'a') as z:
            z.writestr('[trash]/0000.dat', b'injected by the verification negative test')
        found = scan_artifacts(probe_path)
        detected = any('OneDrive' in f for f in found)
        print(f'  {"OK  " if detected else "FAIL"}  scan_artifacts flagged the injected artifact')
        if detected:
            print(f'  finding: {found[0][:110]}')
        try:
            check_artifacts({'probe': probe_path})
        except CorruptionArtifact as exc:
            named = 'probe_corrupted.xlsx' in str(exc)
            print(f'  {"OK  " if named else "FAIL"}  check_artifacts raised and named the file')
        else:
            print('  FAIL  check_artifacts did not raise on a known-bad file')
            return 1
        if not detected:
            return 1

        # ---- formula errors after a full recalculation ----
        print('\nformula-error scan:')
        fe = check_formula_errors(paths)
        print(f'  method actually used: {fe["method"]}'
              + ('   << DEGRADED' if fe['degraded'] else '   (full recalculation)'))
        if fe['degraded']:
            print(f'  reason: {fe["reason"]}')
            print('  WARNING: recalculation-only errors were NOT detectable in this run')
        print(f'  blank-template baseline: {fe["baseline_size"]} error cells already present')
        for label in fe['results']:
            new, old = len(fe['introduced'][label]), len(fe['inherited'][label])
            print(f'  {"OK  " if not new else "FAIL"}  {label:12} {new} introduced, {old} inherited from the template')

        # Negative test 1: a real formula error must be caught, and named by sheet and cell.
        print('\nnegative test — injecting =1/0 into a copy of the analysis workbook:')
        import openpyxl
        bad = os.path.join(workdir, 'probe_formula_error.xlsx')
        shutil.copy(paths['analysis'], bad)
        wbp = openpyxl.load_workbook(bad)
        target = wbp['Summary']
        target['Z99'] = '=1/0'
        wbp.save(bad)
        wbp.close()
        try:
            check_formula_errors({'probe': bad})
        except FormulaError as exc:
            msg = str(exc)
            named = "'Summary'" in msg and 'Z99' in msg
            print(f'  {"OK  " if named else "FAIL"}  raised FormulaError naming the sheet and cell')
            print(f'  message: {msg.splitlines()[1].strip()[:130]}')
            if not named:
                return 1
        else:
            print('  FAIL  a =1/0 cell was not detected')
            return 1

        # Negative test 2 (design D5): the reduced path must announce itself.
        print('\nnegative test — forcing the degraded path:')
        deg = check_formula_errors(paths, force_degraded=True)
        says = 'were NOT detectable' in deg['note'] and deg['degraded']
        print(f'  {"OK  " if says else "FAIL"}  result states the reduced check ran and what it could not see')
        print(f'  method: {deg["method"]}   reason: {deg["reason"]}')
        if not says:
            return 1

        total_inherited = sum(len(v) for v in fe['inherited'].values())
        print(f'\nRESULT: all three workbooks have their expected sheets, carry no corruption '
              f'artifacts, and introduce no Excel errors (method: {fe["method"]}). '
              f'{total_inherited} error cell(s) are inherited from the blank template, which '
              f'itself carries {fe["baseline_size"]}. Every check fails correctly when given a bad '
              f'input, and the reduced check announces itself.')
        return 0


if __name__ == '__main__':
    import sys
    sys.exit(_main())


def check_distance_ranking():
    """Real-distance ranking with its ±20% cap (change apply-head-of-pm-decisions-2026-10, group 4, tasks 4.1-4.2),
    exercised on an INVENTED set of comparables with coordinates: the standard sample carries none, so without this
    the distance path would never run in verify.

    Asserts, for a project at (10.7700, 106.7000) of 10,000 m2 against 'Near' (0.1 km away, 40% off in size, no real
    relation to any project) and 'Far' (same size, no coordinates):
      - the module has the distance comparison switched on;
      - with coordinates, 'Near' ranks first; without them, 'Far' does, and every rate equals the no-distance rate;
      - a Shophouse rate the ranking moves by 200% is capped at +20%, and so is the blended fallback rate;
      - a rate moved by 10% is left alone.
    Returns (ok, rows, differences, notes) like the other checks; rows are (label, 'ok'|'fail')."""
    import master_comparables as mc
    rows, diffs = [], []

    def check(label, ok, why=''):
        rows.append((label, 'ok' if ok else 'fail'))
        if not ok:
            diffs.append((label, why))

    def comp(name, nfa, apt, shop, lat=None, lon=None):
        c = dict(name=name, nfa=nfa, district=None, city=None, mgmt_rate=apt, mgmt_rate_vat=None,
                 rates={'Apartment': apt, 'Shophouse': shop})
        if lat is not None:
            c['lat'], c['lon'] = lat, lon
        return c

    saved_pool, saved_flag = mc.MASTER_COMPARABLES[:], mc.DISTANCE_COMPARISON_ENABLED
    try:
        check('distance comparison is switched on', mc.DISTANCE_COMPARISON_ENABLED is True,
              'master_comparables.DISTANCE_COMPARISON_ENABLED is not True')
        lat, lon = 10.7700, 106.7000
        mc.MASTER_COMPARABLES[:] = [comp('Near', 14_000, 30_000, 30_000, 10.7701, 106.7001),
                                    comp('Far', 10_000, 10_000, 10_000)]
        names = lambda cs: [c['name'] for c in cs]
        check('with coordinates the within-1 km comparable ranks first',
              names(mc.nearest_comparables(10_000, n=2, input_lat=lat, input_lon=lon)) == ['Near', 'Far'],
              'expected Near before Far')
        check('without coordinates the same-size comparable ranks first',
              names(mc.nearest_comparables(10_000, n=2)) == ['Far', 'Near'], 'expected Far before Near')
        shop, shop_used, shop_note, _ = mc.derive_product_rate_capped(10_000, 'ZZ New', 'Shophouse',
                                                                      input_lat=lat, input_lon=lon, n=1)
        check('a non-Apartment rate moved by distance is capped at +20%',
              shop == 12_000 and names(shop_used) == ['Near'] and 'clamped' in (shop_note or ''),
              f'got {shop} from {names(shop_used)}')
        apt, _u, apt_note, _ = mc.derive_product_rate_capped(10_000, 'ZZ New', 'Apartment',
                                                             input_lat=lat, input_lon=lon, n=1)
        check('the Apartment rate moved by distance is capped at +20%', apt == 12_000 and 'clamped' in (apt_note or ''),
              f'got {apt}')
        blended, b_used, b_note, _ = mc.derive_mgmt_rate_capped(10_000, 'ZZ New', input_lat=lat, input_lon=lon, n=1)
        check('the blended fallback rate is capped at +20%',
              blended == 12_000 and names(b_used) == ['Near'] and 'clamped' in (b_note or ''), f'got {blended}')
        none_rate, _u2, _n2, _r2 = mc.derive_product_rate_capped(10_000, 'ZZ New', 'Shophouse', n=1)
        check('without coordinates the rate is the no-distance rate', none_rate == 10_000, f'got {none_rate}')
        mc.MASTER_COMPARABLES[:] = [comp('Near', 14_000, 11_000, 11_000, 10.7701, 106.7001),
                                    comp('Far', 10_000, 10_000, 10_000)]
        small, _u3, small_note, _ = mc.derive_product_rate_capped(10_000, 'ZZ New', 'Shophouse',
                                                                  input_lat=lat, input_lon=lon, n=1)
        check('a rate moved by 10% is left alone', small == 11_000 and 'clamped' not in (small_note or ''),
              f'got {small}')
    finally:
        mc.MASTER_COMPARABLES[:] = saved_pool
        mc.DISTANCE_COMPARISON_ENABLED = saved_flag
    return (not diffs), rows, diffs, ['invented comparables with coordinates; the standard sample carries none']
