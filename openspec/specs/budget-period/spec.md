# budget-period Specification

## Purpose
Defines which twelve calendar months a budget covers, so that both fund sheets of the client deliverable show the same
months and every month-dated rule (VAT rate, tariff, paid holidays, working days) looks up the month it is applied to.

Data files read: the input workbook's optional budget start month. Data files written: none besides the output
workbooks. A recorded baseline moves only through the month-dated rules that use the period.

## Requirements

### Requirement: The budget covers twelve calendar months from an entered start month

The input form SHALL offer a budget start month. The budget SHALL cover that month and the eleven months after it. When
the field is blank or its label is absent, the start month SHALL be January 2027. A value that is not a month SHALL stop
the run with a message naming the field.

#### Scenario: Blank start month

- **WHEN** the budget start month is blank
- **THEN** the budget SHALL cover January to December 2027

#### Scenario: Entered start month

- **WHEN** the PM enters July 2027
- **THEN** the budget SHALL cover July 2027 to June 2028

#### Scenario: Invalid start month

- **WHEN** the field holds text that is not a month
- **THEN** the run SHALL stop and name the field

### Requirement: Both fund sheets show the same period

The tool SHALL write the period's first and last day into `2. Budget-Management Fund` (`AH6`, `AL6`), so that the
sheet's twelve month columns are the budget's months, and SHALL make `1. Summary`'s period cells (`H4`, `H5`) show the
same two dates.

#### Scenario: Period cells agree

- **WHEN** the deliverable is generated for a January 2027 start
- **THEN** `2. Budget-Management Fund!AH6` SHALL be 01/01/2027 and `AL6` 31/12/2027
- **AND** `1. Summary!H4` and `H5` SHALL show the same two dates

### Requirement: Every month-dated rule uses the calendar month it is applied to

A rule that depends on the date (a VAT rate, a tariff, the paid-holiday calendar, a working-day count) SHALL use the
calendar month of the budget column it is computing, in both workbooks. The occupancy fill-up curve SHALL stay counted in
operational months, with operational month 1 equal to the budget's first month.

#### Scenario: A period that straddles a VAT change

- **WHEN** the budget starts in October 2026
- **THEN** October to December 2026 SHALL use the VAT rate in force in 2026
- **AND** January to September 2027 SHALL use the rate in force from 1 January 2027

#### Scenario: The fill-up curve follows the start month

- **WHEN** the budget starts in July 2027
- **THEN** the fill-up curve's month 1 SHALL be July 2027
