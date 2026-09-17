## 1. Record the starting point

- [x] 1.1 Capture the figures that must NOT move — every figure in the recorded baseline, since both new lines are read from the analysis sheet which already carries them — verify by reading them from `verification/baselines/baseline.json` and noting the values before any code is touched
- [x] 1.2 Capture the deliverable's two target sections at zero, and its Management Fund total — verify by reading the section subtotals from a generated deliverable and recording them, since the baseline does not track them
- [x] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Place the figures without displacing the form's arithmetic

- [x] 2.1 Confirm each target row is a line item and not a subtotal — verify by reading both target rows and both section roll-up rows from a generated deliverable and confirming only the roll-ups carry a subtotal formula
- [x] 2.2 Confirm each target row already carries the form's own row formula and no value — verify by reading it before any write and confirming the annual formula is present and the monthly cell is empty
- [x] 2.3 Write the administrative expense figure to its line item — verify by confirming the value appears there and equals the figure the analysis workbook reports for that category
- [~] 2.4 Write the repairs and maintenance figure to its line item — **DEFERRED**, see design D6. Implemented and measured correct (28,135,740, ER section +28,135,740, TOTAL EXPENSE +85,302,456 exactly), then reverted: the write introduces two #DIV/0! cells from a latent template defect affecting 351 rows. Moved to `fix-parking-allocation-divide-by-zero`.
- [x] 2.5 Fail loudly if either target row is not the expected cost code — verify by temporarily asserting against a wrong code and confirming the run stops rather than writing to whatever row is at that position

## 3. State the basis on each row

- [x] 3.1 State the ratio, the property it came from and its sample size in each remark — verify by reading both generated remarks and confirming each carries the per-m² rate, the source property and `n`
- [x] 3.2 State what the repairs figure excludes — verify by confirming its remark names both maintenance contracts and the clearance work the section otherwise contains, and says the figure covers neither
- [x] 3.3 State that each figure is an undecomposed total for its whole section — verify by confirming each remark says it is not a breakdown across the section's individual line items and why no breakdown exists

## 4. Confirm both workbooks now agree

- [x] 4.1 Confirm every category the estimator computes appears in both workbooks — verify by listing the estimator's categories and confirming each has a figure in the deliverable and in the analysis
- [~] 4.2 Confirm the two workbooks carry the same figure for each — verify by comparing them category by category from a single run and confirming each pair matches. **5/6 match.** Repairs & Maintenance remains 28,135,740 in the analysis and blank in the deliverable, per 2.4.
- [~] 4.3 Confirm no category is reported in one workbook and blank in the other — **one remains**: Repairs & Maintenance, named and tracked in its own change rather than left unexplained.

## 5. Confirm the blast radius

- [x] 5.1 Confirm each section total rose by exactly its new figure — measured under full recalculation: EMA 0 -> 57,166,716 and (in the two-line version) ER 0 -> 28,135,740, TOTAL EXPENSE +85,302,456 exactly. Delivered state: EMA only.
- [x] 5.2 Confirm the form's subtotal formulas survived — verify by reading both roll-up rows after the run and confirming each still holds its original subtotal formula over its original range
- [x] 5.3 Confirm the analysis workbook did not move at all — verify by comparing every figure it reports against its pre-change value, expecting no difference
- [x] 5.4 Confirm the deliverable's Management Fund total rose by the sum of the two figures and by nothing else — verify by reconciling the difference against the two figures
- [x] 5.5 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
- [x] 5.6 Confirm production data was untouched throughout — verify by comparing the production fingerprints against their recorded values

## 6. Re-record the baseline if it moved

- [x] 6.1 Review every named difference and confirm each was intended — verify by producing a short written account before re-recording anything, and by explaining any analysis-side movement rather than accepting it
- [x] 6.2 NOT REQUIRED — no tracked figure moved. The baseline reads both OPEX figures from the ANALYSIS sheet, which this change did not touch; the +57,166,716 is deliverable-side and the baseline watches no deliverable OPEX total. Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change
- [x] 6.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero

## 7. Documentation

- [x] 7.1 Record the cross-workbook gap this closed, with the figure and how it was found — verify by confirming `docs/05-decisions.md` names the amount and the gap analysis that surfaced it
- [x] 7.2 Record that the deliverable's bottom line falls by the amount added, and that this corrects an overstatement rather than adding a cost — verify by confirming a PM reading the decision record would understand why future budgets show lower profit
- [x] 7.3 Record the repairs figure's semantic mismatch with the section it sits in, and that costing the clearance work is separate future work — verify by confirming both the mismatch and its owner are written down
- [x] 7.4 Record the remaining blank cost codes the gap analysis found, so the next change has the evidence — verify by confirming the list, its two source projects and the per-group amounts are captured
- [x] 7.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
