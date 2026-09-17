## Purpose

Defines how the pipeline locates each field in the intake workbook, so that changing the form's
layout cannot silently cause a field to be read from the wrong place.

**Data scope**: this capability changes how inputs are located, not what is computed from them. It
reads the intake workbook only, writes no data, affects neither Generation A nor Generation B
reference tables, and changes no Fact/Dim join key, so the Copilot Studio package's live data is
unaffected.

## ADDED Requirements

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
