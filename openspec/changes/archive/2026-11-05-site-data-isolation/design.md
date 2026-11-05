## Context

`build_site_package.build()` copies `data\` with `copy_tree`. The pipeline reads reference CSVs by fixed paths under
`BUDGET_AGENT/data`; `master_comparables` merges the hand-verified comparables coded in the module with the master list
(`Dim_Property_Residential.csv`, skipped when the name matches a coded one), attaches ward and coordinates from
`Fact_ProjectLocation.csv` by normalised name, and reads the VAT basis from `Ref_ComparableVATBasis.csv` by name;
`estimate_opex` reads `Fact_OPEX.csv` by `facts['A&K Tower']`; `real_budget_ranges` and `service_levels` key projects by a
SHA-256 `name_key`, already anonymous.

## Decisions

**D1. Measured allow-list, not a guess.** A Review of City Garden was run with a `sys.addaudithook('open')` trace
(sitecustomize on PYTHONPATH, so the generator subprocesses were traced too): 15 files under `data\`, plus the template
and the input form. `site_data.KEEP` is that list; a test checks every entry exists, and the package Review (task 3.2)
proves nothing else is needed. A new reader must add its file to KEEP.

**D2. One pseudonym per name across files.** `Pseudonyms` maps the NFC-casefolded name to "Dự án tham chiếu NN" in order
of first sight, starting with the master list, so `Fact_ProjectLocation` rows join to the same masked row. Kept as-is:
the site's own name(s) (the self-exclusion rules of `master_comparables.nearest_comparables` and `real_budget_ranges`
need them) and `site_data.code_names()` = `HAND_VERIFIED_COMPARABLES` names + A&K Tower + Parking Building.

**D3. Blank text, keep figures.** Columns listed per file in `MASK['blank']` and every column ending in `_raw` are
emptied; numeric and categorical columns stay, including `District`, `City_Province` and the coordinates of
`Fact_ProjectLocation` (the 1-km distance tier of the ranking needs them; without them the chosen comparables, hence
figures, could differ from the Hub). The leading `#` comment lines of a CSV (they cite office file paths) are replaced
by one neutral line. `Ref_ComparableVATBasis.source_text` is kept because the loader refuses a blank one.

**D4. The leak check is a scan of the built package, not trust in the rules.** Words = `Name` of both master lists +
file-name stems of the store's `dim_file.csv` (when the store folder exists on the build PC), minus own and coded names,
minus words under 4 characters. Scanned: every `.py/.txt/.md/.json/.html/.cmd/.csv/.pth/.yaml` file and the shared
strings + sheet XML of every `.xlsx/.xlsm` under the package except `python\`. `--check` prints the hits and fails.

**D5. Not in scope.** The 8 reference budgets named in code; `verification/fixtures` (invented samples); the Hub web,
which keeps the full data on the server.

## Measured (2026-11-05, task 3.2)

City Garden package built with this change (`--check --zip`): data 15 files, 159 other-project names anonymised, text
columns blanked in 6 files; import OK; packed file read (MF 411, CA 373 lines); text scan clean; **leak scan: 237 names,
0 hits** (4 names sit in the notes of the standard 2027 form itself and are reported apart, not counted). Package 77 MB
(was 80), zip 31 MB. The Review run inside the package (package Python, trimmed data, same facts) against the same Review
on the office data: MF R 39,598,670,915.36 / E 36,567,450,727.00 / S 3,031,220,188.36 and CA R 47,636,364.00 /
E 43,639,259.36 / S 3,997,104.64 identical to the VND; ties 8 of 8 identical; top-10 codes and differences identical;
counts identical (196 lines, 82 abnormal); 100 "Nhập số" lines added in both. The first trace missed
`Fact_Capex_Rescanned.csv` because the generator opens it through `source_code\..\data`; the package Review caught it
(generator stopped), the trace now normalises paths, and the file is in KEEP with its `Project` column anonymised
(the 8 coded names kept, '11D Thi Sach' without diacritics added to `CODE_NAMES_EXTRA` because that file spells it so).
Runtime code also carried names: `generate_project_output.py` (3 parking-lease comparables and a 6-project market
survey, now "Dự án so sánh 1-3" / "6 real comparable projects"), docstrings in `master_comparables.py` and
`webapp/facts_prefill.py`; office-only scripts (`build_*`, `derive_*`, `etl_*`, `rescan_*`, `study_*`, `transform_*`,
`extract_info_sheets.py`, `verification/method_coverage.py`) are left out of the package.
