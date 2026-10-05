## 1. README

- [x] 1.1 Re-derive the import graph of every module in `source_code/` and confirm each module's role from its own header and the file it writes. Verify: the module list in the new README equals the `*.py` files directly in `source_code/` (31 today), none missing, none from `legacy/`.
- [x] 1.2 Rewrite `README.md` per design decisions 1 and 2, keeping the pointer to `RUNNING.md`. Verify: every filename and path it names exists (a short script run once, output pasted into the report); the "Stale index" banner is gone.

## 2. Docstrings

- [x] 2.1 Correct the wiring statements in the `estimate_capex_qty.py` docstring. Verify: each claim about callers matches a grep of the repo (`generate_project_output.py:37`, `generate_project_budget.py:45`, `estimate_new_project.py:34`); the file still parses (`ast.parse`); `git diff` shows comment lines only.
- [x] 2.2 Correct the wiring and "next step" statements in the `transform_master_list.py` docstring (who reads its CSVs today; what still comes from the 8 detailed budgets). Verify: same grep and parse check; `git diff` shows docstring lines only.

## 3. Config and RUNNING

- [x] 3.1 Show the user the new `context` and `rules` wording for `openspec/config.yaml` and, once approved, write it. Verify: `openspec list` and `openspec validate --all` run without error; `docs/Fact_Dim_Master_Mapping.md` is no longer referenced.
- [x] 3.2 Correct the template file name, sheet counts and "files read at run time" list in `RUNNING.md` from the code (`TEMPLATE_PATH`, a count of sheets in a freshly generated workbook, the data paths the generators open). Verify: each corrected figure comes with the command or line that shows it, listed in the report.

## 4. Close-out

- [x] 4.1 Run `python verification/verify.py` from `Budget_Agent/source_code/`. Verify: PASS on all sections and no baseline re-recorded.
- [x] 4.2 Report files changed, commands run and results, remaining risks. Verify: `git diff --stat` lists only the files named in the proposal's Impact section.
