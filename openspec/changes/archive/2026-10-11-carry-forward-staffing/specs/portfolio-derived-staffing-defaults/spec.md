## ADDED Requirements

### Requirement: In Existing-project mode the prior-year roster outranks the ratio

When the project mode is "Existing project" and a position is in the Prior-Year Roster, that position's
headcount SHALL come from the roster, and the portfolio ratio SHALL NOT replace it. The ratio SHALL apply only to
positions that are neither in the roster nor typed by the PM. In "New prospect" mode this capability SHALL behave
exactly as before (typed override wins, a zero left in place is still treated as not overridden, a thin-sample
role keeps its seeded value).

Data files read: the portfolio staffing-ratio table, as before. No recorded baseline figure moves in New-prospect mode.

#### Scenario: A rostered position is not replaced by the ratio

- **WHEN** the project is an existing project and a position is in the Prior-Year Roster with 3 heads, while its
  portfolio ratio would give 5
- **THEN** the position SHALL keep 3 heads

#### Scenario: New-prospect mode is unchanged

- **WHEN** the project mode is "New prospect" or blank
- **THEN** every headcount SHALL be computed exactly as before this change
