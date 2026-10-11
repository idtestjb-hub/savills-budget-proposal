## 1. Utility tariff table

- [x] 1.1 Create `data/generation_B_verified/Ref_UtilityTariffs.csv` with the columns of design D2. Rows:
  - electricity administrative/public-service, below 6 kV and 6 kV and above (QĐ 1279/QĐ-BCT from 2025-05-10, plus
    the previous decision's rows for months before it);
  - HCMC household top tier 14,400 VND/m³ (QĐ 25/2019/QĐ-UBND);
  - drainage and wastewater charge 25% for 2024 and 30% from 2025 (QĐ 17/2021/QĐ-UBND);
  - VAT by period: electricity and drainage service 8% to 2026-12-31 and 10% from 2027-01-01; clean water 5%.

  Each row carries its legal basis and the date it was checked. Verify: a unit test loads the file, and fails on a row
  without a legal basis or effective date.
- [x] 1.2 Look for the primary text behind two rows: the drainage and wastewater charge for 2026 onwards (UBND HCMC or
  SAWACO), and the electricity rate in force before 2025-05-10. Record what was found in the row's `Note` and in
  `docs/05-decisions.md`. Verify: each row cites a primary document, or its `Note` states that only a secondary source
  was found.
- [x] 1.3 Write `utility_tariffs.py`. It returns the unit price of a month for a line, category and VAT basis (design
  D3), and fails with a clear message for a month before the earliest row or for a category with no base price.
  Verify: unit tests for electricity both bases, water both bases, a VAT change on 2027-01-01, a mid-year base change,
  and the business category without a bill price.

## 2. Input form

- [x] 2.1 Add the "Prior-Year Utilities" sheet to `build_project_input_form.py`: blocks `UTILITY ACTUALS` and
  `UTILITY LINES` with the dropdowns of design D1, and the reason-code side column. Verify: a freshly built form, with
  output redirected to a temp folder, shows the sheet, the labels and the dropdowns; the guard that refuses to
  overwrite a filled form still passes.
- [x] 2.2 Extend `add_existing_project_sheets.py` to add the sheet to the dated copy when it is missing. Verify: run on
  a copy of a filled form; the original's bytes are unchanged and the copy opens in Excel without a repair prompt.
- [x] 2.3 Read the sheet by label in `existing_utilities.py` and apply every stop of design D8. Verify: unit tests
  cover:
  - an old workbook (New prospect unchanged; Existing stops naming the sheet);
  - a renamed label;
  - a duplicate month;
  - a negative amount;
  - a month in the budget year;
  - an unknown line, category or reason code;
  - water outside Ho Chi Minh City, or with a blank province, and no bill price;
  - business electricity without a bill price.

## 3. Baseline and budget-year figures

- [x] 3.1 Implement the window, the treatment of blank and zero months, consumption from the bill or derived from the
  amount, and the implied-rate flag (spec requirements 2 to 5, design D3). Verify: unit tests with invented figures
  cover:
  - 12 months over two years;
  - older months ignored;
  - 11 months with one blank;
  - a zero month;
  - amount-only derivation (48,081,600 VND incl. 8% VAT → 20,000 kWh);
  - a bill rate above 1% off.
- [x] 3.2 Implement the fallback for fewer than 12 months: 3 to 11 months, versus fewer than 3 with or without an
  approved amount (design D4). Verify: unit tests for 8 months, for 2 months with an approved amount (repriced only
  for tariff and VAT), and for 2 months without one (stop).
- [x] 3.3 Implement the budget-year monthly amounts, the VAT switch handling and the bridge decomposition (design D4).
  Verify: unit tests show that `B` + tariff effect + VAT effect + override effect equals the sum of the twelve
  months within 1 VND, for KHOÁN and for THU HỘ CHI HỘ, for both lines, with and without an override.
- [x] 3.4 Implement the reason list, the override rule and the tool-written reasons (design D7). Verify: unit tests
  for each code, for "Khác" without a note, and for an override without a code (stop).

## 4. Deliverable

- [x] 4.1 In Existing-project mode, write `EEE.C` and `EEW.C` on `2. Budget-Management Fund` from the compute result:
  twelve monthly amounts, no curve, no floor (design D5). New-prospect mode is untouched. Verify:
  - an invented Existing run shows equal months and the annual total equals the compute result;
  - the standard sample A/B before and after shows 0 cell differences in both workbooks.
- [x] 4.2 Write the remark: the guideline remark without the curve and floor sentences, then "Điều chỉnh so với NS
  <năm>: …", then the VAT sentence. Make sure the `1. Summary` narrative for `EEE`/`EEW` carries no curve wording in
  this mode. Verify: the remark-content check and the internal-wording scan pass on the Existing sample, and the
  sentence names the months used, the unit price and its basis, the VAT rate and any flag.

## 5. Analysis workbook

- [x] 5.1 Add the `Utility Bridge` sheet (design D6) in Existing-project mode only. In that mode, show the Existing
  figures for Electricity and Water on the OPEX sheet, pointing to the bridge. Verify:
  - the bridge's budget-year figures equal `EEE.C` and `EEW.C` on the deliverable;
  - the deliverable has no bridge sheet;
  - a New-prospect run has none either.
- [x] 5.2 `run.py` prints the utility flags and stops on the D8 cases after an Existing-project run. Verify: run on
  the invented fixtures and confirm the printed flags; a fixture with an override but no reason makes `run.py` fail.

## 6. Verification

- [x] 6.1 Add utility data to both invented section-8 samples in `verification/fixtures/build_existing_fixture.py`
  (design D9), and add a utility-bridge tie check to `verification/checks.py`. Verify: the check fails on a
  deliberately broken deliverable (`EEW.C` typed 1,000 VND off) and passes on the good one; the fixtures contain no
  real name or figure.
- [x] 6.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`, with no other run in progress.
  Verify: all sections pass, and the recorded baselines need no re-record.

## 7. Measurement and sign-off

- [x] 7.1 Regression: run the standard sample in New-prospect mode before and after the change. Verify: zero formula
  or number differences, recorded in `docs/project-status.md`.
- [ ] 7.2 Back-test on the project X clone in `Savills-local`:
  - fill in its utility actuals from the real file's monthly actual columns;
  - compare `EEE.C` and `EEW.C` for 2027 with the real 2027 file;
  - report both figures, the bridge and the gap, explaining it by cause (for example, the real file kept the 2026
    approved electricity amount).

  Verify: every changed line has a reason; the results stay in `Savills-local` and are summarised without real names
  in `docs/05-decisions.md`.
- [ ] 7.3 Sign-off: the Head of PM approves the six utility reason codes, the default tariff categories and the 7.2
  result before the change is archived, after `carry-forward-staffing` is archived. Verify: the approval is recorded
  in `docs/05-decisions.md` with the date. *(2026-10-11: the six reason codes and the default tariff categories are
  approved, as reported by the user after the PM meeting (`docs/05-decisions.md`). Still open: the 7.2 result,
  because the back-test has not run.)*
