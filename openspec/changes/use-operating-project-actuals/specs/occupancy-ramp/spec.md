## ADDED Requirements

### Requirement: A project declared at stable operation is budgeted at full occupancy

The intake form SHALL offer an optional Yes/No field declaring that the project already operates at
stable occupancy. When it is Yes, both workbooks SHALL do the following:
- apply 100% resident fill and 100% parking fill in every month they cover, in place of the
  new-building fill-up curve;
- write `RM.0A`, the developer's management fee on units not yet handed over, as zero in every
  month;
- write electricity at its full monthly figure in every month.

Every ramped line's remark SHALL then say, in Vietnamese, that the project is budgeted at stable
operation with 100% occupancy, chosen on the intake form. It SHALL NOT describe the new-building
curve. The two fill-up sheets SHALL show 100% in every month and state the same reason.

When the field is No or blank, every figure SHALL be what it was before this requirement. This
reads the intake workbook only, writes no data file, and moves no recorded baseline: the standard
synthetic project leaves the field blank.

#### Scenario: A stable project's ramped lines are flat at full occupancy

- **WHEN** the switch is Yes
- **THEN** every month of each occupancy-scaled revenue line SHALL equal one twelfth of its
  full-occupancy annual figure
- **AND** the twelve months SHALL sum to the full-occupancy annual figure

#### Scenario: The developer pays nothing for unsold units

- **WHEN** the switch is Yes
- **THEN** `RM.0A` SHALL be zero in every month
- **AND** its remark SHALL say, in Vietnamese, that the project is operating and has no units
  awaiting handover

#### Scenario: Electricity runs at full load

- **WHEN** the switch is Yes
- **THEN** electricity SHALL be the full monthly figure in every month

#### Scenario: Both workbooks apply the same occupancy

- **WHEN** both generators run with the switch Yes
- **THEN** every month in both workbooks SHALL carry 100% fill, including the analysis workbook's
  multi-year view

#### Scenario: The remarks and fill-up sheets say why

- **WHEN** the switch is Yes
- **THEN** no remark SHALL describe a fill-up from 0%
- **AND** the two fill-up sheets SHALL show 100% for every month and name the intake choice as the
  reason

#### Scenario: Blank or No leaves today's budget unchanged

- **WHEN** the switch is No or blank
- **THEN** every figure and remark in both workbooks SHALL be the same as before this requirement

#### Scenario: An unrecognised value stops the run

- **WHEN** the switch holds a value other than Yes, No or blank
- **THEN** the run SHALL stop and name the field and the value
