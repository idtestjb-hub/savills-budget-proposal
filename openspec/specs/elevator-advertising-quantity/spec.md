## Purpose

Defines how the pipeline determines the quantity of elevator ad frames a project has, for the
"Ad frame (tower lobby, inside elevator)" revenue line on both the client deliverable and the
analysis workbook — a real per-project figure when the intake supplies one, a clearly labelled
fallback assumption when it does not.

## Requirements

### Requirement: A real passenger-elevator count drives ad-frame quantity when supplied

When a project's intake states its real passenger-elevator count per tower, the "Ad frame" revenue
line's quantity SHALL be computed from that real figure (count × tower count) rather than an assumed
default, and its remark SHALL state that the figure is this project's own real data.

#### Scenario: A project states its real passenger-elevator count

- **WHEN** a project's intake includes a passenger-elevator-per-tower count
- **THEN** the "Ad frame" line's quantity SHALL equal that count times the project's tower count
- **AND** its remark SHALL identify the quantity as this project's own real data, not an assumption

### Requirement: Quantity falls back to a disclosed assumption when no real count is supplied

A project whose intake does not state a passenger-elevator count SHALL keep today's behavior
unchanged: the "Ad frame" line's quantity SHALL use the existing fallback assumption, and its remark
SHALL continue to state plainly that the figure is an assumption, not this project's real data.

#### Scenario: A project without a stated elevator count is unaffected

- **WHEN** a project's intake does not include a passenger-elevator-per-tower count
- **THEN** the "Ad frame" line's quantity SHALL equal the pipeline's existing fallback assumption
  times the project's tower count
- **AND** its remark SHALL state that the figure is an assumption, not real per-project data

### Requirement: The tower-lobby LCD-screen line is not affected by either new field

The tower-lobby LCD-screen advertising line prices a screen count, not an elevator or basement
count — neither this capability's elevator-count field nor its basement-count field (see below)
SHALL change its quantity or remark under any circumstance.

#### Scenario: Supplying an elevator or basement count leaves the tower-lobby LCD line unchanged

- **WHEN** a project's intake includes a passenger-elevator-per-tower count, a basement count, or
  both
- **THEN** the tower-lobby LCD-screen line's quantity SHALL be unchanged from what the pipeline
  produced before this capability existed

### Requirement: A real basement count drives the basement-lobby LCD quantity when supplied

When a project's intake states its real basement count, the "LCD screen (basement lobby)" line's
quantity SHALL be computed from that real figure (one screen assumed per basement level) rather
than the flat one-screen-per-project fallback, and its remark SHALL state that the figure is this
project's own real data. No basement-count formula derived from building scale (floor count,
parking slots) exists — real portfolio data shows basement count tracks neither closely enough to
derive one, the same conclusion already reached for the elevator-count field — so this requirement
depends on the intake field, not an estimate.

#### Scenario: A project states its real basement count

- **WHEN** a project's intake includes a basement count
- **THEN** the "LCD screen (basement lobby)" line's quantity SHALL equal that real count
- **AND** its remark SHALL identify the quantity as this project's own real data, not an assumption

#### Scenario: A project without a stated basement count is unaffected

- **WHEN** a project's intake does not include a basement count (or states it as `0`, treated the
  same as not entered)
- **THEN** the "LCD screen (basement lobby)" line's quantity SHALL use the existing flat
  one-screen-per-project fallback
- **AND** its remark SHALL state that the figure is an assumption, not real per-project data
