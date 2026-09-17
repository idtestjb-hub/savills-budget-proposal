## ADDED Requirements

### Requirement: The client deliverable's ramped lines have their own recorded baseline

Verification SHALL record and compare a small set of figures read from the client deliverable
itself — the year-one total of each occupancy-scaled line and the deliverable's estimated surplus —
in addition to the analysis-workbook figures. This is because the occupancy ramp changes the
deliverable's distribution of these lines while the analysis-workbook figures (which do not use the
template) stay put.

#### Scenario: A ramped line reverting to a flat write is caught

- **WHEN** an occupancy-scaled line is written as an even one-twelfth split instead of ramped
- **THEN** verification SHALL fail and name that line

#### Scenario: The deliverable baseline is re-recordable with a stated reason

- **WHEN** the fill-up curve or a ramped line's method changes by an approved change
- **THEN** the affected deliverable baseline figures SHALL be re-recorded together with a stated
  reason
- **AND** subsequent runs compare against the updated values

#### Scenario: The deliverable and the analysis stay consistent where they should

- **WHEN** both workbooks are generated for the same project
- **THEN** the fill-up percentage each applies to a given month SHALL be the same
- **AND** any line that is deliberately shown at full occupancy in the analysis (as a stated
  ceiling) SHALL be identified as such rather than treated as a mismatch
