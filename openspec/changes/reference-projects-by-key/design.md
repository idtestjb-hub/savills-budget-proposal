## Context

See proposal.md, Why. Current state, measured 2026-11-06 on `9b33469`:

- `master_comparables.HAND_VERIFIED_COMPARABLES` (lines 112-192): 7 dict literals (name, nfa, units, total_units,
  mgmt_rate, mgmt_rate_vat, district, city, source, location_source, `excluded_from_ranking` on the two Hà Nội
  projects). `_merge_comparables()` drops master-list rows whose name matches one of them and joins
  `Fact_ProjectLocation.csv` by name. `nearest_comparables(exclude_name=...)` excludes the project being budgeted by
  name substring.
- `estimate_opex._load_opex_facts()` keys `Fact_OPEX.csv` (9 rows) by `Project`; `estimate_opex()` reads
  `facts['A&K Tower']`, `facts.get('Parking Building')` and the constant `AK_TOWER_NFA_M2 = 64_124.0`.
- `estimate_capex_qty.VERIFIED_NFA_FOR_ITEMS`: 7 lowercased names to NFA; `estimate_capex_items()` picks the nearest
  by NFA among `Fact_Capex_Rescanned.csv` (1,329 rows, `Project` column) and excludes by name substring.
- `Fact_CapexReserve.csv` (5 rows): `Project` holds the source *file name*, not the project name; read by
  `generate_project_output.py` for the reserve-rate evidence.
- `Ref_ComparableVATBasis.csv` (8 rows): `project_key` is the name; one row ("Rivergate Residence") is a master-list
  project, not one of the eight.
- `verification/checks.project_names_from_data()` builds the "client deliverable names no other project" list from
  nine data files and `HAND_VERIFIED_COMPARABLES`.
- `site_data.code_names()` = the hand-verified names + `('A&K Tower', 'Parking Building', '11D Thi Sach')`; these are
  exempt from pseudonymisation and from the leak scan.
- Name literals in runtime text: `generate_project_output.py` source notes (steps 3, 6, 7 of the flow sheet),
  `generate_project_budget.py` remarks about missing bank/audit fee lines ("Fact_OPEX.csv, A&K Tower") and comments.
- Tests pinned on names: `test_master_comparables.py`, `test_estimate_opex.py`, `test_client_wording.py`,
  `test_site_data.py`.

Constraints: no figure may move (verify.py with gates closed, baselines not re-recorded); data files live in the outer
repo `PM/Project` (no remote); the Hub web and the site package ship at the same commit.

## Goals / Non-Goals

**Goals:**
- One place that knows who the reference projects are; everything else joins on `RefKey`.
- The eight become maskable like any other project in a site package, with the Review inside the package unchanged.
- The code reads the same whether a display name is real or a pseudonym.

**Non-Goals:**
- Replacing the eight as the source of capex item lists or utility ratios (next change, after the store scan).
- Changing which comparables are chosen, how they are ranked, or any rate.
- Anonymising the Hub's internal analysis: on the office data it keeps the real names (decision 2026-11-05).
- Touching the client deliverable's text or the standard form's notes.

## Decisions

- **D1. One registry CSV in `data/master_list_verified/`, keys `R01`..`R08`.** Columns: `RefKey`, `DisplayName`,
  `Aliases` (`|`-separated name variants: ASCII spelling, the capex file's two Fiato labels, the capex-reserve file
  names), `TotalNFA_m2`, `ApartmentUnits`, `TotalUnits`, `MgmtRate_VND_m2_month`, `MgmtRateVAT`, `District`, `City`,
  `ExcludedFromRanking`, `Roles` (`utilities_base|parking_base|capex_items`), `Source`, `LocationSource`,
  `VerifiedOn`. Keys assigned in the order of the current list literal, then `R08` = Parking Building. Why a CSV and
  not a Python module: the package builder masks CSV columns already (`site_data.MASK`), and the user's rule is that
  names are data, not code. Alternative rejected: keep the literal and add a `key` field to each dict, which leaves the
  names in code and still exempt from masking.
- **D2. `RefKey` is added as a new last column; name columns stay.** The fact files remain readable on the Hub and
  `git diff` of the data shows one column added, no value changed. A one-off `migrate_reference_keys.py` (office only,
  excluded from packages like the other `build_*`/`rescan_*` scripts) maps each row's name through the registry's
  aliases, writes a `.backup-<date>` beside each file first, and refuses to run if any row of the four files cannot be
  mapped (`Ref_ComparableVATBasis.csv`'s "Rivergate Residence" row gets an empty `RefKey` by design: it is a master-list
  project, matched by name as before, since the VAT-basis lookup for master-list projects stays by name). Alternative
  rejected: rename `Project` to `RefKey` in place, which breaks every reader at once and loses the label.
- **D3. Roles instead of names in the estimators.** `estimate_opex` asks the registry for the row with role
  `utilities_base` (today `R02`) and `parking_base` (today `R08`) and takes NFA from the registry; the constant
  `AK_TOWER_NFA_M2` goes. `estimate_capex_qty` takes candidates from the registry rows with role `capex_items` and
  their NFA, and selects rows of `Fact_Capex_Rescanned.csv` by `RefKey`. A later change can point a role at another
  project or at a derived table without touching the estimator.
- **D4. Exclusion of the project being budgeted by key when it is a reference project, by name otherwise.** The
  comparables module resolves the input project's name against the registry (display name and aliases, case-folded) to
  a key once; `nearest_comparables` and `estimate_capex_items` exclude that key. For a project not in the registry the
  existing name-substring exclusion against master-list rows stays. This keeps today's behaviour for the three samples
  (none is a reference project) and for the real-project back-tests (which are).
