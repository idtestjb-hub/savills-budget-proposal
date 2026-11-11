## Why

A client deliverable has to be printed and signed the way an approved budget is: one table per fund, readable, with a
signature block for the people who propose and approve it. The model is an approved 2026 Management Fund budget
(4 A3 pages, signed and stamped). Today sheet `2. Budget-Management Fund` has no print setup:
- no print area, repeated header rows or page footer;
- the form's own "Not Use" filter (column B) is never applied, so 404 of 491 coded rows print as empty lines
  (28 A4 pages);
- the check row under the totals prints a red "TRUE";
- the form's signature block sits across the month columns, so an A4 print (No to Remarks) loses four of its six
  boxes.

The user asked for two prints from the same sheet: A4 from column X ("No") to AO ("Remarks"), and A3 from X to BB
(the 12th month). The options were chosen on 2026-11-11.

## What Changes

- **Print setup in the deliverable.** Sheet `2. Budget-Management Fund` gets a ready print setup. Defaults:
  - A3 landscape, print area X2:BB526, fitted to one page wide;
  - rows 9:10 repeated on every page;
  - "Page x of y" centred in the footer.
- **Not Use rows hidden.** Rows hide by the form's own column B rule: a row is "Not Use" when last year's approved
  monthly average is 0, there is no % change and there is no remark. The column B filter is left on so the PM can
  reapply it after editing.
  - Always shown: top-level section rows (PART, A–D, and roman numerals without a dot), as in the approved sample.
  - Dotted sub-groups follow column B.
  - Always hidden: the check row 506 and the blank spacer rows 507–513.
- **Detail columns folded.** Columns AC, AE, AF and AI (last year's monthly average, actual to date, expected rest of
  year, report monthly average) are folded with a +/− column group. Their figures and formulas are unchanged. This
  matches the approved sample, where each prior-year group prints as one total column, and it makes the text
  larger: about 4.7 pt on A4 and about 4.0 pt on A3, against 3.4 pt and 3.1 pt unfolded.
- **Signature block: 8 boxes, as in the approved sample.** It replaces the form's 6 boxes and lies within X:AO, so
  it prints whole on both A4 and A3:
  - Đề xuất: Trưởng Ban Quản lý;
  - Phê duyệt: Trưởng Ban quản trị, two Phó Ban quản trị, and four Ban quản trị members.

  Each box carries the role, "(Ký tên, ghi rõ họ tên)", space to sign, and "Ngày: ___/___/___". No names are filled
  in. The form's "Xem xét: Đại diện VPC Savills" box is removed (the user's choice). **BREAKING** for anyone who
  expected that box.
- **PDF buttons on the web.** The run result page gets "PDF A4" and "PDF A3". Excel opens a copy of the current
  deliverable (after any web adjustment), recalculates it, reapplies the Not Use filter, sets the paper and range,
  and exports a PDF into the run folder. The PDF opens from the outputs list. The signature block is kept on one
  page.
- **Adjustments keep the setup.** A web adjustment re-applies the print setup after it saves the deliverable, so the
  hidden rows follow the new figures.

No figure on the deliverable changes.

## Capabilities

### New Capabilities
- `deliverable-print-layout`: how the client deliverable's Management Fund sheet is set up for printing. Covers the
  paper and range, the repeated header rows, the footer, which rows and columns are hidden, and the signature block.
- `budget-web-print-pdf`: the web buttons that export the current deliverable's Management Fund sheet as an A4 or A3
  PDF, and who may download it.

### Modified Capabilities
- (none. `standard-budget-template` requirements still hold: the sheet set and the figures are unchanged. Only the
  signature cells and print settings of one sheet differ, as specified in `deliverable-print-layout`.)

## Impact

- New module `print_layout.py`. Its openpyxl part sets up the workbook; its Excel part exports the PDF.
- `generate_project_budget.py` calls it before saving. `webapp/adjust_run.py` calls it after saving an adjustment.
- `webapp/server.py` gains the print endpoint and a new output kind for the PDFs. Viewers may download the PDFs
  because they are the client deliverable. The run page gets the two buttons.
- The PDF needs Microsoft Excel on the machine that runs the web, the same as the existing adjust and review steps.
  Without Excel the button reports why and the xlsx is unaffected.
- New tests, and a check in `verification/verify.py`: hidden rows carry no figure and no remark; signature block
  inside X:AO; print setup present.
- Only `2. Budget-Management Fund`. Other funds (`2.2 Common area Fund`, `3. Budget-Sinking Fund`) are out of scope
  until asked for.
