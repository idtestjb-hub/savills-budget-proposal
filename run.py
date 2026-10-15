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
    _write_run_log(gpb, gpo, newest)
    rc = _report_staffing_reasons(gpo.OUTPUT_PATH)
    _report_utility_flags(gpo.OUTPUT_PATH)
    return rc


def _write_run_log(gpb, gpo, deliverable):
    """One record per complete run (change add-budget-run-log). It must never change the run: run_log.write already
    turns its own failures into a 'Run log:' line, and this guard covers anything it did not foresee."""
    try:
        import run_log
        csv_path = os.path.join(gpb.BUDGET_AGENT, 'data', 'master_list_verified',
                                'AI_Guideline_Required_Classification.csv')
        print('\n  Run log: measuring the finished workbooks in Excel (about 15 to 40 seconds) ...')
        path, rec = run_log.write(deliverable, gpo.OUTPUT_PATH, gpb.INPUT_PATH, csv_path)
        if path and rec and rec.get('status') == 'ok':
            pct = rec['required_pct']
            profit = rec['savills_profit_vnd']
            print(f"  Run log: {os.path.basename(path)}  |  Required lines complete "
                  f"{pct:.0%} ({rec['required_filled']}/{rec['required_total']})  |  "
                  f"fund surplus {rec['fund_surplus_vnd']:,.0f}  |  Savills profit {profit:,.0f} VND")
        elif path:
            print(f'  Run log: {os.path.basename(path)} (some figures blank)')
    except Exception as exc:
        print(f'  Run log: not written ({type(exc).__name__}: {exc}).')


def _report_utility_flags(analysis_path):
    """Existing-project mode (change carry-forward-common-utilities): print EEE.C / EEW.C and their flags
    (missing or zero months, fewer than 12 months, a bill rate off the tariff). Flags never stop the run;
    the stops (duplicate month, override without a reason, ...) already stopped it with a message. A
    New-prospect workbook has no Utility Bridge and prints nothing."""
    import openpyxl
    import existing_utilities as eu
    wb = openpyxl.load_workbook(analysis_path, read_only=True, data_only=True)
    try:
        if eu.BRIDGE_SHEET not in wb.sheetnames:
            return
        print(f"\n  Common-area electricity and water (sheet '{eu.BRIDGE_SHEET}' of the analysis):")
        line = None
        for row in wb[eu.BRIDGE_SHEET].iter_rows(values_only=True):
            label = str(row[0] or '')
            if label == eu.BRIDGE_TOTAL_LABEL:
                print(f'    budget year: EEE.C {row[1]:,.0f} VND, EEW.C {row[2]:,.0f} VND')
            elif label.split(' ')[0] in eu.LINES:
                line = label.split(' ')[0]
            elif label == 'Flags' and line:
                print(f'    {line} flags: {row[1]}')
    finally:
        wb.close()


def _report_staffing_reasons(analysis_path):
    """Existing-project mode (change carry-forward-staffing, design D13): every changed staffing line
    needs a reason. PMs never run verification, so the run itself says which line lacks one. A
    New-prospect workbook has no Staff Bridge and passes silently."""
    from verification.checks import check_staffing_reasons
    ok, rows, problems, _notes = check_staffing_reasons(analysis_path)
    if not rows:
        return 0
    if ok:
        print(f'  -> every changed staffing line has a reason ({len(rows)} on the Staff Bridge).')
        return 0
    print('\n  FAILED: these staffing lines changed without a valid reason '
          "(sheet 'Staff Bridge' of the analysis):")
    for label, problem in problems:
        print(f'    - {label}: {problem}')
    print("  Fill the Reason Code (and a Reason Note for \"Khác\") on 'Prior-Year Roster' or "
          "'Staffing Demand', save, and run again. Do not send the budget until this passes.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
