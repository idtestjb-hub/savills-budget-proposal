## Why

The user reported (2026-11-12) that the Budget Agent output and the web page lack the project's details: towers,
floors, gates, pools, lifts, basements, parking, address. For a budget review these facts should already be there.
The diagnosis found four gaps:
- The Review page fills section 2 from known sources only when a library file is picked. An upload or a site package
  gets nothing, apart from the city and district typed at build time.
- A site package codes every project name in its master list, its own included, so it cannot look the project up.
- The deliverable's `0. Info` shows only the four-product fee table and writes the car slots into F12. The car and
  motorbike rows 15–18 (slots and price) stay empty, and the standard form has no rows for the other facts at all.
- No result page shows the facts a run actually used.

Blank facts are not harmless. Security, cleaning, lifeguard and lift lines are costed from them, so a blank fact
gives 0 on those lines. In the Sunrise Riverside package, 18 lines came out 0 this way.

## What Changes

- **More fact cells on the Review page.** Section 2 gains four cells that already exist on the input form: Passenger
  Elevators per Tower, Number of Basements, Number of Pools, Street Address. Uploads and new projects get them too.
- **Master list fallback at run time.** A Review run fills any fact the page left blank from the master list. The
  match uses the folded project name, the same rule as the library prefill: one tower → floor count used; tower count
  never filled, noted only; two matching rows → nothing used, noted. This covers uploads in the office. The PM's entry
  always wins.
- **The site package carries its own project's facts.** `build_site_package.py` finds the project's own master row:
  by folded name, or by `--master-row "<exact master name>"` when several rows match. It writes every fact the
  master holds into `site.json` (`facts` plus `fact_notes`). The page prefills section 2 from it and shows the notes,
  for example "master ghi 5 tháp; số tháp để PM kiểm và nhập". When no master row matches, the build stops unless
  `--no-master` is given.
- **Every run records where each fact came from.** The input form a run uses gets a `Fact Sources` sheet (label,
  value, source). Sources are: nhập trên trang web, file ngân sách đã duyệt, danh sách master, lượt trước, form nhập
  liệu.
- **`0. Info` shows the whole project.**
  - A new "QUY MÔ DỰ ÁN / PROJECT SCALE" block from row 23 lists every scale, address, amenity and parking fact, each
    with its unit and source.
  - A blank fact is shown and flagged "Chưa có số — PM nhập"; it is never skipped.
  - The parking rows of the existing table are filled: car slots in row 15 (owned by the developer) or row 16 (common),
    following the approved file, else row 16; motorbike slots in row 18; the applied parking prices in I15 / I16 / I18.
  - F12 is no longer written.
  - The G7 note about products without a row becomes Vietnamese.
- **The run page shows "Thông tin dự án".** New-project and Review results get a folding section listing the facts
  the run used, with their sources and the blanks flagged.
- **Coverage check over all projects.** A script runs the fact fill for every approved budget in the library and every
  master project. It reports how many facts each would get and from which source. Counts only, no names.

## Capabilities

### New Capabilities
- `deliverable-project-info`: the `0. Info` scale block, the parking rows and the per-fact source record (`Fact
  Sources`) that every run writes.

### Modified Capabilities
- `budget-web-review-facts`:
  - section 2 gains four cells;
  - blank facts are filled from the master list at run time for uploads too;
  - a site package prefills section 2 from its own facts and notes.
- `budget-site-package`: the package carries its own project's master facts and fact notes in `site.json`; the build
  picks the master row explicitly when names collide.
- `budget-web-review-results`: the run page has a "Thông tin dự án" section.

## Impact

- **Code:**
  - `webapp/facts_prefill.py`: more fields, master columns, and a function shared by the page and run time;
  - `webapp/server.py`: `FACT_LABELS`, plus `site.json` notes in `/api/site`;
  - `review.py` / `review_import.write_form`: master fallback and the `Fact Sources` sheet;
  - `webapp/fill_input.py`: new-project facts and sources;
  - `generate_project_budget.py`: the `0. Info` block and the parking rows;
  - `build_site_package.py`: `--master-row`, `--no-master`, facts written to `site.json`;
  - `webapp/results.py` and `webapp/static/index.html`: the facts section;
  - `verification/checks.py`: a new check that the block and rows are present;
  - tests.
- **Data:** none changed. The master list is read only.
- **Figures:**
  - Lines costed from facts move only in runs where a fact used to be blank and is now found. That is the point of
    the change, so the Review baselines of the sample runs are re-recorded after the user's sign-off.
  - New-project runs from a filled form do not move.
- **Packages:** City Garden and Sunrise Riverside must be rebuilt. The Hub needs the same code (release note through
  [Hub]).
