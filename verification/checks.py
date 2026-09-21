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


def check_revenue_agreement(paths):
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

    sum_fills = sum(year1_fills())

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
# fixed row number: the section's position shifts with the number of comparables and note rows. See
# generate_project_budget.py add_comparison_sheet() and change benchmark-proposal-against-comparables.
_BENCHMARK_RECONCILE = [
    ('Year-1 management-fee revenue (VND)',   'H14'),
    ('Year-1 total operating income (VND)',   'H13'),
    ('Year-1 total operating cost (VND)',     'H20'),
    ('Year-1 operating surplus (VND)',        'H46'),
]
_BENCHMARK_REVENUE_LABEL = 'Year-1 management-fee revenue (VND)'


def check_benchmark_reconciles(paths):
    """Confirm the client deliverable's Comparison-sheet PROPOSAL BENCHMARK section carries the
    deliverable's own '1. Summary' figures forward, rather than restating (and possibly drifting
    from) them.

    The benchmark's own-project revenue / operating income / operating cost / operating surplus
    cells are written as formulas into '1. Summary' (change benchmark-proposal-against-comparables,
    design D1), so this should hold by construction; the check fails if a reference has broken
    (#REF!, wrong cell) or a cell evaluates to an error. It also confirms each "revenue if charged
    at comparable X's rate" projection is a finite positive number, and — where that comparable's
    rate equals this project's derived rate (the projection formula is a bare '1. Summary'!H14) —
    that the projection equals the own-project revenue.

    Returns (ok, rows, differences, notes) where `rows` is [(label, benchmark_vnd, summary_vnd)].
    Raises BaselineUnavailable if Excel cannot be driven.
    """
    import shutil
    import tempfile

    from verification.baseline import BaselineUnavailable

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            'The proposal-benchmark reconciliation check requires Excel — the Comparison sheet and '
            f"'1. Summary' both store these figures as live formulas ({exc}).") from exc

    tmp = tempfile.mkdtemp(prefix='benchmark_recon_')
    dwork = os.path.join(tmp, 'deliverable_' + os.path.basename(paths['deliverable']))
    shutil.copy(paths['deliverable'], dwork)

    def _num(v):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    pythoncom.CoInitialize()
    xl = dwb = None
    rows, differences, notes = [], [], []
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        dwb = xl.Workbooks.Open(dwork, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {ws.Name: ws for ws in dwb.Worksheets}
        cmp_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('Comparison')), None)
        sum_ws = next((sheets[n] for n in sheets if _nfc(n) == _nfc('1. Summary')), None)
        if cmp_ws is None or sum_ws is None:
            raise RuntimeError("deliverable is missing the 'Comparison' or '1. Summary' sheet")

        used = cmp_ws.UsedRange
        last_row = used.Row + used.Rows.Count - 1
        col_a = {}
        for rr in range(1, last_row + 1):
            a = cmp_ws.Cells(rr, 1).Value2
            if isinstance(a, str) and a.strip():
                col_a.setdefault(rr, a.strip())

        def _row_starting(prefix):
            return next((rr for rr in sorted(col_a) if col_a[rr].startswith(prefix)), None)

        for prefix, summary_cell in _BENCHMARK_RECONCILE:
            rr = _row_starting(prefix)
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

        # projections: the "revenue" row's columns C.. (one per comparable)
        rr = _row_starting(_BENCHMARK_REVENUE_LABEL)
        own_rev = _num(cmp_ws.Cells(rr, 2).Value2) if rr else None
        if rr and own_rev is not None:
            col = 3
            while True:
                raw = cmp_ws.Cells(rr, col).Value2
                if raw is None or (isinstance(raw, str) and not raw.strip()):
                    break
                proj = _num(raw)
                formula = str(cmp_ws.Cells(rr, col).Formula or '')
                tail = formula.split('!')[-1] if '!' in formula else formula
                bare_ref = ('+' not in tail and '-' not in tail)  # rate == derived rate
                label = f'projection column {col}'
                rows.append((label, proj, own_rev if bare_ref else None))
                if proj is None or proj <= 0:
                    differences.append((label, proj, None))
                elif bare_ref and abs(proj - own_rev) > max(5_000.0, abs(own_rev) * 5e-5):
                    differences.append((label, proj, own_rev))
                col += 1
        dwb.Close(SaveChanges=False)
        dwb = None
    except Exception as exc:
        raise BaselineUnavailable(
            'Excel could not evaluate the deliverable for the proposal-benchmark reconciliation '
            f'check: {type(exc).__name__}: {exc}') from exc
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

    notes.append("PROPOSAL BENCHMARK own-project cells are formulas into '1. Summary' — this "
                 'confirms none has broken (#REF!, wrong cell) and the projections evaluate.')
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
    'EEW':  ['m3/month', 'PBVMT', 'lấp đầy cư dân'],
    'EEE':  ['kWh', '1279', '40%'],
    'EED':  ['0.005S', 'test', 'backup'],
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
    ('2.2 Common area Fund', 'RP5'),         # template placeholder, literally "demo"
    ('2.2 Common area Fund', 'VAT1'),        # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'VAT2'),        # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT1'),        # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT1a'),       # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT1b'),       # "[Lưu ý nội bộ: ...]" internal accounting note
    ('2.2 Common area Fund', 'CIT2'),        # "[Lưu ý nội bộ: ...]" internal accounting note
}


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

        # VAT sentence
        if incl_vat and vat_vi not in k:
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
            if incl_vat and vat_vi not in t:
                fail(label, 'inclusive-of-VAT run but this written T remark has no VAT-treatment sentence')
                row_failed = True
            t_has_vi = any(ch in t for ch in 'ạảấầẩẫậắằẳẵặẹẻẽếềểễệọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ')
            if not t_has_vi:
                fail(label, 'line-level remark has no Vietnamese content')
                row_failed = True
            bad = next((needle for needle in _INTERNAL_ARTIFACT_DENYLIST if needle in t), None)
            if bad:
                fail(label, f'line-level remark names an internal artifact in its text: {bad!r}')
                row_failed = True
            if not row_failed:
                ok(label)

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
        # F (Unit Price) is a literal the pipeline wrote directly — G is a formula pulling from it,
        # unevaluated under this function's own data_only=False load (see the docstring above).
        _ess9_f = fund.cell(row=_ess9_row, column=6).value
        if isinstance(_ess9_f, (int, float)) and not isinstance(_ess9_f, bool) and _ess9_f:
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

