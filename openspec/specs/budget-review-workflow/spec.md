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
