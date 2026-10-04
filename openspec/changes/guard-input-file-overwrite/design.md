## Context

`build_project_input_form.py` builds the blank workbook in a temporary file (`OUT`) and then
unconditionally copies it onto `FINAL_OUT`, which is `Budget_Agent/reports/Project_Budget_Input.xlsx`
(`main()`, last lines). Nothing reads or tests that target first. The three path names are module
globals, so a test can point them at a temporary folder; `verification/run_workflow.py` already
relies on the same idea for the generators. No other module calls the builder: `run.py` and the
generators only mention it in an error message that tells the user to run it.

See proposal.md for why.

## Goals / Non-Goals

**Goals:**
- A run with no `--force` cannot change or delete an existing project input workbook.
- A run with `--force` cannot lose the replaced workbook.
- The guard is exercised by `verify.py` without touching the live reports folder.

**Non-Goals:**
- No `--out` option or other way to build into a different folder (tests rebind the module paths).
- No judgement about whether the existing file "looks filled in". Presence of the file is the test.
- No change to the form's content, sheets, labels or defaults.
- No cleanup of old `*_PRE_*.xlsx` backups already in `reports/`.

## Decisions

**1. Check at the top of `main()`, before anything is built.** A refused run then leaves nothing
behind (no temp file, no message about a local copy). Alternative: build first and refuse at the copy
step, leaving the blank form in the temp folder for inspection. Rejected: the person who wants a
blank form to compare can use `--force`, which keeps a backup.

**2. `main(force=False)` raises `LiveInputExists` (a `RuntimeError` subclass carrying the path);
the `__main__` block catches it, prints the message and exits 1.** A function that raises is testable
without spawning a process; a non-zero exit lets any launcher or script notice the refusal.
Alternative: print and return normally. Rejected: a script would report success while nothing was
built. Alternative: an interactive "overwrite? y/n" prompt. Rejected: the builder is also run from
launchers and by tools with no keyboard.

**3. Argument handling with the standard library's `argparse`, one flag `--force`.** No new
dependency; `requirements.txt` is unchanged.

**4. Backup is `shutil.copy2` into the same folder, named `Project_Budget_Input_PRE_FORCE_<yyyy-mm-dd_hhmmss>.xlsx`
(with `_2`, `_3`… if that name is taken).** The name follows the three hand-made backups already in
`reports/`. After copying, the copy is compared byte for byte with the original; any exception or
mismatch aborts before the overwrite. A backup is never deleted by this script. The time to the
second, plus the counter, means a second forced run cannot overwrite the backup of the project the
first one replaced (found while writing the test: with minute resolution two runs in one minute
would have). The backup is made at the top of `main()`, before the form is built, so a build that
fails part-way leaves the original in place and a backup beside it. Alternative: back up to a different folder. Rejected: the person looking for the old file
looks beside it. This does add a file to a SharePoint-synced folder; that is the point.

**5. "Exists" means a file is present at the target path** (any size, whether or not Excel has it
open). An open file is therefore refused too, which is the safe side; the existing "still locked"
branch only matters for a forced run.

**6. The verification check builds in `tempfile.TemporaryDirectory`.** It writes a stand-in
workbook (a few bytes, not a real form) to the temp `FINAL_OUT`, rebinds the module's `OUT_DIR`,
`FINAL_OUT` and `OUT` there, calls `main()` (expects `LiveInputExists`, stand-in byte-identical),
then `main(force=True)` (expects a backup equal to the stand-in's old bytes and a replaced file),
and restores the globals in a `finally`. It also hashes the live input file before and after, as
`run_workflow` does for its production list, so a bug in the rebinding would be caught. It is wired
in as section 7 of `verify.py`, after the existing six.

## Risks / Trade-offs

- A person who relied on the old behaviour (rebuild without thinking) now sees a refusal. That is
  the intended change; the message says what to type.
- The check imports and runs the full builder (about 800 lines of openpyxl work) twice, so
  `verify.py` gains a second or two. Acceptable against the several minutes it already takes.
- Rebinding module globals only protects the test, not a future edit that adds a fourth path
  constant to the builder. The hash comparison of the live file is the backstop for that.
- Backups accumulate in `reports/`. They are small (about 30 KB) and named so they are easy to find.
