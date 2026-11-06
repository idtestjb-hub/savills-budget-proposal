## Why

The eight real budgets the tool was first built on (the files in `input/budget_planning/`) are still looked up by
their project names: a list literal in the comparables module, a dictionary of NFA by name in the capex estimator,
`'A&K Tower'` and `'Parking Building'` in the utilities estimator, and name columns in four data files that the code
joins on. Because the code needs those exact names, the site package of 2026-11-05 had to leave them readable while it
anonymised every other project, and the same names appear in docstrings and in the internal analysis' source notes.
The user asked (2026-11-06) why the tool is still bound to those eight; the answer is that nothing identifies them other
than their names. This change gives each of them a stable key so the names become display data that can be masked.

## What Changes

- A new reference-project registry, `Budget_Agent/data/master_list_verified/Dim_ReferenceProject.csv` (outer repo,
  `PM/Project`), holds one row per reference budget: key `R01`..`R08`, display name, the name variants each data file
  uses today, NFA, units, management-fee rate and its VAT basis, district, city, the "excluded from ranking" flag, the
  roles the code relies on (utilities base, parking base, carries capex line items), and the source and location
  evidence that today sit in code comments.
- The four data files that carry a reference project's figures gain a `RefKey` column, filled once by a migration
  script from the registry's name variants: `Fact_OPEX.csv`, `Fact_Capex_Rescanned.csv`, `Fact_CapexReserve.csv`,
  `Ref_ComparableVATBasis.csv`. Their name columns stay for readability. The rescan scripts that rebuild these files
  write `RefKey` from now on.
- The comparables module, the utilities estimator, the capex estimator and the verification check read the registry
  and join on `RefKey`. No runtime module keeps a reference project's name as a text literal; the internal analysis
  still shows the registry's display name where it names a project today.
- The site package builder treats the eight like every other project: the registry's display names and the fact
  files' name columns become "Dự án tham chiếu NN" inside a package, and the leak scan no longer exempts them. The Hub
  (office) data is untouched, so the internal analysis on the Hub reads as today.
- Figures do not move. Every baseline, the three verification samples and a City Garden Review give the same numbers
  before and after.

## Capabilities

### New Capabilities
- `reference-project-registry`: how the reference budgets are identified (one key each in one data file), how their
  figures in the fact tables are tied to that key, and the rule that runtime code holds no reference project's name.

### Modified Capabilities
- `budget-site-package`: a package anonymises every project other than the site's own, the eight reference budgets
  included; the leak scan exempts only the site's own name.

## Impact

- Code (`source_code`): `master_comparables.py`, `estimate_opex.py`, `estimate_capex_qty.py`,
  `generate_project_budget.py` and `generate_project_output.py` (wording of notes and remarks only),
  `verification/checks.py`, `site_data.py`, `rescan_opex_from_source.py`, `rescan_capex_from_source.py`,
  `rescan_capex_reserve.py`, a one-off `migrate_reference_keys.py`; tests `test_master_comparables.py`,
  `test_estimate_opex.py`, `test_client_wording.py`, `test_site_data.py` plus new registry tests.
- Data (`PM/Project/Budget_Agent/data/`, outer repo, no remote): one new file, four files gain a column. Backups beside
  them before the migration. No SharePoint file outside the project is read or written.
- Deliverables: none of the client deliverable's figures or text change. The internal analysis names the same projects
  with the same names on the Hub. A site package shows pseudonyms for the eight where it showed names.
- Hub web: ships at the same commit as the next site package (user's rule of 2026-11-05).
- Out of scope: replacing the eight as the source of capex item lists and utility ratios (a separate change, after the
  store scan of 2026-11-06).
