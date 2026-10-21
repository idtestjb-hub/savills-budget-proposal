Sign-off for every measured movement: the user, standing in for the Head of PM. Measurements run on the standard
sample and on the Existing-project regression clone in `Savills-local\budget-test\`. Scripts and logs go under
`Savills-local\budget-test\<date>-<session>-real-budget-ranges\`. Real project names stay in `Savills-local`; the
repository and `docs/` carry anonymous ids only.

## 0. Before

- [x] 0.1 Precondition (design D7): `apply-head-of-pm-decisions-2026-10` is archived, or the user says to start
  before it. Then record the "before" outputs of the standard sample and the clone, and the unit-test count. Verify
  that the files exist and that `verify.py` passes on them.
  - Done 2026-10-19 (lane A): the user chose to start before it and fold both into its group 10 record (D7, as
    changed). "Before" = `4e06955` (groups 0-9 and `fix-cleaning-staffing-ratio` merged; a first round on
    `f8238ea`), from a snapshot, on the standard sample, the clone and the three fixtures: 5 runs, RC 0.
- [x] 0.2 Confirm the store still matches its sources: re-check every source file's modified time against
  `dim_file.modified`, and list any new file in `input/budget_planning/`. Verify: 0 changed, 0 new. If not, rerun the
  scan (`scan-2026-10-07\README.md`, "Bản v2") before the build.
  - Done 2026-10-18 (lane C): 83/83 source files match `dim_file.modified`, 0 changed. The 12 files on disk
    that are not in the store are the 7 originals of the `__repaired` copies and 5 exports (no new budget).

## 1. Reference data

- [x] 1.1 Write `build_real_budget_ranges.py` (design D3, D6) and its unit tests on an invented mini-store (SQLite
  fixture, no real names). It covers: main sheet and high confidence only, no PDF/xlsb/duplicate, latest year per
  project, an unnamed file as its own project, zero/blank counted not valued, `name_key` and `nfa_m2`, and the refusal
  when a name would be written. Verify with the unit tests.
  - Done 2026-10-18 (lane C): `tests/test_build_real_budget_ranges.py`. Rules approved by the user on
    2026-10-18 beyond D3, also covered: the "I." products group as the fee-paying NFA when the store summed
    the product rows (it had added the group rows too, so 5 usable files carried twice their NFA; the group
    matches `Dim_Property_v2_verified` for the three files it holds); two files with one NFA to the m2 are one
    project and a same-year tie goes to the later file date (as the service-level table); two files of one
    name whose NFA differs by more than 5% are two projects, flagged, with a blank `name_key` so that only the NFA
    matches them at run time. `--out` has no default.
- [x] 1.2 Build `Ref_CPI_VN.csv` (design D4): 2021–2025 published averages read from Cục Thống kê's year-end
  releases, and the user-approved stand-in for 2026 and 2027 marked `stand-in`, each with its source and check date.
  Verify with a unit test of the factor for 2021, 2025, 2026, 2027 and 2028.
  - Done 2026-10-18 (lane C): 2021 1.84%, 2022 3.15%, 2023 3.25%, 2024 3.63%, 2025 3.31% published; 2026,
    2027 and 2028 4.52% stand-in. `test_cpi_factor_public_table` and `test_cpi_factor_invented_table`.
- [x] 1.3 Run the build on the real store into `Budget_Agent/data/real_budget_ranges/`, with the id map kept in the
  store folder. Verify:
  - the name scan passes (no store project or file name in the output);
  - the per-code counts of projects with a value match an independent SQL count on the store, written separately
    with the same rules;
  - the file is in the outer repository, not under `source_code/`, and tracked there (`git add -f` if a
    `.gitignore` rule hides `data/`, as with `Ref_UtilityTariffs.csv`);
  - the count of projects per code after the latest-file rule, IQR and leave-one-out is at least 10. On 2026-10-12 it
    was 14 (`ESS23`) to 35 (`ESS12`, `ESC1`).
  - Done 2026-10-18 (lane C): 41 projects, 410 rows; the build's name scan and a separate scan of the written
    files against the store's 208 project and file names pass; an independent SQL count matches all 10 codes.
    With the standard sample (36,679 m2) left out: 14 (`ESS23`) to 37 (`ESC1`). Scripts and logs:
    `Savills-local\budget-test\2026-10-18-laneC-real-budget-ranges\`. Tracking in the outer repository
    (`git add -f`, `data/` is ignored there) is handed to the coordinating session.

## 2. Ranges in the tool

- [x] 2.1 Write `real_budget_ranges.py` (design D1–D5, D8): load, leave-one-out by `name_key` or NFA within 0.5%,
  IQR outliers, 10-project floor, `PERCENTILE.INC` percentiles, CPI factor, VAT, the figure, and the reason when not
  usable. Verify with unit tests on invented values: the project left out, an outlier dropped, 9 projects, a 2025 value
  with its factor, both VAT bases, no pool, no tower.
  - Done 2026-10-18 (lane C): `tests/test_real_budget_ranges.py`. Not wired into the pipeline (part 2).
- [x] 2.2 Write the Vietnamese remark sentences: the priced line, the stand-in note for `ESC1`/`ESC2`, and the zero
  reasons (fewer than 10 projects, no pool, no tower). Verify with unit tests, and that `check_remark_content`'s
  internal-wording scan passes on them.
  - Done 2026-10-18 (lane C): sentences in `real_budget_ranges.py`; the test runs them through
    `_INTERNAL_WORDING_DENYLIST` and the Vietnamese check. The full `check_remark_content` on a deliverable
    runs in part 2, where the generic VAT sentence is appended as on other lines.
- [x] 2.3 Wire the figures into `generate_project_budget.py` for the codes in scope that have no other figure, and
  drop a code from `_FLAGGED_NO_METHOD` only when its range is usable. `2.2 Common area Fund` follows its existing
  allocation. Verify:
  - the standard sample shows the codes non-zero on their own leaf rows;
  - `ESI1`, `EMH1` and `EMH3` are unchanged;
  - `1. Summary` still ties to its detail sheets.
  - Done 2026-10-19 (lane A): `_write_real_budget_range_lines` (design "Measured"). Standard sample: six codes
    non-zero, `ESS23` 0 (in-house pool staff); ESI1, EMH1, EMH3 unchanged; summary reconciliation passes in verify.
- [x] 2.4 Add the `Real-Budget Ranges` sheet to the analysis workbook (`generate_project_output.py`), cross-checks
  for `ESI1`, `EMH1` and `EMH3` included. Verify that a COM read-back shows each priced figure equal to the
  deliverable's line.
  - Done 2026-10-19 (lane A): equal on all five cases after Excel recalculation (`m2_check.py`).

## 3. Verification

- [x] 3.1 Add `check_real_budget_ranges` to `verification/checks.py` and a section to `verify.py` (spec
  `budget-workflow-verification`). Fixtures: an invented values file, a project that matches one entry, and a list of
  invented names. Verify that the check fails on a deliverable with `ESS12` typed 1,000 VND off and passes on the good
  one.
  - Done 2026-10-19 (lane A): unit tests on invented fixtures (`test_verification_ties_floor_and_leave_one_out`,
    `test_name_scan_on_invented_names`) and a negative probe inside the check on every verify run.
- [x] 3.2 Update `openspec/config.yaml` (the "8 detailed project budgets only" line), `RUNNING.md` (how to rebuild the
  data file) and `README.md`'s module map. Verify by reading them back; the config validates (`openspec validate
  --strict`).
  - Done 2026-10-19 (lane A).

## 4. Measurement and sign-off

- [x] 4.1 A/B on the standard sample and on the clone: each moved line, the total expense, the surplus. Each line comes
  with its median, range and project count. Verify that every changed cell is one of the codes in scope or a total that
  contains them. Record it in `docs/project-status.md`.
  - Done 2026-10-19 (lane A): design "Measured". `docs/project-status.md` is the coordinator's (lane rule).
- [x] 4.2 Back-test on the clone: the tool's figures for the codes in scope against the real project's own budget lines,
  with the project left out of its own range. Report the gap per code in `Savills-local`, summarised without names in
  `docs/05-decisions.md`. Verify that the summary names no project.
  - Done 2026-10-19 (lane A): design "Measured"; the summary for `docs/05-decisions.md` goes to the coordinator.
- [x] 4.3 Sign-off: the user (for the Head of PM) approves the 4.1 movements and the 4.2 result. Verify that the approval
  is recorded in `docs/05-decisions.md` with the date.
  - Done 2026-10-19: signed by the user (for the Head of PM), recorded in design "Measured"; the line in
    `docs/05-decisions.md` is the coordinator's.
- [x] 4.4 (Folded into group 10 of `apply-head-of-pm-decisions-2026-10`, design D7 as changed.) Re-record the
  baseline once, with the user's approval, then run `python verification/verify.py` from
  `Budget_Agent/source_code/`. Verify: all sections pass.
