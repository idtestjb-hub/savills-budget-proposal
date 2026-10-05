"""
Extracts the headline figures from a generated analysis workbook, and hand-checks a few of them.

WHY THIS NEEDS EXCEL, unavoidably: the analysis workbook's headline cells are live formulas, and
openpyxl writes formulas without evaluating them. Reading the file with openpyxl returns None for
almost every figure here. So unlike the structural checks, there is no weaker fallback for the
numeric baseline — without Excel there is no baseline at all, and this module says so rather than
recording a page of nulls.

The figures follow design D4: the totals a reviewer would actually check.
"""
import os

VND = 'VND'
RATE = 'VND/m²/month'
RATIO = 'ratio'

# name, sheet, row, column, unit — fixed positions on the Summary sheet, which has a stable layout.
CELL_FIGURES = [
    ('derived_apartment_rate',        'Summary', 33, 2, RATE),
    ('mgmt_fee_revenue_monthly',      'Summary', 34, 2, VND),
    ('mgmt_fee_revenue_annual',       'Summary', 35, 2, VND),
    ('staff_cost_annual',             'Summary', 36, 2, VND),
    ('service_reference_annual',      'Summary', 37, 2, VND),
    ('capex_selected',                'Summary', 38, 2, VND),
    ('opex_annual',                   'Summary', 39, 2, VND),
    ('additional_revenue_annual',     'Summary', 40, 2, VND),
    ('total_profit_value',            'Summary', 19, 2, VND),
    ('margin',                        'Summary', 20, 2, RATIO),
    ('markup',                        'Summary', 21, 2, RATIO),
]

# name, sheet, label to find in column A, column holding the value, unit.
# Located by label because these rows shift: the Capex item list grows and shrinks with the project,
# which moves every subtotal below it. A fixed row number would silently read the wrong line.
LABEL_FIGURES = [
    ('service_security_annual',   'Service',       'Security',                               8, VND),
    ('service_cleaning_annual',   'Service',       'Cleaning',                               8, VND),
    ('service_landscape_annual',  'Service',       'Landscape',                              8, VND),
    ('capex_mo_equipment',        'Cost Priority', 'MO Equipment',                           2, VND),
    ('capex_public_area',         'Cost Priority', 'Public Area',                            2, VND),
    ('capex_me_equipment',        'Cost Priority', 'M&E Equipment',                          2, VND),
    ('capex_amenity_area',        'Cost Priority', 'Amenity Area',                           2, VND),
    ('opex_electricity_annual',   'OPEX',          'Electricity',                            3, VND),
    ('opex_water_annual',         'OPEX',          'Water',                                  3, VND),
    ('opex_diesel_annual',        'OPEX',          'Diesel (Generator Fuel)',                3, VND),
    ('opex_repairs_annual',       'OPEX',          'Repairs & Maintenance (materials only)', 3, VND),
    ('opex_admin_annual',         'OPEX',          'Administrative Expense (office overhead)', 3, VND),
    ('opex_pool_salt_annual',     'OPEX',          'Pool Salt',                              3, VND),
]

UNITS = {name: unit for name, _, _, _, unit in CELL_FIGURES}
UNITS.update({name: unit for name, _, _, _, unit in LABEL_FIGURES})


class BaselineUnavailable(RuntimeError):
    """Raised when the numeric baseline cannot be produced at all."""


class FigureMissing(RuntimeError):
    """Raised when an expected figure is absent or null in the generated workbook."""


def _read_sheet_values(worksheet):
    used = worksheet.UsedRange
    values = used.Value2
    if values is None:
        return [], used.Row, used.Column
    if not isinstance(values, tuple):
        values = ((values,),)
    elif values and not isinstance(values[0], tuple):
        values = (values,)
    return values, used.Row, used.Column


