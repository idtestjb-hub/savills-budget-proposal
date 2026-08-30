## 1. Synthetic sample project

- [x] 1.1 Create the synthetic project input workbook with the same sheet structure the live input uses (Project Info, Roster Setup, Shift Types, Staffing Demand), using invented but realistic scale figures and an obviously fictional project name — verify by confirming the file contains no real client name and no value copied from the live input
- [x] 1.2 Store it inside `source_code/` alongside the verification entry point, not in `reports/` or `input/` — verify by confirming the path is outside every folder the live workflow reads or writes
- [x] 1.3 Confirm the sample loads through the existing `read_input()` without error and yields a complete project record — verify by calling `read_input()` on it and checking that apartment NFA, unit count and staffing demand rows are all populated

## 2. Production-data isolation

- [x] 2.1 Implement the path-constant override described in design D1, redirecting `INPUT_PATH`, `BUDGET_OUT_DIR`, `ROSTER_FINAL_OUT` and `OUTPUT_PATH` to a temporary directory — verify by printing the four resolved paths during a run and confirming all four point inside the temp directory
- [x] 2.2 Assert all four constants exist before overriding, aborting with a message naming the missing one — verify by temporarily renaming one constant and confirming the harness fails loudly rather than writing to a production path
- [x] 2.3 Record content hashes and modification times of the live input workbook, the analysis workbook and the client deliverable before and after a verification run — verify by confirming all three are byte-identical and unchanged in timestamp afterwards
- [x] 2.4 Confirm verification still completes when no live input workbook is present — verify by temporarily moving the live input aside and re-running

## 3. Structural checks

- [ ] 3.1 Check that each generated workbook contains its expected sheets — verify by asserting the client deliverable has its full sheet set and the analysis workbook has its own, failing with the names of any missing sheet
- [ ] 3.2 Scan every generated workbook for cells resolving to an Excel error value after a full recalculation — verify by confirming a clean run reports zero, and that the failure message names the sheet and cell of the first error found
- [ ] 3.3 Scan generated files for the file-corruption artifacts that trigger an Excel repair prompt — verify by confirming a clean run reports none and that the check names the affected file when artifacts are present
- [ ] 3.4 Implement the degraded-mode reporting from design D5, stating which checking method actually ran — verify by forcing the reduced path and confirming the result explicitly says recalculation-only errors were not detectable in that run

## 4. Numeric baseline

- [ ] 4.1 Extract the headline figures listed in design D4 from the generated workbooks — verify by printing each figure with its name and the unit VND, and confirming every expected figure is present and non-null
- [ ] 4.2 **Manual spot-check**: hand-calculate at least three of the extracted figures from the synthetic project's own inputs (management fee revenue, one service-contract cost, one Capex category) and compare against what the harness read — verify by confirming each matches, which proves the harness is reading the intended cells rather than adjacent ones
- [ ] 4.3 Record the baseline together with the interpreter version used to produce it — verify by confirming the stored baseline contains every figure from 4.1, each labelled with VND, plus the recorded Python version
- [ ] 4.4 Implement baseline comparison with an explicit tolerance — verify by running twice unchanged and confirming a pass, then altering one stored value and confirming the failure names the figure with both its baseline and current value in VND
- [ ] 4.5 Document the deliberate re-baseline procedure requiring a stated reason — verify by following the written steps to update one figure and confirming the reason is recorded alongside it

## 5. Documentation

- [ ] 5.1 Write the real run procedure: the actual entry points, in execution order, including that both generators must run after any input change — verify by following the written steps from a clean state and confirming both outputs are produced
- [ ] 5.2 State explicitly in that procedure what happens if only one generator is run — verify by confirming the text says the two outputs will describe different projects
- [ ] 5.3 Produce the unread-dataset inventory, listing each dataset present in the repository that no runtime code path reads, with the evidence for each — verify by confirming every listed dataset has evidence recorded and that none is connected to the pipeline by this change
- [ ] 5.4 Confirm producing the inventory moved no figure — verify by re-running verification after 5.3 and confirming the baseline still passes unchanged

## 6. End-to-end validation

- [ ] 6.1 Run the complete verification from a clean state and confirm it passes — verify by a single command exiting zero and reporting both structural and numeric passes plus the checking method used
- [ ] 6.2 Confirm a real regression is caught — verify by temporarily altering one input value in the synthetic project, re-running, and confirming verification exits non-zero and names the changed figure
- [ ] 6.3 Confirm a partial run is reported as failure — verify by causing one generator to fail and confirming the result names which generator did not complete
- [ ] 6.4 Re-confirm production isolation after all work is complete — verify by repeating the before/after hash comparison from 2.3 and confirming the live input, analysis workbook and client deliverable are all still untouched
