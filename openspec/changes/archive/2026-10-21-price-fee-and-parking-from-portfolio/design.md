## Context

See proposal.md for why. The state that shapes the approach:

- **One decision point per rate already exists.** `master_comparables.resolve_product_rates()` decides every
  product's applied management-fee rate once per run; both generators read it (change
  `use-operating-project-actuals`, P5; spec `product-revenue-pricing`). The Apartment branch calls
  `derive_product_rate_capped()` (two nearest comparables with a `Fee_Apartment` value, mean, ±20% swing cap),
  then the blended fallback. An entered rate ranks first. Excl.-VAT comparable rates are multiplied by
  (1 + VAT of the budget period's first month) in `_on_incl_vat()`.
- **The real-budget range machinery exists** (change `use-real-budget-ranges`, on `main` since `3fc3e33`):
  `build_real_budget_ranges.py` → `Ref_RealBudgetValues.csv` (41 projects, 10 codes, value per m² of fee-paying
  NFA, CPI factor) and `real_budget_ranges.py` (`form_range`: leave-one-out by `name_key` or NFA within 0.5%, IQR
  once, 10-project floor, PERCENTILE.INC; `price_line` multiplies the median by the fee-paying NFA × 12 and adds
  VAT by month). `generate_project_budget.real_budget_range_results()` prices seven cost lines from it and the
  analysis has a `Real-Budget Ranges` sheet. The store has an `RM.AP` line on 51 primary sheets (33 with a
  value) and `file_profile.nfa_apartment` for most of them; 24 projects give a rate.
- **Parking prices are two module constants** in `generate_project_output.py` (`PARKING_FEE_CAR_MONTHLY`,
  `PARKING_FEE_MOTO_MONTHLY`), imported by `generate_project_budget.py` for the fund rows, `_UNIT_RATES` (the
  `RPa` narrative), `_HELPER_FIGURES['parking']` (helper sheet B5), `_parking_allocation_weights()` (BM11) and
  the analysis' Additional Revenue sheet. The master list's `CarParkingFee_raw` / `BikeParkingFee_raw` are free
  text (53 and 61 rows with a readable first-vehicle price; the rest blank, 0, "không có", "N/A", "CĐT đã bán ô").
- **Operating inputs** (`operating_inputs.py`) read optional labelled fields on `Project Info`; the recorded
  parking revenue needs `Stable Operation? = Yes` (`require_stable`). The form builder places those fields in
  `add_operating_project_fields()`.
- **Constraints.** `main` is frozen at `14778cb` until after 2026-10-21; this change lives on `lane-b`. The
  baselines are re-recorded once in group 10, so verify runs with the two gates open. Real project names stay in
  `Savills-local`; the values file stays anonymous; the client deliverable names no other project (D3). Chosen by
  the user on 2026-10-20: store median for `RM.AP` with `RM.0A` added, master-list median for parking, two
  optional price fields.

## Goals / Non-Goals

**Goals:**
- Both unit rates are decided once per run, read by both workbooks and by every remark, narrative and helper sheet
  that quotes them, so the existing cross-generator agreement checks keep passing.
- The range rules, statistics and anonymity of `use-real-budget-ranges` are reused, not re-implemented.
- Rollback is a data or label change: without the values file, or with fewer than 10 projects, the tool prices as
  today; a form without the new labels runs as today.

**Non-Goals:**
- No change to the fill-up curves, to `RM.0A`'s mirror logic, to the casual parking lines, to the parking lease
  alternative on the analysis, or to how the two comparables are ranked.
- No segment, grade or district split of either range (the user declined a fee-level selector on 2026-10-20).
- No re-pricing of the other products' comparable rates.

## Decisions

**D1. `RM.AP` joins the values file as a rate code with its own denominator.** `build_real_budget_ranges.py`
reads `RM.AP` and `RM.0A` from the primary sheet and `file_profile.nfa_apartment`; the value is
(ΣRM.AP + ΣRM.0A) ÷ apartment NFA, excl. VAT per month, CPI factor as for the other codes. The file gains a
`basis` column (`fee_nfa` for the ten existing codes, `apartment_nfa` for `RM.AP`); `load_values()` defaults a
missing column to `fee_nfa`, so the file written before this change still loads. Alternative considered: a
separate `Ref_ApartmentFeeRates.csv` — rejected, the leave-one-out, IQR, CPI and anonymity code would be
duplicated and the sheet would need a second reader. The README's per-code count lists `RM.AP` like the others
and states the denominator.

**D2. `RM.0A` is added because the rate is the full fee.** The developer's share is the fee on units not yet
handed over; `RM.AP + RM.0A` per month is the fee at 100% hand-over, which is what the tool's rate × NFA means
before the fill-up curve. Four store files carry it (year-1 budgets); without it their rate reads 15–25% low.
Where a project has no apartment NFA the row is not written (no denominator), and a file whose `RM.0A` covers
several products slightly overstates the apartment rate — accepted and noted in the README (the alternative,
splitting `RM.0A` by product NFA, would invent a split the files do not give).

**D3. The range enters `resolve_product_rates()` as source `range`, between `entered` and `comparable`.**
`real_budget_ranges.price_line('RM.AP', …)` returns a `RangeResult` whose `usable` means "at least 10 projects";
the resolver applies `round(median × (1 + vat_pct/100))` when the deliverable includes VAT (the same conversion
`_on_incl_vat()` does for an excl.-VAT comparable), else the median. `apartment_comparable_rate` keeps the
two-comparable figure so the Comparison sheets and the printout show what the range replaced; `comparables`,
`apartment_rates_on_basis` and the benchmark verdict are unchanged. The result dict gains `apartment_range`
(the `RangeResult`) and `apartment_source` can now be `range`. The analysis' `Management Fee` and `Comparison`
sheets, the deliverable's `Comparison` and `0. Info` note label the source. Alternative: price `RM.AP` in
`real_budget_range_results()` like a cost line — rejected, the rate would then be decided in two places and the
other products' Apartment fallback would not follow it.

**D4. `price_line` learns a rate role.** `RATE_CODES = ('RM.AP',)`: for these the function forms the range, sets
`usable` by the floor, exposes `median`/`p25`/`p75` as the rate (VND per m² of apartment NFA per month, 2027
prices, excl. VAT) and leaves `figure` at 0 with `figure_excl_vat` unused; the caller never multiplies it by the
fee-paying NFA. `real_budget_range_results()` passes the project's name and NFA as today, so the self-exclusion
works for the M3 projects (`self_keys` strips the "(M3 REBUILD)" suffix). `CODE_NAMES` gains `RM.AP`; the
`Real-Budget Ranges` sheet shows role "rate" and the applied incl.-VAT rate in place of the annual amount.

**D5. Parking prices get their own small module, `parking_prices.py`, and one resolver.** It loads
`Dim_Property_Residential.csv` (name, district, the two fee texts), parses each text with one deterministic rule
— the first number in the text that falls in the vehicle's plausible band (car 300,000–5,000,000; motorbike
30,000–400,000 VND), after normalising "1.300.000", "1,300,000", "1300000" and "909090.9" — and classifies the
rest as `blank`, `zero`, `no paid parking` (keywords: không, n/a, free, miễn, chưa, đơn vị khác, CĐT đã bán) or
`unparsed`. `form_range(vehicle, self_name)` reuses `real_budget_ranges.percentile_inc` and the same IQR and
10-project rules. `resolve(project)` returns, per vehicle, `dict(price, source, range)` with source `recorded`,
`entered`, `range` or `default`; it is called once by the deliverable generator, stored on
`project['parking_prices']`, and the analysis generator reads the same dict (the analysis already receives the
project dict). The former constants stay in `generate_project_output.py` as the `default` source. Alternative:
pre-parse the prices into the CSV by `transform_master_list.py` — rejected for now, the master list is rebuilt
rarely and a run-time parse with a status per row is easier to review on the analysis sheet; it can move into the
transform later without changing behaviour.

