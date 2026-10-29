## ADDED Requirements

### Requirement: The file's own prior-year approved, actual and expected columns are read

A budget of year N is prepared during year N-1, so its file carries what was known of N-1 at that time. Besides the
approved figure of year N, the reader SHALL look on the two fund sheets it reads, and on their report sheets
(`2.1 Report-Management Fund`, `2.2.1 Report-Common area Fund`, or another report sheet of the same fund), for three
kinds of column of year N-1, recognised by the column's own header text with the form's head labels removed:
- **Duyệt N-1**: "Approved budget", "Ngân sách phê duyệt", "Ngân sách được duyệt";
- **Dự kiến cả năm N-1**: "Expected Report Year", "Báo cáo dự kiến", "Dự ước" (not "Total Expected From");
- **Thực tế lũy kế N-1**: "Total Actual", "Actual", "Thực tế", "Lũy kế", "YTD", "Thực chi", "Thực hiện", except headers
  that describe planned occurrences ("dự kiến thực hiện", "số lần thực hiện" and the like).

A column SHALL NOT be used when its header is a variance or % column, says "tham khảo" / "reference", is a template
sample ("AAA"), names another known project, gives no period, when it has no figure, or when an actual period ends
after the month the file was last saved. All three columns SHALL fall in year N-1 (for the actual: its period ends in
N-1; for the other two: the year with most of their months is N-1). A column of another year SHALL NOT be used and
SHALL be listed in the import notes. A cumulative actual without its own period SHALL end the month before the sheet's
"Total Expected From" column starts.

