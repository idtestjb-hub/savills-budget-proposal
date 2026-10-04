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
from verification import checks                                              # noqa: E402
from verification.checks import (CorruptionArtifact, FormulaError,           # noqa: E402
                                 StructureError, check_artifacts,
                                 check_formula_errors, check_sheets,
                                 check_deliverable_figures, check_benchmark_reconciles,
                                 check_remark_content, check_summary_reconciles,
                                 check_revenue_agreement, check_required_line_items,
                                 check_method_coverage, locate_outputs)
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

        # ---- 5. deliverable figures (occupancy-ramped lines) -------------------------------
        _headline('5. DELIVERABLE FIGURES')
        try:
            dmatched, dfigures, ddiffs, dnotes = checks.check_deliverable_figures(paths)
        except (bl.BaselineUnavailable, bl.FigureMissing) as exc:
            print(f'FAIL  {exc}')
            return 1
        for n in dnotes:
            print(f'NOTE  {n}')
        if not dmatched:
            print(f'FAIL  {len(ddiffs)} ramped deliverable figure(s) differ from the baseline:')
            for line in bl.format_differences(ddiffs):
                print(f'        - {line}')
            print('\nA ramped line reverting to a flat 1/12 write, or the fill-up curve changing, '
                  'shows up here. If intended, re-record: '
                  'python verification/deliverable_baseline.py --record --reason "...".')
            return 1
        rm_tot = dfigures['rm_collected_year1']['value'] + dfigures['rm_developer_year1']['value']
        print(f'OK    all {len(dfigures)} ramped deliverable figures match the baseline')
        print(f'      RM collected + RM.0A developer top-up = {rm_tot:,.0f} VND '
              f'(total management fee, unchanged by the ramp)')

        # ---- 5b. the two workbooks agree on revenue ---------------------------------------
        try:
            ramatched, rarows, radiffs, ranotes = check_revenue_agreement(paths)
        except bl.BaselineUnavailable as exc:
            print(f'FAIL  {exc}')
            return 1
        for n in ranotes:
            print(f'NOTE  {n}')
        if not ramatched:
            print(f'FAIL  the deliverable and the analysis disagree on {len(radiffs)} '
                  f'management-fee revenue figure(s):')
            for label, dv, av in radiffs:
                print(f'        - {label}: deliverable {dv:,.0f} VND vs analysis {av:,.0f} VND '
                      f'(gap {dv - av:+,.0f})')
            print('\nBoth generators must rank comparables on the same basis (Total building NFA). '
                  'This is backlog B3 / change unify-revenue-basis-across-outputs.')
            return 1
        _dtot = next(a for lbl, d, a in rarows if lbl.startswith('TOTAL'))
        print(f'OK    deliverable and analysis agree on all {len(rarows) - 1} priced product(s) '
              f'and the total ({_dtot:,.0f} VND/year at full occupancy)')

        # ---- 5c. the Comparison-sheet PROPOSAL BENCHMARK carries '1. Summary' forward ---------
        try:
            bmatched, brows, bdiffs, bnotes = check_benchmark_reconciles(paths)
        except bl.BaselineUnavailable as exc:
            print(f'FAIL  {exc}')
            return 1
        for n in bnotes:
            print(f'NOTE  {n}')
        if not bmatched:
            print(f'FAIL  the Comparison sheet PROPOSAL BENCHMARK disagrees with the deliverable '
                  f"'1. Summary' on {len(bdiffs)} figure(s):")
            for label, bv, sv in bdiffs:
                bv_s = f'{bv:,.0f}' if isinstance(bv, (int, float)) else 'missing/error'
                sv_s = f'{sv:,.0f}' if isinstance(sv, (int, float)) else 'n/a'
                print(f'        - {label}: benchmark {bv_s} VND vs 1. Summary {sv_s} VND')
            print("\nThe benchmark cells are formulas into '1. Summary' — a mismatch means a broken "
                  'reference (change benchmark-proposal-against-comparables).')
            return 1
        print(f'OK    all {len(brows)} PROPOSAL BENCHMARK figure(s) reconcile with the deliverable '
              f"'1. Summary'")

        # ---- 5d. the deliverable's remarks say what the AI Guideline instructs ----------------
        rcok, rcrows, rcdiffs, rcnotes = check_remark_content(paths)
        for n in rcnotes:
            print(f'NOTE  {n}')
        if not rcok:
            print(f'FAIL  {len(rcdiffs)} remark-content problem(s) in the deliverable:')
            for label, msg in rcdiffs:
                print(f'        - {label}: {msg}')
            print('\nThe AI Guideline instructs the content of every remark (docs/11-guideline-'
                  'remark-model.md); change apply-guideline-remark-model composes them. A composed '
                  "'1. Summary' K narrative missing a required part, an unlisted funded child, or a "
                  'missing VAT sentence shows up here. Remarks are text — no baseline moves.')
            return 1
        print(f'OK    all {sum(1 for _l, s in rcrows if s == "ok")} remark-content assertion(s) '
              f'passed (composed narratives, funded-child lists, VAT sentence, line-level T remark '
              f'Vietnamese content, no internal-artifact citations)')

        # ---- 5e. '1. Summary' ties to '2. Budget-Management Fund' end to end ------------------
        try:
            scok, scrows, scdiffs, scnotes = check_summary_reconciles(paths)
        except bl.BaselineUnavailable as exc:
            print(f'FAIL  {exc}')
            return 1
        for n in scnotes:
            print(f'NOTE  {n}')
        if not scok:
            print(f'FAIL  {len(scdiffs)} summary-reconciliation problem(s):')
            for label, left, right in scdiffs:
                l_s = f'{left:,.0f}' if isinstance(left, (int, float)) else str(left)
                r_s = f'{right:,.0f}' if isinstance(right, (int, float)) else str(right)
                print(f'        - {label}: {l_s} vs {r_s}')
            print("\n'1. Summary' should tie to '2. Budget-Management Fund' on every code, every "
                  'fund leaf G/AK split, the surplus derivation, and EMH vs the A1 payroll total — '
                  'change reconcile-summary-with-detail-sheets. A gap here is a real reconciliation '
                  'break, not a baseline move.')
            return 1
        print(f'OK    all {len(scrows)} summary-reconciliation check(s) passed '
              f"('1. Summary' <-> '2. Budget-Management Fund' <-> A1 payroll, error-cell ceiling)")

        # ---- 5f. every AI-Guideline-Required code is priced or its zero is explained -----------
        try:
            rlok, rlrows, rldiffs, rlnotes = check_required_line_items(paths)
        except bl.BaselineUnavailable as exc:
            print(f'FAIL  {exc}')
            return 1
        for n in rlnotes:
            print(f'NOTE  {n}')
        if not rlok:
            print(f'FAIL  {len(rldiffs)} Required code(s) are zero with no stated reason:')
            for label, msg in rldiffs:
                print(f'        - {label}: {msg}')
            print("\nEvery code the AI Guideline classifies 'Bắt buộc/Required' on "
                  "'2. Budget-Management Fund' or '2.2 Common area Fund' must carry a non-zero "
                  "figure or a remark stating why it genuinely does not apply (changes "
                  "fill-guideline-required-line-items, explain-common-area-fund-zero-lines). "
                  "A gap here is an undisclosed Required-line-item zero, not a baseline move.")
            return 1
        print(f'OK    all {sum(1 for _l, s in rlrows if s.startswith("ok"))} Required-line-item '
              f'check(s) passed on \'2. Budget-Management Fund\' and \'2.2 Common area Fund\'')

        # ---- 6. coverage & method fidelity (never a pass/fail on the score itself) -----------
        _headline('6. COVERAGE & METHOD FIDELITY')
        try:
            mcok, mcrows, mcdiffs, mcnotes = check_method_coverage(paths)
        except bl.BaselineUnavailable as exc:
            print(f'FAIL  {exc}')
            return 1
        if not mcok:
            print('FAIL  the method-coverage verdict registry is out of sync with the pipeline:')
            for n in mcnotes:
                print(f'        - {n}')
            print("\nEvery cost code the pipeline writes needs a recorded method verdict in "
                  "verification/method_coverage.py's METHOD_VERDICTS, and every recorded verdict "
                  "needs a live write site — change report-method-coverage-in-verification, "
                  "design D2. This is the one thing this section fails a run for; a low coverage "
                  "or fidelity score never does.")
            return 1
        fidelity_note = next((n for n in mcnotes if n.startswith('method fidelity')), None)
        coverage_notes = [n for n in mcnotes if n.startswith('coverage against')]
        if fidelity_note:
            print(f'NOTE  {fidelity_note}')
        for n in coverage_notes:
            print(f'NOTE  {n}')
        print('OK    every written cost code carries a recorded method verdict, none orphaned')
        fidelity_matches_share = next(v for label, v, _r in mcrows if label == 'fidelity: matches')
        coverage_shares = {label.split(': ', 1)[1]: v for label, v, _r in mcrows
                            if label.startswith('coverage: ')}

        # ---- verdict -------------------------------------------------------------------------
        _headline('RESULT')
        print(f'PASS — reproduces its own recorded baseline; coverage and method fidelity are '
              f'measured and reported below, NOT asserted as correct.')
        print(f'       checking method: {method}'
              + ('  (REDUCED — see above)' if fe['degraded'] else '  (full Excel recalculation)'))
        print(f'       {len(figures)} figures matched, {len(hand)} independently hand-checked, '
              f'production untouched.')
        print(f'       method fidelity: {fidelity_matches_share*100:.1f}% of written cost is by a '
              f'spec-stated method (measured, not implied by the PASS above).')
        for name, share in coverage_shares.items():
            print(f'       coverage vs {name}: {share*100:.1f}% of its real spend is on lines this '
                  f'pipeline fills.')
        print('       A green run says the pipeline reproduced its own numbers. It does NOT say '
              'those numbers are right — see verification/README.md.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
