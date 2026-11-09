# budget-web-adjust-table Specification

## Purpose
How the Budget web's adjust table stays readable on a normal screen: the unit column, the pinned code and item columns
and header, the toggles that hide the prior-year and Remark column groups (remembered on the PC), and full screen.

## Requirements

### Requirement: The adjust table shows the unit and keeps its code in sight

The web adjust table SHALL show, on each code row after Hạng mục, a column ĐVT: the unit of the code's detail rows when
they share one, "nhiều" with the units listed on hover when they differ, blank when the code has no detail row. The
year N-1 column headers SHALL be short and wrap (Duyệt <year>, Thực tế <period>, Dự kiến <year>) with the full label on
hover. The selection box, the +/- button, Mã and Hạng mục SHALL stay visible on the left while the table scrolls
sideways, and the header row SHALL stay visible while it scrolls down; the table SHALL scroll inside a box no taller
than the window so its horizontal scrollbar is on screen. No figure, saved value or file SHALL change.

#### Scenario: A code with several units
- **WHEN** a code's detail rows are in "người" and "vị trí"
- **THEN** its ĐVT cell SHALL read "nhiều" and list both units on hover

#### Scenario: Scrolling to the right
- **WHEN** the PM scrolls the table to the Remark column
- **THEN** Mã and Hạng mục of every row SHALL still be visible on the left

### Requirement: The PM can hide column groups and open the table full screen

The page SHALL offer buttons to hide or show the year N-1 columns and the Remark column; the choice SHALL be remembered
in the browser of that PC. A full-screen button SHALL open the adjust table and its tools over the whole window; Esc or
the same button SHALL close it. Hidden columns SHALL keep their values: hiding Remark SHALL NOT clear or skip a remark
when saving.

#### Scenario: Remark hidden, then saved
- **WHEN** the PM types a remark, hides the Remark column and saves
- **THEN** the remark SHALL be saved as if the column were shown

#### Scenario: Full screen
- **WHEN** the PM presses the full-screen button and then Esc
- **THEN** the table SHALL fill the window and then return to its place on the page with its edits kept

### Requirement: The adjust table is grouped as on the 2027 form
Within Thu and Chi, the adjust table SHALL list the codes by fund (MF before CA) and template row, nested in every
level of the form's groups as the Review sheet nests them (`review_import.group_chain`); a code not on the form SHALL
sit in a group "Mã ngoài form 2027". Each group SHALL have a row "Cộng <mã> · <tên>" above its codes whose money
columns equal the sum of the codes of that group shown on the table, refreshed while the PM edits. A group row SHALL
fold and unfold its codes and subgroups; all groups start open. Grouping SHALL NOT change any saved value.

#### Scenario: Subtotals tie
- **WHEN** a Review run's adjust table is shown
- **THEN** each "Cộng" row equals the sum of its direct subgroups and codes, and the Chi row equals the sum of its top-level groups

#### Scenario: Fold a group
- **WHEN** the PM folds "Cộng EM"
- **THEN** its codes and subgroups are hidden, its own row and figures stay, and unfolding shows them again

#### Scenario: Edit updates the group
- **WHEN** the PM sets an inflation of 10% on a code of group ESS
- **THEN** the "Cộng ESS" row's new amount and difference grow by that code's change without reloading

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

### Requirement: The adjust table edits a code's frequency and its months

The web adjust table SHALL show on each code row, after Hạng mục and ĐVT, a column Tần suất with the code's current
frequency in Vietnamese and in the form's word ("Hàng tháng (Monthly)", "Hàng quý (Quarterly)", "6 tháng/lần (Half a
Year)", "Hàng năm (Yearly)", "Không theo chu kỳ (Optional)", "Theo lịch từng tháng (Schedule)") and the number of times
a year. The PM SHALL be able to change it on the code row:
- Quarterly, Half a Year, Yearly: a Tháng đầu list of the allowed T-months, each labelled with its month and year in
  the budget period (for example "T3 · 03/2027"), and the resulting months shown under the row;
- Optional: 12 month boxes to tick, the count shown as the number of times (1 to 11);
- Schedule: 12 amount cells in VND, pre-filled with the code's current month spread.

The preview of Thành tiền mới and Chênh lệch SHALL apply the rule of requirement "The frequency of a budget code is set
on its total row" and SHALL equal the Excel figures after recalculation. The web SHALL refuse, writing nothing, an
Optional with no month or with 12 months ("chọn Hàng tháng khi chi đủ 12 tháng"), a first month out of range, and a
negative Schedule amount. Saving SHALL write the cells to sheet 4; reopening the run SHALL show the saved frequency.

#### Scenario: Picking Quarterly
- **WHEN** the PM changes a Monthly code to "Hàng quý (Quarterly)" and picks "T3 · 03/2027"
- **THEN** the row SHALL show "chi vào T3, T6, T9, T12" and the new amount at 4 ÷ 12 of the adjusted annual amount
- **AND** after saving and reopening, the row SHALL show Quarterly and T3

#### Scenario: Optional with every month ticked
- **WHEN** the PM ticks all 12 months under Optional and saves
- **THEN** the web SHALL refuse with "chọn Hàng tháng khi chi đủ 12 tháng" and write nothing

#### Scenario: Switching to Schedule
- **WHEN** the PM picks Schedule on a code whose adjustment type is "Đơn giá"
- **THEN** the 12 amount cells SHALL open pre-filled with the current spread, the row SHALL say the adjustment type
  has no effect under Schedule, and the new amount SHALL be the sum of the 12 cells

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
