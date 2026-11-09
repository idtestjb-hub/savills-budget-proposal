## ADDED Requirements

### Requirement: The adjust table shows the difference against the approved figure and can sort by it
On a Review run the adjust table SHALL show, beside "Duyệt", the column "Chênh so với duyệt" = the tool's original
amount minus the approved figure (VND) and its % of the approved figure ("N/A" when the approved figure is 0),
both before any edit, and SHALL keep them fixed while the PM edits. A control "Thứ tự" SHALL switch between the form
order (default) and "lệch lớn nhất": codes within a group sorted by the absolute difference, largest first, and
groups by their largest member; subtotal rows SHALL stay correct in both orders. The codes of the Review's "10
dòng lệch lớn nhất" SHALL carry a mark "Top 10" beside the code. A new-project run SHALL show neither the column
nor the control.

#### Scenario: Largest first
- **WHEN** the PM picks "lệch lớn nhất" on the CITY GARDEN review
- **THEN** ESS1 (−3,406.6 triệu VND against approved) and ESS38 (−3,175.2 triệu VND) are the first two codes under
  Chi, each marked "Top 10", and the "Cộng ESS" row still equals the sum of its codes

#### Scenario: Zero row on the table
- **WHEN** the table lists ESS38 (tool 0, approved 3,175.2 triệu VND)
- **THEN** the row shows "Thành tiền gốc" 0, "Duyệt" 3,175.2 triệu VND, "Chênh so với duyệt" −3,175.2 triệu VND and
  −100%, and offers the type "Nhập số"

### Requirement: The web applies "Nhập số" like Excel does
The adjust table SHALL offer "Nhập số" on every code with detail rows. Under that type the detail row's "Đơn giá
mới" cell SHALL be labelled "Số nhập (VND/năm)", the preview's new amount SHALL be that figure per row, a negative
figure SHALL be refused, and saving SHALL write the type to column D and the figure to column K, nothing else.

#### Scenario: Preview and save
- **WHEN** the PM picks "Nhập số" on a zero row, types 240,000,000 and saves
- **THEN** the preview showed +240,000,000 for the code, the deliverable's column D reads "Nhập số", column K of
  the detail row 240,000,000, and after Excel recalculates the fund's E grows by 240,000,000 plus the contingency
  that follows
