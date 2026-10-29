## ADDED Requirements

### Requirement: Files the Review reader cannot read are not selectable
A store file whose row in `prior_coverage.csv` has status `error` SHALL NOT be selectable on the Review tab; its
reason SHALL be "Review chưa đọc được file này (sheet quỹ quản lý khác form chuẩn, ví dụ ngân sách nhiều giai đoạn)"
and its reason kind `review_unread`. A missing `prior_coverage.csv` SHALL leave every file as it is today.
`build_prior_coverage.py` SHALL measure over the files that are selectable without this rule.

#### Scenario: Unreadable file
- **WHEN** `prior_coverage.csv` gives status `error` for file `x`
- **THEN** `/api/library` lists `x` as not selectable with reason kind `review_unread`, and the Kho tab counts it
  under "Không chọn được"

#### Scenario: Next coverage build
- **WHEN** `build_prior_coverage.py` runs after `x` was marked unreadable
- **THEN** `x` is measured again and stays in `prior_coverage.csv`
