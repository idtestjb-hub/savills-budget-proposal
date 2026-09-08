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

# Captured from a verified run on 2026-09-08 against the 2026-08 Resi template.
# The deliverable is the template's own 21 sheets plus 'Comparison', which the pipeline appends.
# Trailing spaces in two names are real and are preserved deliberately — matching is exact.
EXPECTED_SHEETS = {
    'deliverable': [
        'Cover',
        '0. Info',
        '1. Summary',
        '1. Staff cost From 08.2026 (VN)',
        '1.1 Allowance (From 08.2026)',
        '2. Budget-Management Fund',
        '2.1 Report-Management Fund',
        '2.2 Common area Fund',
        '2.2.1 Report-Common area Fund',
        '3. Budget-Sinking Fund',
        '3.1 Report-Sinking Fund',
        'A2. Bảo vệ - Security',
        'A3. Vệ sinh - Cleaning',
        'A4. Cây xanh - Landscape',
        'A5. Trợ cấp PCCC',
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
        missing = [s for s in want if s not in actual]
        unexpected = [s for s in actual if s not in want]
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
