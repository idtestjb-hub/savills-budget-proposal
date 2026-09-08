## 1. Record the starting point

- [x] 1.1 Confirm verification passes before the change, so any later movement is attributable to this work — verify by running `python verification/verify.py` and confirming it exits zero with all figures matching
- [x] 1.2 Preserve the pre-migration fixture as a second test input, with its old row layout intact — verify by confirming it is stored somewhere the tests can reach and that its layout differs from the current fixture in the sections below the product block

## 2. The label resolver

- [x] 2.1 Build a resolver that indexes a sheet's labels and returns the value beside a requested one — verify by asking it for a field on the current fixture and confirming it returns the same value the fixed address returns today
- [x] 2.2 Normalise labels so a parenthetical hint or trailing note does not break the match — verify by confirming a field whose label carries units and a trailing note resolves correctly
- [x] 2.3 Fail loudly when a label is absent, naming the label and the sheet — verify by asking for a label that does not exist and confirming the error names both
- [x] 2.4 Fail when two labels normalise to the same key rather than silently choosing one — verify by constructing that collision and confirming it raises
- [x] 2.5 Treat a present label with an empty value cell as an empty value, not a missing field — verify by confirming the deliberately blank Savills fee cells still read as empty without raising

## 3. Convert Project Info

- [x] 3.1 Read every scalar field on Project Info by label instead of by address — verify by confirming each value matches what the fixed address returned before the change, field by field
- [x] 3.2 Locate the product mix block by its own section header and read each product from the row bearing its name — verify by confirming every product's area matches what positional reading returned, and that no value from outside the block is read as a product
- [x] 3.3 Confirm no value is read from outside the product block — verify by checking the parking rows are not read as product areas, which is the specific failure this change exists to prevent

## 4. Convert Roster Setup

- [x] 4.1 Read the staffing ratios and the schedule month and year by label — verify by confirming each matches what the fixed address returned
- [x] 4.2 Locate the public-holiday rows by their section header rather than a fixed row range — verify by confirming the same holidays are read as before

## 5. Prove it against both layouts

- [x] 5.1 Confirm the current fixture produces figures identical to before the change — verify by running verification and confirming all recorded figures match with no re-record
- [x] 5.2 Confirm the pre-migration fixture reads correctly and produces the same figures — verify by running the workflow against it and comparing every headline figure against the current fixture's, expecting a match
- [x] 5.3 Confirm a deliberately shifted layout still reads correctly — verify by inserting rows above a field in a temporary copy and confirming the figures are unchanged
- [x] 5.4 Confirm a workbook missing an expected label fails rather than producing a budget — verify by removing a label in a temporary copy and confirming the run stops and names it

## 6. Confirm nothing moved

- [x] 6.1 Confirm the baseline is unchanged and was not re-recorded — verify by running `python verification/verify.py`, confirming it exits zero, and confirming the stored baseline's recorded timestamp and reason are the ones from before this change
- [x] 6.2 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
- [x] 6.3 Confirm production data was untouched throughout — verify by comparing the four production fingerprints against their recorded values
- [x] 6.4 Confirm no temporary artefact was left behind — verify by checking both fixtures are byte-identical to their pre-run state and no scratch file remains in the repository

## 7. Documentation

- [x] 7.1 Record in the run procedure that the form's rows may be reordered without breaking the reader, and what happens if a label is renamed — verify by confirming `RUNNING.md` states both
- [x] 7.2 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
