"""
Run the whole pipeline with one command:  python run.py

WHY THIS EXISTS: the pipeline has always needed TWO commands — generate_project_budget.py for the
client deliverable and the roster, generate_project_output.py for the internal analysis. They read
the input file independently, neither reads the other's output, and nothing reconciles them. So
running only one leaves the other workbook silently describing the PREVIOUS project, with no
warning and no visible sign. That has happened repeatedly: at one point the two outputs on disk were
an hour apart and described different inputs, and the only way to notice was comparing timestamps by
hand.

This runs both, in order, and refuses to let a half-finished run look like a finished one:

  - If the deliverable is written and the analysis then fails, that is reported as a FAILURE naming
    the consequence, not as a partial success. The workbooks are inconsistent at that point.
  - After both succeed, it re-opens them and checks they name the SAME project. That is the actual
    drift symptom, so it is worth testing directly rather than inferring from exit codes.

Both generators remain runnable on their own. This does not replace them; it removes the chance to
forget the second one.
"""
import os
import sys
import time

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)


class PartialRun(RuntimeError):
    """One generator completed and the other did not — the outputs now disagree."""


def _preflight(input_path):
    """Fail before writing anything if the input cannot be read.

    The usual cause is the workbook being open in Excel, which locks it. Catching that here costs
    a second; catching it halfway through costs a half-written set of outputs.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f'{input_path} not found. Run build_project_input_form.py to create it, fill it in, '
            f'then re-run this.')
    try:
        with open(input_path, 'rb'):
            pass
    except PermissionError:
        raise PermissionError(
            f'{input_path} is locked — it is almost certainly open in Excel. Close it and re-run.')


def _describe(path):
    if not path or not os.path.exists(path):
        return '(not written)'
    st = os.stat(path)
    return f'{st.st_size:>10,} bytes   {time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))}'


def _project_name(path, sheet):
    """Read a workbook's own idea of which project it describes.

    By label, not by cell address — both sheets happen to put it at B5 today, and that is exactly
    the kind of coincidence that turns into a silent wrong answer when a row is inserted above it.
    """
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    try:
        if sheet not in wb.sheetnames:
            return None
        ws = wb[sheet]
        # A local scan rather than input_labels.SheetLabels: that resolver requires every label on
        # the sheet to be unique and raises otherwise, which is right for the intake form but wrong
        # here — the analysis Summary legitimately carries two rows that both read as "margin".
        # This only needs one specific label, so it does not need the whole sheet to be unambiguous.
        for row in range(1, min(ws.max_row, 40) + 1):
            label = ws.cell(row=row, column=1).value
            if isinstance(label, str) and label.strip().casefold() == 'project name':
                return ws.cell(row=row, column=2).value
        return None
    finally:
        wb.close()


def main():
    import generate_project_budget as gpb

    _preflight(gpb.INPUT_PATH)
    print('=' * 78)
    print('BUDGET AGENT — full run')
    print('  input:', gpb.INPUT_PATH)
    print('=' * 78)

    print('\n[1/2] Client deliverable + roster  (generate_project_budget.py)')
    print('-' * 78)
    gpb.main()

    print('\n[2/2] Internal analysis  (generate_project_output.py)')
    print('-' * 78)
    import generate_project_output as gpo
    try:
        gpo.main()
    except Exception as exc:
        raise PartialRun(
            f'The client deliverable and roster were written, but the internal analysis FAILED: '
            f'{type(exc).__name__}: {exc}\n\n'
            f'The two workbooks now describe different things — the deliverable reflects the current '
            f'input and {os.path.basename(gpo.OUTPUT_PATH)} still reflects the previous one. Fix the '
            f'error and re-run this script; do not ship the deliverable until both have completed '
            f'from the same input.') from exc

    # ---- Both completed. Check they actually agree, rather than assuming it. ----
    import glob
    deliverables = glob.glob(os.path.join(gpb.BUDGET_OUT_DIR, '*Consulting Budget*.xlsx'))
    newest = max(deliverables, key=os.path.getmtime) if deliverables else None

    print('\n' + '=' * 78)
    print('DONE — all three workbooks written from one input')
    print('=' * 78)
    print(f'  deliverable  {_describe(newest)}')
    print(f'               {newest or ""}')
    print(f'  analysis     {_describe(gpo.OUTPUT_PATH)}')
    print(f'               {gpo.OUTPUT_PATH}')
    print(f'  roster       {_describe(gpb.ROSTER_FINAL_OUT)}')
    print(f'               {gpb.ROSTER_FINAL_OUT}')

    analysis_name = _project_name(gpo.OUTPUT_PATH, 'Summary')
    input_name = _project_name(gpb.INPUT_PATH, 'Project Info')
    print(f'\n  input names the project   : {input_name!r}')
    print(f'  analysis names the project: {analysis_name!r}')
    if analysis_name and input_name and str(analysis_name).strip() != str(input_name).strip():
        print('\n  WARNING: those do not match. The analysis was not produced from this input.')
        return 1
    if newest and input_name and str(input_name).strip() not in os.path.basename(newest):
        print('\n  WARNING: the newest deliverable is not named after this input — an older file may '
              'be the most recent one in sample_output.')
        return 1
    print('  -> both outputs describe the same project.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
