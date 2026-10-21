## ADDED Requirements

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