**D6. Two labelled optional fields, not gated by the stable switch.** `operating_inputs` gains
`PARKING_CAR_PRICE_LABEL` / `PARKING_MOTO_PRICE_LABEL` and `read_parking_prices(L)` (the same `_amount` parsing
as the recorded revenue: blank or 0 → None, text or negative → `OperatingInputError`). They sit in the operating
block of the form for proximity to the recorded revenue fields but are valid for a new building too, so
`require_stable()` does not list them. Order of precedence per vehicle: recorded revenue (stable only) →
entered price → range → default.

**D7. VAT and CPI.** `RM.AP`: the store value is excl. VAT; the applied rate is converted at the first budget
month's VAT when the deliverable is inclusive (KHOÁN: as it is); CPI to 2027 from `Ref_CPI_VN.csv` as for every
code. Parking: the master list quotes list prices including VAT in its 2026 snapshot; they are used as quoted,
with no VAT re-rating and no CPI step (list prices are round-number tariffs set by the Owner, not indexed), and
the remark says "đã gồm VAT". A budget period starting in 2027 therefore carries 2026 list prices; stated in the
remark's wording as "giá niêm yết hiện hành".

**D8. Rounding.** The applied `RM.AP` rate is rounded to the VND (as `derive_product_rate` does). The applied
parking price is the median rounded to the VND; medians of the current data are already round.

