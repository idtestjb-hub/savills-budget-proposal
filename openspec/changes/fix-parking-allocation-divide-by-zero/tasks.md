## 1. Record the starting point

- [ ] 1.1 Capture the figures that must NOT move — verify by reading them from `verification/baselines/baseline.json` and recording them before any code is touched
- [ ] 1.2 Capture how many rows would error once the trigger input is present — verify by generating with a temporary non-zero parking area and recording the count and a sample of the error cells, so the fix has something to be measured against
- [ ] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Establish the split before writing it

- [ ] 2.1 Establish whether any reference budget records a monthly-versus-casual parking revenue split — verify by reading them and recording plainly whether a basis exists, since the answer decides what is written
- [ ] 2.2 Use the pipeline's own monthly parking revenue for the monthly half — verify by confirming the value written equals the parking revenue the deliverable already reports, and is not separately re-derived
- [ ] 2.3 Write zero for the casual half if no basis was found, rather than a plausible ratio — verify by confirming no split was chosen that cannot be traced to evidence, and that the choice is stated on the output
- [ ] 2.4 Do not overwrite weights a project already carries — verify by pre-filling the cells with different values, running, and confirming the pipeline leaves them and says it did

## 3. Make a zero denominator impossible to ship

- [ ] 3.1 Fail the run when the allocation denominator would be zero — verify by temporarily clearing the weights and confirming the run stops and names the affected cells
- [ ] 3.2 Confirm no deliverable is produced when that check fails — verify by confirming the output directory holds no client workbook after a failed run
- [ ] 3.3 Confirm the check does not depend on which cost rows were written — verify by running with a cost line added and removed and confirming the check behaves identically both times

## 4. Prove the fix on the state that actually triggers it

- [ ] 4.1 Generate with a temporary non-zero parking area and confirm no error cells appear — verify by full Excel recalculation and comparing against the count recorded in 1.2
- [ ] 4.2 Confirm the allocation columns resolve to numbers — verify by reading a sample of the previously-dormant rows and confirming each holds a value rather than an error
- [ ] 4.3 Confirm the temporary variant touched no real input file — verify by comparing the production fingerprints before and after
- [ ] 4.4 Confirm no cost figure changed as a result of the allocation weights — verify by comparing every cost line against its pre-change value, since the allocation is a view over costs and not a cost

## 5. Restore the deferred Repairs & Maintenance write

- [ ] 5.1 Restore the write site deferred by `write-computed-opex-categories-to-deliverable`, with the remark it already carried — verify by confirming the figure appears and equals the analysis workbook's
- [ ] 5.2 Confirm writing it introduces no error cells — verify by full Excel recalculation, both with and without a parking area present
- [ ] 5.3 Confirm every category the estimator computes now agrees across both workbooks — verify by comparing them category by category and confirming the count with a figure is identical in both
- [ ] 5.4 Confirm the section total and the expense total rose by exactly the restored figure — verify by recalculating and reconciling the difference

## 6. Confirm the blast radius

- [ ] 6.1 Confirm the analysis workbook did not move — verify by comparing it cell by cell against a pre-change run
- [ ] 6.2 Confirm the structural checks pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
- [ ] 6.3 Confirm production data was untouched throughout — verify by comparing the production fingerprints against their recorded values

## 7. Re-record the baseline if it moved

- [ ] 7.1 Review every named difference and confirm each was intended — verify by producing a short written account before re-recording anything
- [ ] 7.2 Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change
- [ ] 7.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero

## 8. Documentation

- [ ] 8.1 Record the template defect precisely enough to act on — verify by confirming `docs/05-decisions.md` names the cells, the formula, the row count and the input that triggers it
- [ ] 8.2 Record that correcting the template is Savills' decision and the pipeline is working around it — verify by confirming the choice and its owner are both written down
- [ ] 8.3 Record what split was written and on what basis, including if it was zero — verify by confirming a reader can tell whether the allocation is evidenced or a stated placeholder
- [ ] 8.4 Record that the cross-workbook OPEX gap is now closed, with the final figure — verify by confirming the decision record no longer describes Repairs & Maintenance as deferred
- [ ] 8.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
