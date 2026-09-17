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

### Requirement: The LCD-screen lines are not affected by the elevator-count field

The two LCD-screen advertising lines (tower lobby, basement lobby) price a screen count, not an
elevator count — this capability's new field SHALL NOT change their quantity or remark under any
circumstance.

#### Scenario: Supplying an elevator count leaves LCD-screen quantities unchanged

- **WHEN** a project's intake includes a passenger-elevator-per-tower count
- **THEN** the tower-lobby and basement-lobby LCD-screen lines' quantities SHALL be unchanged from
  what the pipeline produced before this capability existed
