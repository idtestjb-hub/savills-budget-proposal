## MODIFIED Requirements

### Requirement: Last year's approved budget is read by line code

The tool SHALL read an approved budget workbook on the Savills form (2026 or 2027 layout) and return, for the
Management Fund budget sheet and the Common area Fund sheet, every leaf line of sections R and E: the code, the item
text, the approved annual figure from the year column, the twelve monthly figures, the sheet's VAT basis, the source
sheet and row, and the line's remark. The reader SHALL find the code column, the indicator column, the R, E, PL1 and
PL2 rows, the value column and the month columns by their content and headers, never by fixed addresses. The reader
SHALL read only budget sheets of the two funds: report, scenario, pre-opening and year-2 sheets are not read.

Leaf lines and aggregate rows SHALL be told apart by the rules of `budget-workbook-aggregate-rows`. A sheet that ties
after explanation SHALL be read as a tying sheet, and its note SHALL be listed in the import notes.

When the template's own sheet name is absent and more than one sheet of a fund qualifies, a visible sheet SHALL be
chosen before a hidden one.

A year column SHALL tie only when its R and E section figures equal the sheet's own R and E rows. A column whose R
figure is 0 SHALL NOT be chosen when another column of the same sheet carries a non-zero R that ties.

Data files read: the workbook the user names. Data files written: a stripped copy of that workbook in the work folder
when openpyxl cannot open the original. No recorded baseline figure moves.

#### Scenario: A workbook on the form
- **WHEN** the workbook has a Management Fund budget sheet with code column Y and a year column that ties to its own R
  and E rows
- **THEN** every leaf line of sections R and E SHALL be returned with its annual figure and twelve months
- **AND** the section totals of the lines returned SHALL equal the sheet's own R and E rows within 1 VND

#### Scenario: The year column and the twelve months disagree
- **WHEN** a line's twelve months sum to a figure more than 1 VND away from its year column
- **THEN** the year column SHALL be the approved figure
- **AND** the line SHALL carry the flag "12 tháng không khớp cột năm"

#### Scenario: A file that cannot be read
- **WHEN** the file is a PDF, an xlsb, or a workbook with no fund sheet
- **THEN** the command SHALL stop with a message naming the file and the reason
- **AND** nothing SHALL be written

#### Scenario: A code the 2027 form does not carry
- **WHEN** a line's code is not on the same fund sheet of the 2027 template
- **THEN** the line SHALL still be returned with its figure
- **AND** it SHALL be listed in the import notes as not on the 2027 form

#### Scenario: A SUBTOTAL that spans a sibling code
- **WHEN** the approved budget's `RO4` is a `SUBTOTAL` over `RO4.A` … `RO4.L` and `RO5`
- **THEN** `RO4` SHALL NOT be returned as a line, and `RO5` SHALL be returned once

#### Scenario: A file saved with a filter
- **WHEN** the Management Fund sheet ties only after a filter
- **THEN** every leaf line SHALL be returned with its value
- **AND** the import notes SHALL carry "ô tổng bị bộ lọc che (N dòng ẩn)"

#### Scenario: A visible sheet beside hidden scenario sheets
- **WHEN** the workbook has a hidden `2. Budget-Management Fund (OP3)` and a visible `2. Budget-THCN`, and no sheet
  named as in the template
- **THEN** `2. Budget-THCN` SHALL be read

#### Scenario: A column with no revenue
- **WHEN** one column ties with R = 0 and E equal to the E row, and another column ties with a non-zero R
- **THEN** the column with the non-zero R SHALL be the year column

### Requirement: The Review sheet ties to the deliverable and to the source file

The tool column's totals per section SHALL equal the deliverable's own R and E rows of the same fund sheet, after
Excel recalculates the deliverable, within 1 VND. The approved column's totals per section (as read, before VAT
conversion) SHALL equal the source file's own R and E rows within 1 VND, or the sheet SHALL tie after explanation
(`budget-workbook-aggregate-rows`). The command SHALL print both ties, with the explanation note where there is one,
and SHALL exit non-zero, naming the sheet, section and difference, when either fails. The Review sheet SHALL still
be written.

#### Scenario: Both ties hold
- **WHEN** the command runs on a file whose fund sheets tie to their own totals
- **THEN** the printed summary SHALL show four ties (two sheets, R and E) with difference 0
- **AND** the exit code SHALL be 0

#### Scenario: The source file does not tie
- **WHEN** the file's Management Fund sheet has leaf sums that differ from its own E row and nothing explains the gap
- **THEN** the command SHALL print the difference and exit non-zero
- **AND** the Review sheet SHALL be written with the lines read

#### Scenario: The source file ties after explanation
- **WHEN** the file's Management Fund R row differs from the leaf sum by a row the file counts twice
- **THEN** the printed summary SHALL show the R tie as held, with that row's note (for example "lỗi file: <mã> trùng số
  với dòng con, tổng của file cộng trùng <số> VND")
- **AND** the exit code SHALL be 0 when the tool column also ties
