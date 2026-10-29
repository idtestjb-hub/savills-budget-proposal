## ADDED Requirements

### Requirement: The budget year is the year holding most of the period's months

A budget's year SHALL be the calendar year that holds most of its twelve months; when two years hold six months each it
SHALL be the later year. The deliverable's budget year cell (`2. Budget-Management Fund!AL5`), the prior-year check of
Existing-project mode and the Existing-project staff and utility figures SHALL use this year. The Review import SHALL
name an approved file's year by the same rule, so that the next budget's year is always one more than the file's.

#### Scenario: January start

- **WHEN** the budget starts in January 2027
- **THEN** the budget year SHALL be 2027

#### Scenario: Most months in the second year

- **WHEN** the budget starts in August 2025
- **THEN** the budget year SHALL be 2026

#### Scenario: Six months in each year

- **WHEN** the budget starts in July 2027
- **THEN** the budget year SHALL be 2028

#### Scenario: Review of an August-to-July budget

- **WHEN** the approved file covers 08/2024–07/2025
- **THEN** the file's year SHALL be 2025, the new period 08/2025–07/2026 and the new budget year 2026
- **AND** the run SHALL NOT stop at the prior-year check
