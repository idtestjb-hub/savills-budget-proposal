## ADDED Requirements

### Requirement: The Prior-Year Utilities sheet is read by label

The generators SHALL read the Prior-Year Utilities sheet by its labels, like every other field. That covers:
- the monthly actuals: line, month, amount in VND, VAT basis, optional consumption, note;
- the per-line settings: tariff category, PM unit price and its source, approved prior-year amount and its VAT basis,
  consumption override, reason code, reason note.

A missing required label SHALL stop the run and name the label. A workbook made before this change has no such sheet;
it SHALL still be read, and in "New prospect" mode it SHALL give the same result as before. In "Existing project" mode
a workbook without the sheet SHALL stop with a message naming the sheet, because the two lines then have nothing to
start from.

Data files read: the input workbook only. No recorded baseline figure moves.

#### Scenario: An old workbook in New-prospect mode

- **WHEN** a workbook without the Prior-Year Utilities sheet is run as a new prospect
- **THEN** it SHALL be read as before and its figures SHALL not change

#### Scenario: An old workbook switched to Existing-project mode

- **WHEN** a workbook without the sheet is run in "Existing project" mode
- **THEN** the run SHALL stop and name the Prior-Year Utilities sheet and the tool that adds it to a dated copy