A column's period SHALL come from its own header before the month label of the column group around it (a date cell or
a "Tháng m/yyyy" label to its left, which can be the sheet's Starting Month): a month range or "from" month first; then,
for an approved or expected column, a year in the header gives January–December of that year even when the header also
writes a month in another style ("From 01,2024 to 12.2024"); for an actual column, a month in the header ("01/2025
Actual") gives that month and a year without a month gives the whole year. A header naming two years takes the last
one. Only a header without a year takes the group label.

When several columns of one kind qualify on one fund, the reader SHALL take, in order: one that ties to its own R and E
rows, one on a report sheet, one on a visible sheet, the one with more figures. Each column SHALL be read for every
leaf line the approved figure is read for (on the fund sheet: the same rows and aggregate-row rules; on a report sheet:
the same code within the same section), with the VAT basis of its sheet, and SHALL be tied to its own R and E rows; a
column that does not tie SHALL still be used and SHALL carry the flag "chưa khớp tổng" with the difference.

Data files read: only the approved workbook of year N. Data files written: none outside the run folder. No recorded
baseline figure moves.

#### Scenario: A 2026 file on the form
- **WHEN** the Management Fund sheet has "Approved budget of Year 2025", "Total Actual From 01/2025 to 09/2025" and
  "Expected Report Year 2025" columns that tie to its own R and E rows
- **THEN** the reader SHALL return them as Duyệt 2025, Thực tế 01–09/2025 (9 months) and Dự kiến 2025, with one figure
  per leaf line read

#### Scenario: A column of the wrong year
- **WHEN** a 2026 file's only approved column is headed "Approved budget of Year 2026"
- **THEN** no Duyệt N-1 column SHALL be returned
- **AND** the import notes SHALL say the column was left out because of its year

#### Scenario: An actual column without its own period
- **WHEN** a report sheet of a 2026 file has "Lũy kế" without dates and "Total Expected From 10/2025"
- **THEN** the actual column SHALL be read as 01/2025–09/2025, 9 months

#### Scenario: A year header under another year's group label
- **WHEN** a 2026 file's approved column is headed "Approved Budget of Year 2025 (From 01,2025 to 12.2025)" and the
  month label to its left reads 01/2026
- **THEN** the column SHALL be read as 2025, January–December, 12 months

#### Scenario: A file without the columns
- **WHEN** the file has no approved, actual or expected column of year N-1
- **THEN** the reader SHALL return none and the Review SHALL run as before

### Requirement: The Review shows N-1 approved, actual and expected beside N and N+1

The Review sheet SHALL show, per fund sheet, section and code, in this order: Duyệt N-1, Thực tế lũy kế N-1, Dự kiến
cả năm N-1, Duyệt N (the existing columns: as read, VAT factor, converted), Công cụ N+1 and the existing difference and
%; and three % columns: Duyệt N so Duyệt N-1, Dự kiến N-1 so Duyệt N-1, Duyệt N so Dự kiến N-1 (all on converted
figures). The three new figures SHALL be converted to the deliverable's VAT basis by the per-line rule used for Duyệt
N, on each column's own months. Headers SHALL name the actual years and, for the actual column, its period and month
count (for example "Thực tế 01–09/2025 (9 tháng)"). The actual column SHALL be shown as read, never annualised, and
SHALL NOT enter any % column. A % SHALL be blank when its base is 0 or missing.

A column the file does not carry SHALL be blank with the header note "File không có số …"; a column that does not
tie SHALL carry "(chưa khớp tổng, lệch X)" in its header and in the summary. The ties of the three columns SHALL be
printed with the others and SHALL NOT change the exit code. The summary block, the subtotals and totals, and
`review_summary.md` / `review_summary.json` SHALL carry the same figures. The Budget web SHALL show Duyệt N-1, Thực tế
lũy kế N-1 and Dự kiến cả năm N-1, and the three %, in the revenue / expense / surplus table, and the three figures in
the adjust table, only for the columns the run has.

No figure of the N+1 budget SHALL change. For a file without any of the three columns, the Duyệt N, tool, difference
and % figures, the ties and the exit code SHALL be identical to before this change.

#### Scenario: All three columns present
- **WHEN** a 2026 file carries Approved 2025, Total Actual 01–09/2025 and Expected Report Year 2025 on the Management
  Fund, all tying, and the tool builds 2027
- **THEN** each code row SHALL show Duyệt 2025, Thực tế 01–09/2025 (9 tháng), Dự kiến 2025, Duyệt 2026, Công cụ 2027
- **AND** the % columns SHALL be Duyệt 2026 so Duyệt 2025, Dự kiến 2025 so Duyệt 2025, Duyệt 2026 so Dự kiến 2025

#### Scenario: The expected column does not tie
- **WHEN** the Expected Report Year 2025 column's E leaf sum differs from its own E row by 12,000,000
- **THEN** the column SHALL be shown with "(chưa khớp tổng, lệch 12,000,000)"
- **AND** the exit code SHALL be that of the existing ties alone

#### Scenario: A rolling year
- **WHEN** the template moves to 2028 and the Review reads a 2027 file carrying Approved, Actual and Expected 2026
- **THEN** the columns SHALL read Duyệt 2026, Thực tế 2026, Dự kiến 2026, Duyệt 2027, Công cụ 2028 without any change
  of code

#### Scenario: No column in the file
- **WHEN** the file carries none of the three columns
- **THEN** the three columns and the three % SHALL be blank with "File không có số …"
- **AND** every existing figure, tie and the exit code SHALL be as before this change

### Requirement: Review lines are grouped as on the 2027 form, with a subtotal per group

The Review sheet SHALL place each line, within its fund and section, in the groups of the 2027 template, nested to
every level the template has. A line's groups SHALL be taken from the template's own SUBTOTAL ranges (the smallest
range that holds the line's row), never from the code's spelling. Each group with at least one shown line SHALL have
one summary row above its lines, reading "Cộng <group code>" and the template's group name, whose money columns are
`SUBTOTAL(9, …)` over the rows below it and whose % columns are recomputed on those sums; an N-1 column the file does
not carry SHALL stay blank on the summary row. The rows SHALL carry Excel outline levels by depth with the summary
row above, so each group can be folded. Codes not on the 2027 form SHALL stay in one block at the end of the section
with its own summary row "Cộng ngoài form". The section totals, the ties, the summaries, `review_summary.md` /
`review_summary.json` and the web tables SHALL NOT change, and the web SHALL NOT read a summary row as a line.

#### Scenario: Nested groups
- **WHEN** the Review shows EMH2 and ESS1 of the Management Fund
- **THEN** the rows SHALL read, in form order, "Cộng EM", "Cộng EMH", EMH2, …, "Cộng ES", "Cộng ESS", ESS1
- **AND** after Excel recalculates, each summary row SHALL equal the sum of its direct lines and sub-groups, and the
  top-level rows of a section SHALL add up to its "Tổng" row

#### Scenario: A code the form groups elsewhere than its spelling suggests
- **WHEN** the Review shows EM# (contingency), which the form's SUBTOTAL places in EM, after the EMO lines
- **THEN** EM# SHALL sit directly under "Cộng EM", not under "Cộng EMO"

#### Scenario: A code not on the form
- **WHEN** a line's code is not on the 2027 form
- **THEN** it SHALL sit in the block "Cộng ngoài form" at the end of its section, and still count in the section total
