## 1. Labour-law parameter table

- [x] 1.1 Create `data/generation_B_verified/Ref_LaborLawParams.csv` with the columns in design D3 and the rows listed in spec `existing-project-staffing` (regional minimum wage I to IV effective 2024-07-01 and 2026-01-01, insurance base 2,340,000 and 2,530,000 VND, ceiling multiple 20, employer rates, trade union 2%, plus the template rows 13th month and 10% markup); every legal row has a legal basis and a checked-on date. Verify: a unit test loads the file and fails on a row without legal basis or effective date.
- [x] 1.2 Add a loader that returns the values in force for each month of a budget year, and a clear message when the year starts after the latest row. Verify: unit tests for a year inside one rule, a year spanning 2026-06-30 / 2026-07-01 (insurance base changes mid-year), and a year after the latest row.
- [x] 1.3 Replace the `STATUTORY_*_2026` constants in `generate_project_output.py` with values read from the table. Verify: New-prospect run of the standard sample gives zero cell differences against the recorded baseline (before/after, `verify.py` section on figures unchanged).

## 2. Input form

- [x] 2.1 Add to `Project Info` the fields "Project Mode" (dropdown "New prospect", "Existing project"), "Minimum Wage Region" (I–IV, blank = I) and "Prior Budget Year"; add the sheet "Prior-Year Roster" with four labelled blocks (roster with New Headcount / New Monthly Gross / Reason Code / Reason Note columns, Holiday and Night Duty, Staff Lines with approved prior-year EMH2/EMH3/EMH4, override and reason, Actual Headcount (optional)); and the two columns "Reason Code" and "Reason Note" on `Staffing Demand`, in `build_project_input_form.py` (design D8–D10). Verify: a freshly built form shows the new fields and the dropdown values; the guard that refuses to overwrite a filled form still passes.
- [x] 2.2 Write the helper that appends the new sheets and fields to a dated copy of an existing filled input workbook, leaving the original untouched. Verify: run it on a copy of a filled form, confirm the original's bytes are unchanged and the copy opens in Excel without a repair prompt.
- [x] 2.3 Read mode, region, prior year, the four blocks and the reasons by label in the generators; a blank mode is "New prospect"; an unknown mode, or "Existing project" with neither roster rows nor an approved prior-year EMH2, stops with a message naming the fields. Verify: unit tests for blank, valid, unknown, roster-only, lump-sum-only and neither cases.

## 3. Staffing in Existing-project mode

- [x] 3.1 Implement the source priority of design D9 (roster rows and their New columns for codes the roster covers; typed headcount, else ratio, for codes it does not, labelled "ước tính"), and the overflow of design D12. Verify: unit tests for the three sources, for a code with more heads than its `A1` rows, and for the rule that New-prospect mode computes exactly as before.
- [x] 3.2 Feed the roster's headcount and monthly gross straight into `A1` column G (no daily-rate conversion), apply the minimum-wage floor and write the budget-year parameters to `A1!I4/I5/T8/U8/V8` (Existing-project mode only, design D14), keep the `A1` formula chain unchanged; build the Python replica of the `A1` row chain (design D13); without a roster, EMH2 is the approved amount (design D8). Verify: an invented fixture with a salary below the floor is raised to the floor and the line carries the generated reason; `EMH2` equals the `A1` payroll without the allowance; the replica equals Excel's recalculated `A1` on the fixture.
- [x] 3.3 Price EMH3 on `A1.1` from the Holiday and Night Duty block and the paid-holiday calendar, exclude it from EMH2, and generate the holiday reason (design D10). Verify: a unit test with a year that has one more paid holiday than the baseline year raises EMH3 by that day's cost and names the holiday; the deliverable's EMH2 + EMH3 counts the allowance once.
- [x] 3.4 Recompute EMH4 per design D11 (prior amount × minimum-wage ratio; zero stays zero; blank = as today) and attach a reason when it changes. Verify: unit tests for the three cases with invented figures.

## 4. Calendar and law checks