- **D5. Display names from the registry wherever the internal analysis names a project.** `source=` notes in
  `generate_project_output.py` are rebuilt with `', '.join(display names of role capex_items)` and the like; the two
  remark strings in `generate_project_budget.py` take the utilities base's display name. Comments and docstrings that
  name projects are reworded ("the utilities base", "the seven projects with capex line items"). On the office data
  the text reads as today; in a package it reads with pseudonyms, which is the point.
- **D6. `checks.project_names_from_data()` adds the registry (display names and aliases) to its sources and drops the
  import of the list literal.** The verification keeps catching every name on the client deliverable.
- **D7. `site_data`: the registry joins `KEEP`; `MASK` masks `DisplayName` and `Aliases` of the registry and the name
  columns of the four fact files (`Fact_CapexReserve.csv` `Project` and `SourceFile` added); `code_names()` returns an
  empty set; `leak_words()` adds the registry's names.** Pseudonyms are assigned per *key* for the eight so that
  display name and every alias of one project map to the same "Dự án tham chiếu NN"; other projects keep the per-name
  rule. Alternative rejected: keep the eight readable and document it, which is what the user asked to end.
- **D8. Measured, not assumed.** Before/after on the three verification samples and one City Garden Review (read-only,
  `C:\ZWork`), cell-for-cell on figures; the recorded baselines are not re-recorded. The user signs off the "no
  movement" table before the commit.

## Risks / Trade-offs

- [A name variant missed by the alias list leaves a row with empty `RefKey` and silently drops it from pricing] →
  the migration refuses to run on an unmapped row in `Fact_OPEX`, `Fact_Capex_Rescanned` and `Fact_CapexReserve`; the
  run log counts skipped rows; the before/after comparison would show the movement.
- [Pseudonymising the registry inside a package changes the pseudonym numbering of other projects] → pseudonyms are
  assigned in a fixed order (registry first, then the master list); the package Review is compared with the office run
  as in the previous change.
- [Tests that assert on "A&K Tower" in generated text] → updated to assert on the registry's display name read at test
  time, so they pass on real and pseudonymised data alike.
- [The rescan scripts are rarely run; a future rebuild could write the files without `RefKey`] → each rescan script
  writes `RefKey` from the registry and a test checks that every committed fact file has the column filled.
- [Data files in the outer repo change while `source_code` is committed separately] → commit order as always:
  `source_code` first, then the outer repo with the data and the status entry, and the release note names both.

## Migration Plan

1. Build the registry from the current list literal and the data files (script, output reviewed by hand once).
2. Back up the four fact files beside themselves (`.backup-2026-11-06`), run `migrate_reference_keys.py`, check that
   row counts and every figure column are byte-identical except for the new column.
3. Switch the code to the registry and `RefKey`; run the affected tests, then the full suite and `verify.py`.
4. Before/after measurement (D8); user's sign-off.
5. Rebuild the City Garden package; the check must pass with the eight now pseudonymised and the Review identical.
6. Release note for the Hub web at the same commit; rollback = previous commit, the data files' backups restore the
   pre-migration CSVs (the new column is harmless to the old code, which ignores unknown columns).

## Measured

Measured 2026-11-06 (session P22). "Before" = a copy of `source_code` at `7670fc7` (git archive) with copies of the
data folder, the input form and the template in `C:\ZWork`; "after" = the working tree of this change. Every `.xlsx`
the two runs wrote was compared cell for cell (stored values and formula text, `compare_outputs.py`).

| Run | Files | Cells compared | Numeric / formula / shape diffs | Text diffs |
|---|---|---|---|---|
| 5 fixtures (standard, existing, existing_lump, villa, operating): deliverable, analysis, roster | 25 | about 300,000 | **0 / 0 / 0** | 50, all reworded source notes (the Data Flow sheet's "7 hand-verified projects" step now reads LIVE from the registry; "the utilities base project" instead of a name) |
| City Garden Review (read-only on the approved file, facts City / District) | 6 | 232,925 | **0 / 0 / 0** | 4 (same reworded notes) |

City Garden `review_summary.json`: summary, ties, measure_ties, top, abnormal, abnormal_rule and counts identical
(194 lines, 39 both, 105 only approved, 32 only tool, 73 no method, 29 tool zero, 81 abnormal; same top 10).
One unintended text change was caught and fixed on the way: a whole-number rate read from the CSV printed as
"18,000.0" instead of "18,000" on the Comparison sheet; the registry loader now keeps whole-number rates as `int`.

Tests: full suite 1,367 passed + 1 xfailed (two end-to-end failures were the missing import fixed above; both pass
alone). `verify.py` with the gates closed: PASS, baselines not re-recorded. Rule learnt: the generators save to one
fixed temp file before copying into place, so two runs sharing `TEMP` corrupt each other (Bad CRC-32); the
verification chain was re-run strictly one job at a time.

Package (task 4.3): first build's leak scan caught two names the code-level scan could not: `Fact_OPEX.csv`'s
`PriceAsOf` text ("~2020 (A&K Tower budget)", a column that must keep its date) and `build_project_input_form.py`
(imported by `review_import`, so a runtime module the test had wrongly exempted). Fixed by substituting registry
names inside text columns (`site_data` `subst`) and rewording the builder; `build_reference_registry.py` left out of
packages. Second build: see project-status for the scan result.
