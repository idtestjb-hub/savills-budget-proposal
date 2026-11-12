## ADDED Requirements

### Requirement: The run page shows the project facts the run used
The result of a run, new project or Review, SHALL show a folding section "Thông tin dự án". The section SHALL list
every fact of the `0. Info` scale block with its value and source. Blank facts SHALL be flagged "Chưa có số — PM
nhập". Viewers SHALL see the section too.

#### Scenario: Review run in a site package
- **WHEN** a Review run in a package used master facts from `site.json`
- **THEN** the section SHALL show those facts with source "dữ kiện đóng trong gói", and the facts the PM changed with
  source "nhập trên trang web"

#### Scenario: Earlier run without a sources sheet
- **WHEN** the page shows a run made before this change
- **THEN** the section SHALL show the values read from that run's input form with source "form nhập liệu", or say
  that the run has no input form
