# Tasks — rebase-output-onto-25-sheet-form

Deliverable: one committed blank template + a one-line `TEMPLATE_PATH` change + verification updates.
No budget figure moves in value. Money stays in VND with units stated. Reads/writes no Generation A
or B table; no Fact/Dim join-key change.

## 1. Confirm the shared sheets are safe to re-base — DONE 2026-09-10

- [x] 1.1 Diffed every pipeline-touched sheet row-by-row between `202608` and the 25-sheet AI Guideline form (`diff_templates.py`, `_fulldiff.py`). Result: `2. Budget-Management Fund` (493 codes) and `2.2 Common area Fund` (453 codes) row-identical; `3. Budget-Sinking Fund` / `3.1` / `1. Summary` differ materially but the pipeline never writes them; `0. Info` row 11 `Shopping Mall`→`Shophouse` is the only write-site difference (display only); `A2`/`A3` differ in example staffing only (pipeline computes those costs in Python). Drove design D1 (strip, not graft) and D1a. Verify: findings recorded in `design.md` Context table.
- [x] 1.2 Every `wb['<name>']` sheet access in `generate_project_budget.py` resolves in the AI Guideline form (15/15 Savills sheets). The staff sheet: the form's native `A1. Staff cost 08.2026 (VN)` is byte-for-byte the same payroll calculator as `202608`'s `1. Staff cost From 08.2026 (VN)` except cell G15 — so `STAFF_COST_SHEET` is re-pointed, no graft (design D1).
- [x] 1.3 `2. Budget-Management Fund` / `1. Summary` / `2.2 Common area Fund` carry zero formula references into `Tỷ lệ lấp đầy cư dân`, `Tiến độ lấp đầy bãi xe`, `Master Info`, or `B2.6`.

## 2. Build the blank standard template (design D1)

- [x] 2.1 Write `build_standard_template.py` in the change folder: start from the AI Guideline form; clear the `AI GUIDELINE` instruction cells (`L` on `0. Info` and `1. Summary`, `W` on `2. Budget-Management Fund`, `H` on `B2.6`, and the advisory column on `A2`/`A3`); drop the `Master Info ( tính Staff cost)` sheet (design D3); clear the identifiable THẢO ĐIỀN GREEN project inputs on the three new sheets (occupancy/parking curve rows and count cells, `B2.6` example working columns) while keeping every formula. No staff-sheet graft — the native `A1. Staff cost 08.2026 (VN)` / `A1.1 Allowance` are the same calculator as `202608`'s (design D1). Verify: script runs and writes `input/template/2027 Resi Budget Form (IT team).xlsx` — 24 Savills sheets (25 minus `Master Info`).
- [x] 2.2 Assert the deleted columns are the only formula difference: for each edited Savills sheet, formula-cell count and used-range (minus the removed column) match the source. Verify: report shows no unexpected formula loss.
- [x] 2.3 Open the built file through the pipeline's `copyfile → common_utils_v2.repair_workbook() → load_workbook` path. Verify: opens without repair; `generate_project_budget.py`'s 15 accessed Savills sheet names + `A1. Staff cost 08.2026 (VN)` + `A1.1 Allowance (From 08.2026)` all present; `Master Info` absent; openpyxl reports no missing sheets.
- [x] 2.4 Recalculate the built file and the blank `202608` in Excel (COM) and compare error cells. Verify: the built file opens without an Excel repair prompt; it has **no `#REF!` / `#NAME?` / `#VALUE!` cell that blank `202608` did not already have**; any extra `#DIV/0!` is confined to `Tỷ lệ lấp đầy cư dân` / `Tiến độ lấp đầy bãi xe` (unfilled fill-up sheets that change B populates). Re-confirm no formula on any other sheet references those two sheets or `B2.6` — they feed no budget total.
- [x] 2.5 Confirm `202608 - 2027 Resi Budget Form.xlsx` stays in `input/template/`; add a short `input/template/README` marking it superseded by the new file. Verify: both files present; note names the successor and the change.