**D9. Only the two lines and their consequences move.** The fund rows `RM.AP`, `RP1`, `RP2` take the new rates
through the existing code paths (`rates['products']['Apartment']['rate']`, `_UNIT_RATES`, `_HELPER_FIGURES`,
`_parking_allocation_weights(ws, recorded, moto_full_monthly, car_full_monthly)`), so `RM.0A`, `EMH1` (% fee),
`RI1`, the contingency rows, `RPa`, BM11 and `0. Info` follow without new code. The A/B diff of every fund row
proves nothing else moved.

**D10. Measurement.** Before = `14778cb`. After = the lane-b working tree, measured in two steps (after the fee
tasks, after the parking tasks) so each line's movement is attributable. Runs: the standard sample, the four
fixtures (`Sample_Existing`, `Sample_Existing_Lump`, `Sample_Operating`, `Sample_Villa_Input`) and the four real
projects through a copy of the M3 runner pointed at the lane-b clone
(`Savills-local\budget-test\2026-10-20-laneB-fee-parking\`). The runner already removes the project's row from
the master list (parking leave-one-out) and the values file's self-exclusion works by NFA and name key.

## Risks / Trade-offs

- [A whole-portfolio median ignores the project's segment: City Garden's real rate (23,000 excl. VAT) sits near
  P75, Lumi's (13,733) near P25.] → The remark quotes the band; the benchmark line still compares with the two
  nearest comparables; the PM's entered rate wins. Measured on the four real projects before sign-off; the user
  declined a fee-level selector and may add one later without touching the range.
- [Only 24 projects carry `RM.AP`; after self-exclusion and IQR a small project set could fall below 10.] → The
  floor is enforced and the tool falls back to the two comparables with a remark; the count is checked in task 1.
- [`RM.0A` of a mixed-use year-1 file covers more than apartments.] → Four files, each apartment-dominant; noted
  in the README; the IQR step bounds the effect.
- [The free-text parser misreads a price (a tier, a car price in the motorbike cell, "2 xe đầu: 60,000").] →
  One rule, unit-tested on an invented copy of every pattern seen in the real column; every row and its status is
  on the analysis sheet; the band limits damage; a wrong row is fixed in the master list, not in code.
- [Master-list prices are a 2026 snapshot and some rows may be older.] → Stated in the remark and README; no CPI
  applied rather than a guessed one.
- [Baselines move; verify's closed gates would fail.] → Gates open (`verify_gate_open.py`) as for every change
  since group 6; group 10 re-records once.
- [The analysis and the deliverable disagree on a rate.] → Both read the one resolver result; the existing
  cross-generator check (`derived_apartment_rate`, product revenue) and a new assertion on `RP1`/`RP2` prices
  guard it.

## Migration Plan

1. Rebuild `Ref_RealBudgetValues.csv` with the new build (outer repository, `git add -f`; handed to the
   coordinating session with the lane-b commit, as for part 2 of `use-real-budget-ranges`).
2. Code lands on `lane-b`; merge order after 2026-10-21 is the coordinating session's (docs/32).
3. Rollback: delete the `RM.AP` rows from the values file (or the file) and the tool prices `RM.AP` from the two
   comparables; the parking range needs the master list, which is always present, so rollback there is the
   `default` branch when the master list has fewer than 10 prices, or reverting the module.
4. The live `Project_Budget_Input.xlsx` is not rebuilt (guard); the two fields appear on the next rebuilt form,
   and the current form runs as before.

## Open Questions

- Whether the parking price should later be CPI-adjusted or split by district can be decided from the A/B on the
  four real projects without changing the specs (it would be a rule inside `parking_prices.form_range`).
