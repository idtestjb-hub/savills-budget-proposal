## 1. Sinking-fund reference data

- [x] 1.1 `build_real_budget_ranges.py`: add `read_sf_lines()`.
  - Read SF budget sheets of the chosen files.
  - Amount = H first, then the read column. A sheet whose read column is the prior year's approved budget gives 0 when H is blank.
  - Take only sheets of the file's own budget year; sum A/B sheets.
  - Drop placeholder sheets: 5 or more expense lines, all with the same amount.
  - Take VAT out with each line's own factor.
- [x] 1.2 Lift driver: the master-list `ElevatorCount` by folded name, one matching row only. Write `basis = lift` for ERLM1–ERLM4 and ESA1. The file also carries `name_key` and `nfa_m2` (coded, as in the management-fund file) for the Review self-exclusion.
- [x] 1.3 Write `Ref_SinkingFundValues.csv`.
  - Add a README section with n and median per code, plus the counts left out (placeholder, other year, no NFA, no lifts).
  - Extend `name_scan` to both.
- [x] 1.4 Build the overlay in a scratch folder outside the repository, using store `final_v5`. Confirm the result matches the 12/11 analysis: 32 projects, 48 codes with at least 10 projects, and ERLM1/ERLM2/ESA1 priced per lift.
- [x] 1.5 Tests (TEST DATA only), one each: H vs read column, the placeholder rule, the other-year sheet, the A/B sum, the lift basis, the name refusal.

## 2. Pricing rule

- [x] 2.1 `real_budget_ranges.py`: add `load_sf_values()` and `price_sf(nfa, lifts, warranty_months, budget_period, self_key, prior=None)`. For each code it returns:
  - the amount per month, or the month vector;
  - the status: `priced`, `pm_fill`, `warranty_zero`, `other_fund`, `carry_forward`;
  - n, p25, p75;
  - the Vietnamese remark.
- [x] 2.2 The warranty list as a closed constant (design D3). Check it against the template's sheet 3 item names at start-up.
- [x] 2.3 One fund per code (design D5).
  - Build the excluded set at run time from sheet 2: any code it writes with an amount, or leaves for the PM. Today that is ERM and ERCS1.
  - Write those codes as 0 on sheet 3, remarked "đang tính ở quỹ quản lý" or "để PM điền ở quỹ quản lý".
- [x] 2.3b VAT: `price_sf` follows sheet 2's basis (`vat_rate` / `vat_factors` / `vat_inclusive` / `vat_clause`, as in `price_line`). A carry-forward base comes out of VAT with its own file's factor. Leave the sheet 3 `VAT` row at 0 until the user decides.
- [x] 2.4 Carry-forward: prior approved per year × `cpi_factor(prior_year → budget_year)`. With no prior, fall back to the median; with no median either, mark `pm_fill`.
- [x] 2.5 Unit tests covering: the median × NFA, the lift count missing, a code under 10 projects, a warranty covering the full year and one ending mid-year, a 0-month warranty, carry-forward with fallback, and an excluded code.

## 3. Input form: warranty months

- [x] 3.1 Back up the live `Project_Budget_Input.xlsx`. Then add two Project Info labels in `build_project_input_form.py`:
  - "Remaining Warranty Months / Số tháng bảo hành còn lại tính từ tháng đầu ngân sách" (default 24, allowed 0–60);
  - "Total Elevators (incl. service) / Tổng số thang máy (gồm thang dịch vụ)" (blank by default; decided 12/11).
- [x] 3.2 Add both to `webapp/fill_input.SCALARS`, the server map and the new-project tab. The generator reads them: warranty 24 when missing; total lifts blank → lift codes left for the PM. The Review / site page pre-fills total lifts from the master `ElevatorCount` (one matching row, no division by towers).

## 4. Generator: sheets 3 and 3.1

- [x] 4.1 Write sheet 3 lines.
  - A priced line gets D = "Monthly", G = monthly amount, U = remark.
  - A line partly in the warranty gets D = "Schedule" with I:T set.
  - A PM line is left blank, shaded, with the remark "PM điền: …".
- [x] 4.2 Review mode: read the input-form sheet `Sinking Fund Prior`, then write the prior figures into 3.1 (code column E, by header) so that AC/AD show them.
- [x] 4.3 Make sheets 3 and 3.1 visible when they hold figures; otherwise leave them hidden.
- [x] 4.4 Add PM rows for sheet 3 (`add_pm_rows` with AF / AL, prefix `SF|`). Record the PM lines in the analysis sheet and in `run.log`.
- [x] 4.5 Add an analysis sheet section "Quỹ bảo trì": the basis, n, p25–p75 and the status per code.

## 5. Budget Review