## 3. Repoint the pipeline

- [x] 3.1 Change `TEMPLATE_PATH` in `generate_project_budget.py` to the new template. Verify: `python run.py` completes and writes the client deliverable and the internal analysis.
- [x] 3.2 Update the `0. Info` write block (design D1a): write Apartment(8) / Officetel(9) / Office(10) / **Shophouse(11)**; stop writing Shopping Mall to `0. Info`; update the stale comment at `generate_project_budget.py:977-979`. Verify: on a run with a Shophouse product, `0. Info!B11..E11` shows the Shophouse figures; a Shopping Mall product's `RM.SM` revenue still lands on `2. Budget-Management Fund` unchanged.
- [x] 3.3 Confirm the row guard runs against the new template and covers `MGMT_FUND_ROWS`, `PRODUCT_REVENUE_ROWS` and `COMMON_AREA_FUND_ROWS`; extend `assert_row_code` coverage to any not currently guarded (design D5). Verify: deliberately passing a wrong expected code makes the run stop and name the mismatch.
- [x] 3.4 Re-point `STAFF_COST_SHEET` to `'A1. Staff cost 08.2026 (VN)'` (design D1); update the `WORKDAYS_PER_MONTH` source comment and the "pasted by a PM" comment. Verify: `fill_staff_cost_sheet` writes column G on `A1.`; the deliverable's staff-cost figures match a run on the old template (see 4.1); `Comparison` sheet still added.

## 4. Figure parity and re-baseline

- [x] 4.1 Generated the fixture deliverable on the old and new templates and diffed `2. Budget-Management Fund` and `2.2 Common area Fund` cell by cell. Result: **every line the pipeline writes is identical**; three template-default cells differ (`ESC12` 14M, `ESM25` 14M/yr, one `2.2 Common area Fund` cell → `RI` −119k), all unwritten by the pipeline, `202608` shipping unsourced examples the standard form leaves blank. Net: deliverable expense −28M VND (−0.28%). Recorded in `design.md` D1b.
- [x] 4.2 No verification baseline figure is re-recorded — `verify.py`'s 24 figures are all analysis-workbook figures (template-independent) and all still match the 2026-09-08 baseline within tolerance (`verify.py` run 2026-09-10). The ~28M deliverable-total shift is documented in `design.md` D1b and `docs/05` D6, not baselined (those two lines belong to change D).
- [x] 4.3 Re-record the deliverable sheet-count baseline (22 → 25: 24 Savills sheets + `Comparison`) with a stated reason, or switch the check to "carries every standard-template sheet name" if that is how `verify.py` expresses it. Verify: `verify.py`'s recorded expectation matches the new deliverable and the reason references this change.

## 5. Verification harness

- [x] 5.1 Add the `budget-workflow-verification` delta's check: the generated deliverable carries every sheet name the standard template defines; verification fails and names any missing sheet. Verify: removing a sheet from a test copy makes `verify.py` fail and name it.
- [x] 5.2 Run `python verification/verify.py`. Verify: green — structural pass, formula-error check clean under full recalculation, sheet-set check passes, headline figures match the (re-recorded) baseline.
- [x] 5.3 Run `openspec validate rebase-output-onto-25-sheet-form --strict`. Verify: reports valid.

## 6. Records

- [x] 6.1 Update `docs/05-decisions.md` D6: note the template is built and live, and that `Master Info` is deferred to change C with the `#REF!` / external-link reason (design D3). Verify: D6 status line updated.
- [x] 6.2 Update `docs/08-guideline-change-family.md`: mark change A done; note `Master Info` moved from A to C. Verify: the table row for A shows done and C mentions Master Info.
- [x] 6.3 Manual spot-check task (per `openspec/config.yaml`): a reviewer confirms 6 headline figures on the new-template deliverable for one real project against the same figures on the old-template deliverable. Verify: sign-off recorded with the project name and the 6 figures in VND.