def extract_figures(analysis_path):
    """Open a COPY in Excel, recalculate, and pull every figure in D4.

    Returns {name: {'value','unit','where'}}. Raises BaselineUnavailable if Excel cannot be driven.
    """
    import shutil
    import tempfile

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            'The numeric baseline requires Excel: the analysis workbook stores its headline figures '
            'as formulas with no cached values, so they cannot be read without recalculation. '
            f'Python cannot reach Excel here ({exc}). No baseline was produced — this is not a '
            'weaker baseline, it is none.'
        ) from exc

    work = os.path.join(tempfile.mkdtemp(prefix='baseline_'), os.path.basename(analysis_path))
    shutil.copy(analysis_path, work)

    pythoncom.CoInitialize()
    xl = None
    wb = None
    figures = {}
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()

        sheets = {ws.Name: ws for ws in wb.Worksheets}

        for name, sheet, row, col, unit in CELL_FIGURES:
            if sheet not in sheets:
                continue
            figures[name] = {
                'value': sheets[sheet].Cells(row, col).Value2,
                'unit': unit,
                'where': f'{sheet}!R{row}C{col}',
            }

        for name, sheet, label, col, unit in LABEL_FIGURES:
            if sheet not in sheets:
                continue
            values, r0, c0 = _read_sheet_values(sheets[sheet])
            for ri, values_row in enumerate(values):
                first = values_row[0] if values_row else None
                if isinstance(first, str) and first.strip() == label:
                    figures[name] = {
                        'value': sheets[sheet].Cells(r0 + ri, col).Value2,
                        'unit': unit,
                        'where': f'{sheet}!{label!r} row {r0 + ri}, col {col}',
                    }
                    break
    except Exception as exc:
        raise BaselineUnavailable(
            f'Excel could not evaluate the analysis workbook: {type(exc).__name__}: {exc}'
        ) from exc
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

    expected = [n for n, *_ in CELL_FIGURES] + [n for n, *_ in LABEL_FIGURES]
    missing = [n for n in expected if n not in figures or figures[n]['value'] is None]
    if missing:
        raise FigureMissing(
            'These expected figures are absent or null in the generated workbook: '
            + ', '.join(missing)
            + '. Either the sheet layout moved, or the pipeline stopped producing them. A baseline '
              'with holes in it is not a baseline — fix the extraction before recording one.'
        )
    return figures


def read_sample_scale(sample_path):
    """The synthetic project's own inputs, read straight from the fixture.

    Used to hand-check figures from first principles rather than from the workbook that produced
    them — a check that reads its expectation out of the thing under test proves nothing.

    Read BY LABEL, for the same reason generate_project_budget.read_input() is. This function used
    to read fixed addresses (C14/C16/C18/B21/B22/B27). When the Product Mix block grew from 5
    products to 9, every row below it moved down four, and five of these seven values silently
    became 0 or None on the current fixture — which did not fail anything, because the two checks
    that consume them then fell back to the workbook under test (the management-fee check) or
    compared against zero (the parking check). Both went on reporting OK while proving nothing.
    Reading by label is what stops that; raising on a miss is what stops it from recurring
    silently, since a hand-check that cannot find its input must fail, not degrade.
    """
    import openpyxl

    from generate_project_budget import PRODUCT_ROWS
    from input_labels import SheetLabels

    wb = openpyxl.load_workbook(sample_path, data_only=True)
    try:
        ws = wb['Project Info']
        L = SheetLabels(ws)
        # Product rows carry GFA/NFA/Units across columns B/C/D; scalars carry one value in B.
        return {
            # Every product the tool can price, by its PRODUCT_ROWS name (the Vietnamese half of
            # 'Nursery / Nhà trẻ' is part of its label: normalise() splits on '(' and dashes, not
            # '/'). row_of() raises on a missing label, so a form without one of the nine rows
            # fails this hand-check by name instead of being read from a fallback position.
            'product_nfa': {p: ws.cell(row=L.row_of(p), column=3).value for p in PRODUCT_ROWS},
            'apartment_units': ws.cell(row=L.row_of('Apartment'), column=4).value,
            'car_slots': L.value('Car Parking Slots'),
            'moto_slots': L.value('Moto Parking Slots'),
            'gates': L.value('Gate / Entrance Count'),
        }
    finally:
        wb.close()


