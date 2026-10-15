## Purpose

For a project not yet at stable occupancy, makes the budget's occupancy-scaled revenue and
load-driven cost lines vary month by month with a fill-up curve, writes the developer's
management-fee top-up on unsold units as that curve's mirror, and keeps one curve shared by the
client deliverable and the internal analysis.

**Data scope**: this capability changes how certain existing budget lines in the generated
workbooks are distributed across the twelve months and adds one line (`RM.0A`) the pipeline did not
previously write. It reads and writes no Generation A or Generation B reference table and changes no
Fact/Dim join key, so the Copilot Studio package's live data is unaffected. Figures stay in VND.

## Requirements


### Requirement: Occupancy-scaled lines are distributed by a fill-up curve, not evenly

Where the method catalogue marks a code as occupancy-scaled, the generated budget SHALL distribute
that code's annual figure across the twelve months in proportion to a monthly fill-up percentage,
rather than as an even one-twelfth each month. The line SHALL be written so the sheet's own total
is the sum of the twelve monthly values.

#### Scenario: A revenue line ramps with occupancy

- **WHEN** a management-fee or monthly-parking line is written for a project not yet at stable
  occupancy
- **THEN** its month values SHALL rise across the year in proportion to the fill-up percentage
- **AND** an early month SHALL hold a smaller figure than a late month
- **AND** the twelve month values SHALL sum to the line's annual total

#### Scenario: A line not linked to occupancy stays flat

- **WHEN** a code the catalogue does NOT mark occupancy-scaled is written (for example diesel, or a
  fixed service contract)
- **THEN** its distribution across the months SHALL be unchanged by this capability

### Requirement: The developer's top-up on unsold units is the curve's mirror

The budget SHALL write `RM.0A` — the management fee the developer pays on units not yet handed over
— as, for each month, the full management fee for all units at the applied rate multiplied by one
minus that month's fill-up percentage.

#### Scenario: RM.0A falls as occupancy rises

- **WHEN** the fill-up percentage increases from one month to the next
- **THEN** `RM.0A` for the later month SHALL be lower than for the earlier month
- **AND** in a month at 100% fill `RM.0A` SHALL be zero

#### Scenario: Collected fee plus developer top-up covers the full fee

- **WHEN** `RM` (collected from residents) and `RM.0A` (paid by the developer) are both written for
  the same month
- **THEN** their sum SHALL equal the full management fee for all units at the applied rate for that
  month, within rounding

### Requirement: Electricity has a floor below which it does not fall

Electricity SHALL NOT be distributed below a stated fraction of its full monthly figure even at very
low occupancy: at zero occupancy it SHALL be at that floor, and it SHALL reach the full monthly
figure by the occupancy level the guideline states, not only at 100%.

#### Scenario: A near-empty month still carries base electricity load

- **WHEN** electricity is written for a month whose fill-up percentage is below the guideline's
  full-load threshold
- **THEN** that month's electricity SHALL be at least the stated floor fraction of the full monthly
  figure

#### Scenario: Electricity reaches full before the building is full

- **WHEN** a month's fill-up percentage is at or above the guideline's stated full-load threshold
- **THEN** that month's electricity SHALL be the full monthly figure

### Requirement: One fill-up curve, shared by both generators

The monthly fill-up curve SHALL be defined in one place and used by both the client-deliverable
generator and the internal-analysis generator, so the two workbooks ramp identically for the same
project.

#### Scenario: The two workbooks agree on the curve

- **WHEN** both generators run against the same input
- **THEN** the fill-up percentage they apply to each month SHALL be the same in both

#### Scenario: The analysis workbook's figures do not move on adoption

- **WHEN** the internal analysis is generated before and after the curve is moved to the shared
  module
- **THEN** every figure it produces SHALL be unchanged

### Requirement: The fill-up sheets carry the curve and the lines reference them

The two fill-up sheets in the deliverable (`Tỷ lệ lấp đầy cư dân`, `Tiến độ lấp đầy bãi xe`) SHALL
be populated with the resident and parking curves used, and each ramped budget line's remark SHALL
point to the sheet its distribution came from.

#### Scenario: A reader can trace a ramped figure to its curve

- **WHEN** a ramped line is written
- **THEN** its remark SHALL name the fill-up sheet the month-by-month distribution is based on
- **AND** that sheet SHALL show the monthly fill-up percentages the line was distributed by

#### Scenario: The fill-up sheets carry no spreadsheet error after population

- **WHEN** the deliverable is generated and recalculated
- **THEN** the two fill-up sheets SHALL contain no cell resolving to a spreadsheet error value

### Requirement: The figure movement is measured and disclosed

Because this capability changes how much of a line's annual value lands in year one, the change
SHALL measure the effect on a real project — the year-one totals of every affected line, and the net
effect on the estimated surplus — and record it for review.

#### Scenario: The effect on a real project is on record

- **WHEN** the capability is implemented
- **THEN** the change SHALL record, for a named real project, each affected line's year-one total
  before and after, both in VND, and the net change to the estimated surplus

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

Existing-project mode wins over this switch for common-area electricity and water. When the project
mode is Existing, `EEE.C` and `EEW.C` SHALL keep the amounts that mode computes from the project's
actual spend (requirement "Existing-project common-area utilities are not ramped", added by change
`carry-forward-common-utilities`), whatever the switch says. The switch still applies to every other line it names.

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

#### Scenario: Existing-project mode keeps its utility amounts

- **WHEN** the switch is Yes and the project mode is Existing
- **THEN** `EEE.C` and `EEW.C` SHALL equal the amounts computed from the project's actual spend, as
  with the switch blank
- **AND** their remarks SHALL be the Existing-mode remarks

#### Scenario: Blank or No leaves today's budget unchanged

- **WHEN** the switch is No or blank
- **THEN** every figure and remark in both workbooks SHALL be the same as before this requirement

#### Scenario: An unrecognised value stops the run

- **WHEN** the switch holds a value other than Yes, No or blank
- **THEN** the run SHALL stop and name the field and the value

### Requirement: Existing-project common-area utilities are not ramped

In "Existing project" mode, common-area electricity (`EEE.C`) and common-area water (`EEW.C`) SHALL NOT be distributed
by the fill-up curve, and electricity SHALL NOT carry the occupancy floor. The actual spend they start from already
reflects the building's current occupancy (capability `existing-project-utilities`). Every other occupancy-scaled line
SHALL keep its present behaviour. In "New prospect" mode nothing changes.

Data files read: none beyond those of `existing-project-utilities`. No recorded baseline figure moves; the standard
sample is a new prospect.

#### Scenario: An existing project's electricity is not floored or ramped

- **WHEN** an Existing-project sample with utility actuals is run
- **THEN** `EEE.C` and `EEW.C` SHALL hold the same amount in every month in which no tariff row changes
- **AND** the remarks on those two lines SHALL NOT describe the fill-up curve or the electricity floor

#### Scenario: Other ramped lines keep the curve

- **WHEN** the same Existing-project sample is run
- **THEN** the management-fee revenue lines SHALL be distributed exactly as they would be without this requirement
