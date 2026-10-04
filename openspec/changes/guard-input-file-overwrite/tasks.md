## 1. Guard in the builder

- [x] 1.1 In `build_project_input_form.py`, add `LiveInputExists`, a `force` parameter on `main()`, and the check at the top of `main()`. Verify: with paths rebound to a temp folder holding a stand-in file, `main()` raises `LiveInputExists` and the stand-in's bytes and mtime are unchanged and the folder holds no other file.
- [x] 1.2 Add the dated backup before the copy, with the size comparison and abort-on-failure. Verify: with the same temp setup and `main(force=True)`, a `Project_Budget_Input_PRE_FORCE_*.xlsx` exists whose bytes equal the stand-in's old bytes, and `FINAL_OUT` now opens as the blank form; with the backup copy forced to fail, `FINAL_OUT` is unchanged.
- [x] 1.3 Add `argparse` with `--force` in the `__main__` block; print the refusal message and exit 1 on `LiveInputExists`. Verify: running `python build_project_input_form.py` against a temp-rebound copy exits 1 with the message naming the file; with `--force` exits 0.
- [x] 1.4 Confirm first-time creation is unchanged. Verify: with an empty temp folder, `main()` writes the form and the workbook's four sheets match those listed in `RUNNING.md`.

## 2. Verification section

- [x] 2.1 Add `check_input_form_guard()` to `verification/checks.py` implementing design decision 6, and call it as section 7 of `verification/verify.py`. Verify: `python verification/verify.py` prints section 7 as OK and the live `reports/Project_Budget_Input.xlsx` hash is the same before and after.
- [x] 2.2 Prove the check can fail. Verify: temporarily make the guard a no-op in a scratch copy of the module (not the repo file), run the check against it, and see it report that the guard did not hold; discard the scratch copy.

## 3. Documentation and close-out

- [x] 3.1 Update `RUNNING.md` step 1 (the refusal, `--force`, the backup) and `verification/README.md` (seven sections, the new check). Verify: both files read correctly and name the new section.
- [x] 3.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`. Verify: PASS on all seven sections, and the figure baselines are unchanged (no re-record).
- [x] 3.3 Report files changed, commands run and results, and remaining risks. Verify: the report lists the live-input hash before and after.