def hand_checks(figures, sample_path, analysis_path):
    """Recompute figures independently and compare, per task 4.2.

    Each check derives its expectation from the synthetic project's own inputs or from the workbook's
    own component cells — never from the headline cell it is checking. That is what proves the
    extractor reads the intended cell rather than one next to it.

    Returns a list of (name, expected, actual, matched, how).
    """
    import shutil
    import tempfile

    import pythoncom
    import win32com.client

    from generate_project_budget import PRODUCT_ROWS

    scale = read_sample_scale(sample_path)
    work = os.path.join(tempfile.mkdtemp(prefix='handcheck_'), os.path.basename(analysis_path))
    shutil.copy(analysis_path, work)

    pythoncom.CoInitialize()
    xl = None
    wb = None
    checks = []
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()

        # --- 1. Management fee revenue: every product's NFA (from the INPUT file) x its rate ---
        mf = wb.Worksheets('Management Fee')
        values, r0, _ = _read_sheet_values(mf)
        per_product = []
        for ri, row in enumerate(values):
            label = row[0] if row else None
            if isinstance(label, str) and label.strip() in PRODUCT_ROWS:
                nfa = mf.Cells(r0 + ri, 2).Value2
                rate = mf.Cells(r0 + ri, 3).Value2
                # Product names repeat further down in the PER-PRODUCT RATE NOTES block, where the
                # neighbouring cells hold explanatory prose. Only the pricing table has numbers in
                # both columns, so that is what identifies it.
                if isinstance(nfa, (int, float)) and isinstance(rate, (int, float)):
                    per_product.append((label.strip(), nfa, rate))

        def _input_area(product):
            # Every product is anchored to the input file. A blank or non-numeric cell is read as
            # 0 m2 (the form says "leave 0 for products this project doesn't have"), so a workbook
            # that prices an area the input does not have fails the anchoring test below.
            raw = scale['product_nfa'][product]
            return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else 0.0

        monthly = 0.0
        anchored = True
        for label, nfa, rate in per_product:
            from_input = _input_area(label)
            if abs(from_input - float(nfa)) > 0.5:
                anchored = False
            monthly += from_input * float(rate)
        # A product with an area in the input but no numeric row in the fee table is unpriced. It
        # may be deliberate (the deliverable's own remarks say so), so it counts 0 here and is
        # named, never silently dropped.
        priced = {label for label, _nfa, _rate in per_product}
        unpriced = [f"{p} ({_input_area(p):,.0f} m²)" for p in PRODUCT_ROWS
                    if p not in priced and _input_area(p) > 0]
        expected_mf = monthly * 12
        actual_mf = figures['mgmt_fee_revenue_annual']['value']
        checks.append((
            'mgmt_fee_revenue_annual', expected_mf, actual_mf,
            # An unanchored check FAILS. It is not a warning: if the input file's NFA disagrees with
            # the workbook's, this check is comparing the workbook against itself and proves nothing,
            # which is worse than a red line because it looks like evidence.
            anchored and abs(expected_mf - actual_mf) < 1.0,
            'Σ(product NFA from Sample_Project_Input.xlsx × its derived rate) × 12, over the '
            f'{len(per_product)} priced product(s)'
            + (f'; unpriced, counted as 0: {", ".join(unpriced)}' if unpriced else '')
            + ('' if anchored else '  [FAILED: input NFA does not match the workbook, so this check '
                                   'is not anchored to the input file and proves nothing]'),
        ))

        # --- 2. One service contract: Security ---
        sv = wb.Worksheets('Service')
        values, r0, _ = _read_sheet_values(sv)
        for ri, row in enumerate(values):
            if isinstance(row[0], str) and row[0].strip() == 'Security':
                post_rate = float(sv.Cells(r0 + ri, 2).Value2)
                roles = float(sv.Cells(r0 + ri, 3).Value2)
                blend = float(sv.Cells(r0 + ri, 4).Value2)
                qty = float(sv.Cells(r0 + ri, 6).Value2)
                expected_sec = post_rate / roles * blend * qty * 12
                actual_sec = figures['service_security_annual']['value']
                checks.append((
                    'service_security_annual', expected_sec, actual_sec,
                    abs(expected_sec - actual_sec) < 1.0,
                    'citywide post rate ÷ shift roles × night blend × headcount × 12',
                ))
                break

        # --- 3. One Capex category, summed from the item list rather than read from a subtotal ---
        cx = wb.Worksheets('Capex')
        values, r0, _ = _read_sheet_values(cx)
        amenity_total = 0.0
        for row in values:
            label = row[0] if row else None
            subtotal = row[5] if len(row) > 5 else None
            if isinstance(label, str) and label.strip() == 'Amenity Area' and isinstance(subtotal, (int, float)):
                amenity_total += float(subtotal)
        actual_amenity = figures['capex_amenity_area']['value']
        checks.append((
            'capex_amenity_area', amenity_total, actual_amenity,
            abs(amenity_total - actual_amenity) < 1.0,
            'sum of every Amenity Area line item on the Capex sheet',
        ))

        # --- 4. The Cost Basis toggle: Must-Have Only = MO + M&E, nothing else ---
        expected_capex = (figures['capex_mo_equipment']['value']
                          + figures['capex_me_equipment']['value'])
        actual_capex = figures['capex_selected']['value']
        checks.append((
            'capex_selected', expected_capex, actual_capex,
            abs(expected_capex - actual_capex) < 1.0,
            'Must-Have Only toggle = MO Equipment + M&E Equipment',
        ))

        # --- 5. Parking revenue, anchored entirely on the input file's slot counts ---
        ar = wb.Worksheets('Additional Revenue')
        values, r0, _ = _read_sheet_values(ar)
        car_rate = moto_rate = None
        for ri, row in enumerate(values):
            if isinstance(row[0], str) and row[0].strip() == 'Car':
                car_rate = float(ar.Cells(r0 + ri, 2).Value2)
            if isinstance(row[0], str) and row[0].strip() == 'Motorbike':
                moto_rate = float(ar.Cells(r0 + ri, 2).Value2)
        if car_rate and moto_rate:
            parking = (float(scale['car_slots']) * car_rate + float(scale['moto_slots']) * moto_rate) * 12
            actual_add = figures['additional_revenue_annual']['value']
            checks.append((
                'additional_revenue_annual (parking portion)', parking, actual_add,
                # `parking > 0` matters as much as the inequality: 0 < anything is true, so when the
                # slot counts failed to read this check passed while comparing against nothing.
                parking > 0 and parking < actual_add,  # advertising revenue sits on top of parking
                'car slots × car rate + moto slots × moto rate, × 12, from the INPUT file — '
                'expected to be above zero and below the total, which also includes advertising',
            ))
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

    return checks


BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'baselines', 'baseline.json')


def _runtime_fingerprint(sample_path=None):
    """What produced these numbers.

    Recorded because the project pins nothing: there is no dependency manifest and two Python
    versions are in evidence in the repository. If a baseline stops reproducing on another machine,
    this is what makes the difference diagnosable instead of mysterious.
    """
    import hashlib
    import platform
    import sys

    import openpyxl

    from verification.run_workflow import DEFAULT_SAMPLE

    # Hash the sample ACTUALLY used, not the default. Hashing the default meant that running against
    # a different fixture reported no input change, so the resulting figure differences read as a
    # code regression when they were nothing of the kind.
    sample_path = sample_path or DEFAULT_SAMPLE
    with open(sample_path, 'rb') as fh:
        sample_hash = hashlib.sha256(fh.read()).hexdigest()

    excel_version = None
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        xl = win32com.client.DispatchEx('Excel.Application')
        excel_version = str(xl.Version)
        xl.Quit()
        pythoncom.CoUninitialize()
    except Exception:
        pass

    return {
        'python_version': sys.version.split()[0],
        'python_full': sys.version.replace('\n', ' '),
        'platform': platform.platform(),
        'openpyxl_version': getattr(openpyxl, '__version__', 'unknown'),
        'excel_version': excel_version,
        'sample_fixture': os.path.basename(sample_path),
        'sample_sha256': sample_hash,
    }


