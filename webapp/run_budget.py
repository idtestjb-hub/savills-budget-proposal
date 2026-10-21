"""
Run the whole pipeline (run.py) against ONE input workbook, with every output written into ONE
folder, without touching Budget_Agent/reports or Budget_Agent/sample_output.

    python webapp/run_budget.py --input <Project_Budget_Input.xlsx> --workdir <folder>

run.py itself takes no arguments: both generators resolve their input and output locations from
module-level constants. verification/isolation.redirected_paths already rebinds those constants
(it is how verify.py runs the real pipeline on a synthetic project), so this reuses it rather than
editing run.py. The run log lands in <workdir>/run_log because run_log.write derives its folder
from the input file's folder.

Exit code is run.main()'s own (0 = both workbooks written and they name the same project).
"""
import argparse
import os
import sys

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--workdir', required=True)
    args = ap.parse_args()

    # Line-buffered, UTF-8 output so a parent process can stream the log as it is written.
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    os.chdir(SOURCE_DIR)

    from verification.isolation import redirected_paths
    import run

    workdir = os.path.abspath(args.workdir)
    os.makedirs(workdir, exist_ok=True)
    with redirected_paths(os.path.abspath(args.input), workdir) as resolved:
        for name, path in sorted(resolved.items()):
            print(f'  redirect  {name:44} {path}')
        rc = run.main()
    return rc


if __name__ == '__main__':
    sys.exit(main())
