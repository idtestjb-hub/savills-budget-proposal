## Context

Today the template's `3. Budget-Sinking Fund` and `3.1 Report-Sinking Fund` reach the deliverable blank and hidden.
Nothing in the generator writes them; only `project_facts.py:97` sets a sheet state, and that is for another sheet.
`1. Summary` rows 66–70 read sheet 3 through the template's own VLOOKUP (`'3. Budget-Sinking Fund'!$Z$14:$AI$264`).

**Sheet 3 layout** (template, same grammar as sheet 2 but shifted):

| Column | Holds |
|---|---|
| D | frequency |
| E | the Optional count |
| F | times, a formula |
| G | unit price, the input |
| H | Total Price, `=IF(D="Schedule",SUM(I:T),G*F)` |
| I:T | month cells |
| U | remarks; AJ mirrors it |
| Z | code |
| AA | item |
| AC / AD | VLOOKUP into 3.1 (prior figures) |
| AF | `=SUM(AL:AW)`, the year that `1. Summary` reads |
| AL:AW | monthly allocation formulas |

3.1 holds codes in column E. Its value columns F:Q carry the prior year's actual, expected and approved columns
under headers built from the cover year.

**Review today has no carry-forward step.** `review_import` reads the approved file into the Existing-project input
form. The generator then produces the new year, and `review.py` sets the approved figure beside the tool's figure:
- `FUNDS = ('MF','CA')` is at `review_import.py:50`;
- the deliverable layout per fund is at `review.py:43-46`;
- the adjustment key `<fund>|<code>` is at `webapp/adjust.py:56`.

**The real-budget ranges reader** (`build_real_budget_ranges.read_store`) reads only each file's primary sheet, the
main management fund. Sinking-fund sheets need their own query.

