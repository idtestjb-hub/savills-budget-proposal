Sign-off for every measured movement: the user, standing in for the Head of PM (as for docs/22). Measurements run on the
standard sample (`Sample_Project_Input.xlsx`) and on the regression clone in `Savills-local\budget-test\`. Each group's
scripts and logs go under `Savills-local\budget-test\<date>-p17-<group>\`. During the change, `verify.py`'s structural,
tie and remark checks must pass after each group. Baseline mismatches are expected, and each must equal the recorded
A/B movements (design D16).

## 0. Before

- [x] 0.1 Record the "before" outputs: both workbooks for the standard sample and for the clone, plus the
  unit-test count. Verify that the files exist under `...-p17-before\` and that `verify.py` passes on them.
- [x] 0.2 Write a diff script (kept in `Savills-local`) that reads the "before" outputs and the current outputs, and
  reports each baseline figure's change in VND next to the task group expected to explain it. Any change with no group
  is printed as unexplained. Verify that on the unchanged code it reports 0 changes, and that a planted change is
  reported as unexplained.

## 1. Budget period (G1)

- [x] 1.1 Add the budget start month to the input form builder and to label reading, with a default of 01/2027 and
  a loud failure on an invalid value. Verify with unit tests for blank, a valid month and an invalid value.
- [x] 1.2 Add the period helper and make GPB write `2. Budget-Management Fund!AH6/AL6` and `1. Summary!H4/H5` from it.
  Verify that a January 2027 run shows 01/01/2027–31/12/2027 on both sheets (unit test plus a COM read-back).
- [x] 1.3 Route every month-dated lookup through the period: the fill-up curve's month 1, holidays and the roster.
  Verify with a July 2027 start test and a full A/B; figures move only through date-dependent lines, and the movement
  is recorded.

## 2. Dated rates, VAT by month, diesel, water, waste (D1, B4, A3)

- [x] 2.0 Precondition: `carry-forward-common-utilities` has its 7.2 back-test and 7.3 sign-off done and is archived
  (design D9b). Then add a MODIFIED delta on `existing-project-utilities` for the shared VAT rows and the two new water
  groups as choices; the Existing default stays household top tier. Verify with `openspec validate --strict`, which must
  report the change valid with the new delta.
- [x] 2.1 Extend `Ref_UtilityTariffs.csv`: general VAT (8% to 31/12/2026, 10% from 01/01/2027), insurance VAT 10%,
  diesel 29,710 incl. 8% VAT from 01/10/2026, and water base prices for business 21,300 and administrative 13,000.
  Each row cites its basis. Keep a dated backup of the file. Verify with a `utility_tariffs` unit test per row kind.
- [x] 2.2 Replace the electricity and drainage VAT rows with the general rate, and add `vat_rate(month, kind)` and the
  price lookup by line, category and month. Verify that the Existing samples' utility figures are unchanged at equal
  prices, and that new tests cover 2026 and 2027 months.
- [x] 2.3 Price new-prospect water and diesel from the dated file. Add the water customer-group input (default
  business). Keep the usage per m². Choose the water remark's source sentence from the tariff category. Verify with an
  A/B on the standard sample (expected near water 306.0 → 452.6M, diesel 61.0 → 94.1M at 2026 prices) and on the clone.
- [x] 2.4 Offer the business and administrative water groups in Existing mode as choices; the default stays household
  top tier (the user's choice in place of B4-c). Verify with an A/B on both Existing samples: staff and utility lines
  are unchanged at equal prices, and selecting business moves water as expected.
- [x] 2.5 Apply VAT by month to `ESC12`, `ESM25`, `ESS9` and `EEE.C`. Fix their remarks (no "(chưa gồm VAT)") and the
  ESS9 remark check. Verify with an A/B (expected EEE.C year 1 about +183.8M VND on the standard sample) and with the
  remark checks passing.
- [x] 2.6 Change the household-waste price to QĐ 65/2026/QĐ-UBND, 1,087 VND/kg, with its citation in code, remark and
  catalogue. Verify that `ESS9` moves by 1,087 / 1,086.49 and that the remark names QĐ 65/2026.
- [x] 2.7 Make the analysis apply the same prices and monthly VAT to electricity, water and diesel. Verify that the
  analysis electricity equals its monthly excl.-VAT amount × 12 × 1.10 for 2027.
- [x] 2.8 Record group 2's measured movements in `design.md` "Measured", and get the user's sign-off.

## 3. Building insurance (B5)

- [x] 3.1 Add the ESI2 premium (USD) and USD rate inputs (defaults 1,000 and 26,190), price `ESI2` as USD × rate ×
  1.10, and write its remark. Update `_FLAGGED_NO_METHOD`, `METHOD_VERDICTS` and the catalogue. Verify that the
  default run gives 28,809,000 VND/year and that the method-verdict check passes.
- [x] 3.2 Record the A/B on both samples and get the user's sign-off.

## 4. Comparables (B12, then D8)

- [x] 4.1 Turn on `DISTANCE_COMPARISON_ENABLED` and route every product's rate and the blended fallback through the ±20%
  cap. Update the stale comments and `measured-effect.md`. Verify with unit tests for a capped non-Apartment product
  and for no coordinates.
- [x] 4.2 Add an invented fixture with coordinates and make `verify.py` check its distance-ranked result. Verify that
  `verify.py` reaches the path.
- [x] 4.3 Seed `Ref_ComparableVATBasis.csv` from the raw-text evidence and the hand-verified tags, and show the seed to
  the user for confirmation before it is read. Verify that the user has confirmed it.
- [x] 4.4 Convert excl.-VAT comparable rates before averaging, and flag unknown bases on the analysis. Entered rates
  are not converted. Verify with unit tests (mixed basis, unknown basis, entered rate) and an A/B (expected standard
  Apartment rate 17,175 → about 18,893).
- [x] 4.5 Record group 4's movements and get the user's sign-off.

## 5. New-prospect staff cost (D4, B2, D5, D6, D7)

- [x] 5.1 Add the working-day count to `vn_holidays` (302 for 2027 at 6 days; Monday–Friday for 5-day; 6 per person
  for 7-day). Verify with unit tests for 2026, 2027 and Sep 2026–Aug 2027.
- [x] 5.2 Use the count for the new-prospect `A1` gross, `A1.1!E7:E11` and the input form's default daily rates, and
  in the analysis roster (in place of 317). Existing mode is unchanged. Verify that both workbooks use the same count,
  that the Existing staff lines are unchanged, and an A/B.
- [x] 5.3 Fill `A1.1` for new prospects:
  - 24/7 = 7 coverage days and a D or 24H shift;
  - holiday staff = day staff per day;
  - night staff = night staff per day;
  - 390% holiday nights;
  - write `D7`;
  - insert rows for missing codes.

  Set `EMH3` = `S13`, and `EMH2` to exclude `AC90`. Verify with a fixture position test and with `existing_detail_ties`
  now running on the standard sample (and failing on a forced double count).
- [x] 5.4 Make the analysis price night and holiday allowance per shift (no ×1.3 loading). Verify that its annual
  allowance equals the deliverable's `EMH3` over the year.
- [x] 5.5 Generalise the `A1` overflow block to every group, PM included, and flag zero-pay rows. Verify with a fixture
  with 2 Accountants and 2 PMs; `EMH2` includes them and check (d) passes.
- [x] 5.6 Add the analysis's missing categories (Accountant, Cashier, Operations Manager, Technical Secretary) and the A1
  per-person extras before the markup, from `a1_row_cost`'s constants. Remove the stale note and the dead function.
  Verify with unit tests on one in-house and one outsourced position.
- [x] 5.7 Flag a blank holiday and night-duty table in Existing mode (run output and `EMH3` remark). Verify on an
  Existing fixture with an empty table.
- [x] 5.8 Record group 5's movements per decision: D4, B2, D5 (compared with the +214.4M VND the PM saw), D6 and D7. Get
  the user's sign-off.

## 6. Contingency (B6)

- [x] 6.1 Add the contingency rate input (default 2%), and write `EM#`, `ES#` and `EE#` on `2. Budget-Management Fund`
  as live month formulas (`H:S`), using `SUBTOTAL(9, first leaf:row above)` minus the excluded leaves (design D9). The
  base excludes `EMH1`, `EEW.A` and `EEE.A`. A rate of 0 gives 0 with a reason. Verify with a COM read-back that:
  - each month equals 2% of its base, with each leaf counted once;
  - no contingency cell is among its own precedents;
  - a collect-on-behalf pair leaves the surplus unchanged.
