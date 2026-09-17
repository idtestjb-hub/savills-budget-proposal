## Purpose

Defines how the Staffing Demand sheet's default (non-overridden) headcount for a role that has a
real, portfolio-derived staffing ratio behind it is computed, so a freshly-generated intake form
starts from real comparable-property data rather than an arbitrary placeholder, while a PM's own
typed judgment always still wins.

## Requirements

### Requirement: A role's default headcount comes from its portfolio ratio when one is usable

The Staffing Demand sheet's default headcount for a role with a usable portfolio-derived staffing
ratio (measured on at least the usability floor's worth of comparable properties, and the project
has a positive Total NFA) SHALL be computed from that ratio on every row for that role, whether or
not the row has ever been individually edited — not left at a static seeded placeholder — as long as
the row has not been genuinely overridden (see the next requirement).

#### Scenario: A freshly-generated form's role headcount reflects the ratio

- **WHEN** a new project's Staffing Demand sheet is generated for a role with a usable portfolio
  ratio
- **THEN** that role's headcount SHALL be the ratio's derived value for this project's Total NFA,
  not a static seed
- **AND** the row's remark SHALL state the derivation (see the disclosure requirement below)

#### Scenario: A role split across shift rows divides its total across those rows

- **WHEN** a role's portfolio-derived total headcount applies to more than one Staffing Demand row
  (for example a role staffed across morning/afternoon/night shifts)
- **THEN** the total SHALL be divided across that role's rows rather than applied in full to each row

### Requirement: A PM's typed override always wins

The whole point of a portfolio-derived default is that it is a starting point, not a mandate — a PM
who types a real headcount over it SHALL have that number used, and the ratio SHALL NOT silently
override it back.

#### Scenario: A PM overrides the ratio-derived default

- **WHEN** a PM types a headcount onto a Staffing Demand row for a role that has a portfolio ratio,
  after the row already holds a ratio-derived or seeded value
- **THEN** the typed number SHALL be used exactly as typed
- **AND** the row's remark SHALL state that it is a PM override, not a ratio-derived figure

#### Scenario: A genuinely zero headcount is expressed by deleting the row, not typing zero

- **WHEN** a project genuinely has no need for a role that has a portfolio ratio
- **THEN** the row for that role SHALL be deleted from the Staffing Demand sheet
- **AND** a row left in place holding zero SHALL still be treated as not-yet-overridden, and the
  ratio SHALL still be applied to it — zero is not a way to force a ratio-covered role to zero

### Requirement: A role with no usable ratio keeps its seeded default

A role whose portfolio ratio is not usable — measured on fewer comparable properties than the
usability floor, or the project has no Total NFA yet — SHALL keep whatever value is on the Staffing
Demand sheet (today's behavior, unchanged) rather than estimate from too little data.

#### Scenario: A thin-sample role is not estimated from

- **WHEN** a role's portfolio ratio is measured on fewer comparable properties than the usability
  floor
- **THEN** the Staffing Demand sheet SHALL keep its seeded or PM-entered value for that role
- **AND** the row's remark SHALL state that no portfolio estimate was applied and why

### Requirement: A ratio-derived headcount discloses its basis, not just its number

Whenever a role's headcount comes from its portfolio ratio, the Staffing Demand row's remark SHALL
state the portfolio median per 1,000 m² of Total NFA, the number of comparable properties it was
measured on, and that the figure describes what peer buildings employ — not a Savills standard or a
statutory minimum — so a PM reviewing the form can judge whether to keep or override it.

#### Scenario: The remark states the ratio's real basis

- **WHEN** a Staffing Demand row's headcount comes from a portfolio ratio
- **THEN** its remark SHALL state the median headcount per 1,000 m² of Total NFA, the sample size of
  comparable properties it was measured on, and that it is not a Savills standard or statutory
  minimum
