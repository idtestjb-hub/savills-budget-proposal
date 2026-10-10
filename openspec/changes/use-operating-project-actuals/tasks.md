## 0. Approval gates (no code before these)

- [x] 0.1 Through the user, take P1–P4 to the Head of PM, each with its row of design.md "Expected movement" and the "Decisions awaiting the Head of PM" table (PM-1 to PM-6). Record each answer, with name and date, in design.md and `docs/05-decisions.md`. Verify: P1–P4 each read approved or rejected; PM-1 to PM-6 each have an answer.
- [x] 0.2 For P4, also record the approval of whoever signs for the AI Guideline (PM-6). Verify: name, date and decision reference are in design.md. Without them, groups 6 and 7.1's collect-on-behalf fields do not start.
- [x] 0.3 For each rejected proposal, and for PM-1 (b), PM-3 (b) or PM-4 (b), revise this change with `/opsx:update`: remove or adjust the spec delta, these tasks and the proposal line. Verify: `openspec validate use-operating-project-actuals --strict` passes, and no remaining requirement depends on a rejected proposal.
- [x] 0.4 Get the user's go-ahead to start P5 (group 2), which moves no figure. Verify: the go-ahead is quoted in the session report.

## 1. Before measurements (no code edits)

- [x] 1.1 Run `python verification/verify.py` from `Budget_Agent/source_code/` and save the output outside SharePoint as "before". Verify: PASS on every section, and the saved path is in the report.
- [ ] 1.2 Build the regression clone (design D8) in a new dated folder under `Savills-local\budget-test\`. Remove the reference project from the clone's `Dim_Property_Residential.csv` and `Fact_ProjectLocation.csv`, fill the scale fields with non-zero known values, and record the hash of the live `Project_Budget_Input.xlsx`. Verify: a default (new-building) run of the clone reproduces the 2026-10-07 comparison's new-building revenue and expense totals, or any difference is explained before going on.
- [x] 1.3 Generate "before" deliverable and analysis copies, in a temp folder, for the standard synthetic project and the existing three-product test copy in `Savills-local\budget-test\`. Verify: four workbooks exist and their paths are in the report.

## 2. P5: one rate resolver (moves no figure)

- [x] 2.1 Add the resolver beside the rate functions in `master_comparables.py` (design D1). It returns each product's rate, source kind, comparables used, note and VAT basis, plus the ranking. Verify: a test covers each source kind (comparable, Apartment fallback, blended fallback), and the blended fallback gives the rate `build_budget()` gives today.
- [x] 2.2 In `generate_project_budget.py`, call the resolver once in `build_budget()` and pass the result to `fill_management_fund_sheet()`, the `0. Info` fee table, the complete-total note and `add_comparison_sheet()`. Remove the five derivation sites. Verify: grep finds no `derive_product_rate`, `derive_product_rate_capped` or `derive_mgmt_rate` call left in that file.
- [x] 2.3 In `generate_project_output.py`, call the same resolver once in the `Management Fee` section and remove its two derivation sites. Verify: grep as in 2.2 finds none.
- [x] 2.4 Regenerate the four workbooks of 1.3 and compare them cell by cell with the "before" copies. Verify: no difference in any formula or number; the comparison output is in the report.
- [x] 2.5 Run `python verification/verify.py`. Verify: PASS, and no baseline re-recorded.

## 3. P3: stable-operation switch (only if approved in 0.1)

- [ ] 3.1 Read `Stable Operation?` through `L.has()`. Accept Yes, No or blank, stop on any other value, and print the `Operating-project inputs:` block (design D6). Verify: the standard sample's form, which lacks the label, runs unchanged, and a value of "Maybe" stops the run and names the field.
- [ ] 3.2 Give the four `fill_curve` functions a `stable` argument and pass `project['stable_operation']` from every caller in both generators (design D3). Verify: with `stable` false, each function's output equals today's, by test; with it true, every value is 1.0.
- [ ] 3.3 Show the user the stable-operation wording for the ramped-line remark, the `RM.0A` remark and the fill-up sheets, and record the approved text in design.md. Then write it. Verify: on a run with the switch Yes, no remark contains the new-building curve wording, `RM.0A` is zero in all 12 months, and both fill-up sheets show 100% with the reason.
- [ ] 3.4 Measure on the regression clone: switch off vs on, line by line (`RM.0A`, collected `RM.*`, `RP*`, `EEE.C`, `EEW.C`), plus revenue, expense and surplus totals. Keep absolute figures in the clone folder; put only ratios in this change's folder. Verify: the movement matches design.md P3 or the difference is explained; the Head of PM signs off the measured movement.

## 4. P1: entered rate wins (only if approved in 0.1)

- [ ] 4.1 Add the `Actual Rate (VND/m²/month)` and `Rate VAT Basis` columns to the product mix block in `build_project_input_form.py`, testing only with `OUT_DIR` / `FINAL_OUT` / `OUT` rebound to a temp folder. Verify: the freshly built temp form carries both headers and the VAT list; the live form's hash is unchanged.
- [ ] 4.2 In `read_input()`, read both columns by header (design D2). A blank or 0 rate means not entered. Text or a negative value stops the run, and so does a rate without its VAT basis. A rate on a product without area is named in the printout. Verify: one test per scenario of the "entered real rate" requirement.
- [ ] 4.3 Rank an entered rate first in the resolver, without the swing cap, and make an entered Apartment rate the fallback for products with neither an entered nor a comparable rate. Verify: tests show the cap is not applied and the fallback follows the entered Apartment rate; both workbooks agree on a two-product case.
- [ ] 4.4 Show the user the entered-rate remark and the VAT-mismatch sentence (design D2), record the approved text, then write the remarks, the `Comparison` label and the printout. Verify: on a run with an entered rate, the remark states the source and the VAT basis and names no comparable as the source; the benchmark clause calls the rate the PM's figure.
- [ ] 4.5 Measure on the regression clone with the project's real rates entered. Verify: `RM.AP` equals the real budget's line within rounding, the analysis workbook shows the same rate as the deliverable, and the ratios are recorded as in 3.4; the Head of PM signs off.

## 5. P2: recorded parking revenue (only if approved in 0.1)

- [ ] 5.1 Add `Actual Car Parking Revenue (VND/month)` and `Actual Motorbike Parking Revenue (VND/month)` to the form builder (temp paths as in 4.1) and to `read_input()` through `L.has()`. Stop when a figure is entered without the stable switch (PM-3). Verify: tests for the blank, entered, zero and no-switch cases.
- [ ] 5.2 In the deliverable, write an entered figure flat × 12 on `RP1` / `RP2`, quote it in the `RPa` narrative, and set `BM11` by the rule in design D4. Verify: on a run with both figures entered, `RP2` = figure × 12 with equal months; the allocation rows keep their proportions; with both figures 0 the sheet has no `#DIV/0!`.
- [ ] 5.3 Use the same figures in the analysis workbook's parking section. Verify: both workbooks show the same `RP1` and `RP2` in VND.
- [ ] 5.4 Measure on the regression clone with the recorded monthly averages entered. Verify: `RP1` and `RP2` equal the real budget's lines; `RP8`, `ESS38` and `RM.PA` are unchanged; the ratios are recorded; the Head of PM signs off.

