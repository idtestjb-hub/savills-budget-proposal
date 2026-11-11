## Purpose

Lets a web user export the current client deliverable's Management Fund sheet as a signed-budget-style PDF on A4 or A3,
ready to print for signature, without opening Excel themselves.

Data: reads the run's deliverable and writes the PDF into the same run folder. Nothing else is read or written. No
figure moves, so no recorded baseline changes.

## ADDED Requirements

### Requirement: The run page offers PDF A4 and PDF A3
The result page of a finished run that has a client deliverable SHALL show two buttons, "PDF A4" and "PDF A3". Each
SHALL produce a PDF of sheet `2. Budget-Management Fund` from the deliverable as it stands now, including any web
adjustment already saved:

| Button | Paper | Columns | Rows |
|---|---|---|---|
| PDF A4 | A4 landscape | X ("No") to AO ("Remarks") | 2 to 526 |
| PDF A3 | A3 landscape | X to BB (12th month) | 2 to 526 |

Both SHALL:
- fit the columns to one page wide;
- repeat rows 9:10 on every page;
- show "Page x of y";
- hide "Not Use" rows and the check row by the rules in `deliverable-print-layout`, worked out from freshly
  recalculated figures;
- hide columns AC, AE, AF and AI.

#### Scenario: A4 PDF
- **WHEN** the user clicks "PDF A4" on a finished run
- **THEN** a PDF on A4 landscape pages appears in the run's outputs, its columns run from "No" to "Remarks", and its
  last page carries the 8 signature boxes

#### Scenario: A3 PDF
- **WHEN** the user clicks "PDF A3"
- **THEN** a PDF on A3 landscape pages appears, with the 12 month columns after "Remarks"

#### Scenario: PDF follows an adjustment
- **WHEN** the user saves a web adjustment and then clicks "PDF A4"
- **THEN** the PDF shows the adjusted figures

### Requirement: The signature block is never split across pages
The PDF SHALL keep the whole signature block on one page. If the automatic page break falls inside it, the break SHALL
move to just before the block.

#### Scenario: Break would cut the block
- **WHEN** the table ends so that the signature rows would straddle two pages
- **THEN** the PDF starts the signature block on a new page and every box is on that page

### Requirement: The PDF leaves the deliverable untouched
Exporting SHALL work on a copy. The deliverable xlsx SHALL NOT be changed or locked. A failure SHALL leave the
deliverable as it was and report the reason in plain Vietnamese. Failure cases: Excel unavailable, the deliverable open
in Excel on the server, or the export failing.

#### Scenario: Excel not available
- **WHEN** the machine running the web has no usable Excel
- **THEN** the button reports that the PDF needs Excel on the server, and no file is written

#### Scenario: Deliverable unchanged
- **WHEN** a PDF is exported
- **THEN** the deliverable's modified time and content are unchanged

### Requirement: Who can download the PDF
The PDFs are the client deliverable in another format. Every role allowed to download the client deliverable,
viewers included, SHALL be able to export and download them. In the site package they SHALL be available like the
deliverable.

#### Scenario: Viewer downloads the PDF
- **WHEN** a viewer opens a run whose PDF A4 was exported
- **THEN** the PDF is in the viewer's outputs list and downloads
