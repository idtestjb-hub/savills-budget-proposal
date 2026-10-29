## ADDED Requirements

### Requirement: The twelve months are the first run of twelve month columns
On a fund sheet the Review SHALL take as month columns the first run of twelve consecutive columns, to the right of
the year column and within 40 columns of it, whose header (rows 8–14) is the first day of a month or a `mm/yyyy` text.
When no run reaches twelve, it SHALL take the longest run (the first of equal length) and flag the number found.

#### Scenario: A remark with a month text before the months
- **WHEN** the column two to the right of the year column is Remarks with a cell "… 12/2025" in rows 8–14, and twelve
  month columns 01–12/2026 start four columns to the right
- **THEN** the months are 01–12/2026 and no month-count flag is raised

#### Scenario: Only eleven months
- **WHEN** the longest run of month columns has eleven columns
- **THEN** those eleven are taken and the flag says 11 month columns were found instead of 12

### Requirement: A full-year range of another year yields to the stated year
For an approved (N-1) or expected-year column, when the header states a year and its month range is exactly 01–12 of
one different year, the column's period SHALL be the stated year (how `header_year_over_range`), and the Review note
of the chosen column SHALL say the range is old template text. Any other range SHALL keep today's rule.

#### Scenario: Stale range
- **WHEN** an approved column is headed "Approved budget of Year 2025 (From 01.2023 to 12.2023)" in a 2026 file
- **THEN** its period is 01–12/2025, it can be chosen as Duyệt N-1, and the note mentions the old range

#### Scenario: Range that is not a full year
- **WHEN** an expected column is headed "Expected Year 2025 (From 08.2024 to 07.2025)"
- **THEN** its period is 08/2024–07/2025 as today

### Requirement: An error cell in the source remark becomes a reminder text
A remark cell whose value in the source is an Excel error code (`#NULL!`, `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`,
`#NUM!`, `#N/A`) SHALL be read as the text "(ghi chú trong file gốc là ô lỗi <code>)", so the Review sheet holds no
error cell from it.

#### Scenario: #REF! remark
- **WHEN** the remark of EN1 in the approved file is `#REF!`
- **THEN** the Review line's remark is "(ghi chú trong file gốc là ô lỗi #REF!)" and the cell is a text cell

### Requirement: Staff-cost, night-shift and break-even sheets are never the Management Fund sheet
The sheet-name rule SHALL NOT pick a sheet whose name contains "staff cost", "ca đêm", the word "hv" or "hòa vốn"
(a break-even scenario, not the approved budget) as a fund budget sheet. A workbook left without a Management Fund
sheet SHALL stop with the existing message listing its sheets; a workbook whose next candidate is not a fund sheet
SHALL stop with that sheet's reading error (and is then not selectable, see `library-overview`).

#### Scenario: Only staff-cost and scenario sheets
- **WHEN** the only sheets the name rule would take for MF are "2.1. Staff cost From Savills", "2. Budget-M Fund (N1)
  hv" and two "(N1) 100%" / "(9TN2) 100%" sheets of kind other
- **THEN** the Review stops with "no Management Fund budget sheet found" and the list of sheets
