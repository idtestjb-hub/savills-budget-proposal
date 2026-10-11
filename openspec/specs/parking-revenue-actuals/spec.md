## Purpose

For a project that is already operating, monthly parking revenue is taken from its recorded actual
average, not estimated as bays × a default rate × a fill-up curve. Recorded revenue already reflects
how many bays are really rented.

**Data scope**: reads the intake workbook only. Writes no data file. No Generation A or Generation B
table and no Fact/Dim key changes. No recorded baseline moves, because the standard synthetic project
leaves these fields blank. Figures are in VND.

## Requirements

### Requirement: Recorded parking revenue replaces the estimate for a project at stable operation

The intake form SHALL offer two optional fields: the actual average monthly revenue from car monthly
parking, and the same for motorbike monthly parking, each in VND per month.

When the project is declared at stable operation and a figure is entered, both workbooks SHALL
write the matching line (`RP2` for cars, `RP1` for motorbikes) as that figure × 12. The figure SHALL
be spread evenly across the twelve months, and the bay count, the default per-bay rate and the
fill-up curve SHALL NOT be applied to it.

The line's remark SHALL say, in Vietnamese, that the figure is the recorded monthly average entered
by the PM. Any `1. Summary` narrative that quotes parking prices SHALL quote that monthly figure,
not a per-bay rate.

A blank field SHALL leave that line exactly as it was before this requirement.

#### Scenario: An entered car parking figure is used

- **WHEN** the project is at stable operation and an actual car parking figure is entered
- **THEN** `RP2` in both workbooks SHALL be that figure × 12, in VND
- **AND** each of its twelve months SHALL hold the entered figure

#### Scenario: Only one vehicle type is entered

- **WHEN** an actual figure is entered for motorbikes and the car field is blank
- **THEN** `RP1` SHALL use the entered figure
- **AND** `RP2` SHALL be estimated exactly as before this requirement

#### Scenario: The narrative quotes the recorded figure

- **WHEN** a parking line uses an entered figure
- **THEN** its remark and any `1. Summary` narrative that quotes the parking price SHALL state the
  recorded monthly figure and say it is the PM's recorded average
- **AND** SHALL NOT quote a per-bay rate for that vehicle type

#### Scenario: A zero is kept and flagged

- **WHEN** an actual figure of 0 is entered
- **THEN** the line SHALL be written as 0
- **AND** its remark SHALL say the PM recorded no monthly parking revenue
- **AND** the run's printed summary SHALL flag the zero

#### Scenario: Figures entered without the stable-operation switch stop the run

- **WHEN** an actual parking figure is entered and the project is not declared at stable operation
- **THEN** the run SHALL stop before writing any workbook
- **AND** SHALL name both fields

#### Scenario: Parking cost allocation keeps its proportions

- **WHEN** a parking line uses an entered figure
- **THEN** the share of shared costs that the template allocates to monthly parking versus casual
  parking SHALL be the same proportion as before this requirement
- **AND** no allocation cell SHALL resolve to a spreadsheet error, even when both entered figures
  are 0

#### Scenario: Developer revenue-sharing lines are untouched

- **WHEN** a parking line uses an entered figure
- **THEN** `RP8`, `ESS38` and `RM.PA` SHALL be written exactly as before this requirement
