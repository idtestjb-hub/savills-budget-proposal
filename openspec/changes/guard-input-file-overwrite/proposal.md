## Why

`build_project_input_form.py` writes a blank form with placeholder data straight onto the live
`Budget_Agent/reports/Project_Budget_Input.xlsx`, with no check that a filled-in project is already
there. `RUNNING.md` warns that "this has destroyed live input more than once", and the only
protection today is a sentence a person has to remember. The verification harness protects itself
from production files, but that does not cover someone running the builder by hand.

## What Changes

- The builder stops, before it builds anything, when `Project_Budget_Input.xlsx` already exists in
  the reports folder. It says which file it kept and how to force a rebuild, and exits with a
  failure code. The existing file is left exactly as it was.
- A new `--force` option allows the rebuild. Before replacing the file, the builder copies it beside
  itself as `Project_Budget_Input_PRE_FORCE_<yyyy-mm-dd_hhmm>.xlsx` (the same naming the folder
  already uses for hand-made backups). If that copy cannot be made, nothing is replaced.
- First-time creation (no existing file) behaves as it does today.
- Verification gains one section that builds the form twice in a temporary folder, once without
  and once with `--force`, and fails if the guard does not hold. The live reports folder is not
  touched by that section.
- `RUNNING.md` step 1 and `verification/README.md` describe the guard.
- No figure moves. No baseline is re-recorded. No generated workbook changes.

## Capabilities

### New Capabilities
- `input-form-protection`: what building the input form may and may not do to a project input
  workbook that already exists.

### Modified Capabilities
- `budget-workflow-verification`: verification also confirms the input-form guard (a delta spec
  adds one requirement; the existing requirements are unchanged).

## Impact

- `build_project_input_form.py`: new guard, `--force`, dated backup.
- `verification/checks.py` and `verification/verify.py`: one new check and one new section (7).
- `RUNNING.md`, `verification/README.md`: wording.
- Outer repo `docs/project-status.md`: section count and backlog row, at the end of the work.
- Nothing in the generators, the template, the baselines or the data files changes.