def save_baseline(figures, reason, path=None, sample_path=None):
    """Write the baseline to disk with the runtime that produced it.

    `reason` is required and must be non-empty. A baseline that can be overwritten without saying
    why is worthless — the first failing run would simply be re-recorded and the regression lost
    (design D3).
    """
    import datetime
    import json

    if not reason or not str(reason).strip():
        raise ValueError(
            'A baseline needs a stated reason. Recording one without saying why is how a real '
            'regression gets quietly absorbed into the expected values.'
        )

    path = path or BASELINE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        'recorded_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'reason': str(reason).strip(),
        'runtime': _runtime_fingerprint(sample_path),
        'figures': {
            name: {'value': f['value'], 'unit': f['unit'], 'where': f['where']}
            for name, f in figures.items()
        },
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def load_baseline(path=None):
    """Read the stored baseline, or None if none has been recorded yet."""
    import json
    path = path or BASELINE_PATH
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def verify_stored_baseline(path=None):
    """Confirm a stored baseline is complete: every figure, each with a unit, plus the runtime.

    Returns (ok, problems).
    """
    stored = load_baseline(path)
    if stored is None:
        return False, [f'No baseline recorded at {path or BASELINE_PATH}']

    problems = []
    expected = [n for n, *_ in CELL_FIGURES] + [n for n, *_ in LABEL_FIGURES]
    figures = stored.get('figures', {})
    for name in expected:
        if name not in figures:
            problems.append(f'missing figure: {name}')
        elif figures[name].get('value') is None:
            problems.append(f'null value: {name}')
        elif not figures[name].get('unit'):
            problems.append(f'no unit recorded: {name}')
        elif figures[name]['unit'] != UNITS[name]:
            problems.append(
                f'unit mismatch on {name}: stored {figures[name]["unit"]!r}, expected {UNITS[name]!r}')

    runtime = stored.get('runtime', {})
    if not runtime.get('python_version'):
        problems.append('no Python version recorded')
    if not stored.get('reason'):
        problems.append('no reason recorded')
    if not runtime.get('sample_sha256'):
        problems.append('no sample-fixture hash recorded')

    return not problems, problems


class BaselineMismatch(RuntimeError):
    """Raised when a figure has moved away from its recorded baseline."""


# How much drift counts as "the same number".
#   VND and the derived rate are whole currency amounts — they should reproduce exactly. 1.0 absorbs
#   float representation noise from Excel without hiding a real change (the smallest figure here is
#   28 million VND, so a 1 VND allowance cannot mask anything meaningful).
#   Ratios are computed by division and carry genuine float error, so they get a relative tolerance.
TOLERANCES = {
    VND:   ('absolute', 1.0),
    RATE:  ('absolute', 1.0),
    RATIO: ('relative', 1e-9),
}


def _within_tolerance(unit, baseline_value, current_value):
    kind, limit = TOLERANCES.get(unit, ('absolute', 1.0))
    delta = abs(float(current_value) - float(baseline_value))
    if kind == 'relative':
        denom = abs(float(baseline_value)) or 1.0
        return (delta / denom) <= limit, delta
    return delta <= limit, delta


