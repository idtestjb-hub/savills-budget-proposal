## Why

On 2026-10-11 the Head of PM answered the full question list the tool had raised (docs/22). Most answers change
budget figures or deliverable text, and the user then approved an implementation rule for each one, choosing every
recommended option (`PM/Project/docs/30-quy-tac-ap-dung-quyet-dinh-pm-2026-10-11.md`). This change builds them
together, so the standard baselines are re-recorded once instead of once per decision.

## What Changes

Every decision code below (A3, B1–B12, D1–D8, K14) is the code used in docs/22 and docs/30.

**Budget period and dated rates**
- New input: budget start month (default 01/2027). The tool writes the fund sheet's period cells so
  `2. Budget-Management Fund` and `1. Summary` show the same twelve months. Every month-dated rule uses those
  calendar months.
- One dated table holds VAT rates and utility and fuel tariffs, used by both project modes.
- D1: `ESC12`, `ESM25`, `ESS9` and `EEE.C` add VAT by month: 8% to 31/12/2026, then 10%.
- B4: diesel is 29,710 VND/l incl. 8% VAT from 01/10/2026, re-grossed at 10% from 2027. A new water customer-group
  input offers business or administrative. A new prospect defaults to business. An Existing project keeps the
  household top-tier default approved for it on 2026-10-11 (the user's choice).
- A3: household waste uses QĐ 65/2026/QĐ-UBND at 1,087 VND/kg.

**Staff cost, new prospects only**
- B2 and D5: `EMH3` is priced on the form's `A1.1 Allowance` sheet.
  - Holidays at 300% for positions on 7-day coverage with a night shift.
  - Night shift at 30%; night shift on a holiday at 390%.
  - `EMH2` stops counting the allowance a second time.
  - The analysis follows the same per-shift method.
- D4: working days are counted on the calendar, Monday to Saturday minus paid holidays: 302 in 2027. One count is
  used in both workbooks, replacing 25, 26 and 317.
- D6: headcount beyond a group's template rows goes to overflow rows on `A1`, for every group. Nothing is dropped
  silently. Positions the analysis could not categorise are now costed.
- D7: the analysis adds the per-person extras `A1` carries: team building, training 1.3%, health check, accident
  insurance and uniform.

**New priced lines**
- B6: a 2% contingency on `EM#`, `ES#` and `EE#`, on both funds. The base excludes `EMH1` and the collect-on-behalf
  lines. The rate is an input.
- B5: `ESI2` is a USD premium times an editable FX rate, plus 10% VAT. Defaults: 1,000 USD and 26,190 VND/USD.

**Comparables**
- B12: the real-distance tie-break is on again. The ±20% cap on a distance-driven rate swing now covers every product
  and the blended fallback.
- D8: comparable management-fee rates are put on one VAT basis before they are averaged. A new hand-checked table
  records each comparable's basis by product; an unknown basis counts as incl. VAT and is flagged. Conversion uses
  the budget period's VAT rate.

**Deliverable text and sheets**
- D3: the deliverable no longer names other projects. About 20 remark cells and the template's own text on the two
  fill-up sheets are affected, and each source now reads "dự án tham chiếu".
  - The `Comparison` sheet keeps only this project's own figures and a verdict without peer names or rates.
  - The peer comparison moves to the internal analysis, which keeps every name.
- D2: `A2`–`A4` are filled from the tool's post lists and tie to `ESS1`/`ESS4`/`ESS16`.
  - `B1` gets the reception duty calendar.
  - `B2`–`B5` get the tool's own figures where it has them; their sample values are cleared.
  - `A5` is unchanged, because it feeds `EMH4`.
- K14: the `1. Summary` fee narrative ends with the revenue sentence, not the generic cost VAT sentence.
- B10: `BK507`/`BK511` show "N/A" through a live formula when the parking area is 0.
- B7: the `ERCS1` reason says residential quotes are awaited. No figure moves.
- B1: the fixed-fee and %-fee inputs already exist.
  - Remarks cite them by label.
  - The %-basis narrative is corrected.
  - The entered fee is excl. VAT and VAT is added by month.
  - The analysis shows it.

**Existing-project mode**
- The staffing rules (B2, D4, D5) do not apply there.
- The price and tax rules (B4, D1, A3) do apply, from the same dated table.

## Capabilities

### New Capabilities
- `budget-period`: the budget start month input, the twelve calendar months both fund sheets show, and the month every
  dated rule looks up.
- `dated-tax-and-tariff-rates`: one dated source for VAT rates and utility and fuel tariffs, and VAT applied by month to
  the lines priced excl. VAT.
- `new-prospect-staff-cost`: a new prospect's holiday and night allowance (`EMH3`), the calendar working-day count, the
  `A1` overflow rows, and the analysis carrying the same staff-cost components as `A1`.
- `contingency-reserve`: the 2% contingency lines, their base and exclusions, and their counterparts on
  `2.2 Common area Fund` and in the analysis.
- `building-insurance-premium`: `ESI2` priced from a USD premium and an editable FX rate.
- `deliverable-helper-sheets`: what the deliverable's helper sheets `A2`–`A5` and `B1`–`B5` show, and how `A2`–`A4` tie to
  the outsourced service lines.

### Modified Capabilities
- `product-revenue-pricing`: comparable rates are averaged on one VAT basis, and the distance tie-break and its cap
  apply to every product.
- `proposal-benchmark`: the deliverable's `Comparison` sheet shows only this project's figures; the peer comparison
  moves to the internal analysis.
- `deliverable-remarks`: no other project is named on the deliverable; the fee narrative's closing sentence; inputs
  cited by label.
- `waste-collection-costing`: the waste tariff's legal basis becomes QĐ 65/2026/QĐ-UBND, with VAT by month.
- `input-workbook-reading`: the new optional inputs (budget start month, water customer group, contingency rate, ESI2
  premium and FX rate) and their defaults.
- `deliverable-total-integrity`: the parking break-even cells no longer carry `#DIV/0!`.
- `existing-project-staffing`: the new-prospect staffing rules do not apply, and a blank holiday and night-duty table is
  flagged.
- `budget-workflow-verification`: the new fixtures (coordinates, a filled Savills fee, two Accountants) and the single
  baseline re-record.

## Impact

- **Code:**
  - `generate_project_budget.py` (deliverable and roster);
  - `generate_project_output.py` (analysis);
  - `master_comparables.py`, `estimate_opex.py`, `utility_tariffs.py`, `existing_utilities.py`, `existing_staffing.py`;
  - `vn_holidays.py` (working-day count);
  - `build_project_input_form.py` (new fields);
  - `verification/` (checks, method verdicts, fixtures, baselines);
  - unit tests.
- **Data files read:**
  - `Ref_UtilityTariffs.csv`, which gains diesel, the business and administrative water rows and the VAT rates, or a
    dated VAT table beside it (design decides);
  - `Fact_OPEX.csv`, whose water and diesel prices are no longer read;
  - `Dim_Property_Residential.csv` and `Fact_ProjectLocation.csv`;
  - `Costing_Method_Catalogue.csv`, whose entries for `EMH1`, `EEW`, `ESI2`, `EM#` and `ES#` are updated once at
    implementation.
- **Data file added:** a hand-checked comparable VAT-basis table under `Budget_Agent/data/`. It is git-ignored like the
  other reference CSVs.
- **Baselines:** recorded figures move.
  - Standard analysis baseline: staff cost, water, diesel, electricity, management-fee revenue (D8), profit, margin
    and markup.
  - Deliverable baseline: staff, water, electricity, management-fee revenue and surplus.
  - Operating baseline: the same groups, except the entered rates.
  - Each decision is measured on its own, before and after, on the standard sample and on a regression clone outside
    the repository. The baselines are re-recorded once, at the end, with the reason stated.
- **Client deliverable:** figures, remark text and the `Comparison` sheet change. The internal analysis keeps every
  comparable name.
- **Not changed:** the template file, `A5`'s fire-team formula, the collect-on-behalf zero-surplus rule, and Existing
  mode's staffing method.
