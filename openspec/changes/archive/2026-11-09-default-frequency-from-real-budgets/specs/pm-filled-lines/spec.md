## MODIFIED Requirements

### Requirement: A line left for the PM is blank, shaded and says "PM điền"
On `2. Budget-Management Fund`, a line left for the PM SHALL have its unit-price cell (column F) and its twelve month
cells (columns H–S) empty — no 0 typed in — or linked to the adjustment sheet so they show nothing until the PM types
a figure; those cells SHALL be shaded light yellow; its remark (column T) SHALL read "PM điền: <reason>", in
Vietnamese, with no "Để ở mức 0" wording. Its annual total, `1. Summary` and the contingency lines SHALL read the
empty cells as 0 VND and SHALL show no Excel error. A zero line (kind C) SHALL keep 0 VND and "Để ở mức 0: <reason>".

A line left for the PM whose code has a cyclic default frequency (`Ref_LineFrequency.csv`, for example ESC4 Yearly)
SHALL carry that frequency and its months of payment: the month cells of the paid months show the month, as on any
cyclic row of the form, and are not shaded; F stays empty and shaded. When the PM types an annual figure on sheet
`4. Điều chỉnh`, the line SHALL be paid at the table's times (Yearly: the whole figure once, in T1) and G SHALL equal
the figure. When that figure is saved on the web, the remark SHALL end with the frequency sentence.

#### Scenario: Blank line on the fund sheet
- **WHEN** the deliverable is opened in Excel after a run where ESM6 is left for the PM
- **THEN** F and H–S of the ESM6 row show nothing and are shaded light yellow, G shows 0 or "-", T reads
  "PM điền: Chưa có phương pháp định giá được ghi nhận." and no cell on the row or on `1. Summary` shows an error

#### Scenario: A yearly line left for the PM
- **WHEN** ESC4 is left for the PM and the table lists ESC4 as Yearly
- **THEN** the ESC4 row reads Yearly, its T1 cell shows the first month of the period, F is empty and shaded, G is 0
- **AND** after the PM types 24,000,000 VND on sheet 4 and saves on the web, G reads 24,000,000 VND, F reads
  24,000,000 VND per time and the remark ends with "Hàng năm, 1 lần/năm × 24,000,000 VND/lần, chi vào T1"

#### Scenario: Summary still ties
- **WHEN** verification compares `1. Summary` with its detail sheets on that run
- **THEN** they agree to the VND, as before this change

### Requirement: Verification confirms the lines left for the PM
On every sample run, verification SHALL confirm that each line left for the PM is blank in F and H–S (or linked and
showing nothing, or showing only the months of payment of a cyclic frequency), shaded, carries a "PM điền:" remark and
has a row on sheet `4. Điều chỉnh`; that no zero line (kind C) carries "PM điền"; and that no remark on the deliverable
still starts "Để ở mức 0" for a line of kind A or B. In Excel, it SHALL confirm that the line totals 0 VND before
typing and that typing 24,000,000 VND on sheet 4 gives an annual total (G) of 24,000,000 VND with no error, for a
Monthly and for a cyclic line. A failure SHALL name the code and what is wrong.

#### Scenario: A line typed as 0
- **WHEN** a writer types 0 into the month cells of a line left for the PM
- **THEN** verification fails naming that code and "ô có số 0, phải để trống"

#### Scenario: A cyclic line left for the PM
- **WHEN** ESC4 is left for the PM as Yearly and verification types 24,000,000 VND on its sheet-4 row
- **THEN** verification reads G = 24,000,000 VND on the ESC4 row and passes
