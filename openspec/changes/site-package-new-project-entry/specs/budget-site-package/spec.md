## ADDED Requirements

### Requirement: A package without an approved budget also offers the new-project entry
When the package's `site.json` names no approved budget (`prior_file` empty, a package built without `--prior`), the
site page SHALL show, besides Review dự án đang vận hành, Dự án đã tạo and Hướng dẫn, the tabs Nhập liệu dự án mới and
Kết quả dự án mới, the guide's new-project section and the Clone button of Dự án đã tạo. The page SHALL open on the
Review tab with "Tải file lên" selected and a plain note naming both ways. The Nhập liệu form SHALL be pre-filled with
the project name and the packaged city and district, the other cells keeping the sample values. A new-project run
inside the package SHALL use the same `api/runs` path as the Hub and give the same figures as the same input run on the
office data. When the package names an approved budget, the page SHALL keep only the three tabs and `POST api/runs`
SHALL be refused; outside site mode nothing changes.

#### Scenario: Package without an approved budget
- **WHEN** the page opens in site mode and `site.json` has `prior_file` ""
- **THEN** five tabs are shown, the Review tab is open on "Tải file lên" with a note pointing to Nhập liệu dự án mới,
  and the Nhập liệu form holds the project name, Hồ Chí Minh and the packaged district

#### Scenario: New project run in the package
- **WHEN** the site fills the Nhập liệu form and clicks Tạo ngân sách
- **THEN** the run finishes, Kết quả dự án mới shows the year-one figures and the deliverable and roster to download
  (no internal analysis), and Dự án đã tạo lists the run with Clone enabled

#### Scenario: Package with an approved budget
- **WHEN** `site.json` names the packaged approved budget and `POST api/runs` is called
- **THEN** the server answers 403 and the page shows only the three tabs, as before
