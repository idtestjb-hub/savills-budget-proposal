## ADDED Requirements

### Requirement: Site mode shows one project and three tabs
With `BUDGET_WEB_SITE` set to a folder holding `site.json` and the approved budget, the page SHALL show only the tabs
Review dự án đang vận hành, Dự án đã tạo and Hướng dẫn; the page title SHALL name the project. The Review tab's
source SHALL offer "Ngân sách đã duyệt của dự án" (selected by default, showing the project and file name), "Tải
file lên" and "Bản giao của lượt cũ", and SHALL NOT offer "Dự án có sẵn". Section 2 SHALL be pre-filled from
`site.json` with the source of each value, and the PM's own entry wins. The guide SHALL hide the parts about new
projects, the library and the Kho tab. Without the variable the page SHALL behave exactly as today.

#### Scenario: Site page
- **WHEN** the page opens in site mode
- **THEN** three tabs are shown, the Review source is the packaged budget, and Tỉnh / thành phố holds the packaged
  value

#### Scenario: Hub page unchanged
- **WHEN** the variable is absent
- **THEN** six tabs are shown and the Review source list starts at "Dự án có sẵn" as before

### Requirement: A Review in site mode snapshots the packaged budget
`POST api/reviews` with `site=1` SHALL copy the packaged approved budget into the run's `prior\` folder and run the
Review on that copy, so a later run gives the same figures even if the packaged file is replaced. The library routes
SHALL answer as if the scan store were absent.

#### Scenario: Run from the packaged budget
- **WHEN** the PM clicks Tạo ngân sách năm mới with the default source
- **THEN** the run folder holds `prior\<approved>.xlsx`, `facts.json` and the results, and History lists the run
  under the project's name

#### Scenario: Library not reachable
- **WHEN** `GET api/library` is called in site mode
- **THEN** it returns an empty list and the page keeps the three sources above