- [x] 4.1 Check `vn_holidays.py` against the law for 24 November as a paid public holiday from the year it applies, and cite the legal basis in the file and in `docs/05-decisions.md`. Verify: a test counts the paid holidays of the budget year and agrees with the number in `docs/project-status.md` (12 for 2027) or the discrepancy is written to the decision log.
- [ ] 4.2 Confirm with the Head of PM whether a regulation for 2027 exists that is not in the table; if so add its row. Verify: the table row exists with its source, or the Staff bridge states that no newer rule was available.

## 5. Reasons and remarks

- [x] 5.1 Implement the reason record (code, text, source) and the approved code list; "Khác" requires a note. Verify: unit tests for each code and for the missing note.
- [x] 5.2 Append "Điều chỉnh so với NS <năm>: …" after the guideline's original remark on changed staffing lines; unchanged lines keep the original remark only. Verify: a generated workbook shows both parts on a changed line and one part on an unchanged line; the remark content check and the internal-wording scan pass.

## 6. Staff bridge

- [x] 6.1 Build the internal Staff bridge sheet in the analysis workbook in the order of design D4 and D13 (with the PM-override step and the reason records), the optional actual-headcount comparison and the back-cast flag; `run.py` reports a changed line without a reason after an Existing-project run. Verify: the bridge total equals EMH2 plus EMH3 plus EMH4 on the invented fixture and on the back-test clone; the client deliverable contains no bridge sheet; `run.py` fails on a fixture with a missing reason.

## 7. Verification

- [x] 7.1 Add the two checks to `verification/checks.py`: changed staffing line without a reason fails; Staff bridge ties to EMH2 plus EMH3 plus EMH4 and is absent from the client deliverable (present only in Existing-project mode). Add an invented Existing-project fixture under `verification/fixtures/` and a verify section that runs the pipeline on it with these checks (the New-prospect fixture and its baselines stay untouched). Verify: each check fails on a deliberately broken fixture and passes on a good one.
- [x] 7.2 Run `python verification/verify.py` from `Budget_Agent/source_code/` with no other run in progress. Verify: it passes all sections and the recorded baseline needs no re-record.

## 8. Measurement and sign-off

- [x] 8.1 Regression: run the standard sample in New-prospect mode before and after the change. Verify: zero formula or number differences, recorded in `docs/project-status.md`.
- [x] 8.2 Acceptance on project X in a clone outside SharePoint: feed the approved 2026 line amounts and holiday-duty counts (project X has no roster, design D8), compare EMH2 and EMH3 for 2027 with the real 2027 file, and report both figures, the Staff bridge and the gap, with and without the PM's +5% override. Verify: EMH2 within the agreed tolerance (proposed plus or minus 5%), EMH3 includes the added holiday with its reason, every changed line has a reason; results are kept in `Savills-local` and not committed.
- [x] 8.3 Invented second case (multi-region wage floor plus a headcount change) in the test suite. Verify: the case passes and its fixture contains no real name or payroll.
- [ ] 8.4 Sign-off: the Head of PM approves the reason-code list and the 8.2 result before the change is archived. Verify: the approval is recorded in `docs/05-decisions.md` with the date.

## 9. Detail sheets tie to the staffing lines (design D15, added 2026-10-10)

- [x] 9.1 A line that ends at zero in Existing-project mode (e.g. approved EMH4 of 0) gives its reason to the matching '2.2 Common area Fund' allocation. Verify: the Required-line-item check passes on project X's variants A and B.
- [x] 9.2 Compute the detail rows in `existing_staffing.py` (carried, minimum-wage and PM-adjustment rows per line). Verify: unit tests for lump-sum, carried EMH3, carried EMH4 with and without a ratio change, and overrides on each line.
- [x] 9.3 Write the rows on A1, A1.1 and A5, zero the empty PM row's X and A5's default team where D15 says so, and make EMH2/EMH3/EMH4 formulas into them, with remarks naming the rows. Verify: project X variants A and B still match the real 2027 file and every line equals its detail sheet.
- [x] 9.4 Add the detail-tie check to `verification/checks.py` and a second invented sample without a roster to section 8. Verify: the check fails on a deliverable whose EMH2 is a typed number; `verify.py` passes both samples; New prospect A/B before and after shows 0 differences.
