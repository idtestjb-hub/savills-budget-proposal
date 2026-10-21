## Purpose

Defines how the pipeline locates each field in the intake workbook, so that changing the form's
layout cannot silently cause a field to be read from the wrong place.

**Data scope**: this capability changes how inputs are located, not what is computed from them. It
reads the intake workbook only, writes no data, affects neither Generation A nor Generation B
reference tables, and changes no Fact/Dim join key, so the Copilot Studio package's live data is
unaffected.

## Requirements

### Requirement: Fields are located by their label, not by position

The pipeline SHALL locate each field in the intake workbook by the label that names it, not by a
fixed cell address. Moving a field to a different row MUST NOT change which value is read.

#### Scenario: A field is read correctly after rows shift above it

- **WHEN** rows are inserted above a field, moving it down the sheet
- **THEN** the pipeline SHALL still read that field's own value
- **AND** the figures produced SHALL be identical to those produced before the shift

#### Scenario: A workbook in the previous layout still reads correctly

- **WHEN** an intake workbook created before the form's layout changed is used
- **THEN** every field SHALL be read correctly without modifying the workbook

#### Scenario: Product areas are read against their own product names

- **WHEN** the product mix block is read
- **THEN** each product's area SHALL be taken from the row labelled with that product's name
- **AND** no value from outside the product mix block SHALL be read as a product area

### Requirement: A missing field fails loudly

Where an expected label cannot be found, the pipeline SHALL stop and name the label it could not
find. It MUST NOT substitute a default, an empty value, or whatever occupies a fallback position.

#### Scenario: A missing label is named

- **WHEN** an expected label is absent from the intake workbook
- **THEN** the pipeline SHALL fail
- **AND** the failure SHALL name the missing label and the sheet it was expected on

#### Scenario: A renamed label is not silently mismatched

- **WHEN** a label has been changed so it no longer matches what the pipeline expects
- **THEN** the pipeline SHALL fail rather than read a neighbouring value

#### Scenario: An empty field is distinguished from a missing one

- **WHEN** a label is present and its value cell is empty
- **THEN** the pipeline SHALL treat that as an empty value, not as a missing field
- **AND** SHALL apply whatever handling that field's emptiness already implies

### Requirement: Reading is unchanged in effect

This capability SHALL change only how fields are located. Every figure the pipeline produces from a
given input SHALL be identical to what it produced before.

#### Scenario: The recorded baseline does not move

- **WHEN** verification is run after this capability is implemented
- **THEN** every recorded baseline figure SHALL match, unchanged
- **AND** no baseline re-record SHALL be required

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

### Requirement: Project mode and the Prior-Year Roster are read by label

The generators SHALL read the project mode, the minimum-wage region, the prior budget year, the Prior-Year Roster
block, the Holiday and Night Duty block, the Staff Lines block (approved prior-year amounts, overrides and their
reasons) and the optional actual-headcount block by their labels, like every other field, so that moving a section does not break the read. A missing required label SHALL
fail loudly and name the label. A workbook made before this change, which has none of these labels, SHALL still be
read and treated as "New prospect".

Data files read: the input workbook only.

#### Scenario: A renamed label

- **WHEN** the label of the Prior-Year Roster block is renamed
- **THEN** the run stops and names the label it could not find

#### Scenario: An old workbook

- **WHEN** a workbook without the new labels is read
- **THEN** it is read as before and treated as "New prospect"

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

### Requirement: The new optional inputs are read by label with stated defaults

The pipeline SHALL read these inputs by label. A blank field, or a label absent from an older form, SHALL take the
default, and the remark that uses it SHALL say a default was used.

| Input | Default |
|---|---|
| Budget start month | January 2027 |
| Water customer group | business (`Kinh doanh`) for a new prospect; Existing mode keeps its own default |
| Contingency rate | 2% |
| ESI2 premium (USD per year) | 1,000 |
| USD exchange rate (VND per USD) | 26,190, the Vietcombank selling rate on 05/10/2026 |

A value of the wrong kind SHALL stop the run and name the field. Examples: a month that is not a month; a group other
than the two; a negative rate.

Data files read: the input workbook only. No recorded baseline moves through reading alone. The standard sample leaves
these fields blank, and the defaults' effects are stated under the capabilities that use them.

#### Scenario: An older form without the new labels

- **WHEN** the input workbook was built before these fields existed
- **THEN** every new input SHALL take its default, and the run SHALL NOT fail

#### Scenario: A wrong value

- **WHEN** the contingency rate is −1%
- **THEN** the run SHALL stop and name the contingency rate field

### Requirement: The parking price fields are optional, read by label, and absent reads as blank

`Project Info` SHALL carry two optional fields in the operating-project block, "Car Parking Price
(VND/vehicle/month)" and "Motorbike Parking Price (VND/vehicle/month)", each found by its label, not by cell
address. A blank cell or 0 SHALL read as "not entered". A form built before this change, which has no such label,
SHALL read both as "not entered" and SHALL run exactly as before. Text or a negative number SHALL stop the run and
name the field. Unlike the recorded parking revenue fields, these two SHALL NOT require "Stable Operation? = Yes".

Data files read: the intake workbook only. No data file is written. No recorded baseline figure moves on its own
account: the standard sample leaves both fields blank.

#### Scenario: An older form

- **WHEN** an intake workbook has no "Car Parking Price (VND/vehicle/month)" label
- **THEN** both prices SHALL read as not entered and the run SHALL proceed

#### Scenario: A price on a new building

- **WHEN** a new building (no stable-operation switch) enters a motorbike price of 120,000
- **THEN** the run SHALL proceed and `RP1` SHALL use 120,000 VND per bay per month before the fill-up curve

#### Scenario: Text in the field

- **WHEN** the car price field reads "1,2 triệu"
- **THEN** the run SHALL stop before writing any workbook and SHALL name the field and the value

### Requirement: The input form builder writes the two parking price fields

The form builder SHALL add the two labelled cells, with a comment explaining each (optional, VND per vehicle per
month, wins over the portfolio price; the recorded revenue of a stable project still ranks first), beside the
recorded parking revenue fields. The guard that protects the live input file from being overwritten SHALL be
unchanged.

#### Scenario: A rebuilt form carries the fields

- **WHEN** the form builder writes a new intake workbook
- **THEN** `Project Info` SHALL contain both labels, each with an empty input cell beside it
