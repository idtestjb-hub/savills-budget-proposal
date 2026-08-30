"""
Redirects the pipeline's hardcoded input/output paths at run time so verification can exercise the
real code path against synthetic data without reading or writing anything in production.

Why this exists (see the change's design.md, decision D1): neither generator's main() takes
arguments. Both resolve their input and output locations from module-level constants, so the only
way to point the workflow somewhere else — without editing production code — is to rebind those
constants on the imported modules before calling in.

A NON-OBVIOUS DETAIL, verified rather than assumed: generate_project_output.py imports INPUT_PATH
*by value* from generate_project_budget at module load. Rebinding only the source module leaves
generate_project_output still holding the original production path, so the budget generator would
read the sample while the analysis generator quietly read the live input. Both bindings are
therefore rebound, and the self-check below proves it.

Nothing here modifies the pipeline. Originals are restored on exit so a process that imports these
modules for anything else afterwards sees them unchanged.
"""
import contextlib
import os


class ConstantMissing(RuntimeError):
    """Raised when a path constant this module expects to rebind no longer exists.

    Deliberately fatal. If a constant were renamed and this failed quietly, the generators would
    fall back to their real defaults and write over live deliverables — the exact outcome
    verification exists to prevent.
    """


# module attribute -> ('dir'|'file', filename when 'file')
# Both modules are listed separately because each holds its own binding (see module docstring).
REDIRECT_PLAN = {
    'generate_project_budget': {
        'INPUT_PATH':       ('input', None),
        'BUDGET_OUT_DIR':   ('dir',   None),
        'ROSTER_OUT_DIR':   ('dir',   None),
        'ROSTER_FINAL_OUT': ('file',  'Roster_Demand_Model.xlsx'),
    },
    'generate_project_output': {
        'INPUT_PATH':  ('input', None),
        'OUTPUT_PATH': ('file',  'Project_Budget_Output.xlsx'),
    },
}


def _assert_constants_present(modules):
    """Fail loudly, naming what is missing, before anything is rebound."""
    missing = []
    for mod_name, consts in REDIRECT_PLAN.items():
        mod = modules[mod_name]
        for const in consts:
            if not hasattr(mod, const):
                missing.append(f'{mod_name}.{const}')
    if missing:
        raise ConstantMissing(
            'Cannot isolate the pipeline from production data — these path constants no longer '
            'exist: ' + ', '.join(missing) + '. The pipeline has been refactored since this '
            'verification was written. Update REDIRECT_PLAN in verification/isolation.py to match '
            'before running again. Refusing to continue, because proceeding would let the '
            'generators write to their real production locations.'
        )


@contextlib.contextmanager
def redirected_paths(sample_input, workdir):
    """Point both generators at `sample_input` and have every output land inside `workdir`.

    Yields a dict of {'<module>.<constant>': resolved path} so a caller can show exactly where the
    workflow was aimed. Restores every original value on exit, including on error.
    """
    import generate_project_budget as gpb
    import generate_project_output as gpo
    modules = {'generate_project_budget': gpb, 'generate_project_output': gpo}

    _assert_constants_present(modules)

    sample_input = os.path.abspath(sample_input)
    workdir = os.path.abspath(workdir)
    os.makedirs(workdir, exist_ok=True)

    originals = {}
    resolved = {}
    try:
        for mod_name, consts in REDIRECT_PLAN.items():
            mod = modules[mod_name]
            for const, (kind, filename) in consts.items():
                originals[(mod_name, const)] = getattr(mod, const)
                if kind == 'input':
                    new = sample_input
                elif kind == 'dir':
                    new = workdir
                else:
                    new = os.path.join(workdir, filename)
                setattr(mod, const, new)
                resolved[f'{mod_name}.{const}'] = new
        yield resolved
    finally:
        for (mod_name, const), value in originals.items():
            setattr(modules[mod_name], const, value)


