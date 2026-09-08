## 1. Record the starting point

- [x] 1.1 Capture the current values of the figures this change is expected to move — Savills staff cost, total profit value, margin and markup, plus the three `service_*_annual` figures as controls that must NOT move — verify by confirming each is present in `verification/baselines/baseline.json` and noting its value before any code is touched
- [x] 1.2 Confirm verification passes before the change, so any later failure is attributable to this work — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Client deliverable

- [x] 2.1 Add an unloaded per-position cost alongside the existing loaded one in `generate_project_budget.py`, without changing which positions exist or how their hours and rates are computed — verify by confirming the loaded value still equals the unloaded value times the employer insurance rate for every position
- [x] 2.2 Price the deliverable's `ESS1`, `ESS4` and `ESS16` lines from the unloaded basis — verify by confirming each falls to exactly its loaded value divided by 1.215, and that no other row on the sheet changes
- [x] 2.3 Keep the Savills staff cost line as the loaded residual, covering exactly the positions it covers today — verify by confirming its value is unchanged from the figure recorded in 1.1
- [x] 2.4 Confirm every roster position is still represented exactly once across the four lines — verify by checking that the three unloaded service lines plus the loaded `EMH2` residual account for every position in the staffing demand, with none counted twice and none dropped
- [x] 2.5 Update the remarks on the three service lines to state that the figure is an outsourced vendor cost with no employer insurance contribution, and on the staff line that it does include one — verify by reading the generated remarks in the output workbook

## 3. Analysis workbook

- [x] 3.1 Apply the same unloaded basis to the security, cleaning and landscape figures in `generate_project_output.py`, leaving every other cost category on the loaded basis — verify by confirming only those three categories move
- [x] 3.2 Confirm the two workbooks agree — verify by running both generators from one input and comparing the deliverable's `ESS1`/`ESS4`/`ESS16` values against the analysis workbook's Cost Priority Security/Cleaning/Landscape rows, expecting a match to within the deliverable's monthly-split rounding (at most 11 VND, see design Risks)
- [x] 3.3 Confirm the cost-basis toggle, cost priority classification and every downstream total still reconcile — verify by checking that the analysis workbook's own internal sums are consistent after the change

## 4. Verify the movement is the predicted one

- [x] 4.1 Run verification and confirm it fails naming the expected figures — verify by running `python verification/verify.py`, confirming a non-zero exit, and confirming the named figures are `staff_cost_annual`, `total_profit_value`, `margin` and `markup` and no others
- [x] 4.2 Confirm the size and direction of the movement match design D4's corrected table — verify by checking `staff_cost_annual` fell by 351,952,420 VND to 3,597,812,105, `total_profit_value` rose by the same amount to 5,148,804,513, the three `service_*_annual` control figures did not move at all, and the Cost Priority Staff TOTAL fell by 409,611,550
- [x] 4.3 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean, and that the checking method reported is full recalculation
- [x] 4.4 Confirm production data was untouched throughout — verify by comparing the four production fingerprints against their recorded values

## 5. Re-record the baseline

- [x] 5.1 Review every named difference line by line and confirm each one was intended — verify by producing a short written account of which figures moved and why, before re-recording anything
- [x] 5.2 Re-record the baseline with a reason identifying this change — verify by running `python verification/baseline.py --record --reason "..."` following `verification/README.md`, and confirming the stored reason names this change
- [x] 5.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero

## 6. Documentation

- [x] 6.1 Record in `docs/05-decisions.md` that D3 is implemented, with the measured effect on the figures — verify by confirming the decision's status is no longer "decided, not implemented" and that the recorded figures match what 4.2 measured
- [x] 6.2 Update `docs/project-status.md` with the new state, the re-recorded baseline and the next decided change — verify by confirming it names the correct active change and next action
