# budget-web-review-results Specification

## Purpose
What the Budget web's Review results block shows for a Review run: the counts line and the list of the ten
largest differences, with the abnormal-difference flags the Review computed. The page reads only the run's
`review_summary.json`; it writes no data file and moves no recorded baseline figure.

## Requirements

### Requirement: The Review page shows the abnormal count and tags the top list
The counts line of a Review run SHALL state the number of abnormal lines with the rule in brackets, and each line of "10
dòng lệch lớn nhất" that the Review flagged SHALL carry the tag "Bất thường" after its code. A run recorded before the
rule SHALL show the counts line without the abnormal count and the top list without tags.

#### Scenario: Counts and tags
- **WHEN** a Review run flagged 12 lines and 9 of the top 10 are among them
- **THEN** the counts line ends with "bất thường (≥20% và ≥50 triệu/năm): 12" and 9 rows of the top table carry the tag

### Requirement: The Review result sections fold
The sections "Ngân sách đã duyệt so với ngân sách năm mới do công cụ sinh" and "Đối chiếu tổng" of a Review run
SHALL each carry a button on their heading that folds the section to its heading and unfolds it again. Both SHALL
start open on first use; the browser SHALL remember each state across runs and reloads. Folding SHALL NOT change
any figure, request or saved value.

#### Scenario: Fold and reload
- **WHEN** the PM folds "Đối chiếu tổng" and reloads the page or opens another run
- **THEN** that section opens folded and "Ngân sách đã duyệt..." stays open

#### Scenario: Unfold
- **WHEN** the PM clicks the folded heading's button
- **THEN** the section's table is shown with the figures of the current run

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

### Requirement: The Review page shows a sinking-fund comparison table

The Review results SHALL include a folded section "Quỹ bảo trì". It SHALL have one row per sinking-fund code that
carries a figure on either side. The columns SHALL be:
- code and item;
- prior approved;
- the tool's new year;
- the median reference (VND per year for this project's NFA or lifts, blank when the code has none);
- the difference and the difference in %.

Rows in the warranty or left for the PM SHALL be tagged. The section SHALL show the fund totals. A Review whose file
has no sinking fund SHALL show the section with the line "file không có quỹ bảo trì".

#### Scenario: Line far from the median

- **WHEN** a code's new year is more than twice its median reference
- **THEN** the row SHALL be tagged "cao hơn trung vị"
