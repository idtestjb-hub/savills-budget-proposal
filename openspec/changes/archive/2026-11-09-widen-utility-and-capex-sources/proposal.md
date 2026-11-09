## Why

A new prospect's electricity, water and diesel cost still comes from one reference budget: its usage per m² is the
utilities base project's alone (n=1), and its electricity price is the price inside that budget. Its capex item list
comes from the nearest of only seven reference budgets. The real-budget store of 55 mapped projects now holds usage
rows in 24 of them and capex item lists in 4 more (store scan 2026-11-06), so the tool can rest on many projects
instead of one. The user decided the rules on 2026-11-06 (outer `docs/05-decisions.md`, "Utility and capex sources:
four rules for the next change").

## What Changes

- **Electricity priced at the market tariff.** A new prospect's electricity is priced month by month from the dated EVN
  tariff in `Ref_UtilityTariffs.csv` (default category: administrative, below 6 kV, the common-area rate), the way
  water and diesel already are. `Fact_OPEX.csv`'s electricity price is no longer read.
- **Usage per m² is a median over many projects.** A new data file, `Ref_UtilityUsage.csv`, holds one hand-checked row
  per project and utility (monthly quantity, the NFA it covers, the source sheet and cell, the check result). The tool
  takes the median usage per m² per month of the accepted rows after removing outliers (1.5 × IQR), with at least five
  projects; below five it falls back to the utilities base project and says so on the remark.
- **Every usage row is checked by hand before use.** The 24 store files of the 55 mapped projects that the scan flagged
  (tier A) are read row by row; each candidate is accepted or rejected with a reason. Rows the scan did not flag are not
  searched for.
- **Capex item lists widen from 7 to 11 projects.** Four store projects with priced item lists join the registry as
  `R09`..`R12` with the `capex_items` role; their items are extracted into `Fact_Capex_Rescanned.csv` with their key.
  Nearest-by-NFA selection and NFA scaling are unchanged; the candidate pool grows. Study 1's per-1,000 m² category
  ratios are recomputed from the same 11.
- **Only the 55 mapped projects are used.** Store files outside `real_budget_ranges_map.csv` are not read.
- **Figures move** for new-prospect electricity, water, diesel, the capex lines, total expense and surplus, and for the
  same lines in a Budget Review. The baselines are re-recorded once, after the user signs off the before/after.
- Site packages: the new data file joins the files a Review reads, and the four new registry names are pseudonymised
  like the other eight.

## Capabilities

### New Capabilities
- `utility-usage-benchmark`: the hand-checked usage table, the median-with-outlier-removal rule, the minimum count and
  the fallback, and how the remark discloses the basis.
- `capex-item-sources`: which projects supply capex item lists (the 11), how a new one is admitted (store project of
  the 55, priced item rows, checked NFA), and how the nearest one is chosen and scaled.

### Modified Capabilities
- `dated-tax-and-tariff-rates`: new-prospect electricity is priced from the dated tariff (today only water and diesel
  are); "a new prospect's usage is unchanged by a price change" now covers electricity too.
- `reference-project-registry` (introduced by change `reference-projects-by-key`, to be archived first): the registry
  grows to twelve rows; the utilities base becomes the fallback for usage, not the source.

## Impact

- Code: `estimate_opex.py` (usage from the benchmark, electricity from `utility_tariffs.LineTariff`),
  `estimate_capex_qty.py` (Study 1 ratios from data, 11 candidates), `reference_projects.py` (no change expected beyond
  more rows), `generate_project_output.py` / `generate_project_budget.py` remarks, `site_data.py` (`KEEP`, pseudonyms),
  new office-only scripts to extract the four capex lists and to build `Ref_UtilityUsage.csv` from the checked rows.
- Data (outer repo, SharePoint, gitignored): `Dim_ReferenceProject.csv` (+4 rows), `Fact_Capex_Rescanned.csv`
  (+4 projects), new `Ref_UtilityUsage.csv`; backups beside each changed file.
- Verification: baselines re-recorded once; before/after on the five fixtures, the City Garden Review and the four real
  projects of the M3 runner.
- Depends on: change `reference-projects-by-key` archived (its registry spec synced) before this one is applied.
- Deploy: budget-web release after commit; the City Garden site package is rebuilt at the same commit.
