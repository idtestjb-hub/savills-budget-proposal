## MODIFIED Requirements

### Requirement: The zero-tool codes are hidden until asked for
On a Review run the adjust table SHALL hide, when it opens, every code whose original amount is 0 (`zero_row`) unless
that code is flagged abnormal or is a line left for the PM, and SHALL offer a toolbar button "Mã công cụ ra 0" that
shows all of them and, pressed again, hides them again. A line left for the PM SHALL never be hidden by this button.
The button SHALL show how many codes it is hiding; it SHALL be absent when the run has no such code. The THU and CHI
header rows SHALL state how many zero-tool codes are hidden. Hiding SHALL change nothing in the deliverable's sheet
`4. Điều chỉnh`, which keeps every row.

#### Scenario: Default view
- **WHEN** the PM opens the adjust table of a Review run with 102 zero-tool codes of which 60 are abnormal and none is
  left for the PM
- **THEN** the table shows the 60 abnormal zero-tool codes and every priced code, the button reads "Mã công cụ ra 0
  (42 đang ẩn)" and the CHI header row states "42 mã công cụ ra 0 đang ẩn"

#### Scenario: Show them
- **WHEN** the PM presses the button
- **THEN** all 102 zero-tool codes are listed in their groups and the button offers to hide them again

#### Scenario: Lines left for the PM stay visible
- **WHEN** 18 of the zero-tool codes are lines left for the PM and the table opens
- **THEN** all 18 are shown whatever the button's state, and the button's count excludes them

## ADDED Requirements

### Requirement: The adjust table marks the lines left for the PM and counts the empty ones
On every run, the adjust table SHALL show each line left for the PM with a mark "PM điền" beside its code, its
reason as a tooltip or second line, an empty "Nhập số" figure, and "Thành tiền gốc" shown as empty rather than 0.
The toolbar SHALL state "N dòng chờ PM điền" counting the lines whose figure is still empty, and SHALL offer a filter
showing only those lines. Saving a figure for such a line SHALL write it to sheet `4. Điều chỉnh` the same way as any
"Nhập số" edit, and the line's remark on the fund sheet SHALL then read "Số do PM nhập: <figure> VND/năm. Công cụ không
tính được: <reason>".

#### Scenario: New project table
- **WHEN** the PM opens the adjust table after "Tạo ngân sách" with 18 lines left for the PM
- **THEN** 18 codes carry "PM điền", the toolbar reads "18 dòng chờ PM điền", and the filter shows only those 18

#### Scenario: PM fills one
- **WHEN** the PM types 24,000,000 VND for ESM6 and saves
- **THEN** the toolbar reads "17 dòng chờ PM điền", ESM6's months on `2. Budget-Management Fund` read 2,000,000 VND
  each, and its remark reads "Số do PM nhập: 24,000,000 VND/năm. Công cụ không tính được: Chưa có phương pháp định
  giá được ghi nhận."
