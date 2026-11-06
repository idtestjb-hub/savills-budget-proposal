## 1. Prerequisites

- [ ] 1.1 Archive change `reference-projects-by-key` (sync `reference-project-registry`, MODIFIED `budget-site-package`)
- [ ] 1.2 Record the "before" tree (`27e2ea3`) in `C:\ZWork` for the measurement; back up `Dim_ReferenceProject.csv` and `Fact_Capex_Rescanned.csv` (`.backup-<date>` beside each)

## 2. Usage table (hand check)

- [ ] 2.1 Office-only script: export every tier-A usage candidate of the 24 mapped files to a checking worksheet (file id, project id, utility, sheet, cell, label, value, unit, nearby period labels, fee NFA)
- [ ] 2.2 Check every candidate against its source cell: accept one row per project and utility or reject with a reason; note period basis, conversion and NFA source
- [ ] 2.3 User spot-checks a sample of accepted and rejected rows; fix what they flag
- [ ] 2.4 Office-only script builds `Ref_UtilityUsage.csv` from the checked worksheet; report per utility: accepted n, rejected n, values, outliers

## 3. Usage benchmark in code

- [ ] 3.1 Benchmark module: load the table, accepted rows only, median after the 1.5 × IQR fence, minimum five, fallback flag
- [ ] 3.2 `estimate_opex.py`: energy usage per m² from the benchmark; fallback to the utilities base with its reason
- [ ] 3.3 Electricity priced month by month from `utility_tariffs.LineTariff` (category default below 6 kV administrative); `Fact_OPEX.csv` electricity price no longer read
- [ ] 3.4 Remarks (Vietnamese) and the internal analysis: usage per m², n, price and month, the list of projects in the median
- [ ] 3.5 Tests: median and fence (spec example 2.55), fallback below five, rejected rows ignored, electricity month change on the 1st, price-ratio scenario

## 4. Capex item sources

- [ ] 4.1 Extend `rescan_capex_from_source.py` to the four store files; resolve repeated block sheets by the hand check; write `RefKey` R09..R12
- [ ] 4.2 Add R09..R12 to the registry (`build_reference_registry.py`): store ids, capex NFA, role `capex_items`, excluded from ranking
- [ ] 4.3 `estimate_capex_qty.py`: Study 1 ratios computed from the admitted items with n; item selection over the 11
- [ ] 4.4 Tests: nearest-by-NFA over 11, store row not ranked as comparable, ratio n shown, no name in runtime code

## 5. Site package

- [ ] 5.1 `site_data.KEEP` gains `Ref_UtilityUsage.csv` (sheet names masked); R09..R12 pseudonymised; `tests/test_site_data.py` updated
- [ ] 5.2 Rebuild the City Garden package after the commit; leak scan clean

## 6. Measure and verify

- [ ] 6.1 Before/after on the five fixtures, the City Garden Review and the four M3 projects: energy, capex, total expense, surplus; report in `Savills-local\backups\budget-agent\<date>-widen-sources-measure`
- [ ] 6.2 User signs off the before/after
- [ ] 6.3 Re-record the three baselines once; full test suite; `python verification/verify.py` PASS
- [ ] 6.4 Docs: RUNNING, README module table, outer `docs/05-decisions.md` (open questions answered), `docs/project-status.md`; release note
