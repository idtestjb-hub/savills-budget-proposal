## ADDED Requirements

### Requirement: Operating-project fields are optional, and an absent label reads as blank

The following fields SHALL be optional:
- the per-product actual rate and its VAT basis;
- the stable-operation switch;
- the actual car and motorbike parking revenue;
- the per-product collect-on-behalf water and electricity amounts.

Where the form does not carry one of these labels, the pipeline SHALL read that field as blank and
SHALL NOT fail, in the same way it already reads a product row the form does not carry. Every
field the form already carried before this requirement SHALL still fail loudly when its label is
missing.

Each run SHALL print which of these optional fields it found filled, so that a misspelt label shows
up as "not found" in the printout instead of passing silently.

This reads the intake workbook only, writes no data file, and moves no recorded baseline.

#### Scenario: A form that predates the new fields still reads

- **WHEN** an intake workbook filled in before this requirement, carrying none of the new labels, is used
- **THEN** the run SHALL complete without modifying the workbook
- **AND** every figure SHALL be the same as before this requirement

#### Scenario: The run states which operating-project fields it found

- **WHEN** a run reads an intake workbook
- **THEN** its printed output SHALL list each optional operating-project field as filled, blank or
  not on the form

#### Scenario: An existing field still fails loudly

- **WHEN** a label that the form carried before this requirement is missing
- **THEN** the run SHALL stop and name that label and its sheet, as before

#### Scenario: New columns on the product rows are found by their header

- **WHEN** the product mix block carries the actual-rate and VAT-basis columns
- **THEN** each product's rate SHALL be read from the column whose header names it, on the row
  labelled with that product
- **AND** moving those columns SHALL NOT change which value is read
