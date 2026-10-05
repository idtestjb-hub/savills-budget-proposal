## 1. Measure before editing

- [x] 1.1 Without editing code, call the management-fee hand-check on the Diamond Skyline test copy (`C:\Users\CDangQuang\Savills-local\budget-test\2026-10-05-diamond-skyline`: `input_copy.xlsx` and `out\Project_Budget_Output.xlsx`). Verify: the printed gap for `mgmt_fee_revenue_annual` is 394,200,000 VND (1,800 m² × 18,250 × 12) and the line is red.
- [x] 1.2 Without editing code, run the Required-code check on `out\Diamond Skyline - Sample Consulting Budget.xlsx` and save its row list. Verify: RP5 on `2.2 Common area Fund` reads "ok — zero, reason stated", and no other Required line passes on a remark in `_TEMPLATE_OWNED_T_ROWS`.
- [x] 1.3 Run `python verification/verify.py` from `Budget_Agent/source_code/` and save the output as the "before" copy outside SharePoint. Verify: PASS, and the output file path is noted in the report.
- [x] 1.4 Generate the Diamond Skyline deliverable into a temp folder with the existing run script in the test folder, and keep it as the "before" copy. Verify: the file exists and its path is noted in the report.

## 2. The hand-check

- [x] 2.1 Make `read_sample_scale` also return every product's area by label, and make the hand-check sum over all nine products (design D1), with unpriced products counted 0 and named in the description (design D2). Verify: on the Diamond Skyline copy the gap in 1.1 is within 1 VND and the line is green.
- [x] 2.2 Update the comments in `hand_checks` that say only the three priced products are anchored. Verify: no comment in `verification/baseline.py` still names the three-product list.

## 3. RP5 reason and the checks

- [x] 3.1 Show the user the proposed Vietnamese RP5 reason (design D3), record the approved text in design.md, then add the write step to `fill_common_area_fund_sheet` (only when the cell is empty or exactly "demo"). Verify: on a fresh Diamond Skyline run, `2.2` T15 holds the approved text plus the VAT sentence, and the RP5 figure is still 0.
- [x] 3.2 Remove the RP5 cell from `_TEMPLATE_OWNED_TEXT_CELLS` and the RP5 line from `_TEMPLATE_OWNED_T_ROWS`, add the placeholder mapping, and make the Required check treat the exact placeholder as no reason (design D4). Verify: `python verification/verify.py` passes.
- [x] 3.3 Prove each check can fail, in a scratch copy of the deliverable or generator, never in the repo file: put "demo" back into T15 (the Required check, the wording scan and the line-remark scan each fail and name the cell); drop a price row for a product that has an area (the hand-check names it as unpriced and does not fail); change one product's area in the input copy by 5 m² (the hand-check fails as not anchored). Verify: each of the four outcomes is pasted into the report.

## 4. Close-out

- [x] 4.1 Compare the "before" and "after" Diamond Skyline deliverables cell by cell. Verify: no difference in any formula or number; the only text difference is `2.2` T15; the comparison output is pasted into the report.
- [x] 4.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`. Verify: PASS on every section; no baseline re-recorded; the Required-check row list is unchanged (118 rows, RP5 now passes on a real reason), and rejection of the placeholder is proven by task 3.3 case A.
- [x] 4.3 Update `verification/README.md` (hand-check covers every product; RP5 no longer exempt) and `docs/project-status.md` (the 2026-10-05 entry, and the "hand check sums only three products" red line is gone). Verify: both files name the new behaviour; `git status` in both repositories lists only the files this change touched.