## 6. P4: collect-on-behalf pairs (only if approved in 0.1 and 0.2)

- [ ] 6.1 Add catalogue entries for each `RO3.*` / `RO4.*` code in the approved mapping (PM-5) and its paired expense row (PM-2). Each entry gets the departure, the guideline's own wording, the approver, the date and the decision reference. Each entry keeps "not estimated" as the behaviour when no amount is entered. Verify: a before/after diff of `Costing_Method_Catalogue.csv` shows only those entries.
- [ ] 6.2 Teach `verification/method_coverage.py` the new method. An approved departure is expected, and a departure without an approval record is a mismatch. Verify: in a scratch copy of the catalogue, removing one approval record makes the report list that code as a mismatch; and on the standard synthetic project, the method-fidelity figure and the remark-assertion count are the same as in the 1.1 "before" output.
- [ ] 6.3 Add the `COLLECT ON BEHALF (THU HỘ CHI HỘ)` block to the form builder (temp paths) and to `read_input()`. Stop for an unmapped product and for amounts without the stable switch; list zeros in the printout. Verify: one test per scenario of the requirement.
- [ ] 6.4 Show the user the paired remarks, record the approved text, then write each entered amount on its revenue row and its paired expense row, flat × 12. Verify: on a run with two products' amounts, every pair is equal, the surplus equals the same run with the amounts blank to within 1 VND, and the template's VAT/CIT rows are still 0.
- [ ] 6.5 Measure on the regression clone with the project's collect-on-behalf amounts. Verify: three pairs, each equal to the real budget's revenue line; the surplus is unchanged; the Head of PM and the guideline approver sign off.

## 7. Verification of the operating-project path

- [ ] 7.1 Add a fictional operating-project intake under `verification/fixtures/` that fills only the approved proposals' fields (spec "Verification exercises the operating-project path"). Verify: none of its values equals a value of the reference project; check against a list kept in the clone folder, not in this repo.
- [ ] 7.2 Add the operating-project section to `verify.py` and record its baseline with a reason naming this change. Verify: the section passes, and the standard sample's baseline is not re-recorded.
- [ ] 7.3 Prove each check can fail, in scratch copies only: one workbook ignores an entered rate; `RM.0A` is non-zero; `RP2` is not the entered figure × 12; one pair is unbalanced. Verify: each failure names the figure with both values in VND, and the four outputs are in the report.

## 8. Close-out

- [ ] 8.1 Run the regression clone once with every approved proposal on. Verify: the revenue, expense and surplus ratios against the real budget are recorded next to design.md "Expected movement"; the live `Project_Budget_Input.xlsx` hash equals the one from 1.2; the Head of PM signs off the combined movement.
- [ ] 8.2 Update `RUNNING.md` (the new fields and how to add their labels to an existing form), `verification/README.md` (the new section), `docs/05-decisions.md` (the answers from 0.1) and `docs/project-status.md`. None of them names the reference project. Verify: each file describes the new behaviour; `git status` in both repositories lists only the files this change touched.
- [ ] 8.3 Run `openspec validate use-operating-project-actuals --strict`, then `python verification/verify.py` from `Budget_Agent/source_code/`. Verify: both pass; the standard synthetic project's recorded baseline is unchanged.
