## Purpose

Sets up the client deliverable's Management Fund sheet so it prints like an approved, signed budget: the right paper and
columns, only the lines in use, readable text, and a signature block for the people who propose and approve it.

Data: reads and writes only the generated deliverable (`sample_output/<project> - Sample Consulting Budget.xlsx` and
the web run's copy). No reference data file is read. No figure moves, so no recorded baseline changes.

## ADDED Requirements

### Requirement: The Management Fund sheet carries a ready A3 print setup
Sheet `2. Budget-Management Fund` of every generated deliverable SHALL carry this print setup:
- print area X2:BB526, from "No" to the 12th month column, from the title down to the signature dates;
- A3 paper, landscape, fitted to one page wide with as many pages tall as needed;
- rows 9:10 (the column headings) repeated at the top of every page;
- "Page x of y" centred in the footer.

Row 1 (helper column numbers) and columns A:W (the working area) SHALL NOT print.

#### Scenario: Setup present after generation
- **WHEN** a deliverable is generated
- **THEN** its Management Fund sheet has print area X2:BB526, A3 landscape paper, fit to 1 page wide, print titles
  rows 9:10 and a centred "Page &P of &N" footer

#### Scenario: Column BB is the 12th month, whatever the start month
- **WHEN** the budget starts in a month other than January
- **THEN** the print area still ends at column BB, whose heading is the 12th month of the budget period (for example
  Aug/2027 for a September start)

### Requirement: Lines not in use are hidden by the form's own rule
Coded rows SHALL be hidden when the form's column B rule marks them "Not Use":
- last year's approved monthly average is 0;
- there is no % change between this year's and last year's monthly averages (both are 0);
- there is no remark.

Top-level section rows SHALL always show, even when every figure is 0. These are the rows whose column X holds a PART
label, a letter A–D, or a roman numeral without a dot (I, II, … VII). Dotted sub-groups (I.1, II.4, V.33 and so on)
follow column B like any coded line. This matches the approved sample, which prints VI and VII at 0 but leaves out
empty sub-groups such as II.2 and V.1–V.32.

The check row under PART 3 (row 506) and the blank spacer rows 507–513 SHALL be hidden.

The column B filter SHALL be saved on the sheet over A12:AW505, so the PM can reapply it after changing figures.

Column B is worked out by Excel when the machine running the tool has it. Without Excel, a line whose inputs are
formulas SHALL stay visible.

#### Scenario: No Excel on the machine
- **WHEN** a deliverable is generated where Excel is not available
- **THEN** lines whose column B the tool cannot work out without Excel stay visible (none is hidden by mistake), and
  the run says so in one line

#### Scenario: Unused line hidden
- **WHEN** a coded line has no prior-year figure, no estimate and no remark
- **THEN** its row is hidden and does not print

#### Scenario: Line with a remark but no figure stays
- **WHEN** a coded line has all figures 0 but carries a remark
- **THEN** its row shows and prints

#### Scenario: Line with only a prior-year figure stays
- **WHEN** a coded line has a prior-year approved figure and a 0 estimate
- **THEN** its row shows and prints

#### Scenario: Empty top-level group stays
- **WHEN** a group row whose X is a plain roman numeral (for example VI) has all figures 0
- **THEN** its row shows and prints

#### Scenario: Empty sub-group hides
- **WHEN** a dotted sub-group row (for example V.1) has all figures 0 and no remark
- **THEN** its row is hidden like any unused line

#### Scenario: Check row and spacer rows never print
- **WHEN** the deliverable is printed
- **THEN** row 506 (TRUE/FALSE checks) and rows 507–513 are hidden, and the signature block follows the PART 3 row
  with no large gap

#### Scenario: Hidden rows hold nothing
- **WHEN** the verification runs on a recalculated copy
- **THEN** every hidden coded row has 0 or blank in AB:BB and no remark in AO, and every total is the same as with all
  rows shown

### Requirement: Four detail columns are folded, not removed
Columns AC, AE, AF and AI SHALL be folded in a column group that the PM can open with "+":
- AC: last year's monthly average;
- AE: actual to date;
- AF: expected for the rest of the year;
- AI: report monthly average.

Their values and formulas SHALL be unchanged. Each prior-year group then prints as one total column, as in the approved
sample.

#### Scenario: Columns folded with figures intact
- **WHEN** a deliverable is generated
- **THEN** columns AC, AE, AF and AI are hidden inside an outline group, and their cells hold the same formulas as
  before this change

#### Scenario: PM opens a folded column
- **WHEN** the PM clicks the "+" above the group
- **THEN** the four columns show again with their figures

### Requirement: The signature block has the 8 boxes of the approved sample and fits within No to Remarks
Below the table, the signature block SHALL have 8 boxes in one row, all inside columns X:AO, so it prints whole on both
A4 and A3. With the detail columns folded, the boxes SHALL look roughly even in width; a box may widen when the PM
unfolds a column. In order:

| Box | Heading | Role |
|---|---|---|
| 1 | Đề xuất | Trưởng Ban Quản lý |
| 2 | Phê duyệt | Trưởng Ban quản trị |
| 3 | Phê duyệt | Phó Ban quản trị |
| 4 | Phê duyệt | Phó Ban quản trị |
| 5–8 | Phê duyệt | Ban quản trị |

Each box SHALL show its heading, its role, "(Ký tên, ghi rõ họ tên)", blank space to sign, and "Ngày: ___/___/___".
The block SHALL NOT carry any person's name. The form's previous signature cells (including "Xem xét – Đại diện VPC
Savills" and the boxes at AQ, AT, AW, AZ) SHALL be cleared.

#### Scenario: Eight boxes inside X:AO
- **WHEN** a deliverable is generated
- **THEN** rows 514–526 hold exactly 8 signature boxes with the headings and roles above, every one of them within
  columns X:AO and none overlapping another, and no signature text remains in AP:BB

#### Scenario: No names written
- **WHEN** a deliverable is generated
- **THEN** the signature block contains only headings, roles, the signing instruction and blank date lines

### Requirement: A web adjustment keeps the print setup
When a web adjustment saves the deliverable, the print setup, hidden rows, folded columns and signature block SHALL be
applied again. The hidden rows SHALL follow the adjusted figures.

#### Scenario: Line brought into use by an adjustment
- **WHEN** an adjustment gives a previously hidden line a non-zero amount
- **THEN** after the save that line's row shows
