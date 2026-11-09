## 1. Table builder

- [x] 1.1 `build_line_frequency.py`: store read (logic of the office `read_freq.py`: header in C/D/E, budget sheets of
  MF and CA, `review_import.open_workbook` repair), raw read written only to `--workdir`; `--from-votes <csv>` for tests
- [x] 1.2 Votes per the rules (MF only, one vote per file, ties vote nothing, Schedule not counted, >= 5 files,
  > 50 %); CA counted and printed for reference
- [x] 1.3 `COSTING_KEEPS` exceptions (ESC12, ESM2, ESM5, ESM25) with source and note; codes not on the 2027 MF form
  dropped; template column C kept as a note only
- [x] 1.4 Source text in counts only; leak scan of the written CSV against the store's project names (fails on a match)
- [x] 1.5 Tests on a TEST DATA votes file: threshold, tie, Schedule ignored, exception kept, off-form code dropped
- [x] 1.6 Run on the office machine (cwd in ZWork) and write `Ref_LineFrequency.csv`: expect 11 rows (Yearly ESC4,
  ESC5, ESS10, EMB4, ESA16, ESC12; Half a Year ESM3, ERCS1, ESM2; Quarterly ESM5, ESM25); user reviews the table
  (2026-11-09, P28: store read through the builder = 94,198 lines, 0 problems, identical to the P27 raw read; 11 rows
  as expected, leak check clean; written to the measurement overlay; live table written after the sign-off, old one kept as
  `Ref_LineFrequency.csv.backup-2026-11-09-p28`)

## 2. Lines left for the PM

- [x] 2.1 `budget_adjustment.lumped_item` / `add_pm_rows`: a PM line on a Monthly or blank C takes the table's
  non-Monthly default (D3)
- [x] 2.2 `shade_pm_fund_row`: a cyclic PM row keeps H:S in the month format, unshaded; F shaded (D4)
- [x] 2.3 `webapp/adjust.py` `_pm_remark`: a saved PM figure on a non-Monthly line ends the remark with the frequency
  sentence (D6); test
- [x] 2.4 `verification/checks.py`: `pm_line_problems` accepts month headers in H:S of a cyclic PM row;
  `check_pm_lines` checks G = 24,000,000 VND after typing for cyclic and Monthly lines (D5); test

## 3. Measure and sign off

- [x] 3.1 Before/after on the standard sample and the four real projects of the earlier changes: per code, frequency,
  F, month spread, annual (VND) and remark for every line that moves; annual totals of both funds and `1. Summary`
  (expect only per-time rounding); report in `Savills-local\backups\budget-agent\<date>-default-frequency-measure\`
  (2026-11-09: 5 fixtures + 6 M3 runs; annual unchanged, EMB4/ESC5 once in T1, PM lines cyclic at 0, RO2a Monthly;
  expense -8 to +13 VND from contingency rounding; the RO2a fix (design D7) was found while measuring; `summary.md`)
- [x] 3.2 Excel check on one generated sample: no error cell, a cyclic PM line typed on sheet 4 pays once (browser
  check of the web save writing the sentence on a TEST DATA run) (2026-11-09: verify's check_pm_lines types on a
  Monthly and a cyclic line, PASS; web: ZZ Sample Tower run, ESC4 Yearly, 24,000,000 VND saved -> remark ends
  "Hàng năm, 1 lần/năm × 24,000,000 VND/lần, chi vào T1", Excel G = AK = 24,000,000 paid in T1, 0 error cells)
- [x] 3.3 Sign-off by the user on the before/after; then re-record the three baselines once (signed off 2026-11-09,
  P28; baselines re-recorded the same day)

## 4. Close

- [x] 4.1 `python verification/verify.py` from `Budget_Agent/source_code/` passes (gates closed after re-recording) (2026-11-09: PASS; 1482 tests pass)
