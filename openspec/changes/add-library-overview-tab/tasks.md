## 1. Builder: usage file

- [x] 1.1 In `build_real_budget_ranges.py`, record each file's decision (reason code, merged-into id) while `candidates()` and `group_projects()` run, and for `RM.AP` left out in `build_rows()`; verify with a unit test that every store file gets exactly one decision.
- [x] 1.2 Write `Ref_RealBudgetUsage.csv` (`file_id, usage, reason_code, merged_into`) in `write_outputs()`, include it in the name check, and verify the builder refuses a store name in it (test).
- [x] 1.3 Run the builder on the 2026-10-22 store into a scratch folder and verify: 87 rows, 55 used / 3 merged / 29 left out, `used` equals the project count of `Ref_RealBudgetValues.csv`, and `Ref_RealBudgetValues.csv` is byte-identical to the committed one.
- [x] 1.4 Add a test that every id in the README "Files excluded or merged" list has the matching usage and reason code in the usage file.

## 2. Web server: aggregates

- [x] 2.1 Add `reason_kind` to each `library.load()` entry (existing sentence unchanged) and verify `tests/test_webapp_library.py` still passes with a new assertion per kind.
- [x] 2.2 Add a function in `webapp/library.py` that returns the aggregates (per year × class, reasons, file type × class) for both views, reading `Ref_RealBudgetUsage.csv` and checking its ids against `dim_file.csv`; verify with tests for the 87-file shape, a missing usage file, and an id mismatch (view 2 unavailable with the unlisted count).
- [x] 2.3 Add `GET /api/library/overview` behind `require_user` in `webapp/server.py` and verify with tests: refused without a session, and no response string contains a file name, project name or path.

## 3. Web page

- [x] 3.1 Add the "Kho ngân sách" tab to `static/index.html` with the two views, the stacked-column SVG, the reason table and the file-type table (Primary palette as explicit hex, Arial, no gridlines, no logo); verify in the browser pane on a local run at desktop width that each table sums to the total.
- [x] 3.2 Show the plain "not available" message when view 2 is unavailable and the empty message when no store is found; verify both by running the page against a scratch store without the usage file and with an empty store folder.
- [x] 3.3 Check light and dark mode and a narrow width; verify no text is cut off and the page fits one screen at 1280 × 800.

## 4. Close

- [x] 4.1 Run the full test suite (`python -m pytest`) and `openspec validate --all --strict`; verify both pass.
- [x] 4.2 No figure moves: confirm `Ref_RealBudgetValues.csv` is unchanged in git, then run `python verification/verify.py` from `Budget_Agent/source_code/` and verify it passes (about 35 minutes; run last).
- [x] 4.3 Update `docs/project-status.md`, write the release note for [Hub] (`Savills-Automation-Hub-Setup\releases\`, template `_MAU-RELEASE.txt`), and commit `source_code` first, then the outer repository, only on the user's request; report both hashes.
