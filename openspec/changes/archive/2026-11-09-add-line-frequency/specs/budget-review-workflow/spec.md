## ADDED Requirements

### Requirement: A line added for a zero-tool code takes the code's default frequency

When a Budget Review adds a line to sheet `4. Điều chỉnh` for a code the tool priced at 0 but last year's approved
budget carries, that line SHALL take the code's default frequency from `Ref_LineFrequency.csv` (Monthly when the code
is not listed), not be forced to Monthly. A frequency the fund row already carries SHALL be kept. The PM SHALL be able
to change it like on any other line.

#### Scenario: A zero-tool code listed as Yearly
- **WHEN** a Review adds a line for a code the table lists as Yearly, first month T1
- **THEN** the line SHALL be listed with frequency Yearly, and when the PM types 12,000,000 VND under "Nhập số" the fund
  row SHALL read Yearly, 12,000,000 VND per time, paid in T1