def _self_check():
    """Prove the redirect works: print every resolved path and confirm it is inside the workdir.

    Exits non-zero if any path still points at a production location.
    """
    import sys
    import tempfile

    here = os.path.dirname(os.path.abspath(__file__))
    sample = os.path.join(here, 'fixtures', 'Sample_Project_Input.xlsx')

    with tempfile.TemporaryDirectory(prefix='budget_verify_') as workdir:
        import generate_project_budget as gpb
        import generate_project_output as gpo
        before = {
            'generate_project_budget.INPUT_PATH': gpb.INPUT_PATH,
            'generate_project_output.INPUT_PATH': gpo.INPUT_PATH,
        }

        with redirected_paths(sample, workdir) as resolved:
            print(f'sample input : {sample}')
            print(f'workdir      : {workdir}\n')
            print('redirected constants:')
            leaked = []
            for name, path in sorted(resolved.items()):
                inside = os.path.commonpath([path, workdir]) == workdir
                ok = inside or (path == os.path.abspath(sample))
                if not ok:
                    leaked.append(name)
                print(f'  {"OK  " if ok else "LEAK"}  {name:44} {path}')

            print('\nboth INPUT_PATH bindings point at the sample:')
            for m in ('generate_project_budget', 'generate_project_output'):
                v = resolved[f'{m}.INPUT_PATH']
                print(f'  {"OK  " if v == os.path.abspath(sample) else "LEAK"}  {m}')

        print('\noriginals restored after exit:')
        restored = (gpb.INPUT_PATH == before['generate_project_budget.INPUT_PATH']
                    and gpo.INPUT_PATH == before['generate_project_output.INPUT_PATH'])
        print(f'  {"OK  " if restored else "FAIL"}  both modules back to their production values')

        if leaked or not restored:
            print('\nRESULT: FAILED')
            sys.exit(1)
        print('\nRESULT: every path is inside the workdir or the sample; originals restored')


def _guard_check():
    """Prove the missing-constant guard actually fires, and fails safe when it does.

    Simulates a renamed constant by removing the attribute from the imported module rather than
    editing the pipeline source — at run time that is the identical condition (hasattr is False),
    and it leaves production code untouched.

    Three things must hold: the abort happens, the message names the missing constant, and nothing
    was rebound before the abort (a partial rebind would leave the modules in a half-redirected
    state that later code could mistake for a working redirect).
    """
    import sys
    import tempfile

    import generate_project_budget as gpb
    import generate_project_output as gpo

    here = os.path.dirname(os.path.abspath(__file__))
    sample = os.path.join(here, 'fixtures', 'Sample_Project_Input.xlsx')

    victim = 'BUDGET_OUT_DIR'
    saved = getattr(gpb, victim)
    input_before = gpb.INPUT_PATH
    gpo_input_before = gpo.INPUT_PATH

    aborted = named = unchanged = False
    try:
        delattr(gpb, victim)
        with tempfile.TemporaryDirectory(prefix='budget_guard_') as workdir:
            try:
                with redirected_paths(sample, workdir):
                    pass  # must not be reached
            except ConstantMissing as exc:
                aborted = True
                named = f'generate_project_budget.{victim}' in str(exc)
                unchanged = (gpb.INPUT_PATH == input_before
                             and gpo.INPUT_PATH == gpo_input_before)
                message = str(exc)
    finally:
        setattr(gpb, victim, saved)

    print(f'simulated a rename of generate_project_budget.{victim}\n')
    print(f'  {"OK  " if aborted else "FAIL"}  aborted instead of continuing')
    print(f'  {"OK  " if named else "FAIL"}  message names the missing constant')
    print(f'  {"OK  " if unchanged else "FAIL"}  nothing was rebound before the abort')
    print(f'  {"OK  " if hasattr(gpb, victim) else "FAIL"}  constant restored after the test')
    if aborted:
        print(f'\n  message: {message[:150]}...')

    if not (aborted and named and unchanged and hasattr(gpb, victim)):
        print('\nGUARD RESULT: FAILED')
        sys.exit(1)
    print('\nGUARD RESULT: guard fires, names the constant, and fails before any rebinding')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _self_check()
    print('\n' + '-' * 70 + '\n')
    _guard_check()
