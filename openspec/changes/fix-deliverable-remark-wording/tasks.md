## 1. Numbers inside narratives

- [x] 1.1 Before any edit, generate the sample deliverable with `run_workflow` into a temp folder and keep it as the "before" copy. Verify: the file exists and its path is noted in the report.
- [x] 1.2 Make the RM narrative (K14) quote each product's priced unit rate and the RPa narrative (K15) quote the RP1/RP2 unit prices (design decision 1). Verify: on the sample, K14 states the same rate as the RM line remark on `2. Budget-Management Fund`, and K15 states the same prices as RP1/RP2; a manual spot-check against the Diamond Skyline copy gives 15,900 / 110,000 / 1,100,000.
- [x] 1.3 Make the security/cleaning narratives list priced posts that add up to the stated total, with unpriced posts shown separately (K29, K30). Verify: on a sample with a cleaning supervisor, the K30 text sums to its stated count.

## 2. Wording

- [x] 2.1 Show the user the before/after wording table in design.md, with the two open questions, and record the approved text. Verify: the user's answers are written into design.md under Decisions before any wording is changed.
- [x] 2.2 Apply the approved wording (EMH2, `0. Info` G21, `Comparison` A2, K22 and EMA7 count bases, the water source sentence, the three consumption caveats, the document-name and "n=1" replacements). Verify: for each cell in the table, print its text before and after; each caveat still states both facts (single reference project; dated price) where it did before.

## 3. Verification

- [x] 3.1 Replace the column-T keyword check in `verification/checks.py` with the whole-workbook scan and the two lists (design decision 3), reporting cells scanned and exempt. Verify: `python verification/verify.py` prints the new counts and passes on the sample.
- [x] 3.2 Prove the scan can fail. Verify: in a scratch copy of the generator (not the repo file), re-insert "derive_product_rate" into `0. Info` G21, "Python" into a fund-sheet remark, and a changed text into an exempt template cell; the scan fails on each and names the cell.
- [x] 3.3 Update `verification/README.md` and the `deliverable-remarks` references in `RUNNING.md` if any. Verify: both name the new scan.

## 4. Close-out

- [x] 4.1 Compare the "before" and "after" deliverables cell by cell. Verify: zero differences in formulas and numeric values; text differences only in the cells listed in design.md; the comparison output is pasted into the report.
- [x] 4.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`. Verify: PASS on every section; no baseline re-recorded.
- [x] 4.3 Re-read all remarks of the Diamond Skyline copy with the scripts in `docs/23-24-scripts/` and confirm findings B1, B2, B3, B4, B6, B8 of `docs/23` are gone. Verify: the report lists each finding id with its new cell text.
