## Why

The site package of change `site-standalone-package` copies the whole `data\` folder, so the City Garden package carried
the budgets, staff costs by position and names of 15 reference projects, the master list of 160 managed properties with
addresses, and the detailed figures of the 8 comparable budgets (found 2026-11-05 while uploading the package). The user's
rule: a package holds the data of its own project and nothing of other projects. Several projects will get a package for
demos, each run on its own, and the same split prepares the per-role data view planned for the server.

## What Changes

User's decisions on 2026-11-05: anonymise and keep the aggregates (not drop the reference data), so the package gives the
same figures as the Hub; make it a reusable tool, not a one-off cut.

- **A module `site_data.py`** that builds the data folder of one site: it copies only the files a Review run reads
  (15 files, measured with an open-file trace on City Garden) and anonymises the five that name other projects: names
  become "Dự án tham chiếu NN" (one code per name across every file, so joins by name still work), addresses, source file
  names and raw-text columns are blanked, figures (NFA, rates, coordinates, ratios) stay. The project's own name and the
  names coded into `master_comparables.py` / `estimate_opex.py` (the method's 8 reference budgets, A&K Tower, Parking
  Building) are kept, because the code looks them up by name.
- **A leak check** `site_data.find_leaks()`: every name of the two master lists and every file name of the scan store,
  except the project's own and the coded names, must be absent from every text file and every Excel string of the
  package. `build_site_package.py --check` runs it and fails on a hit.
- `build_site_package.py` uses the module instead of copying `data\`.

## Capabilities

### Modified Capabilities
- `budget-site-package`: the package's data folder is the trimmed, anonymised set; the check scans for other projects'
  names.

## Impact

- Changed: `build_site_package.py`, new `site_data.py`, new `tests/test_site_data.py`, `webapp/README.md`.
- Reads: `data\` (15 files), `Dim_Property_Commercial.csv` and the scan store's `dim_file.csv` for the leak word list.
  Writes: the package's `app\Budget_Agent\data` only. No figure on any deliverable moves; the equality is measured on
  City Garden (task 3.2).
- Known limit, stated to the user: the 8 reference budgets are named in code and on the Comparison sheet of every
  deliverable (Hub too); hiding them is a separate change (move them to data, key by code).