The figures behind every decision below are in the proposal's "Data checks". The detail, keyed by anonymous file id,
lives outside the repository in `Savills-local\budget-agent\sinking-fund-2026-11-12\v2-final_v5\`.

## Goals / Non-Goals

**Goals:**
- Sheet 3 priced for a new project, using the medians, the warranty rule and the PM lines.
- Sheet 3 and 3.1 filled for a review: prior approved × CPI per code, with the median fallback.
- `1. Summary` 66–70 tied and verified.
- A web table for the sinking fund.
- Site packages that price it as the office does.

**Non-Goals:**
- Moving ERM or ERCS1 between funds. That waits on B8.
- Any change to management-fund or common-area-fund figures.
- Reading the sinking fund from PDFs or other forms.
- An equipment-level capex plan.
- Pointing the code at `final_v5`. Store promotion follows the existing procedure (RUNNING.md, "How the store is
  built", step 5).

## Decisions

**D1. Reference data: a second anonymous file, not new rows in `Ref_RealBudgetValues.csv`.**
- The file is `data/real_budget_ranges/Ref_SinkingFundValues.csv`. Its columns are `project_id`, `name_key`,
  `nfa_m2`, `budget_year`, `code`, `basis` (`fee_nfa` or `lift`), `value_unit_month`, `cpi_factor`,
  `value_unit_month_2027`, `flag`.
- Its `project_id` is numbered like the management-fund file's, but the two files may come from different store
  snapshots, so the Review self-exclusion uses the file's own `name_key` (the same coded key) and `nfa_m2`, never a
  join to the other file.
- The median is plain (no IQR trim), the rule the 12/11 analysis and the user's approval used.
- `build_real_budget_ranges.py` builds both files in one run:
  - the same `candidates()` / `group_projects()` choice and NFA;
  - a new `read_sf_lines()` query on `sheet_catalog.fund='SF' and sheet_kind='budget'`;
  - the read rules of the spec: H first, same budget year, A/B sheets summed, placeholder test, line VAT factor;
  - lift counts from the master list via `facts_prefill.fold`, one row only.
- `name_scan` covers the new file and its README section.
- Alternative: add SF rows to the MF file. Rejected: its readers assume per-m² NFA rows and the 7 priced codes, and
  mixing bases there risks a wrong lookup.

**D2. Pricing for a new project: `real_budget_ranges.price_sf(...)`.**
- The rule is median × driver × 12, with at least 10 projects per code for its driver. There is no exclusion of the
  project's own name for a new project; a review uses the existing self-exclusion by name key, as for MF.
- **VAT:** sheet 3 follows sheet 2's basis. It takes the same `vat_rate`, `vat_factors`, `vat_inclusive` and
  `vat_clause` as `price_line`, so a VAT-inclusive deliverable gets each month at that month's rate. A carry-forward
  base is first taken out of VAT with its own file's factor.
- The function returns per code: amount per month, status (`priced`, `pm_fill`, `warranty_zero`, `other_fund`),
  n, p25, p75 and the Vietnamese remark.
- All 32 projects form the pool (user, 12/11).
- Writing a line on sheet 3:
  - D = "Monthly" and G = the monthly amount;
  - U = the remark;
  - sheet formulas give H, AF and the allocation;
  - months inside the warranty use D = "Schedule", with I:T set to 0 or the monthly amount, so H and AF stay
    formula-driven.

**D3. Warranty months.**
- A new Project Info label: "Remaining Warranty Months" / "Số tháng bảo hành còn lại tính từ tháng đầu ngân sách".
  Default 24, allowed 0–60. It goes through `build_project_input_form.py`, `webapp/fill_input.SCALARS` and the
  new-project tab.
- It counts from `Budget Start Month`. The input has no handover date, so the PM enters the months left.
- The warranty list is a closed list in code, built from the template item names and approved by the user on 12/11:
  - the maintenance-contract codes (x1, the ERLM1#/1## variants and ERF*.1; 40 codes);
  - ESA1–21, ERCS1–5, ERS1, EMB1, ERPS4 and ERPS5;
  - ERM, which is on the list but priced on sheet 2 (D5).
- The list is checked against the template at start-up.
- The warranty does not apply in Review mode: carry-forward already reflects what the site budgets.

**D4. Review: the prior figures travel through the input form.**
- *Implementation note (P3, 12/11):* `SF` is read by its own `review_import.read_sf_prior` and compared by
  `review.sf_review`, not by adding it to `FUNDS`: the `FUNDS` loops feed the 'Prior-Year Budget' sheet and the
  management-fund Review, and sinking-fund codes such as ERE2 also exist on sheet 2, so the other funds could move.
  `DELIVERABLE_LAYOUT['SF']` serves the "Nhập số" rows only.
- `review_import` gains `SF` in `FUNDS` and `FUND_SHEETS` and reads sheet 3 / 3.1 like the others:
  - sheet 3 has no R/E total rows, so it gets a "không có dòng tổng" note and is treated as untied;
  - it is never fatal (as for CA).
- The base per code is chosen in this order:
  1. The approved file's own sheet 3, which is the approved year N, × CPI(N → N+1).
  2. When sheet 3 is empty: 3.1's approved column × CPI over the extra years. This is the site-package sample's case.
     A note names the year used.
  3. The median.
- The amount is read from H (unit price × times, or the schedule sum), never from a column chosen by its header.
  On one form variant the header-chosen column is the prior year.
- It is written into a new input-form sheet `Sinking Fund Prior`: code, item, year, approved per year excluding VAT,
  source.
- The generator reads that sheet when present:
  - it brings each code to the budget year with `cpi_factor`;
  - it writes sheet 3;
  - it writes 3.1's approved column (and actual / expected when read) so sheet 3's AC/AD lookups show them.
- `review.py`:
  - a `DELIVERABLE_LAYOUT['SF']` of Z / AA / AF / AL;
  - SF added to the fund loops;
  - zero-tool rows for SF.
- Alternative: compute carry-forward inside `review.py` after generation. Rejected: then the deliverable would hold
  the median while the Review shows another figure.

**D5. One fund per code.**
- The excluded set is derived at run time, after sheet 2 is written: any code that sheet 2 carries with an amount, or
  leaves for the PM. ERM and ERCS1 are today's known members.
- On sheet 3 those codes are left at 0, with one of two remarks:
  - "đang tính ở quỹ quản lý" when sheet 2 prices the code, as for ERM;
  - "để PM điền ở quỹ quản lý" when sheet 2 leaves it for the PM, as for ERCS1.
- A check fails when any code has an amount on sheet 2 and sheet 3. In Review, a file that budgeted these codes in
  its sinking fund shows the approved figure against 0. The Review row notes "B8", and no "Nhập số" row is added.

**D6. Adjustment and web.**
- *Implementation note (P4, 12/11):* a sheet 3 line on '4. Điều chỉnh' is a Schedule row whose I:T link back to sheet
  4 month by month (`budget_adjustment._link_fund_row`), so `adjust_run` writes nothing on sheet 3 itself: the PM's
  "Nhập số" figure reaches I:T and AF through those formulas, and the remark in U becomes "Số do PM nhập: … VND/năm. Công
  cụ không tính được: …" (`webapp/adjust.remark_col`: U on sheet 3, T elsewhere). Only PM lines and a Review's zero
  rows are on sheet 4; priced sheet 3 lines are not. `adjust_run` reports the sinking-fund total (sheet 3 AF14) beside
  the two other funds. The Review's approved figure per `SF|` key comes from `sf_rows` in `review_summary.json`, since
  sheet 'Review' carries MF and CA only.
- `FUND_SHORT['3. Budget-Sinking Fund'] = 'SF'`.
- `budget_adjustment.add_pm_rows` runs for sheet 3 with AF / AL as the year and first-month columns.
- `adjust_run` applies `SF|` rows to sheet 3 (G = year / 12, D = "Monthly", remark "PM nhập").
- `index.html`:
  - `FUND_RANK` gets SF:2, and the fund filter gets a "Quỹ bảo trì" option;
  - the Review summary loops gain SF;
  - a new folded section, "Quỹ bảo trì", fed from `review_summary.json`.
- The JSON gains `sf_rows` with code, item, approved, new, median_ref, diff, tags.

**D7. Sheet visibility.**
- After writing: sheet 3 has any non-zero AF, or 3.1 has any prior figure → both `sheet_state = 'visible'`.
- Sheet order is unchanged. Sheet 4 still follows 3.1, as `check_adjustment_sheet` requires.

**D8. Verification.**
- `checks.py` gains `check_sinking_fund`, covering:
  - Summary 66–70 equal to sheet 3 (read through Excel recalculation, as the other ties are);
  - each priced line equal to the reference × driver, or prior × CPI;
  - the warranty zeros;
  - the PM lines with their `SF|` rows;
  - no code in both funds;
  - visibility.
- `check_pm_lines` reads both fund sheets.
- `verify.py` wires it for the standard, Existing and Review samples. The baselines are re-recorded once.
- *Implementation note (P4, 12/11):* the check recomputes each line from the reference file with
  `statistics.median` (not `price_sf`), reads the totals through Excel, and the sheet 3 formula text through openpyxl
  (Excel refuses a bulk `.Formula` read of that sheet). `check_adjustment_sheet` and `check_pm_lines` read sheet 3 too.
  verify's "Review" sample is the Existing sample plus an invented 'Sinking Fund Prior' sheet (section 8b): it runs the
  generator's carry-forward half; reading an approved file is covered by `tests/test_review_sinking_fund.py`.

**D9. Site package.** `site_data.KEEP` gains `real_budget_ranges/Ref_SinkingFundValues.csv`. It carries no names, so
no MASK entry. The package check scans it.

## Risks / Trade-offs

- **[Median is a weak predictor: about 87% median error]** → The remark states the basis and the p25–p75 range. The
  PM is expected to adjust. The user accepted this for new projects on 12/11.
- **[Carry-forward copies last year's one-off renovations]** → The Review table shows the median reference and tags
  a line far from it. The PM adjusts through `SF|` rows.
- **[Lift counts]** The master's `ElevatorCount` counts every lift, service lifts included. The run uses the new
  total-lifts input on the same basis (decided 12/11), and the remark names the count.
- **[ERLM3/ERLM4 and other lift codes need a lift count]** → Missing lifts give PM lines, never a silent 0.
- **[The store's SF column misread, and the placeholder files]** → Handled in the reader (D1). The store itself
  is not changed. A note goes to the store README.
- **[Rebuilding the input form overwrites the live `Project_Budget_Input.xlsx`]** → Back it up first (budget-agent
  rule).
- **[The template's 3.1 header columns may differ between form years]** → Columns are found by header text through
  `review_measures.parse_period`, the same as 2.1. An unread column gives a note, never a guess.

## Migration Plan

1. Build `Ref_SinkingFundValues.csv` from the store as an overlay in a scratch folder. Measure, get sign-off, then copy
   it into `data/real_budget_ranges/`.
2. Code changes behind no flag: an input without "Warranty Months" uses 24.
3. Re-record the baselines once, with the movement reported: the standard sample, the Existing sample, the site-package
   Review sample and one more Review.
4. Rebuild the two site packages, then write the Hub release note through [Hub].

Rollback: revert the commit. The data file is unused without the code.

## Open Questions

- **B8 (Head of PM):** which fund holds ERM, ERCS1 and the other repair and maintenance codes that real budgets put on
  the management fund (ERCS4, ERP2, ESA3, ESA4…)? Until it is answered, D5 holds.
- ~~Lift count for the lift codes~~ **Decided 12/11 (user):** a new Project Info input "Total Elevators (incl.
  service)" / "Tổng số thang máy (gồm thang dịch vụ)", the same count as the master's `ElevatorCount`. The site page
  pre-fills it from the master total (one matching row, no division by towers). Blank or 0 → the lift codes are PM
  lines "chưa có số thang máy". The per-tower passenger input stays for its other uses.
- ~~The `VAT` row on sheet 3~~ **Decided 12/11 (user):** leave it at 0; the lines are written on sheet 2's VAT basis.
- ~~Warranty for an Existing project without a Review~~ **Decided 12/11 (user, P4):** no warranty. An Existing form
  without a 'Sinking Fund Prior' sheet is priced like a Review with no prior figures: the median for all twelve months.
- ~~PM rows for the codes under 10 projects~~ **Decided 12/11 (user, P4):** keep them. Every code the tool cannot price
  (54 in the standard sample) is a shaded "PM điền" line with its "Nhập số" row on sheet 4, as the spec says. The same
  holds in a Review, where no warranty applies, so a package Review carries 126–134 such rows (kept, user 12/11).
- ~~A base older than N−1~~ **Decided 12/11 (user, P4):** keep it, brought forward with CPI from its own year, the year
  named (one package file's 3.1 is two years older than the file).
- ~~City Garden's master lift count of 1~~ **Decided 12/11 (user, P4):** the rebuilt package leaves total lifts blank
  for the PM to enter; the other package pre-fills the master total. *16/11 (P5):* the build had no way to do this
  (`--facts` only adds, and a Review fills a blank fact back from the master by name), so the user chose a small fix
  inside this change: `build_site_package.py --blank-fact total_lifts` drops the fact, notes it and lists it in
  `site.json` `blank_facts`; the site server sends those labels as `_no_master` and `master_fallback` skips them
  (`tests/test_blank_fact.py`).
- **Store promotion:** whether `final_v5` replaces `final_v4` for every reader. It is a separate decision; this change
  builds its reference from the store the build is pointed at.