# This check's own enforceable scope — the sheet(s) a zero-with-no-reason code actually FAILs the
# run on. '2.2 Common area Fund' is scanned and reported (below) but never fails here: its own
# Required-code completeness is entirely downstream of change activate-common-area-fund-cost-share
# (still pending PM/finance sign-off) — every one of its expense codes either cascades to non-zero
# once that lands, or needs that change's own remark work, not this one's. Failing this run on a
# sheet this change does not own would conflate two separately-gated changes' completion criteria.
_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS = ('2. Budget-Management Fund',)

# EMA1-4 are Required but have no itemized comparable source anywhere in this repo (change
# fill-guideline-required-line-items, design D3, task 3.2) — they stay folded into EMA15's
# catch-all, and D3's own fallback puts the "stated reason" on EMA15's remark, not on EMA1-4's own
# (blank) remark cells. Recorded here as the one documented exception, not inferred at check time.
_REQUIRED_CODE_DISCLOSED_ON = {'EMA1': 'EMA15', 'EMA2': 'EMA15', 'EMA3': 'EMA15', 'EMA4': 'EMA15'}


def check_required_line_items(paths):
    """Confirm every code the AI Guideline classifies 'Bắt buộc/Required' on
    '2. Budget-Management Fund' carries a non-zero figure, or a stated reason for staying zero
    (change fill-guideline-required-line-items, spec guideline-required-line-items).

    Also scans '2.2 Common area Fund' and reports its status as notes, but never fails the run on
    it — see _REQUIRED_CLASSIFICATION_ENFORCED_SHEETS.

    Reads `data/master_list_verified/AI_Guideline_Required_Classification.csv` (task 1's own
    transcribed reference — NFC-normalised at extraction time, see that CSV's own header). For
    each Required leaf code on an enforced sheet (SUBTOTAL/header rows excluded, the same
    'SUBTOTAL' in the G-formula signal check_summary_reconciles uses):

      - non-zero G -> pass;
      - zero G, but the code's own T (Remarks) cell is non-empty -> pass (a stated reason);
      - zero G, and the code is one of EMA1-4 (see _REQUIRED_CODE_DISCLOSED_ON) -> check the named
        code's remark instead (EMA15's catch-all disclosure covers all four);
      - zero G with no remark anywhere applicable -> FAIL, naming the code.

    A Required code with no matching Y-column row on the deliverable at all (a template-version
    mismatch between the reference file and the live form — PL1/PL2/PL2CA/ERCS/ERCS1 as of
    2026-09-14) is reported as a note, not a failure — a separate, already-documented concern
    (docs/14-required-line-item-gaps.md), not something this check can price or explain.

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
            maxr = 495 if sheet_name.startswith('2. Budget') else 300
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

                if isinstance(t, str) and t.strip():
                    rows.append((label, 'ok — zero, reason stated'))
                elif enforced:
                    differences.append((label, 'Required code is zero with no stated reason'))
                    rows.append((label, 'FAIL — zero, no stated reason'))
                else:
                    sheet_pending.append(label)

            if sheet_pending:
                notes.append(
                    f"'{sheet_name}' — {len(sheet_pending)} Required code(s) still zero with no "
                    f"stated reason, not failed here: this sheet's own completeness is gated on "
                    f"change activate-common-area-fund-cost-share (pending PM/finance sign-off), "
                    f"not this change. {', '.join(c for c in sheet_pending)}")

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
        for r in range(1, 495):
            code = fund_ws.Cells(r, 25).Value2  # Y — cost code
            if not (isinstance(code, str) and code.strip()):
                continue
            code = code.strip()
            if code not in written_codes:
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
