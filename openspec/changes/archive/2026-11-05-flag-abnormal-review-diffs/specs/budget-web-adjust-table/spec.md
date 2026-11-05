## ADDED Requirements

### Requirement: The adjust table marks abnormal differences and can show only them
On a Review run the adjust table SHALL mark every code the Review flagged abnormal with a tag "Bất thường" beside the
code and a light-red fill on its "Chênh so với duyệt" and "% so với duyệt" cells, SHALL offer a filter "Chỉ dòng bất
thường", and SHALL state the number of abnormal codes among the visible ones on the THU and CHI header rows. The flags
SHALL come from the run's `review_summary.json`; for a run recorded before the rule existed the server SHALL compute
them from the table's own "Thành tiền gốc" minus "Duyệt" with the same rule, for codes that have an approved figure. A
new-project run SHALL show neither the tag nor the filter.

#### Scenario: Filter to the flagged codes
- **WHEN** the PM ticks "Chỉ dòng bất thường" on a Review run with 12 flagged codes
- **THEN** the table lists exactly those 12 codes under their groups, each tagged, and the "Cộng" rows sum them

#### Scenario: An old run
- **WHEN** the PM opens the adjust table of a Review run whose summary file has no `abnormal` list
- **THEN** a code with approved 100,000,000 VND and original amount 0 is tagged, a code with approved 2,592,000,000 VND
  and original amount 2,400,000,000 VND is not

### Requirement: The zero-tool codes are hidden until asked for
On a Review run the adjust table SHALL hide, when it opens, every code whose original amount is 0 (`zero_row`) unless
that code is flagged abnormal, and SHALL offer a toolbar button "Mã công cụ ra 0" that shows all of them and, pressed
again, hides them again. The button SHALL show how many codes it is hiding; it SHALL be absent when the run has no such
code. The THU and CHI header rows SHALL state how many zero-tool codes are hidden. Hiding SHALL change nothing in the
deliverable's sheet `4. Điều chỉnh`, which keeps every row.

#### Scenario: Default view
- **WHEN** the PM opens the adjust table of a Review run with 102 zero-tool codes of which 60 are abnormal
- **THEN** the table shows the 60 abnormal zero-tool codes and every priced code, the button reads "Mã công cụ ra 0
  (42 đang ẩn)" and the CHI header row states "42 mã công cụ ra 0 đang ẩn"

#### Scenario: Show them
- **WHEN** the PM presses the button
- **THEN** all 102 zero-tool codes are listed in their groups and the button offers to hide them again