- [x] 6.2 Write the same on `2.2 Common area Fund` from its own ranges. Add the contingency to `1. Summary`'s
  reconciliation and narratives, and to the analysis. Verify that the summary ties and the two workbooks agree.
- [x] 6.3 Record the A/B and get the user's sign-off.

## 7. Savills fee cleanup, ERCS, break-even cells, fee narrative (B1, B7, B10, K14)

- [x] 7.1 Make the `EMH1` remarks and the guard message cite the inputs by label. Fix the %-basis narrative. Treat the
  entered fee as excl. VAT and add VAT by month. Show the entered fee on `Savills Fee Position`. Update the method verdict
  and the catalogue. Verify with fixed-fee and %-fee fixtures and a remark test with no cell address.
- [x] 7.2 Reword the `ERCS1` reason (residential quotes awaited). Verify with a remark assertion.
- [x] 7.3 Write `BK507`/`BK511` as guarded live formulas, found by label. Verify with a COM read-back showing "N/A" at
  parking area 0 and a number after typing an area; the inherited error count falls.
- [x] 7.4 End `1. Summary!K14` with the revenue sentence and exempt it from the generic VAT-sentence check. Verify
  that the remark checks pass on the standard and operating samples.

## 8. Helper sheets (D2)

- [x] 8.1 Fill `A2`–`A4` from the tool's post lists and rate, keeping the canonical duties and non-zero allocation
  bases. Verify with new checks that `A2`/`A3`/`A4` annual totals equal `ESS1`/`ESS4`/`ESS16`.