def compare_to_baseline(figures, stored=None, path=None, sample_path=None):
    """Compare freshly extracted figures against the recorded baseline.

    Returns (ok, differences, notes). Differences are dicts carrying the figure name, both values
    and the delta, so the caller can report a change in VND rather than as a bare "mismatch".

    A baseline recorded from a different sample fixture is treated as a hard failure: comparing
    figures produced from different inputs is meaningless, and reporting it as drift would be worse
    than reporting nothing.
    """
    stored = stored if stored is not None else load_baseline(path)
    if stored is None:
        return False, [], ['No baseline has been recorded yet — nothing to compare against.']

    notes = []
    runtime = stored.get('runtime', {})
    current_runtime = _runtime_fingerprint(sample_path)

    fixture_changed = (runtime.get('sample_sha256')
                       and runtime['sample_sha256'] != current_runtime['sample_sha256'])
    if fixture_changed:
        # Still enumerate the figure differences below rather than refusing outright. Someone who
        # edits the sample needs to see what it did to the numbers — that is the whole point of
        # changing it. What must not happen is those differences being read as a code regression,
        # so they are labelled as caused by the input change.
        notes.append(
            'THE SAMPLE FIXTURE HAS CHANGED since the baseline was recorded '
            f'(baseline {runtime["sample_sha256"][:16]}, now {current_runtime["sample_sha256"][:16]}). '
            'The differences below follow from the changed input, not from a code regression. '
            'If the new input is intended, re-record the baseline with a reason saying so.'
        )
    for key, label in (('python_version', 'Python'), ('openpyxl_version', 'openpyxl'),
                       ('excel_version', 'Excel')):
        was, now = runtime.get(key), current_runtime.get(key)
        if was and now and was != now:
            notes.append(f'{label} changed since the baseline was recorded: {was} -> {now}')

    stored_figures = stored.get('figures', {})
    differences = []

    for name, current in figures.items():
        if name not in stored_figures:
            differences.append({'name': name, 'baseline': None, 'current': current['value'],
                                'delta': None, 'unit': current['unit'], 'kind': 'new figure'})
            continue
        base = stored_figures[name]
        ok, delta = _within_tolerance(current['unit'], base['value'], current['value'])
        if not ok:
            differences.append({'name': name, 'baseline': base['value'], 'current': current['value'],
                                'delta': delta, 'unit': current['unit'], 'kind': 'changed'})

    for name in stored_figures:
        if name not in figures:
            differences.append({'name': name, 'baseline': stored_figures[name]['value'],
                                'current': None, 'delta': None,
                                'unit': stored_figures[name].get('unit', ''), 'kind': 'no longer produced'})

    return not differences, differences, notes


def format_differences(differences):
    """Render differences with both values, so a failure says what moved and by how much."""
    lines = []
    for d in differences:
        if d['kind'] == 'changed':
            lines.append(
                f'{d["name"]}: baseline {d["baseline"]:,.4f} -> current {d["current"]:,.4f} '
                f'({d["unit"]}), moved by {d["delta"]:,.4f}'
                if d['unit'] == RATIO else
                f'{d["name"]}: baseline {d["baseline"]:,.0f} {d["unit"]} -> current '
                f'{d["current"]:,.0f} {d["unit"]}, moved by {d["delta"]:,.0f} {d["unit"]}'
            )
        elif d['kind'] == 'new figure':
            lines.append(f'{d["name"]}: not in the baseline, now {d["current"]:,.0f} {d["unit"]}')
        else:
            lines.append(
                f'{d["name"]}: was {d["baseline"]:,.0f} {d["unit"]} in the baseline, no longer produced')
    return lines


