## 1. Registry and data migration (outer repo `PM/Project/Budget_Agent/data/`)

- [x] 1.1 Write `build_reference_registry.py` (office only) that creates `data/master_list_verified/Dim_ReferenceProject.csv`
      from the current `HAND_VERIFIED_COMPARABLES` literal plus Parking Building, with the columns of design D1 and the
      alias variants found in the four fact files; verify by reading the file back: 8 rows, every alias of every fact
      file resolves to exactly one key, Parking Building = `R08`.
- [x] 1.2 Write `migrate_reference_keys.py` (office only) that backs up `Fact_OPEX.csv`, `Fact_Capex_Rescanned.csv`,
      `Fact_CapexReserve.csv`, `Ref_ComparableVATBasis.csv` as `.backup-2026-11-06` and appends a filled `RefKey` column;
      verify with a script that compares old and new files: same row count, every original column byte-identical,
      `RefKey` filled on every row except the master-list row of the VAT-basis file.
- [x] 1.3 Make `rescan_opex_from_source.py`, `rescan_capex_from_source.py` and `rescan_capex_reserve.py` write `RefKey`
      from the registry; verify by a dry run into `C:\ZWork` that produces the same `RefKey` values as the migration.

## 2. Code reads the registry and joins on the key

- [x] 2.1 `master_comparables.py`: load `HAND_VERIFIED_COMPARABLES` from the registry (same dict shape, plus `key`),
      resolve the input project to a key for exclusion (design D4), stop with a clear message when the registry is
      missing; verify `tests/test_master_comparables.py` passes with assertions moved from names to keys / registry
      values.
- [x] 2.2 `estimate_opex.py`: utilities base and parking base by role, NFA from the registry, `Fact_OPEX.csv` rows by
      `RefKey`, skipped rows counted in the result; verify `tests/test_estimate_opex.py` passes and the standard
      sample's EEE/EEW/EEF figures are unchanged.
- [x] 2.3 `estimate_capex_qty.py`: candidates = registry rows with role `capex_items`, rows by `RefKey`, exclusion by key;
      verify the capex item list of the standard sample is identical to the one before the change (item, qty, price).
- [x] 2.4 `generate_project_output.py` and `generate_project_budget.py`: source notes and remarks take display names
      from the registry; comments and docstrings reworded; verify with `grep` that no runtime module contains any
      registry display name or alias.
- [x] 2.5 `verification/checks.py`: names for the client-deliverable scan come from the registry as well; verify the
      scan still lists all eight names on the office data (unit test with a registry fixture).
- [x] 2.6 `site_data.py`: registry in `KEEP`, `MASK` for the registry and the four fact files, pseudonym per key,
      `code_names()` empty, `leak_words()` includes the registry; `build_site_package.py` unchanged; verify
      `tests/test_site_data.py` passes with a new case "a reference project is pseudonymised in registry and fact file
      alike".

## 3. Tests

- [x] 3.1 New `tests/test_reference_registry.py`: registry loads, 8 keys, roles resolve, every alias unique, every fact
      file's `RefKey` column filled and known, runtime modules contain no display name or alias; verify it passes.
- [x] 3.2 Update `tests/test_client_wording.py` so its "no other project named" assertions take names from the
      registry; verify it passes.

## 4. Figures unchanged, measured

- [x] 4.1 Before/after on the three verification samples: generate at `9b33469`-equivalent (git stash / worktree) and
      at the change, compare every numeric cell of the deliverable and the internal analysis; deliver the table in
      design.md "Measured"; the user signs off "no movement".
- [x] 4.2 Before/after on a City Garden Review (read-only, `C:\ZWork`, user's OK as on 2026-11-05): fund totals, 8 ties,
      top-10 list and abnormal count identical; add to the "Measured" table.
- [x] 4.3 Rebuild the City Garden site package with `--check --zip`: check passes, the leak scan now counts the eight
      among the names scanned, the registry and fact files inside the package show "Dự án tham chiếu NN"; the Review
      inside the package equals the office run; record the result in design.md "Measured".
- [x] 4.4 Full test suite with `--basetemp` under `C:\ZWork` passes; `python verification/verify.py` run from
      `Budget_Agent/source_code/` passes with the gates closed and no baseline re-recorded.

## 5. Documentation and release

- [x] 5.1 `RUNNING.md`, `README.md` module table and `webapp/README.md`: the registry, the migration script and the
      package rule; `docs/05-decisions.md`: entry "Reference projects by key"; `docs/project-status.md` updated.
- [ ] 5.2 Release note `Savills-Automation-Hub-Setup\releases\<date>-budget-web-tham-chieu-theo-ma.txt` naming the
      `source_code` commit and the outer commit that carries the data; the site package is rebuilt from the same
      commit (user's rule).