- [x] 5.1 `review_import.py`: add `SF` to `FUNDS` / `FUND_SHEETS` / `FUND_VI`.
  - Sheet 3 has no total rows, so record a note rather than a tie; never fatal.
  - Read the amount from H (or the column that ties to H), never from a column chosen by its header.
  - Choose the base per code in this order:
    1. the approved file's sheet 3, which is year N;
    2. else 3.1's approved column, through `choose_measures`, with the year noted;
    3. else none, so the line falls to the median.
- [x] 5.2 Write the input-form sheet `Sinking Fund Prior` (code, item, year, approved per year excl. VAT, source) in `write_form`.
- [x] 5.3 `review.py`: add `DELIVERABLE_LAYOUT['SF']` (Z / AA / AF / AL), SF in the fund loops, and the MF-only `.get('MF')` spots that are left alone. Zero-tool rows for SF; codes from `SF_EXCLUDED_CODES` are noted "B8", with no row.
- [x] 5.4 `review_summary.json`: add `sf_rows` (approved, new, median_ref, diff, tags "cao hơn trung vị" / "trong bảo hành" / "PM điền").
- [x] 5.5 Tests, using a TEST DATA approved file with a sinking fund:
  - carry-forward amounts;
  - a 3.1-only file;
  - a file without a sinking fund;
  - MF/CA unchanged.

## 6. Web and adjustment

- [x] 6.1 `webapp/adjust.py`: `FUND_SHORT` / `FUND_VI` for SF. Apply `SF|` edits in `adjust_run.py` to sheet 3 (G = year / 12, remark "PM nhập"). *P4: done through the sheet-4 links (Schedule I:T), remark in U; see design D6.*
- [x] 6.2 `index.html`:
  - SF in `FUND_RANK`, the fund filter and the Review summary loops;
  - the folded section "Quỹ bảo trì" with totals;
  - the line "file không có quỹ bảo trì" when empty.
- [x] 6.3 Check it in the browser (start the local server from a scratch folder; any preview config file is created only for the session and deleted after). Run a new project and the site-package Review sample, and look at the table and the adjust rows. *P4 (12/11): the first site package's Review checked in the browser (site mode, runs in ZWork): the 'Quỹ bảo trì' section (73 rows, totals, source year), the SF row of the summary, the fund filter 'Quỹ bảo trì' (126 Nhập số rows); this found and fixed results.review_summary dropping sf_*. The new-project inputs (warranty months, total lifts) are covered from fill_input to read_input by tests/test_adjust_sinking_fund.py; P4 (16/11): a new-project run on the page (6 warranty months, 12 lifts) found month cells I:T keeping the form's 'mmm' format, read back as dates / #VALUE! (sheet 3 AF14 an error); fixed in fill_sinking_fund_sheet (number format on I:T), test tests/test_sinking_fund_month_format.py, verify section 8c (mid-year warranty); rerun on the page clean: 47 priced, 150 PM lines with Nhập số, lift codes priced.*

## 7. Site package

- [x] 7.1 `site_data.KEEP`: add `real_budget_ranges/Ref_SinkingFundValues.csv`. Confirm the package check scans it.
- [x] 7.2 Package test: an office run and a package run of the same input give the same sheet 3.

## 8. Verification and baselines

- [x] 8.1 `checks.py`: add `check_sinking_fund`. It checks:
  - Summary 66–70 vs sheet 3;
  - the priced lines vs reference × driver, or prior × CPI;
  - the warranty zeros;
  - each PM line has its `SF|` row;
  - no code in both funds;
  - the visibility rule.

  `check_pm_lines` covers both fund sheets.
- [x] 8.2 Wire it into `verify.py` (standard, Existing and Review samples). Run `python verification/verify.py` and the full pytest suite.
- [x] 8.3 Measure before and after: the standard sample, the Existing sample, the site-package Review sample and one more Review. Report the sinking-fund totals and the lines per status, with no project amounts in any repository file. Re-record the baselines once. *P4: measured 12/11 (figures in ZWork, not here): MF/CA unchanged on both package Reviews (0 lines moved) and on verify's samples; no baseline figure moved, so none was re-recorded.*
- [x] 8.4 Open every generated workbook in Excel (COM). Confirm: no repair prompt, no error cells, sheets 3/3.1 visible, `1. Summary` 66–70 filled.

## 9. Docs and hand-over

- [x] 9.1 Update `RUNNING.md`: how to build the SF reference, the warranty months, and the Review carry-forward.
- [x] 9.2 Update `docs/09-template-map.md` (in `PM/Project/docs`): sheet 3/3.1 are now written. Update `docs/project-status.md`.
- [x] 9.3 B8 task for the Head of PM: which fund holds ERM, ERCS1 and the other repair and maintenance codes that real budgets put on the management fund. Waiting; do not change D5 until it is answered. *Answered 16/11: ERM, EMB1, ERCS1 stay on the management fund; ERCS4, ERP2, ESA3, ESA4 on the sinking fund; D5 unchanged (docs/05-decisions.md).*
- [ ] 9.4 PM sign-off on the moved figures. Then rebuild the two site packages, and write the Hub release note through [Hub].
