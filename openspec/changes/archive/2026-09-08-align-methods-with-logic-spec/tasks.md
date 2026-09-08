## 1. Establish the gap

- [x] 1.1 Identify every filled cost code whose computed method differs from the one its costing spec states — verify by listing each code with both methods side by side
- [x] 1.2 Determine which stated methods are implementable from existing data — verify by checking the reference data for each rate basis the spec calls for, and recording which are absent
- [x] 1.3 Measure the disagreement between the two workbooks on the affected lines before any change — verify by generating both from one input and recording the gap

## 2. Align the service contracts

- [x] 2.1 Price the security, cleaning and landscape lines in the client deliverable as a contract over the budget period rather than from roster headcount — verify by confirming each figure equals posts times the citywide post rate, blended for the project's own night-shift split
- [x] 2.2 Apply the identical basis in the analysis workbook so both cost them the same — verify by comparing the three figures across the two workbooks from a single run and confirming they match
- [x] 2.3 Fold the supervisory variant into its parent contract rather than carrying it as a separate cost — verify by confirming it no longer appears as its own cost-priority row and that the total is unchanged by its removal
- [x] 2.4 State the method and its inputs in each line's remark, including why the spec's primary branch was not used where it could not be — verify by reading the generated remarks

## 3. Confirm the blast radius

- [x] 3.1 Confirm Savills' own staff cost is unchanged — verify by comparing the deliverable's staff line against its pre-change value
- [x] 3.2 Confirm only the intended figures moved — verify by running verification and confirming it names exactly the four expected figures and no others
- [x] 3.3 Confirm the movement matches the arithmetic — verify by reconciling the change in staff cost against the per-category differences, and confirming profit rose by exactly what cost fell
- [x] 3.4 Confirm the cross-workbook gap is closed — verify by confirming the three lines now agree between the deliverable and the analysis
- [x] 3.5 Confirm the structural checks still pass and production data was untouched — verify by running the full verification and comparing the production fingerprints

## 4. Re-record the baseline

- [x] 4.1 Review every named difference before re-recording — verify by producing a written account explaining each
- [x] 4.2 Re-record with a reason identifying this change — verify by confirming the stored reason names it
- [x] 4.3 Confirm verification passes afterwards — verify by running it and confirming a zero exit

## 5. Record what remains misaligned

- [x] 5.1 Record that pool chemicals still uses a flat figure where the spec gives a volume-based formula, and what input is missing — verify by confirming the gap, the formula and the missing input are all written down
- [x] 5.2 Record the Savills-fee branches the spec defines that the code does not implement — verify by confirming each missing branch is named
- [x] 5.3 Record the trade-off this change accepts: citywide rates at n=1 in exchange for method fidelity — verify by confirming it is stated where a reader of the decision record will see it
- [x] 5.4 Update the run procedure and status documents — verify by confirming they describe the current method and the next action

## 6. Cost pool chemicals by the spec's method

- [x] 6.1 Capture the input the spec's method needs but the intake form does not collect — verify by confirming the missing quantity is named and that no existing field can substitute for it
- [x] 6.2 Add that input to the intake form with an explanatory note — verify by generating a fresh form into a scratch location and confirming the field carries the spec's own worked example and says what happens when it is left blank
- [x] 6.3 Read the new field by label and treat its absence as absence, not as zero — verify by confirming a workbook created before the field existed still reads, and that a blank or non-numeric entry selects the fallback rather than costing a pool of no volume
- [x] 6.4 Compute the line from that input in one place both generators use — verify by confirming the figure is identical in the deliverable and the analysis, and that neither recomputes it
- [x] 6.5 Report the method's own uncertainty on the output — verify by confirming every generated note carries the spec's stated range alongside the figure, and names what the figure excludes
- [x] 6.6 State on the output when the fallback was used and what it does not do — verify by confirming the fallback note says it does not vary with pool size and names the field that would change that
- [x] 6.7 Confirm only the intended figure moved — verify by running verification and confirming it names exactly the pool-chemicals figure, and by explaining why the OPEX total and profit did not follow it
- [x] 6.8 Re-record the baseline with a reason naming this method change and the regenerated fixture — verify by confirming the stored reason names both, and that verification passes on the following run

## 7. Restore the hand-checks' independence

- [x] 7.1 Establish whether the verification hand-checks still read the fixture's real inputs — verify by reading each input the checks depend on and comparing against the fixture's actual contents
- [x] 7.2 Read the fixture by label rather than by cell address — verify by confirming every fixture, current and pre-migration, yields identical inputs
- [x] 7.3 Make a check that cannot reach its input fail rather than degrade — verify by feeding the checks the values the address-based reader produced and confirming the affected checks report failure where they previously reported success
