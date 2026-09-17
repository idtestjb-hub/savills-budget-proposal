"""A recorded baseline for the CLIENT DELIVERABLE's occupancy-ramped budget lines.

The existing baseline (baseline.py) reads the ANALYSIS workbook, whose figures do not use the
template and are unaffected by the occupancy ramp (change `ramp-occupancy-scaled-lines`). This
module baselines the deliverable itself, so that:
  - a ramped line reverting to a flat one-twelfth write is caught, and
  - the fill-up curve changing shows up as a figure change to review, not a silent shift.

Same "needs Excel, no weaker fallback" constraint as baseline.py — the deliverable's figures are
live formulas.

Re-record after an approved change with:
    python verification/deliverable_baseline.py --record --reason "why"
"""
import os

from verification.baseline import (VND, BaselineUnavailable, FigureMissing,
                                   save_baseline, load_baseline, compare_to_baseline)

DELIVERABLE_BASELINE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'baselines', 'deliverable_baseline.json')

_FUND = '2. Budget-Management Fund'
_SUMMARY = '1. Summary'

# name -> (sheet, kind, locator, unit). kind 'sum_col_g' sums column G over a row range;
# 'cell' reads one G-column cell; 'summary_code' finds a row on 1. Summary by its column-B code
# and reads column H. All are year-1 totals in VND — the occupancy ramp's whole effect is on how a
# line's annual value distributes across the 12 months, and G / H are those 12-month totals.
DELIVERABLE_FIGURES = [
    ('rm_collected_year1',   _FUND,    'sum_col_g', (14, 22), VND),  # RM.AP..RM.KG (residents pay)
    ('rm_developer_year1',   _FUND,    'cell',      23,        VND),  # RM.0A (developer pays on unsold)
    ('parking_moto_year1',   _FUND,    'cell',      26,        VND),  # RP1
    ('parking_car_year1',    _FUND,    'cell',      27,        VND),  # RP2
    ('water_year1',          _FUND,    'cell',      230,       VND),  # EEW.C
    ('electricity_year1',    _FUND,    'cell',      240,       VND),  # EEE.C
    ('estimated_surplus_year1', _SUMMARY, 'summary_code', 'PART 3:', VND),
    ('emh_staff_year1',       _SUMMARY, 'summary_code', 'EMH',      VND),  # in-house staff cost line
]

UNITS = {name: unit for name, _, _, _, unit in DELIVERABLE_FIGURES}


def extract_deliverable_figures(deliverable_path):
    """Open a COPY in Excel, recalculate, and read every figure above.

    Returns {name: {'value','unit','where'}}. Raises BaselineUnavailable if Excel cannot be driven,
    FigureMissing if a figure is absent or null.
    """
    import shutil
    import tempfile

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise BaselineUnavailable(
            'The deliverable baseline requires Excel: the deliverable stores its figures as '
            f'formulas with no cached values. Python cannot reach Excel here ({exc}).'
        ) from exc

    work = os.path.join(tempfile.mkdtemp(prefix='deliv_baseline_'), os.path.basename(deliverable_path))
    shutil.copy(deliverable_path, work)

    pythoncom.CoInitialize()
    xl = wb = None
    figures = {}
    try:
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(work, UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        sheets = {ws.Name: ws for ws in wb.Worksheets}

        for name, sheet, kind, locator, unit in DELIVERABLE_FIGURES:
            if sheet not in sheets:
                continue
            ws = sheets[sheet]
            if kind == 'cell':
                value = ws.Cells(locator, 7).Value2  # column G
                where = f'{sheet}!G{locator}'
            elif kind == 'sum_col_g':
                lo, hi = locator
                value = sum((ws.Cells(r, 7).Value2 or 0) for r in range(lo, hi + 1))
                where = f'{sheet}!SUM(G{lo}:G{hi})'
            elif kind == 'summary_code':
                value = where = None
                for r in range(8, 80):
                    if str(ws.Cells(r, 2).Value2 or '').strip() == locator:
                        value = ws.Cells(r, 8).Value2  # column H
                        where = f"{sheet}!H{r} (code {locator!r})"
                        break
            else:
                raise ValueError(f'unknown locator kind {kind!r}')
            figures[name] = {'value': value, 'unit': unit, 'where': where}
    except Exception as exc:
        raise BaselineUnavailable(
            f'Excel could not evaluate the deliverable: {type(exc).__name__}: {exc}') from exc
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

    missing = [n for n, *_ in DELIVERABLE_FIGURES
               if n not in figures or figures[n]['value'] is None]
    if missing:
        raise FigureMissing(
            'These deliverable figures are absent or null: ' + ', '.join(missing)
            + '. Either a ramped line stopped being written, or the fund-sheet row layout moved.')
    return figures


def record(reason, deliverable_path):
    figures = extract_deliverable_figures(deliverable_path)
    return save_baseline(figures, reason, path=DELIVERABLE_BASELINE_PATH)


def load():
    return load_baseline(DELIVERABLE_BASELINE_PATH)


def compare(figures, stored=None):
    return compare_to_baseline(figures, stored=stored, path=DELIVERABLE_BASELINE_PATH)


if __name__ == '__main__':
    import sys
    from verification.run_workflow import run_workflow
    from verification.checks import locate_outputs

    if '--record' not in sys.argv:
        stored = load()
        print('no deliverable baseline recorded yet' if stored is None
              else f"recorded {stored['recorded_at']}: {stored['reason']}")
        for n, f in (stored or {}).get('figures', {}).items():
            print(f"  {n}: {f['value']:,.0f} {f['unit']}  ({f['where']})")
        sys.exit(0)

    try:
        reason = sys.argv[sys.argv.index('--reason') + 1]
    except (ValueError, IndexError):
        print('--record requires --reason "why this baseline is being written"')
        sys.exit(2)

    import tempfile
    with tempfile.TemporaryDirectory(prefix='deliv_baseline_run_') as wd:
        outputs, *_ = run_workflow(workdir=wd, quiet=True)
        paths = locate_outputs(outputs)
        path = record(reason, paths['deliverable'])
    print(f'recorded deliverable baseline -> {path}')
