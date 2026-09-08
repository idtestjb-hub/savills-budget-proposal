"""
Runs the real budget workflow end to end against the synthetic sample, with every input and output
redirected away from production (see isolation.py).

The production-untouched check is deliberately built into the run rather than offered as a separate
step. Isolation that is only verified when someone remembers to verify it is not isolation; here a
run that touches a production file fails, whatever else it produced.

Both generators are run, in the order the pipeline requires. Running only one is what leaves the
analysis workbook and the client deliverable describing different projects, so a partial run is
reported as a failure rather than a partial success.
"""
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SOURCE_CODE = os.path.dirname(_HERE)
if _SOURCE_CODE not in sys.path:
    sys.path.insert(0, _SOURCE_CODE)

from verification.isolation import redirected_paths  # noqa: E402

_BUDGET_AGENT = os.path.dirname(_SOURCE_CODE)

# The live artefacts this must never disturb. Missing files are fine — absence is recorded and
# compared just like a hash, so a run that CREATES one of these is caught too.
PRODUCTION_FILES = [
    os.path.join(_BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx'),
    os.path.join(_BUDGET_AGENT, 'reports', 'Project_Budget_Output.xlsx'),
    os.path.join(_BUDGET_AGENT, 'reports', 'Roster_Demand_Model.xlsx'),
    os.path.join(_BUDGET_AGENT, 'sample_output', 'Blue Skyline - Sample Consulting Budget.xlsx'),
]

DEFAULT_SAMPLE = os.path.join(_HERE, 'fixtures', 'Sample_Project_Input.xlsx')


class ProductionTouched(RuntimeError):
    """Raised when a verification run changed something under production paths."""


class PartialRun(RuntimeError):
    """Raised when one generator completed and the other did not."""


def _fingerprint(path):
    """(sha256, mtime) for a file, or None if it does not exist."""
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest(), os.path.getmtime(path)


def snapshot(paths=None):
    return {p: _fingerprint(p) for p in (paths or PRODUCTION_FILES)}


def diff_snapshots(before, after):
    """Human-readable descriptions of anything that changed."""
    changes = []
    for path, was in before.items():
        now = after.get(path)
        name = os.path.basename(path)
        if was is None and now is not None:
            changes.append(f'{name}: CREATED by the run')
        elif was is not None and now is None:
            changes.append(f'{name}: DELETED by the run')
        elif was and now:
            if was[0] != now[0]:
                changes.append(f'{name}: CONTENT changed ({was[0][:12]} -> {now[0][:12]})')
            elif was[1] != now[1]:
                changes.append(f'{name}: timestamp changed (content identical)')
    return changes


def run_workflow(sample=DEFAULT_SAMPLE, workdir=None, quiet=True):
    """Run both generators against `sample`, writing everything into `workdir`.

    Returns (outputs, before, after). Raises ProductionTouched if any live artefact moved.
    """
    import contextlib
    import io

    if workdir is None:
        raise ValueError('workdir is required — refusing to guess an output location')

    before = snapshot()

    import generate_project_budget as gpb
    import generate_project_output as gpo

    generator_log = io.StringIO()
    completed = []
    try:
        with redirected_paths(sample, workdir) as resolved:
            for label, module in (('budget generator', gpb), ('analysis generator', gpo)):
                try:
                    if quiet:
                        with contextlib.redirect_stdout(generator_log):
                            module.main()
                    else:
                        module.main()
                except Exception as exc:
                    # Re-raised as a partial run rather than passed through raw. The bare traceback
                    # says what broke but not what it means: the outputs now describe different
                    # projects, and the one that did complete looks perfectly fine on disk.
                    raise PartialRun(
                        f'The {label} ({module.__name__}.py) did not complete: '
                        f'{type(exc).__name__}: {exc}\n'
                        f'  completed before the failure: {completed or "none"}\n'
                        f'  did NOT complete: {label}\n'
                        'Both generators must run. Whatever outputs exist now describe different '
                        'projects, and the workbook that was written carries no sign that its '
                        'counterpart is missing or stale.'
                    ) from exc
                completed.append(label)
    finally:
        after = snapshot()
        changes = diff_snapshots(before, after)
        if changes:
            raise ProductionTouched(
                'A verification run modified production artefacts, which must never happen:\n  - '
                + '\n  - '.join(changes)
                + '\nThe redirect in verification/isolation.py is not covering every path the '
                  'pipeline writes to. Investigate before running again.'
            )

    if len(completed) != 2:
        raise PartialRun(
            f'Partial run: only completed {completed}. Both generators must run — otherwise the '
            f'analysis workbook and the client deliverable describe different projects.'
        )

    outputs = {
        'deliverable_dir': resolved['generate_project_budget.BUDGET_OUT_DIR'],
        'analysis': resolved['generate_project_output.OUTPUT_PATH'],
        'roster': resolved['generate_project_budget.ROSTER_FINAL_OUT'],
    }
    return outputs, before, after


def _main():
    import tempfile

    with tempfile.TemporaryDirectory(prefix='budget_verify_') as workdir:
        before = snapshot()
        print('production fingerprints BEFORE:')
        for p, fp in before.items():
            print(f'  {fp[0][:12] if fp else "(absent)":12}  {os.path.basename(p)}')

        print('\nrunning both generators against the sample...\n')
        try:
            outputs, before, after = run_workflow(workdir=workdir)
        except Exception as exc:
            print(f'RUN FAILED: {type(exc).__name__}: {exc}')
            return 1

        print('outputs produced (all inside the workdir):')
        produced = sorted(os.listdir(outputs['deliverable_dir']))
        for name in produced:
            full = os.path.join(outputs['deliverable_dir'], name)
            print(f'  {os.path.getsize(full):>9,} bytes  {name}')

        print('\nproduction fingerprints AFTER:')
        for p, fp in after.items():
            print(f'  {fp[0][:12] if fp else "(absent)":12}  {os.path.basename(p)}')

        changes = diff_snapshots(before, after)
        print('\n' + ('CHANGES DETECTED:\n  ' + '\n  '.join(changes) if changes
                      else 'RESULT: all production artefacts byte-identical and unchanged in timestamp'))
        return 1 if changes else 0


if __name__ == '__main__':
    sys.exit(_main())
