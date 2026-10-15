## ADDED Requirements

### Requirement: Verification exercises the run log
Verification SHALL run the run-log measurement on the synthetic project with its paths redirected, and SHALL fail when
the record is missing, when its Required-line counts do not add up to the total, when its surplus differs from revenue
minus expense, or when its figures differ from the same cells read directly through Excel. It SHALL also confirm that
a read-only run log folder produces a warning and not a failure. Verification SHALL NOT write to the live
`Budget_Agent/reports/run_log/` folder.

#### Scenario: Counts do not add up
- **WHEN** the synthetic record says 40 filled, 10 zero with a reason, 5 zero with no reason and a total of 60
- **THEN** verification fails and names the counts

#### Scenario: Production folder untouched
- **WHEN** verification finishes
- **THEN** the live run log folder holds the same files as before it started
