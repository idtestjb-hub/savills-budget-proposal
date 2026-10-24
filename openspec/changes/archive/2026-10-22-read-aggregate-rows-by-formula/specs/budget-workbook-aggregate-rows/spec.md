## Purpose

How a real Savills budget workbook's coded rows are split into leaf lines and aggregate rows, and how a sheet's leaf
sum is tied to its own R and E rows, including the two cases where the file's own total cell is explained rather than
equal. Budget Review and the real-budget scan store both read workbooks by these rules.

## ADDED Requirements

### Requirement: Aggregate rows are recognised by the formula in the cell

A coded row between the sheet's R and PL1 rows SHALL be an aggregate row when its cell in the value column holds a
`SUBTOTAL(...)` or `SUM(...)` formula, written as a normal or an array formula, whose cell range covers at least one
other coded row of the same column. The coded rows inside the range SHALL be its children. An aggregate row SHALL
never be counted in a section total, and its cached value SHALL NOT be used, whatever its code prefix and whatever
the cached value is (including 0).

A coded row that is not an aggregate by formula (a typed-in number, or a formula of another shape such as
`=AK48+AK49`) SHALL be dropped only when the rows that share its code prefix add up exactly (within 1 VND) to it, as
before. Any other coded row without an indicator SHALL be a leaf line.
The rows the form marks with an indicator (section heads) SHALL keep their existing rules.

Data files read: the workbook being read (formulas and Excel's cached values). Data files written: none. No recorded
baseline figure moves by this requirement alone.

#### Scenario: A SUBTOTAL that spans a sibling code

- **WHEN** `RO4` holds `=SUBTOTAL(9,AK48:AK55)` and rows 48 to 55 are `RO4.A` … `RO4.L` and `RO5`
- **THEN** `RO4` SHALL be an aggregate row and SHALL NOT be counted
- **AND** `RO4.A` … `RO4.L` and `RO5` SHALL each be counted once

#### Scenario: An aggregate whose cached value is 0

- **WHEN** an aggregate row's cell caches 0 because a filter hid its children when the file was saved
- **THEN** the row SHALL still be an aggregate row, and its children SHALL be counted with their own values

#### Scenario: A typed-in parent

- **WHEN** `ERM` holds the number 120,000,000 VND, has no formula, and `ERM.1` + `ERM.2` = 120,000,000 VND
- **THEN** `ERM` SHALL NOT be counted

#### Scenario: A formula that adds no coded row

- **WHEN** a coded row holds `=AK40*12` or a `SUM` over cells of non-coded rows only
- **THEN** the row SHALL be a leaf line with its cached value

### Requirement: A sheet's leaf sum ties to its own R and E rows, directly or after explanation

For each section R and E, the leaf sum SHALL be compared with the sheet's own section row in the value column, within
1 VND. The tie states are:
- **direct tie**: the two are equal.
- **tie after a filter**: they differ, the sheet has rows hidden by a filter, and recomputing the section row the
  way `SUBTOTAL` does gives the cached figure. That recomputation leaves out leaf lines on hidden rows and counts
  the double-counted rows below. Note: "ô tổng bị bộ lọc che (N dòng ẩn)", where N is the number of hidden rows
  between R and PL1.
- **tie after a double count**: they differ, and adding to the leaf sum the value of every row not counted here that
  the file's `SUBTOTAL` still counts gives the cached figure. Those rows are an aggregate row written with `SUM`, and
  a parent dropped by the prefix rule whose cell is not a `SUBTOTAL` (the same figure entered in the parent and its
  children). One note per such row: "lỗi file: <mã> dùng SUM, tổng của file cộng trùng <số> VND" for a `SUM`
  aggregate, "lỗi file: <mã> trùng số với dòng con, tổng của file cộng trùng <số> VND" for a parent.
- **no tie**: none of the above holds. Note: the difference per section.

A file whose hidden rows and double-counted rows both apply SHALL get both notes when the combined recomputation matches.
The file's own figures SHALL never be changed. The leaf lines and their sum SHALL be the same in every state. A tie
after explanation SHALL count as tying wherever a tying sheet is required.

Data files read: the workbook being read. Data files written: none.

#### Scenario: A file saved with a filter

- **WHEN** a Management Fund sheet hides 699 of its 706 rows with a filter and its R and E cells cache only the visible
  leaf lines
- **THEN** the sheet SHALL tie after a filter, with the note "ô tổng bị bộ lọc che (699 dòng ẩn)"
- **AND** the leaf lines SHALL carry their full values, hidden or not

#### Scenario: A parent written with SUM

- **WHEN** `RO2` = `SUM(AI37:AI38)` = 1,820,000 VND and the sheet's R row is a `SUBTOTAL` over the whole section
- **THEN** the leaf sum SHALL be 1,820,000 VND below the R row
- **AND** the sheet SHALL tie after a double count, with the note "lỗi file: RO2 dùng SUM, tổng của file cộng trùng
  1,820,000 VND"

#### Scenario: A parent that carries its children's figure

- **WHEN** `RO2` and `RO2a` each hold 1,820,000 VND (each the sum of its own months), `RO2b` holds 0, and the R row is
  a `SUBTOTAL` over the whole section
- **THEN** `RO2` SHALL NOT be counted, and the leaf sum SHALL be 1,820,000 VND below the R row
- **AND** the sheet SHALL tie after a double count, with the note "lỗi file: RO2 trùng số với dòng con, tổng của file
  cộng trùng 1,820,000 VND"

#### Scenario: A gap nothing explains

- **WHEN** the leaf sum differs from the E row and neither recomputation gives the cached E figure
- **THEN** the sheet SHALL NOT tie, and the note SHALL give the difference for E
