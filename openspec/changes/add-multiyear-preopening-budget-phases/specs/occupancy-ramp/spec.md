## MODIFIED Requirements

### Requirement: Occupancy-scaled lines are distributed by a fill-up curve, not evenly

Where the method catalogue marks a code as occupancy-scaled, the generated budget SHALL distribute
that code's figure across the months of the phase it is written on, in proportion to a monthly fill-up
percentage, rather than as an even share each month. The line SHALL be written so the sheet's own
total is the sum of that phase's monthly values.

The fill-up percentage SHALL come from one continuous curve spanning the project's whole budget
horizon, so that a phase begins at the occupancy the previous phase ended at. A pre-opening phase
SHALL sit before the curve's occupied months and carry no resident occupancy. Once the curve reaches
stable occupancy it SHALL stay there for the remaining phases rather than restarting.

#### Scenario: A revenue line ramps with occupancy

- **WHEN** a management-fee or monthly-parking line is written for a project not yet at stable
  occupancy
- **THEN** its month values SHALL rise across the phase in proportion to the fill-up percentage
- **AND** an early month SHALL hold a smaller figure than a late month
- **AND** that phase's month values SHALL sum to the line's total for that phase

#### Scenario: A line not linked to occupancy stays flat

- **WHEN** a code the catalogue does NOT mark occupancy-scaled is written (for example diesel, or a
  fixed service contract)
- **THEN** its distribution across the months SHALL be unchanged by this capability

#### Scenario: The curve carries across a phase boundary

- **WHEN** a horizon covers more than one operating year and the curve has not reached stable
  occupancy by the end of the first year
- **THEN** the second year's first month SHALL carry the occupancy the first year's last month
  reached, continuing upward
- **AND** SHALL NOT restart at the first year's starting occupancy

#### Scenario: A later phase at stable occupancy stays there

- **WHEN** the curve reaches stable occupancy during an operating year and further years follow
- **THEN** every month of those later years SHALL carry stable occupancy

#### Scenario: A pre-opening phase carries no resident occupancy

- **WHEN** the horizon includes a pre-opening phase
- **THEN** every month of that phase SHALL carry no resident occupancy
- **AND** the curve's occupied months SHALL begin at the first operating year

### Requirement: The fill-up sheets carry the curve and the lines reference them

The two fill-up sheets in the deliverable (`Tỷ lệ lấp đầy cư dân`, `Tiến độ lấp đầy bãi xe`) SHALL
be populated with the resident and parking curves used across the project's whole budget horizon —
every phase's months, in order, each identified by the phase it belongs to — and each ramped budget
line's remark SHALL point to the sheet its distribution came from.

#### Scenario: A reader can trace a ramped figure to its curve

- **WHEN** a ramped line is written
- **THEN** its remark SHALL name the fill-up sheet the month-by-month distribution is based on
- **AND** that sheet SHALL show the monthly fill-up percentages the line was distributed by

#### Scenario: The fill-up sheets span every phase

- **WHEN** the horizon covers more than one phase
- **THEN** the fill-up sheets SHALL show every phase's months in order
- **AND** each month shown SHALL identify the phase it belongs to

#### Scenario: The fill-up sheets carry no spreadsheet error after population

- **WHEN** the deliverable is generated and recalculated
- **THEN** the two fill-up sheets SHALL contain no cell resolving to a spreadsheet error value
