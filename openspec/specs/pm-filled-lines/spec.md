# pm-filled-lines Specification

## Purpose
Decide which budget lines the tool leaves for the PM to fill, how such a line looks on the client deliverable, and
how verification confirms it, so a line the tool could not price is never read as a cost of 0 VND.

## Requirements

### Requirement: Every line the generator leaves at zero has a kind
Every line the generator leaves at 0 VND on `2. Budget-Management Fund` with a stated reason SHALL be one of three
kinds, decided where the reason is written:
- **A. No pricing method**: RP3, EMB1, EMO6, ESC4, ESS10, ESS17, ESS18, ESS19, ESM6, ESM7, ESM9, ESM10, ESM12,
  ESM13, ESR, ERCS1;
- **B. A method exists but this project's input is missing**: EMH1 with neither Savills fee field filled; ESI1 with
  no insured asset value entered (blank, not 0); EMH3 on an existing project with no duty roster and no approved
  prior figure; a real-budget range code (EMB4, ESC1, ESC2, ESC5, ESS7, ESS12, ESS23) when fewer than 10 real
  budgets carry it, the values file is missing, or the project has no fee-bearing NFA;
- **C. Genuinely 0 for this project**: every other stated zero, among them no pool, no tower, in-house pool staff, a
  lump staff budget, no night-shift position on a new project, EMO2, a 0 % contingency rate, and a value the PM
  entered as 0 (ESI1, ESI2).
Kinds A and B are "lines left for the PM"; kind C is a "zero line".

#### Scenario: A no-method code
- **WHEN** the deliverable is generated for any project
- **THEN** ESM6 is a line left for the PM with the reason "Chưa có phương pháp định giá được ghi nhận."

#### Scenario: A range code with too few budgets
- **WHEN** only 6 real budgets carry ESC2
- **THEN** ESC2 is a line left for the PM, and its reason states that only 6 budgets carry the line

#### Scenario: A pool code on a project without a pool
- **WHEN** the project has no pool
- **THEN** ESS23 is a zero line (kind C) and keeps "Để ở mức 0: dự án không có hồ bơi…"

#### Scenario: Insured value entered as 0
- **WHEN** the PM entered 0 as the insured asset value
- **THEN** ESI1 is a zero line (kind C); left blank, it is a line left for the PM

### Requirement: A line left for the PM is blank, shaded and says "PM điền"
On `2. Budget-Management Fund`, a line left for the PM SHALL have its unit-price cell (column F) and its twelve month
cells (columns H–S) empty — no 0 typed in — or linked to the adjustment sheet so they show nothing until the PM types
a figure; those cells SHALL be shaded light yellow; its remark (column T) SHALL read "PM điền: <reason>", in
Vietnamese, with no "Để ở mức 0" wording. Its annual total, `1. Summary` and the contingency lines SHALL read the
empty cells as 0 VND and SHALL show no Excel error. A zero line (kind C) SHALL keep 0 VND and "Để ở mức 0: <reason>".

#### Scenario: Blank line on the fund sheet
- **WHEN** the deliverable is opened in Excel after a run where ESM6 is left for the PM
- **THEN** F and H–S of the ESM6 row show nothing and are shaded light yellow, G shows 0 or "-", T reads
  "PM điền: Chưa có phương pháp định giá được ghi nhận." and no cell on the row or on `1. Summary` shows an error

#### Scenario: Summary still ties
- **WHEN** verification compares `1. Summary` with its detail sheets on that run
- **THEN** they agree to the VND, as before this change

### Requirement: The internal analysis lists the lines left for the PM
The internal analysis workbook SHALL list every line left for the PM in the run: code, item name, kind (A or B) and
reason in Vietnamese, in form order, with the count. The list SHALL be empty, with a sentence saying so, when the run
has none.

#### Scenario: Listed
- **WHEN** a run leaves 18 lines for the PM
- **THEN** the analysis shows those 18 lines with their kind and reason and states "18 dòng chờ PM điền"

### Requirement: Verification confirms the lines left for the PM
On every sample run, verification SHALL confirm that each line left for the PM is blank in F and H–S (or linked and
showing nothing), shaded, carries a "PM điền:" remark and has a row on sheet `4. Điều chỉnh`; that no zero line
(kind C) carries "PM điền"; and that no remark on the deliverable still starts "Để ở mức 0" for a line of kind A or B.
A failure SHALL name the code and what is wrong.

#### Scenario: A line typed as 0
- **WHEN** a writer types 0 into the month cells of a line left for the PM
- **THEN** verification fails naming that code and "ô có số 0, phải để trống"
