Sign-off: the user, standing in for the Head of PM. No figure should move; the proof is a before/after that shows every
figure equal. Measurements run on the standard sample and on the Existing-project regression clone in
`Savills-local\budget-test\`. Scripts and logs go under `Savills-local\budget-test\<date>-<session>-service-levels\`.
Real project names stay in `Savills-local`; the repository and `docs/` carry anonymous ids only.
Values revised on 2026-10-18 (security upper cut-off 3.0, sanity bounds, form-only percentile, identical-NFA rule,
"sát ngưỡng" mark) come from `Savills-local\budget-test\level-of-service\phan_bien_p1.md`.

## 0. Before

- [x] 0.1 Record the "before" outputs of the standard sample and the clone (client deliverable, internal analysis,
  roster) and the unit-test count. Verify that the files exist and that `verify.py` passes on them.
  Done 2026-10-18: `Savills-local\budget-test\2026-10-18-p1-service-levels\before\{sample,clone}` (3 workbooks each),
  `figures_sample.json` / `figures_clone.json` (32 figures each, no read error), `verify_before.log` = PASS.
- [x] 0.2 Confirm the store still matches its sources: compare each source file's modified time with
  `dim_file.modified` and list any new file in `input/budget_planning/`. Verify: 0 changed, 0 new. If not, rerun the
  scan before the build.
  Done 2026-10-18: 87 store files matched by name, 0 changed; 4 store entries are the scan's own converted copies
  (`XLSB__`, `ZIP_`) and have no source file; on disk but not in the store: 5 index / model workbooks and 2 invented
  A&K test files (not budgets), 7 originals of the `old8` set that the store holds as repaired copies, and one
  2026-04 Fiato "tính (F Zone - Share G2)" workbook, most likely a content duplicate of the 2026-05 Fiato file the
  store holds. No rescan: no source file changed and the one unmatched file would at most add one row.

## 1. Reference data

- [x] 1.1 Check how the store counted cleaning and security headcount (`extract_fix_v7.py`, `levels4_v7.py` in
  `level-of-service`) against the roster rule in design D5. Verify by writing the comparison on three projects
  (form-read, inferred, no NFA) and recording any difference in the task log. In the same log, open the source files
  of the two cleaning extremes (anonymous ids D32 at 1,062 m² per cleaner and D16 at 7,819) and of the security
  misread (D17: form without an hours column, one row read) and record whether each reading is right; a wrong
  reading is a scan fix, not a threshold change.
  Done 2026-10-18 (`task_log.md` §1.1 in the session folder): the readers count people on duty per form row
  (security × hours / 24); the user chose the matching tool rule (Staff On Duty / Day; 24H = 24 h, other shifts 8 h)
  and the total fee-paying NFA. D17: 14 posts on the form, one row read (text shift column) → fixed later on 2026-10-18 (session P2,
  readers v8: 11.33 posts and 16 cleaners read from the form, `2026-10-18-p2-reader-fix\task_log.md`);
  D16: forms not recognised, inferred from cost, same level; D32: read right, the extreme came from the apartment NFA.
- [x] 1.2 Write `Ref_ServiceLevelThresholds.csv` (design D1) with the approved cut-offs, the sanity bounds, the
  approval dates (2026-10-16 for the cut-offs; 2026-10-18 for the security upper cut-off 3.0 and the bounds) and the
  landscape row marked "not set". Verify with a unit test that loads it and reads back the 2 cut-offs and 2 bounds
  for cleaning and security. Done 2026-10-18 (`tests/test_service_levels.py`).
- [x] 1.3 Write `build_service_levels.py` (design D5, D7, D10, D11) and its unit tests on an invented mini-store
  (SQLite fixture, no real names). Cover: latest year per project, an unnamed file as its own project, two names with
  one identical NFA merged into one row, a form-read and an inferred headcount, missing NFA, zero or blank measure, a
  value outside the bounds kept but not classified, the "sát ngưỡng" mark at cut-off × 0.9 and × 1.1 (inside and
  outside), and a refusal to write when a name would be written. Verify with the unit tests.
  Done 2026-10-18 (`tests/test_build_service_levels.py`, 24 tests across both files pass).
- [x] 1.4 Run the build on the real store into `Budget_Agent/data/service_levels/`, keeping the name-to-id map in the
  store folder. Verify:
  - 48 projects, 45 with a total fee-paying NFA; cleaning gives 7 Nâng cao, 24 Tiêu chuẩn, 11 Cơ bản, 6 "chưa phân
    loại" (3 thiếu NFA, 3 ngoài cận) and security gives 8, 20, 15 plus 5 "chưa phân loại" (3 thiếu NFA, 2 ngoài cận)
    (the 2026-10-18 regression figures; the spec scenario carries them);
  - 3 projects not classified for lack of NFA;
  - form-read, classified rows: 24 for cleaning and 28 for security;
  - no two rows with identical NFA;
  - the name scan passes (no store project or file name in either file);
  - the files sit in the outer repository, not under `source_code/`, and are tracked there (`git add -f` if a
    `.gitignore` rule hides `data/`).
  Done 2026-10-18: `build.log` in the session folder; map and names list in `scan-2026-10-07\final_v2\`;
  `Ref_ServiceLevelProjects.build.txt` beside the table lists the 4 merged files by store id. Tracking: at commit.
  Rebuilt 2026-10-18 (session P2) from `level_assignment_v8.csv` after the reader fix: cleaning 8 / 23 / 11 / 6,
  security 8 / 21 / 15 / 4 (3 thiếu NFA, 1 ngoài cận), form-read classified 28 and 31, map and names list unchanged;
  row diff in `Savills-local\budget-test\2026-10-18-p2-reader-fix\task_log.md`; the quick check on the clean copy
  passes 28 checks with the five deliberate breaks each caught (`gen_check_v8.log`).
  Rebuilt 2026-10-18 (session P2) from `level_assignment_v8.csv` after the reader fix: cleaning 8 / 23 / 11 / 6,
  security 8 / 21 / 15 / 4 (3 thiếu NFA, 1 ngoài cận), form-read classified 28 and 31, map and names list unchanged;
  row diff in `Savills-local\budget-test\2026-10-18-p2-reader-fix\task_log.md`; the quick check on the clean copy
  passes 28 checks with the five deliberate breaks each caught (`gen_check_v8.log`).

## 2. Service levels in the tool

- [x] 2.1 Find the roster rows for security and cleaning in `generate_project_output.py` and the headcount, coverage
  hours and fee-paying NFA the tool already uses. Verify by listing, for the standard sample, the rows found and
  their sum against the costed total. Done 2026-10-18 (`task_log.md` §2.1): 7 security rows (on duty 10, 3.33 posts,
  roster 17) and 2 cleaning rows (on duty 3, roster 4) on the standard sample; NFA 54,400 = the Management Fee sheet.
- [x] 2.2 Write `service_levels.py` (design D2, D3, D4, D5, D8, D10, D11): load both tables, compute the two measures,
  classify with the edge rule, mark "chưa phân loại" with the reason (including outside the bounds), mark "sát
  ngưỡng", and compute the percentile over form-read classified projects with the project left out, plus the
  inferred count for reference. Verify with unit tests: 60,000 m² and 20 cleaners; 100,000 m² with 10 posts of 24
  hours and 10 of 12 hours (1.5, "sát ngưỡng"); 2,400 m² per cleaner ("sát ngưỡng"); 2.9 and 3.0 posts; values
  exactly on 2,500, 4,000, 1.5 and 3.0; 0.08 posts (not classified, value kept); no NFA; zero headcount; an inferred
  row never in the percentile set; the project left out of its own percentile. Done 2026-10-18 (`tests/test_service_levels.py`).
- [x] 2.3 Write the Vietnamese notes for the sheet: display only, no figure changes, fee-paying NFA is not the cleanable
  area, thresholds are round values read off real projects and not an outside standard, input or benchmark headcount,
  the comparison uses form-read projects only with the inferred count beside it, what "sát ngưỡng" means, and the
  landscape gap. Verify by reading the cell text back from the generated workbook. Done 2026-10-18: 9 notes read
  back (`gen_check.py` output, `task_log.md` §2.4).
- [x] 2.4 Add the `Service Levels` sheet to the internal analysis (design D9) in `generate_project_output.py`.
  Verify by generating the standard sample, opening the workbook through Excel, and checking no `#REF!`, `#DIV/0!`
  or `#VALUE!` and that headcount equals the roster. Done 2026-10-18: Excel recalculation clean, 15th sheet, on-duty
  and roster counts tie (`task_log.md` §2.4).

