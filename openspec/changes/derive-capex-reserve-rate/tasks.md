## 1. Record the starting point

- [ ] 1.1 Capture the figures that must NOT move — every Year-1 and category figure in the recorded baseline, since the reserve applies only to Years 2–4 — verify by reading them from `verification/baselines/baseline.json` and noting the values before any code is touched
- [ ] 1.2 Capture the Years 2–4 Capex figures that SHOULD move, from both position sheets — verify by reading them from a generated analysis workbook and recording them, since the baseline does not track them
- [ ] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Extract the evidence

- [x] 2.1 Write an extractor that reads each real project budget's Year-1 and later-year Capex totals — verify by confirming the figures it reports for the four known projects match those recorded in the change's proposal
- [x] 2.2 Record the later year's length in months alongside each observation, so the short-year ambiguity stays visible — verify by confirming each row carries its period and that the 8-, 9- and 12-month cases are distinguishable
- [x] 2.3 Record each observation's provenance — source file, sheet and the date extracted — verify by confirming a reader can trace any row back to the workbook it came from
- [x] 2.4 Write the reference table alongside the other reference data — verify by confirming it loads cleanly and contains one row per project with a later year
- [x] 2.5 Confirm the extractor did not read or write anything under production paths — verify by comparing the four production fingerprints before and after running it

## 3. Derive the rate

- [x] 3.1 Compute the reserve rate from the reference table at run time, replacing the hardcoded constant — verify by confirming the value used matches the mean of the recorded observations and that no constant remains in the code
- [x] 3.2 State which reading of the short-year observations was used — verify by confirming the output distinguishes the annualised reading from the literal one and names the one applied
- [x] 3.3 Fail loudly if the reference table is missing or unreadable — verify by temporarily renaming it and confirming the run stops rather than substituting a default
- [x] 3.4 Report the sample size and range everywhere the rate appears — verify by confirming every generated note that quotes the rate also carries `n` and the observed range

> **Group 4 not started.** The rate is derived and in use; the drop-to-reserve year is still fixed
> at Year 2 for every project. Green Skyline shows it varies, and the extractor now records which
> observations are full-repeat years, so the evidence for this is in place.

## 4. Make the drop year an input

- [ ] 4.1 Add a drop-to-reserve year field to the intake form — verify by generating a fresh form into a scratch location and confirming the field is present with an explanatory note
- [ ] 4.2 Read it by label and default to the year most reference projects use when it is blank — verify by confirming a blank field yields the evidenced default and that the output says a default was applied
- [ ] 4.3 Confirm a project with a later drop year budgets full Capex until that year — verify by running a temporary input variant with the drop year set to 3 and confirming Year 2 carries full Capex rather than the reserve
- [ ] 4.4 Confirm the new field did not disturb any other field — verify by checking every other input value reads back unchanged, and that the pre-migration fixture still reads correctly

## 5. Confirm the blast radius

- [ ] 5.1 Confirm no Year-1 or category figure moved — verify by running `python verification/verify.py` and confirming the figures recorded in 1.1 are unchanged
- [ ] 5.2 Confirm the Years 2–4 Capex figures moved as intended — verify by comparing them against the values recorded in 1.2 and confirming each changed by the expected proportion
- [ ] 5.3 Confirm every generated note quotes the derived rate, not a stale hardcoded one — verify by reading the notes on both position sheets and confirming no `10%` figure survives that is not the derived value
- [ ] 5.4 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
- [x] 5.5 Confirm production data was untouched throughout — verify by comparing the four production fingerprints against their recorded values

## 6. Re-record the baseline if it moved

- [ ] 6.1 Review every named difference and confirm each was intended — verify by producing a short written account before re-recording anything, and by explaining any Year-1 movement rather than accepting it
- [ ] 6.2 Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change
- [ ] 6.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero

## 7. Documentation

- [ ] 7.1 Record in `docs/05-decisions.md` that D4 is implemented, with the derived rate, the sample size and the observed range — verify by confirming the decision's status is no longer "decided, not implemented"
- [ ] 7.2 Record that the logic spec's stated 0.1% is contradicted by all four real projects, and that correcting the spec is the PM's decision — verify by confirming the contradiction and its owner are both written down
- [ ] 7.3 Record that Capex must be excluded from the fill-up ramp when B5 is implemented, with the evidence — verify by confirming the fill-scenario figures are cited where a future implementer will see them
- [ ] 7.4 Update the run procedure to describe the new drop-year field — verify by confirming `RUNNING.md` explains what it does and what happens when it is left blank
- [ ] 7.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
