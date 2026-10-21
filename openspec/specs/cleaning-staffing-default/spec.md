# cleaning-staffing-default Specification

## Purpose

Sizes the cleaning crew on duty from the total fee-paying NFA (every product) and a Roster Setup ratio whose default, 3,300 m² per person, is the median of real Savills projects read from their own cleaning forms; replaces the open-space ratio that no source carried (change `fix-cleaning-staffing-ratio`, signed off 2026-10-19).

## Requirements

### Requirement: The cleaning crew is sized from fee-paying NFA

When the `Cleaning - Common Area` row of `Staffing Demand` holds its seeded formula, or is blank or zero, the tool SHALL
size the cleaning people on duty per day from the project's total fee-paying NFA (every product's NFA on Project
Info) and the Roster Setup ratio `Cleaning: m² Fee-paying NFA per Cleaning Staff`:
- the total = ROUNDUP(total fee-paying NFA ÷ ratio);
- `Cleaning - Supervisor` = ROUNDUP(Tower Count ÷ `Cleaning: Towers per Supervisor`), unchanged;
- `Cleaning - Common Area` = the total minus the supervisors, and at least 1.

The open-space area SHALL NOT change the cleaning count. A number the PM typed on either row SHALL be used as typed.

#### Scenario: The standard sample
- **WHEN** a project has 54,400 m² of fee-paying NFA, 2 towers, and the default ratios
- **THEN** the cleaning total SHALL be 17, with 1 supervisor and 16 on `Cleaning - Common Area`

#### Scenario: Open space does not count
- **WHEN** two projects differ only in `Circulation / Hardscape Area`
- **THEN** their cleaning rows SHALL be equal

#### Scenario: A small project
- **WHEN** a project has 2,000 m² of fee-paying NFA and 4 towers
- **THEN** `Cleaning - Supervisor` SHALL be 2 and `Cleaning - Common Area` SHALL be 1

#### Scenario: A typed number wins
- **WHEN** the PM types 5 over the `Cleaning - Common Area` formula
- **THEN** the row SHALL be 5 and its basis SHALL say it is a PM override

### Requirement: The ratio defaults to 3,300 and says where the default came from

The input form SHALL carry `Cleaning: m² Fee-paying NFA per Cleaning Staff` on Roster Setup, filled with 3,300, with a
note that it is the median of the form-read real Savills projects in the service-level table (rounded) and sits in
the Tiêu chuẩn band. When the field is blank, zero or not on the form, the tool SHALL use 3,300 and the row's basis
SHALL say that the standard default was used. The label `Cleaning: m² Open Space per Cleaner` of older forms SHALL NOT
be read as this ratio.

#### Scenario: An older form
- **WHEN** a form made before this change is run, with `Cleaning: m² Open Space per Cleaner` = 3,000 and the old
  open-space formula on `Cleaning - Common Area`
- **THEN** the cleaning rows SHALL be sized with 3,300 m² of fee-paying NFA per person, and the basis SHALL say the
  form has no such field

#### Scenario: A PM's own ratio
- **WHEN** the PM enters 4,000 on the new field for a project of 60,000 m² and 2 towers
- **THEN** the cleaning total SHALL be 15, with 1 supervisor and 14 on `Cleaning - Common Area`
