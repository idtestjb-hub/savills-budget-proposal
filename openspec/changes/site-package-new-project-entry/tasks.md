## 1. Page and server

- [x] 1.1 `index.html`: in site mode, when `site.json` has no `prior_file`, mark the body `site-new` and show the
  elements marked `site-new-ok` (tabs Nhập liệu dự án mới / Kết quả dự án mới, guide section and link, Clone button
  and its note); the page stays on Review with "Tải file lên" and a plain note
- [x] 1.2 `index.html`: pre-fill the Nhập liệu form with the project name, city and district after the sample values
  load; status line says the other cells are samples
- [x] 1.3 `server.py`: `POST api/runs` refused (403) in site mode when the package names an approved budget

## 2. Package build and docs

- [x] 2.1 `build_site_package.py`: HUONG-DAN of a package without `--prior` names both ways (upload, or Nhập liệu dự
  án mới)
- [x] 2.2 `webapp/README.md`, `RUNNING.md`: site packages without an approved budget
- [x] 2.3 `site_data.KEEP` gains `master_list_verified/AI_Guideline_Required_Classification.csv` (codes only, no
  project name): run.py's run log reads it, and without it the record of every run in a package has blank figures
  (found by task 3.2)
- [x] 2.4 `site_data.MASK`: keep `CarParkingFee_raw` / `BikeParkingFee_raw` of the master list with other projects'
  names replaced (`subst`), instead of blanking them like the other `_raw` columns; the name column is coded first so
  `subst` also knows the master list's names. Found by task 3.2: a new project in the package priced parking from the
  former constants (car 1,100,000 / motorbike 110,000) instead of the portfolio median (1,200,000 / 145,000), revenue
  and fund surplus 329.7M VND lower than the office run

## 3. Verification

- [x] 3.1 Tests: page markup and `api/runs` guard in site mode with and without an approved budget; build guide text
- [x] 3.2 Build the Sunrise Riverside package; inside it run a new project from the sample input and compare the
  year-one totals with the same input run on the office data; check the page in a browser
- [x] 3.3 Full pytest and `verification/verify.py` pass
