## Why

A site package is built for one project from last year's approved budget, and its page offers only the Review tab.
Some managed projects have no approved budget yet (a project in its first year): since de23cf6 such a package can be
built without `--prior`, but its page can then only take an uploaded approved budget. The site needs a way to make a
budget from the project's own facts, the way the Hub's "Nhập liệu dự án mới" tab does (user, 2026-11-11: "chưa có dự
án cũ, nên set up cho package chạy null với các thông tin input hoặc upload file lên chạy").

## What Changes

- A site package whose `site.json` has no approved budget (`prior_file` empty) shows two more tabs: **Nhập liệu dự án
  mới** and **Kết quả dự án mới**, plus the guide's new-project section and the Clone button in Dự án đã tạo. The page
  still opens on the Review tab (user's choice), whose source is "Tải file lên".
- The Nhập liệu form is pre-filled with the project name and the packaged facts (city, district); the other cells keep
  the sample values, as on the Hub, and the status line says so.
- The Review tab's note for such a package is a plain instruction instead of an error ("Gói chưa kèm ngân sách đã
  duyệt: tải file lên ở đây, hoặc lập ngân sách từ thông tin nhập ở tab Nhập liệu dự án mới").
- `POST api/runs` (new project) is refused in site mode when the package carries an approved budget, so a package with
  a budget stays Review-only on both page and server.
- `HUONG-DAN.txt` of a package without `--prior` names both ways.
- The package data gains `AI_Guideline_Required_Classification.csv` (budget codes and their Required / Optional
  class, no project name): every run writes a run-log record from it, and without it the record's figures are blank
  in every package, Review runs included.
- The package's master list keeps the two raw parking-fee columns (other projects' names inside replaced by their
  codes): `parking_prices.py` takes a new project's car and motorbike prices from their portfolio median, and with
  the columns blanked a package fell back to the former constants (measured: 329.7M VND less revenue on the sample).
- Packages with an approved budget (City Garden) and the Hub page are otherwise unchanged.

## Capabilities

### New Capabilities

### Modified Capabilities
- `budget-site-package`: a package without an approved budget also offers the new-project entry.

## Impact

- `webapp/static/index.html` (site-mode init, CSS, history Clone button), `webapp/server.py` (`api/runs` guard),
  `build_site_package.py` (guide text), tests `tests/test_webapp_site.py`, docs `webapp/README.md`, `RUNNING.md`.
- No figure moves: the new-project run is the Hub's own `run_budget.py` path; the package's data folder is the trimmed
  set of change site-data-isolation, so the run is checked inside a package (task 3.2).
- Hub: same code, site-mode branches only; deploy with the next budget-web release.
