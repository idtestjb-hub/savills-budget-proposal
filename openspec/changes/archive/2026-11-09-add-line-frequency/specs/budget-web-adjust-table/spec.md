## ADDED Requirements

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