def _main():
    import sys
    import tempfile

    # Sheet names, units and product labels here are Vietnamese and mathematical. On Windows the
    # console defaults to cp1252, which cannot encode them and raises mid-report — losing the run's
    # output after it has already done the expensive work.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from verification.checks import locate_outputs
    from verification.run_workflow import DEFAULT_SAMPLE, run_workflow

    with tempfile.TemporaryDirectory(prefix='budget_baseline_') as workdir:
        print('running both generators against the sample...\n')
        outputs, _, _ = run_workflow(workdir=workdir)
        paths = locate_outputs(outputs)

        figures = extract_figures(paths['analysis'])
        print(f'HEADLINE FIGURES  ({len(figures)} extracted, all present and non-null)\n')
        width = max(len(n) for n in figures)
        for name, _, _, _, _ in CELL_FIGURES + LABEL_FIGURES:
            f = figures[name]
            v = f['value']
            shown = f'{v:>20,.4f}' if f['unit'] == RATIO else f'{v:>20,.0f}'
            print(f'  {name:<{width}}  {shown}  {f["unit"]}')

        print('\nHAND-CHECKS — recomputed independently, not read back from the same cell\n')
        results = hand_checks(figures, DEFAULT_SAMPLE, paths['analysis'])
        ok = True
        for name, expected, actual, matched, how in results:
            ok &= matched
            print(f'  {"OK  " if matched else "FAIL"}  {name}')
            print(f'          expected {expected:>20,.2f}   actual {actual:>20,.2f}')
            print(f'          {how}')
        if not ok:
            print('\nRESULT: FAILED — at least one figure does not reconcile')
            return 1

        # ---- record the baseline (4.3) ----
        record = '--record' in sys.argv
        reason = None
        if record:
            for i, a in enumerate(sys.argv):
                if a == '--reason' and i + 1 < len(sys.argv):
                    reason = sys.argv[i + 1]
            if not reason:
                print('\n--record requires --reason "why this baseline is being written"')
                return 1
            path = save_baseline(figures, reason)
            print(f'\nBASELINE RECORDED -> {path}')
            print(f'  reason: {reason}')

        stored = load_baseline()
        print('\nSTORED BASELINE')
        if stored is None:
            print('  none recorded yet — run with --record --reason "..." to write one')
            return 0
        else:
            rt = stored['runtime']
            print(f'  recorded_at      {stored["recorded_at"]}')
            print(f'  reason           {stored["reason"]}')
            print(f'  python           {rt["python_version"]}')
            print(f'  openpyxl         {rt["openpyxl_version"]}')
            print(f'  excel            {rt["excel_version"]}')
            print(f'  platform         {rt["platform"]}')
            print(f'  sample fixture   {rt["sample_fixture"]}  sha256 {rt["sample_sha256"][:16]}')
            print(f'  figures stored   {len(stored["figures"])}')
            good, problems = verify_stored_baseline()
            if good:
                units = sorted({f['unit'] for f in stored['figures'].values()})
                print(f'  OK    complete: every figure present, non-null, unit-labelled ({", ".join(units)})')
            else:
                print('  FAIL  incomplete baseline:')
                for p in problems[:10]:
                    print(f'          - {p}')
                return 1

        # ---- compare against the recorded baseline (4.4) ----
        print('\nCOMPARISON AGAINST THE RECORDED BASELINE')
        tol = ', '.join(f'{u}: {k} {v:g}' for u, (k, v) in TOLERANCES.items())
        print(f'  tolerance — {tol}')
        matched, differences, notes = compare_to_baseline(figures, stored=stored)
        for n in notes:
            print(f'  NOTE  {n}')
        if matched:
            print(f'  OK    all {len(figures)} figures match the baseline within tolerance')
        else:
            print(f'  FAIL  {len(differences)} figure(s) differ from the baseline:')
            for line in format_differences(differences):
                print(f'          - {line}')
            print('\nRESULT: FAILED — the pipeline no longer reproduces its recorded baseline. '
                  'If this change was intended, re-record with '
                  'verification/baseline.py --record --reason "..." (see verification/README.md).')
            return 1

        print(f'\nRESULT: {len(figures)} figures extracted, all non-null, all labelled with a unit; '
              f'{len(results)} of them independently reconciled; all {len(figures)} match the '
              f'recorded baseline')
        return 0


if __name__ == '__main__':
    import sys
    sys.exit(_main())
