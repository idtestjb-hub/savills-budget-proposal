## Why

The Budget web runs on the Hub server inside the office network. The Review feature is now wanted at close to 100
managed sites. Those sites have no link to the office network, nobody knows whether their PCs carry Python or allow
installing software, and each site must see only its own budget. Opening the Hub to the internet would need IT work
(a public port, security review) and still leaves the sites dependent on a link. The user's decision on 2026-11-05:
every site gets one self-contained package, extracted from a zip and started with one click, holding the Python
runtime, the generators, the reference data and that site's approved budget only.

## What Changes

User's choices on 2026-11-05: local web with the Python runtime inside the package, the site's own data only; the
page keeps the tabs Review, Dự án đã tạo and Hướng dẫn. A one-shot run without the web page was built as a trial
beside it and removed the same day on the user's decision ("PM phải nhập và sửa được"): the web page is the only way
to run at a site.

- **A build script makes one package per site** from this repository and a prepared runtime folder:
  `BudgetAgent-<site>\` with `python\` (Python 3.14 copied from the build PC and pruned, plus the packages the web
  and the generators import, `pywin32` DLLs beside `python.exe`), `app\` (the generators, `data\`, the 2027 form
  template, the input form; no tests, legacy code, OpenSpec, docs or scan store), `site\` (`site.json` with the
  project's name, the approved budget's file name and the pre-filled facts; the approved budget `.xlsx`),
  `runs\` (empty), two launchers and a one-page guide in Vietnamese. The package is zipped for delivery, because the
  tenant refuses to sync `.cmd` and `.exe` files.
- **Site mode of the web page** (`BUDGET_WEB_SITE=<site folder>`): no login; only the tabs Review, Dự án đã tạo,
  Hướng dẫn; the Review tab's source is "Ngân sách đã duyệt của dự án" (the packaged file) by default, with "Tải file
  lên" and "Bản giao của lượt cũ" still available; section 2 facts are pre-filled from `site.json`; the library and the
  Kho tab are absent; the guide hides the parts about new projects and the library. Nothing in the package compares
  the site with another project on the page. (The internal analysis workbook keeps its Comparison and Service Levels
  sheets as today; whether those stay in a site package is an open decision, see Impact.)
- **Launcher `Chay Budget Agent.cmd`**: starts the local web on a free port of 127.0.0.1 with the package's own
  runs and temp folders, opens the browser, and keeps a console window whose closing stops the web. A second click
  while it runs only opens the browser.
- **Build-PC checks:** the build script starts the packaged runtime, imports every needed module and reads the
  packaged budget; a Review through the packaged web is run on one site package before delivery.

## Capabilities

### New Capabilities
- `budget-site-package`: what a site package contains, how it is built and checked, how it starts.
- `budget-web-site-mode`: how the web page behaves with `BUDGET_WEB_SITE` set.

### Modified Capabilities
- none (the Hub deployment and the existing tabs are unchanged when the variable is absent).

## Impact

- New: `build_site_runtime.py` (runtime folder, once per build PC), `build_site_package.py` (one package per site),
  `webapp/start_site.py` (launcher), the launcher `.cmd` and `HUONG-DAN.txt` written by the build script.
- Changed: `webapp/server.py` (`api/site`, `site=1` source of `POST api/reviews`, site mode flag into the page),
  `webapp/static/index.html` (site mode: tabs, default source, pre-filled facts, guide sections), `webapp/README.md`,
  `RUNNING.md`.
- Reads: `Budget_Agent/data/**` (reference CSVs), `input/template/2027 Resi Budget Form (IT team).xlsx`,
  `reports/Project_Budget_Input.xlsx`, the site's approved budget, and for the facts the scan store's
  `dim_file.csv` / `project_map.csv` and the master list (build PC only). Writes: the package folder and zip under the
  build output folder; at the site, `runs\` and `tmp\` inside the package only.
- No recorded baseline figure moves: the generators are not changed.
- Size: about 100 MB per package before zipping (runtime about 60 MB); 49 sites have a readable approved budget in
  the scan store today, the others start in "Tải file lên" mode with no pre-filled facts.
- Open decision for the user: `data\master_list_verified\` holds the master list of Savills properties (names,
  location, summary figures) that the estimation needs for comparables, and the analysis workbook names two
  reference projects on its Comparison sheet. Either the package keeps them as today (internal Savills staff at the
  site) or the build strips the Comparison and Service Levels sheets from the analysis and the page hides them.
