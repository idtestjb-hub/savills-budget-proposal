## 1. Record the starting point

- [ ] 1.1 Capture the three energy figures that must reproduce unchanged — verify by reading them from `verification/baselines/baseline.json` and recording them before any code is touched
- [ ] 1.2 Capture the cost ratio each category currently uses — verify by recording the VND/m²/month figure the estimator derives for each, so the split can be reconciled against it
- [ ] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Recover consumption and tariff from the source

- [ ] 2.1 Read each energy row's consumption and unit price from the real source workbooks rather than from the prose already recorded — verify by confirming each figure recovered matches the one the existing source note quotes, and reporting any that does not
- [ ] 2.2 Read electricity usage from the equipment load model directly where it exists, rather than dividing cost by tariff — verify by comparing the directly-read figure against the divided one and recording both, since a mismatch means the quoted tariff is blended or partial
- [ ] 2.3 Establish whether the water source sheet carries volumes — verify by reading it and recording plainly whether m³ and a unit price are present, since the answer decides whether water can be split at all
- [ ] 2.4 Record the date each unit price was current — verify by confirming every recovered price carries a date traceable to its source, and that no date is inferred
- [ ] 2.5 Confirm the extractor read nothing under production paths and wrote nothing there — verify by comparing the production fingerprints before and after running it

## 3. Store both halves as data

- [ ] 3.1 Add quantity, unit, unit price and price date alongside the existing monthly cost, without changing what any existing column means — verify by confirming every current reader of the table still loads it unchanged
- [ ] 3.2 Name the unit for every quantity — verify by confirming each row states its unit rather than leaving it implied by the category
- [ ] 3.3 Leave a row unsplit rather than filling it with a borrowed or assumed price — verify by confirming any row that could not be split carries no quantity or price at all, and that no value was taken from a different property or building type
- [ ] 3.4 Keep each row's provenance — verify by confirming a reader can still trace any figure, split or not, back to the workbook and sheet it came from

## 4. Compute each energy line as consumption × tariff

- [ ] 4.1 Derive a usage-per-area ratio from the source property and apply the tariff separately — verify by confirming the calculation multiplies a usage ratio, the project's area and a tariff, and no longer multiplies a cost ratio
- [ ] 4.2 Confirm each figure reproduces its recorded value to within rounding — verify by comparing against the values recorded in 1.1 and confirming the difference is rounding only
- [ ] 4.3 Investigate and write down any figure that does not reproduce, rather than accepting it — verify by producing a written account of the discrepancy naming which half disagrees with the flattened cost, and stopping rather than re-recording the baseline
- [ ] 4.4 Fall back to the existing cost basis for any category that could not be split, and label it — verify by confirming the output names the category, says it is not yet split, and says why
- [ ] 4.5 Confirm a tariff change moves the figure — verify by temporarily changing one tariff and confirming the generated figure changes in proportion, then restoring it

## 5. Report both halves everywhere the figure appears

- [ ] 5.1 State the usage assumed, the tariff applied, and the sample size behind each — verify by reading the generated notes in both workbooks and confirming all three are present for every split category
- [ ] 5.2 State the date each tariff was current — verify by confirming every note quoting a tariff also quotes its date
- [ ] 5.3 Make a tariff older than the budget year visible on the output — verify by generating with a deliberately stale date and confirming a reader of the workbook can see it is stale
- [ ] 5.4 State that the usage ratio remains single-property — verify by confirming no note lets "computed by the spec's method" be read as "now accurate", and that each names its source property and `n`

## 6. Confirm the blast radius

- [ ] 6.1 Confirm only the three energy categories changed how they are derived — verify by confirming every other category's figure is untouched
- [ ] 6.2 Confirm both workbooks still carry the same figure for each energy category — verify by comparing them from a single run
- [ ] 6.3 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
- [ ] 6.4 Confirm production data was untouched throughout — verify by comparing the production fingerprints against their recorded values

## 7. Re-record the baseline only if a movement was explained

- [ ] 7.1 Review every named difference and confirm each was intended — verify by producing a written account before re-recording anything; an unexplained energy movement blocks this step rather than passing through it
- [ ] 7.2 Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change and the movement's cause
- [ ] 7.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero

## 8. Documentation

- [ ] 8.1 Record that the three energy codes now use the method the spec states, with the measured share of cost this represents — verify by confirming `docs/05-decisions.md` names the codes, the method and the 31.0% figure it corrects
- [ ] 8.2 Record which categories were split and which were not, and why — verify by confirming any unsplit category names the missing input and what would recover it
- [ ] 8.3 Record that usage remains single-property and that this change did not widen it — verify by confirming the decision record separates the price fix from the accuracy problem rather than implying both were solved
- [ ] 8.4 Record that updating tariffs to current published rates is the next decision and that it will move client-facing figures — verify by confirming the decision, its owner and its consequence are written down
- [ ] 8.5 Record whether the "water ~3.3× high" error is now attributable to usage or to price, or that it remains unattributed — verify by confirming the finding is written down either way
- [ ] 8.6 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
