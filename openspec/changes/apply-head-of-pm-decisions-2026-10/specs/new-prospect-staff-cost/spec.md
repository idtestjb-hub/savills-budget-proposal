## Purpose

Defines how a new prospect's staff cost is completed: the holiday and night allowance (`EMH3`) on the form's own
`A1.1 Allowance` sheet, one calendar working-day count shared by both workbooks, every position reaching `A1` however
many template rows its group has, and the internal analysis carrying the same staff-cost components as `A1`. It does not
apply in Existing-project mode.

Data files read: the input workbook's Staffing Demand rows (shift code, coverage days, staff per day, daily rate) and
the paid-holiday calendar. Data files written: none besides the output workbooks. Recorded baselines move: the
analysis's staff cost, profit, margin and markup, and the deliverable's staff figure and surplus.

## ADDED Requirements

### Requirement: A new prospect's holiday and night allowance is priced on `A1.1`

For a new prospect the tool SHALL fill `A1.1 Allowance` and set `EMH3` to that sheet's monthly total.
- **Holiday work at 300%:** for each position on 7-day coverage that also has a night shift (shift code D or 24H), the
  number of staff working each public holiday SHALL be the day shift's staff per day. The number of holidays SHALL be
  the paid holidays in the budget period.
- **Night work at 30%:** for each position with a night shift, the night staff count SHALL be the night shift's staff
  per day. The number of nights SHALL be the days in the period minus the paid holidays.
- **Night work on a holiday at 390%:** the night staff count SHALL be the same night staff per day. The number of
  nights SHALL be the paid holidays.
- **Gross pay:** the `A1.1` gross pay of each code SHALL be filled, including `CS`.
- **Missing rows:** a qualifying position whose code has no row on `A1.1` SHALL get its own row, and the sheet's total
  SHALL include it.
- **Nothing qualifies:** when no position qualifies, `EMH3` SHALL be 0 with a stated reason.

The legal basis is Bộ luật Lao động 2019 Điều 98.

#### Scenario: A technician on a 24-hour rotation

- **WHEN** a Technician position has 7 coverage days, a day shift with 2 staff and a night shift with 1 staff
- **THEN** `A1.1` SHALL show 2 staff at 300% on each paid holiday, 1 staff at 30% on each non-holiday night, and 1 staff
  at 390% on each holiday night
- **AND** `EMH3` SHALL equal `A1.1`'s monthly total

#### Scenario: A day-only 7-day position

- **WHEN** a Reception position has 7 coverage days and only an office-hours shift
- **THEN** it SHALL NOT be counted in the 300% holiday branch

### Requirement: `EMH2` does not count the allowance twice

When `EMH3` carries `A1.1`'s total, `EMH2` SHALL exclude the allowance that `A1`'s total already includes from
`A1.1`. Verification SHALL tie each staffing line to its detail sheet on the standard new-prospect sample as well as on
the Existing samples, and SHALL fail on a double count.

#### Scenario: Allowance counted once

- **WHEN** a new prospect has a non-zero `A1.1` total
- **THEN** `EMH2` plus `EMH3` SHALL equal `A1`'s payroll total, counting the allowance once

### Requirement: Working days are counted on the calendar

A person's working days in the budget period SHALL be the Mondays to Saturdays in the period minus the paid holidays.
For January–December 2027 that is 302. The rules for other coverage patterns:
- A position on 5-day coverage counts Mondays to Fridays minus the paid holidays.
- A position on 7-day coverage still counts 6 days a week per person, because its headcount already carries the 7/6
  uplift.

Both workbooks SHALL use this one count:
- monthly gross pay SHALL be the daily rate times the count divided by 12;
- `A1.1`'s daily-wage divisor SHALL be the count divided by 12;
- the input form's default daily rates SHALL be the market monthly pay divided by the count divided by 12.

`A5`'s formulas SHALL NOT change.

#### Scenario: Year 2027

- **WHEN** the budget covers January to December 2027 and a position has 6 coverage days
- **THEN** its working days SHALL be 302, and its monthly gross SHALL be its daily rate times 302 / 12

#### Scenario: The two workbooks agree

- **WHEN** both workbooks are generated for the same input
- **THEN** they SHALL use the same working-day count for the same position

### Requirement: Every position's headcount reaches `A1`

When a position's headcount exceeds the template rows its group has on `A1`:
- each extra person SHALL be written in an overflow block below the table, with `A1`'s own row formulas;
- this SHALL hold for every group, including the Property Manager;
- `EMH2` SHALL include the overflow block;
- a written row whose gross pay is 0 SHALL be flagged in the run output. It SHALL NOT be skipped.

#### Scenario: Two accountants

- **WHEN** the staffing input has 2 Accountants and the template's Accountant group has one row
- **THEN** `A1` SHALL show 2 Accountant rows, and `EMH2` SHALL include both

#### Scenario: A zero-pay row

- **WHEN** a position is written with a daily rate of 0
- **THEN** the run output SHALL flag that row by position name

### Requirement: The analysis costs every in-house position with `A1`'s components

The internal analysis SHALL cost every in-house position on its staff sheet, including Accountant, Cashier, Operations
Manager and Technical Secretary. Before the 10% markup it SHALL add the per-person components `A1` carries, from the same
constants:
- team building: 1,000,000 VND per month for the Property Manager, 300,000 for others;
- training: 1.3% of gross pay;
- health check: 1,350,000 VND per year;
- accident insurance: on `A1`'s formula;
- uniform: 300,000 VND per month.

Outsourced positions SHALL NOT carry these components.

#### Scenario: An in-house technician

- **WHEN** the analysis costs an in-house Technician
- **THEN** its annual cost SHALL include training at 1.3% of gross, the health check, accident insurance, team building
  and uniform before the markup

#### Scenario: An accountant is costed

- **WHEN** the staffing input has an Accountant
- **THEN** the analysis's staff cost SHALL include that position

### Requirement: The analysis prices night and holiday work on `A1.1`'s method

The internal analysis SHALL price night and holiday allowance per shift, as `A1.1` does: the percentage times the
daily wage times the nights or holidays times the staff on duty. It SHALL NOT apply a 1.3 factor to night positions'
loaded cost, so the two workbooks agree on the allowance.

#### Scenario: The allowance agrees

- **WHEN** both workbooks are generated for the same new prospect
- **THEN** the analysis's annual night and holiday allowance SHALL equal 12 times the deliverable's `EMH3` monthly figure