- [x] 8.2 Fill `B1` from the roster's Reception rows. In `B2`–`B5`, write the tool's figures where it has them;
  otherwise clear the sample values and write "chưa áp dụng". Verify with a COM read-back, and that `EMH4` is
  unchanged.

## 9. Client wording and the Comparison sheet (D3)

- [x] 9.1 Give each GPB site that names a source project client wording ("dự án tham chiếu"), without editing the
  shared strings the analysis uses. Overwrite the fill-up sheets' template names with neutral text and add them to the
  form-owner list. Verify that the internal analysis still names the projects.
- [x] 9.2 Split the `Comparison` sheet: the deliverable keeps this project's figures and a verdict without peer
  figures; the peer columns move to the analysis. Update `check_benchmark_reconciles`, `EXPECTED_SHEETS` and the
  `_benchmark_fee_clause` tests. Verify that the benchmark reconciliation passes.
- [x] 9.3 Extend `scan_internal_wording` with the data-built name list and formula text, excluding the project's own
  name. Verify that it passes on every sample and fails on a planted name in a formula.

## 10. Close

- [x] 10.1 Re-record `baseline.json`, `deliverable_baseline.json` and `operating_baseline.json` once, with the reason.
  Verify that every movement equals the sum of the recorded A/Bs.
- [x] 10.2 Run `python verification/verify.py` from `Budget_Agent/source_code/`, and the full unit test suite. Verify
  that `verify.py` passes on all sections and every test passes.
- [x] 10.3 Update `RUNNING.md` (new inputs), `docs/project-status.md` and `docs/05-decisions.md`, and correct the A3
  and B1 records. When archiving, also edit the main spec `waste-collection-costing`'s Purpose, which still says QĐ 67
  (a delta's Purpose is ignored). Verify with `openspec validate --strict`.
- [x] 10.4 Show the user the full before/after table (standard sample and clone) and record their sign-off in
  `design.md`.
