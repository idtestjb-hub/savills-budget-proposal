"""
The single entry point: run the pipeline against the synthetic sample and check everything.

    python verification/verify.py

Exits 0 only if the workflow completed, both workbooks are structurally sound, and every headline
figure still matches the recorded baseline. Exits non-zero otherwise, saying which stage failed.

Runs the workflow ONCE and hands the same outputs to every check, rather than regenerating per
check. The individual modules (checks.py, baseline.py) remain runnable on their own.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verification import baseline as bl                                      # noqa: E402
from verification.checks import (CorruptionArtifact, FormulaError,           # noqa: E402
                                 StructureError, check_artifacts,
                                 check_formula_errors, check_sheets,
                                 locate_outputs)
from verification.run_workflow import (PartialRun, ProductionTouched,        # noqa: E402
                                       DEFAULT_SAMPLE, diff_snapshots,
                                       run_workflow)


def _headline(text):
    print(f'\n{text}\n' + '-' * len(text))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    sample = DEFAULT_SAMPLE
    if '--sample' in argv:
        sample = argv[argv.index('--sample') + 1]

    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    print('VERIFY — Savills budget pipeline')
    print(f'sample: {os.path.basename(sample)}')

    with tempfile.TemporaryDirectory(prefix='budget_verify_all_') as workdir:
        # ---- 1. run the pipeline -------------------------------------------------------------
        _headline('1. WORKFLOW')
        try:
            outputs, before, after = run_workflow(sample=sample, workdir=workdir)
        except PartialRun as exc:
            print(f'FAIL  partial run\n{exc}')
            return 1
        except ProductionTouched as exc:
            print(f'FAIL  production data was touched\n{exc}')
            return 1
        paths = locate_outputs(outputs)
        print('OK    both generators completed')
        for label, p in paths.items():
            print(f'        {os.path.getsize(p):>10,} bytes  {label}')
        if diff_snapshots(before, after):
            print('FAIL  production artefacts changed')
            return 1
        print('OK    all production artefacts byte-identical')

        # ---- 2. structure --------------------------------------------------------------------
        _headline('2. STRUCTURE')
        try:
            sheets = check_sheets(paths)
        except StructureError as exc:
            print(f'FAIL  {exc}')
            return 1
        for label, r in sheets.items():
            print(f'OK    {label:12} {len(r["present"])} sheets, none missing')

        try:
            check_artifacts(paths)
        except CorruptionArtifact as exc:
            print(f'FAIL  {exc}')
            return 1
        print('OK    no corruption artifacts in any workbook')

        try:
            fe = check_formula_errors(paths)
        except FormulaError as exc:
            print(f'FAIL  {exc}')
            return 1
        method = fe['method']
        inherited = sum(len(v) for v in fe['inherited'].values())
        print(f'OK    no Excel errors introduced ({inherited} inherited from the blank template, '
              f'which carries {fe["baseline_size"]})')
        print(f'      checking method used: {method}'
              + ('   << DEGRADED' if fe['degraded'] else ''))
        if fe['degraded']:
            print(f'      {fe["reason"]}')
            print('      recalculation-only errors were NOT detectable in this run')

        # ---- 3. figures ----------------------------------------------------------------------
        _headline('3. FIGURES')
        try:
            figures = bl.extract_figures(paths['analysis'])
        except (bl.BaselineUnavailable, bl.FigureMissing) as exc:
            print(f'FAIL  {exc}')
            return 1
        print(f'OK    {len(figures)} headline figures extracted, all present and non-null')

        hand = bl.hand_checks(figures, sample, paths['analysis'])
        bad = [h for h in hand if not h[3]]
        for name, expected, actual, matched, _how in hand:
            print(f'{"OK  " if matched else "FAIL"}  {name}: {actual:,.2f}'
                  + ('' if matched else f'  (expected {expected:,.2f})'))
        if bad:
            print('FAIL  a hand-check did not reconcile')
            return 1

        # ---- 4. baseline ---------------------------------------------------------------------
        _headline('4. BASELINE')
        stored = bl.load_baseline()
        if stored is None:
            print('FAIL  no baseline recorded — run:')
            print('        python verification/baseline.py --record --reason "..."')
            return 1
        matched, differences, notes = bl.compare_to_baseline(figures, stored=stored, sample_path=sample)
        print(f'      recorded {stored["recorded_at"]} on Python '
              f'{stored["runtime"]["python_version"]}, Excel {stored["runtime"]["excel_version"]}')
        for n in notes:
            print(f'NOTE  {n}')
        if not matched:
            print(f'FAIL  {len(differences)} figure(s) differ from the baseline:')
            for line in bl.format_differences(differences):
                print(f'        - {line}')
            print('\nIf this change was intended, re-record the baseline with a stated reason. '
                  'See verification/README.md.')
            return 1
        print(f'OK    all {len(figures)} figures match the baseline within tolerance')

        # ---- verdict -------------------------------------------------------------------------
        _headline('RESULT')
        print(f'PASS — structural checks and numeric baseline both clean.')
        print(f'       checking method: {method}'
              + ('  (REDUCED — see above)' if fe['degraded'] else '  (full Excel recalculation)'))
        print(f'       {len(figures)} figures matched, {len(hand)} independently hand-checked, '
              f'production untouched.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
