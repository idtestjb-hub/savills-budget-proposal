## Context

Today (source_code `27e2ea3`):

- `estimate_opex.py` prices a new prospect's electricity, water and diesel as usage per m² × NFA × price. The usage per
  m² is the utilities base project's (registry role `utilities_base`, `R02`) stored monthly quantity ÷ its NFA (n=1).
  Water and diesel are priced month by month from `Ref_UtilityTariffs.csv` (`utility_tariffs`); electricity still uses
  the `UnitPrice` of the base's `Fact_OPEX.csv` row, although the tariff file already holds dated EVN rows and
  `utility_tariffs.LineTariff` already prices electricity for Existing mode.
- `estimate_capex_qty.estimate_capex_items()` takes the registry row with role `capex_items` (R01..R07) whose
  `CapexNFA_m2` is nearest the prospect's NFA and scales its `Fact_Capex_Rescanned.csv` items. Study 1 ratios
  (`STUDY1_RATIO_PER_1000_NFA`) are constants derived once from the same seven.
- The store scan of 2026-11-06 (`Savills-local\budget-agent\2026-11-06-p22-capex-scan`) found usage candidate rows
  (tier A heuristic) in 33 files, 24 of them among the 55 mapped projects, and priced capex item sheets in 4 mapped
  projects beyond the eight (store ids `254fb1cef1c3`, `67b7d566b159`, `86160f50e3b4`, `962c7429ec69`).
- User decisions 2026-11-06: market prices; median over many projects; hand-check every candidate; capex 7 → 11; only the
  55 mapped projects.

## Goals / Non-Goals

**Goals:**
- Usage per m² for the three energy lines from a hand-checked, many-project table, with a stated count.
- Electricity priced from the dated EVN tariff like water and diesel.
- Capex item lists from 11 projects; Study 1 ratios from data, recomputed on the same 11.
- Every moved figure explained in a before/after the user signs off before baselines are re-recorded.

**Non-Goals:**
- Existing mode (actual averages, approved amounts repriced): unchanged.
- Searching store files for usage the scan did not flag; reading files outside the 55.
- Escalating old capex unit prices to the budget year (the seven are not escalated today; same rule for the four).
- Changing the 12-category Capex sheet catalogue (`Fact_MasterRateCard.csv`).
- Pool salt and repairs ratios (still from the utilities base).

## Decisions

1. **Usage table `Ref_UtilityUsage.csv`** in `Budget_Agent/data/generation_B_verified/` (outer, gitignored). Columns:
   `file_id, project_id, utility, quantity_month, unit, period_basis, conversion, nfa_m2, nfa_source, source_sheet,
   source_cell, check, reason, checked_by, checked_on`. One accepted row per project and utility; other candidates
   stay as `rejected` with a reason. Built by an office-only script from a checked worksheet; never written at run time.
   *Alternative considered:* compute usage live from the store each run — rejected: the heuristic picks wrong rows and
   the store is not in a site package.
2. **NFA basis:** the fee NFA of `real_budget_ranges_map.csv` (`nfa_fee_m2`) unless the source states the area the
   usage covers; `nfa_source` records which. The prospect side uses its TotalNFA as today.
3. **Period:** monthly. An annual figure ÷ 12; a budget that lists 12 months takes their mean; a pre-opening or partial
   year is rejected (reason recorded), because fill-up skews usage.
4. **Statistic:** median after removing values outside [Q1 − 1.5·IQR, Q3 + 1.5·IQR], quartiles by linear interpolation
   (`statistics.quantiles(..., method='inclusive')`). Minimum five projects after removal; below that the utility falls
   back to the utilities base (n=1) with a remark. The thresholds are module constants, named in the remark text.
5. **Electricity price:** `utility_tariffs.LineTariff(ELECTRICITY, category=CAT_E_LT6, region=...)`, month by month,
   the rate before VAT (each month's VAT is added downstream, as for the existing electricity line), from the same
   tariff rows Existing mode uses. Category below 6 kV administrative (common areas, Thông tư 60/2025/TT-BCT Điều
   8.2.b, already cited in the tariff file); the input form has no electricity-category cell, so there is no override.
6. **Capex registry rows `R09`..`R12`**: display name from the store, `StoreFileId`, `StoreProjectId`, `CapexNFA_m2`
   (fee NFA of the map unless the budget states a grand total), role `capex_items`, `ExcludedFromRanking=1`, blank fee
   rate/units. Items extracted by a new office-only `rescan_capex_store_projects.py` that reuses the Unit-Price
   column detector of `rescan_capex_from_source.py` (the scan confirmed all four layouts keep qty > price > total
   adjacent), writing `RefKey`; `rescan_capex_from_source.py` now keeps the rows of keys it does not scan. Repeated block sheets (one file has
   "3. Chi phí Trang thiết bị MO" and "3. Capex MO B13") keep the copy the hand check names; the other is logged.
7. **Study 1 ratios** move from constants to a computation over the admitted items (median per category per 1,000 m²
   CapexNFA, with n), cached per process. A row whose capex NFA, district and city repeat an earlier row (R07, the
   second budget-phase file of R06's building) is skipped, which reproduces the old constants exactly on the seven.
8. **Borrowed category** (user decision 2026-11-06, after the measurement showed the standard sample losing its
   amenity line when R10 became its source): a category the source project does not list is taken from the nearest
   project that lists it, scaled by that project's own NFA ratio (`source_info['borrowed']`), following the project
   rule for lumped rows. A few amenity items already inside R10/R12's public-area sheet may then appear twice; accepted.
9. **Site package:** `Ref_UtilityUsage.csv` joins `site_data.KEEP` with `file_id`/`project_id` kept and source sheet
   names masked; registry names R09..R12 are pseudonymised like R01..R08.

## Risks / Trade-offs

- [Hand check of 24 files is long and judgement-based] → one worksheet with the source cell for every candidate, the
  user spot-checks a sample before the table is built; reasons recorded for every rejection.
- [Usage in budgets is often a planned figure, not metered] → accepted as the best available; `period_basis` says
  "budget" vs "actual", and the analysis lists the projects so a PM can judge.
- [Fewer than five projects for diesel is likely (10 mapped projects flagged, many may be rejected)] → fallback to n=1
  is explicit on the remark.
- [Capex unit prices from 2024–2027 budgets mixed without escalation] → same as today; the source year is shown on the
  analysis; escalation is a separate decision.
- [Figures move on every new-prospect budget and Review] → before/after on the five fixtures, the City Garden Review
  and the four M3 projects, signed off before baselines are re-recorded once.

## Migration Plan

1. Archive `reference-projects-by-key` first (its registry spec must be in `openspec/specs/`).
2. Build the checked usage worksheet → `Ref_UtilityUsage.csv`; extract the four capex lists; add R09..R12 (backups
   beside each data file).
3. Code changes; measure before/after against `27e2ea3`; user sign-off; re-record baselines; verify.py PASS.
4. Commit; release note; rebuild the City Garden package at the same commit; [Hub] deploys.
Rollback: restore the data backups and check out the previous commit.

## Open Questions

- Minimum five projects and the 1.5 × IQR fence: proposed defaults, the user may change them.
- Should a project's planned-budget usage and its reported actual (when a file has both) both be candidates? Proposed:
  prefer the actual, keep one row per project.
- The common-area electricity category: below 6 kV by default; is any mapped project known to connect at 6 kV or above?