## 3. Verification

- [x] 3.1 (done 2026-10-18: `check_service_levels`, verify section 5h and the Existing-sample sections; the five
  deliberate breaks each fail, `task_log.md` §3.1) Extend `verification/checks.py` and `verify.py`: sheet-to-roster tie; levels and "sát ngưỡng" marks
  recomputed independently from the threshold table; edge values; out-of-bounds value not classified; comparison set
  form-read and classified only, count equal to its size; no duplicate NFA in the real-project table; every other
  sheet and the deliverable equal to the recorded baseline; name scan of both data tables against the list kept
  outside the repository. Verify by a deliberate break of each (wrong headcount, a changed cut-off, an inferred row
  counted, a duplicated NFA row, a name inserted) failing the check.
- [x] 3.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`. Verify: passes, and no baseline was
  re-recorded. Done 2026-10-18 on a clean copy (HEAD + this change, with the two reference budgets and the HEAD
  tariff table): PASS, all 9 sections, 63 OK lines (`verify_after3.log` in the session folder). On the live checkout
  the run fails section 4 on 7 OPEX figures and section 8 on a new `vat` tariff row, both from another session's
  uncommitted group-2 edits, not from this change. No baseline re-recorded.

## 4. Measure and sign-off

- [x] 4.1 Rerun the standard sample and the clone, and compare to the "before" from 0.1. Verify: every client-deliverable
  figure and every existing sheet is identical; the only new content is the `Service Levels` sheet. Name who signs it
  off (the user, for the Head of PM). Done 2026-10-18 on a clean copy (HEAD + this change, because another session's
  uncommitted group-2 edits sat in the live checkout): sample 32 figures and clone 32 figures 0 changed; analysis
  14 → 15 sheets, deliverable and roster unchanged (`diff_after.log`, `task_log.md` §4.1). Sign-off: the user, for the
  Head of PM — given 2026-10-18 (session P2): the thresholds, the security upper cut-off 3.0 and the bounds confirmed;
  recorded in `Ref_ServiceLevelThresholds.csv` (source column) and `docs/05-decisions.md`.
- [x] 4.2 (done 2026-10-18: Active table row, decision section "Service levels: fixed thresholds...", RUNNING.md
  section "The Service Levels sheet" and the reads list; anonymous ids only) Update `docs/project-status.md`, `docs/05-decisions.md` (the thresholds and bounds, their approval dates, the
  2026-10-18 revisions with the reasons from `phan_bien_p1.md` in plain words, and the reasons for the choices in
  design D3 and D4) and `RUNNING.md` (how to rebuild the table). Verify by reading each file back; the anonymised ids
  appear, no project name does.
- [x] 4.3 Add one line to `Savills-local\budget-test\level-of-service\README.md`: the v7 combined level is history
  and the tool's two separate levels are the definition from 2026-10-18 (design D12). Verify by reading it back.
  Done 2026-10-18 (paragraph at the end of that README, read back).
