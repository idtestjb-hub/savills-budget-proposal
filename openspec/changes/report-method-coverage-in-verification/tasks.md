## 1. Record the starting point

- [ ] 1.1 Capture every figure that must NOT move, since this change adds no write site — verify by reading them from `verification/baselines/baseline.json` and recording them before any code is touched
- [ ] 1.2 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Build the reference of what real budgets spend

- [ ] 2.1 Extract each reference budget's cost codes and Year-1 values — verify by confirming the totals reported for each project reconcile against that budget's own section subtotals
- [ ] 2.2 Locate each file's code and value columns by finding known codes rather than assuming a layout — verify by confirming a file whose layout is not recognised fails to load rather than loading the wrong columns
- [ ] 2.3 Separate section roll-ups from line items, and justify every exclusion — verify by confirming each excluded code is recorded with a reason, and that the contingency codes are treated as line items rather than as section markers
- [ ] 2.4 Keep each reference figure's provenance — verify by confirming a reader can trace any row back to the workbook and sheet it came from
- [ ] 2.5 Keep real client figures within the repository's existing handling for real data — verify by confirming the reference table is covered by the same rules as the budgets it derives from, and that the change creates no copy of client data outside them
- [ ] 2.6 Confirm the extractor read nothing under production paths and wrote nothing there — verify by comparing the production fingerprints before and after running it

## 3. Record a method verdict for every code the pipeline writes

- [ ] 3.1 Record, for each cost code the pipeline writes, the method the costing spec states, the method actually used, and a verdict — verify by confirming every write site has an entry and that each entry carries its reasoning rather than a bare verdict
- [ ] 3.2 Derive the list of write sites from the code itself rather than restating it — verify by confirming the check reads the pipeline's own row mappings, so a new write site appears without anyone updating a second list
- [ ] 3.3 Fail the run when a written code has no verdict — verify by temporarily adding a write site with no entry and confirming the run fails and names that code
- [ ] 3.4 Fail the run when a verdict exists for a code no longer written — verify by temporarily removing a write site and confirming the run fails and names it
- [ ] 3.5 Confirm no verdict is inferred at run time — verify by confirming the check reads recorded judgements only, and produces no verdict of its own for an unrecorded code

## 4. Report both measures on every run

- [ ] 4.1 Report which codes a reference budget uses that the pipeline does not fill, and what share of that budget's value they represent — verify by running verification and confirming both the count and the share appear
- [ ] 4.2 Report each reference project separately rather than averaging them — verify by confirming an office property's coverage is not blended with a residential one into a single figure
- [ ] 4.3 Report the share of written cost that matches, partially matches, and does not match the spec's method — verify by confirming the three shares appear and sum to the total written cost
- [ ] 4.4 Name the codes behind a mismatch — verify by confirming a reader can tell which codes make up the mismatching share without reading the source
- [ ] 4.5 Reproduce the measured starting point — verify by confirming the reported fidelity matches the figures recorded in this change's proposal for the current code, and investigating any difference rather than adjusting the expectation

## 5. Stop the summary overstating

- [ ] 5.1 State coverage and method fidelity in the result summary alongside the baseline comparison — verify by reading the final summary of a green run and confirming all three appear
- [ ] 5.2 Confirm the summary does not imply the figures were checked for correctness — verify by reading it as someone who has not used the harness before, and confirming a green run cannot be read as a statement of accuracy

## 6. Confirm nothing moved

- [ ] 6.1 Confirm no tracked figure changed — verify by running `python verification/verify.py` and confirming every figure recorded in 1.1 is unchanged and the baseline was not re-recorded
- [ ] 6.2 Confirm no generator, estimator or template behaviour changed — verify by confirming both generated workbooks are byte-comparable in content to a pre-change run apart from any timestamp
- [ ] 6.3 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
- [ ] 6.4 Confirm production data was untouched throughout — verify by comparing the production fingerprints against their recorded values

## 7. Documentation

- [ ] 7.1 Record what a green run does and does not now assert — verify by confirming `verification/README.md` distinguishes reproducibility, coverage, method fidelity and accuracy, and says which of the four are measured
- [ ] 7.2 Record how to add a verdict when a new cost line is added — verify by confirming a reader who adds a write site knows what the failing run is asking them to do
- [ ] 7.3 Record that a low score does not fail the run, and why no threshold was set — verify by confirming the reasoning and the condition for revisiting it are both written down
- [ ] 7.4 Record the measured starting point so later movement is meaningful — verify by confirming the coverage and fidelity figures for the current code are captured with their date
- [ ] 7.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
