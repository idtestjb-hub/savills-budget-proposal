# budget-review-workflow Specification

## Purpose

Budget Review of an operating project, the second function of the tool beside Budget Propose: one command (`review.py`) reads last year's approved budget workbook by line code, fills the Existing-project form from it, runs both generators in an isolated folder, and adds a `Review` sheet to the internal analysis that sets each approved figure beside the tool's figure with two ties (change `add-budget-renewal-mode`, MVP signed off 2026-10-20). Carrying every line forward with a reason code is a later change.

## Requirements

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

### Requirement: The project's scale is read from the file's Info sheet

The import SHALL read from the file's `0. Info` sheet the fee-paying area (NFA) and the number of units of each of the
nine products the form carries, the motorbike and car parking bay counts, and the applied management-fee rate per
product with its VAT basis. A fact the file does not carry SHALL stay blank on the form and SHALL be listed in the
import notes; an optional facts file (JSON of label to value) SHALL fill such a field and SHALL be recorded in the
notes with its source text. The import SHALL never invent a scale figure.

#### Scenario: Products and parking from the Info sheet
- **WHEN** `0. Info` has an Apartment row with NFA 101,050 m² and 927 units and a motorbike parking row with 739 bays
- **THEN** `Project Info` SHALL carry Apartment NFA 101,050, 927 units and 739 motorbike bays

#### Scenario: A fact not in the file
- **WHEN** the file has no tower count and no facts file gives one
- **THEN** `Tower Count` SHALL stay blank
- **AND** the import notes SHALL list `Tower Count` as left for the PM

### Requirement: The import fills the Existing-project form

The import SHALL write a filled input form in Existing-project mode into the work folder (a fresh form from the form
builder, or a dated copy of the form the user names; the original is never changed): `Project Mode` = Existing
project, `Prior Budget Year` = the file's budget year, `Budget Start Month` = the first month of the file's period
plus twelve months, the `STAFF LINES` block of `Prior-Year Roster` with the approved EMH2, EMH3 and EMH4 of the
Management Fund sheet, the `UTILITY LINES` block of `Prior-Year Utilities` with the approved EEE.C and EEW.C and the
file's VAT basis, and a new sheet `Prior-Year Budget` with one row per line read (fund sheet, section, code, item,
approved figure, VAT basis, twelve months, source sheet, source row, remark) and an `IMPORT NOTES` block. The
generators SHALL NOT read `Prior-Year Budget`.

#### Scenario: Staff and utility baselines from the file
- **WHEN** the Management Fund sheet carries EMH2 13,555,630,260 and EEE.C 6,264,440,940 VND/year, ex-VAT
- **THEN** `STAFF LINES` SHALL carry EMH2 13,555,630,260 as the prior-year approved amount
- **AND** `UTILITY LINES` SHALL carry EEE.C 6,264,440,940 with "Approved Includes VAT" = No

#### Scenario: The form the user names is not changed
- **WHEN** the user passes `--input` with a filled form
- **THEN** the import SHALL write a dated copy in the work folder
- **AND** the bytes of the named form SHALL be unchanged

### Requirement: The Review sheet sets the approved figure beside the tool's figure

After the pipeline has run, the tool SHALL add a sheet `Review` at the end of the analysis workbook with: a header
(file read, sheets, period, VAT bases, counts of lines read, lines with a figure, codes not on the form, lines
unreadable); a summary of the Management Fund's revenue, expense and surplus, approved vs tool, difference and %;
and, per fund sheet and section, one row per code with the Vietnamese item name, the approved figure as read, the VAT
factor, the approved figure on the deliverable's basis, the tool's figure, the difference in VND and in %, how the tool
got its figure, and a remark, with a subtotal per section and a total per fund sheet. The approved figure SHALL be
converted to the deliverable's VAT basis per line (no VAT on salary, tax and fee, bank fee and bank interest lines; the
reduced rate in its dated periods; 10% otherwise) only when the two bases differ, and the sheet SHALL show the figure
as read, the factor and the converted figure. A code repeated on one side SHALL be summed; a line with a figure and no
code SHALL be one "(không mã)" row per section.

#### Scenario: A line present on both sides
- **WHEN** the file carries EEE.C 6,264,440,940 ex-VAT over twelve months of 2026 and the deliverable is inclusive
- **THEN** the row SHALL show 6,264,440,940 as read, the factor 1.08, 6,765,596,215 converted, the tool's figure, the
  difference and %, and "Mang sang theo biểu giá"

#### Scenario: A salary line is not converted
- **WHEN** EMH2 is read ex-VAT and the deliverable is inclusive
- **THEN** the factor SHALL be 1.00 and the converted figure SHALL equal the figure as read

#### Scenario: The approved line has a figure and the tool none
- **WHEN** the file carries a figure on a code the tool has no method for
- **THEN** the tool column SHALL be 0, the label SHALL be "Chưa có phương pháp", and the approved figure SHALL NOT be
  copied into the tool column

#### Scenario: How the tool got its figure
- **WHEN** the project runs in Existing-project mode
- **THEN** EMH2, EMH3 and EMH4 SHALL be labelled "Mang sang theo luật", EEE.C and EEW.C "Mang sang theo biểu giá", a
  management-fee row of a product with an entered rate "PM nhập", and every other line with a figure "Ước lượng:"
  followed by the catalogue's method in Vietnamese

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

### Requirement: One command, isolated from the live files

`python review.py <file> [--input form] [--facts json] [--workdir dir]` SHALL perform the import, run both generators
and build the Review sheet inside the work folder, SHALL never write to the live `reports/` input, output or roster or
to `sample_output/`, and SHALL print the summary (totals, the ten largest differences by VND, the counts) and write
`review_summary.md` and `review_summary.json` in the work folder.

#### Scenario: A full run
- **WHEN** the command runs with a readable file and Excel is installed
- **THEN** the work folder SHALL hold the filled form, the deliverable, the roster, the analysis workbook with the
  Review sheet, and the two summary files
- **AND** the live `reports/Project_Budget_Input.xlsx`, `Project_Budget_Output.xlsx` and `Roster_Demand_Model.xlsx`
  SHALL be byte-for-byte unchanged

#### Scenario: Excel is not available
- **WHEN** Excel cannot be started
- **THEN** the command SHALL stop after the pipeline, say that the Review sheet needs Excel, and leave the three
  workbooks in the work folder

### Requirement: New-prospect mode is unchanged

In "New prospect" mode the tool SHALL produce exactly the workbooks it produced before this change. No generator reads
the `Prior-Year Budget` sheet.

#### Scenario: The standard sample and the five fixtures
- **WHEN** the standard sample and the fixtures `Sample_Existing_Input`, `Sample_Existing_Lump_Input`,
  `Sample_Operating_Input`, `Sample_Villa_Input` and `Sample_Project_Input` are run before and after this change
- **THEN** every cell of every sheet that existed before SHALL be identical

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
