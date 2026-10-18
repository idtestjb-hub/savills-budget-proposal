## ADDED Requirements

### Requirement: Verification checks the Service Levels sheet and the service-level tables

Verification SHALL confirm, on the synthetic project, that:
- the `Service Levels` sheet's cleaning and security headcount equals the roster;
- its measures, levels and "sát ngưỡng" marks equal an independent recomputation from the threshold table;
- a value on a cut-off falls in the higher-numbered band;
- a value outside the sanity bounds is "chưa phân loại" and keeps its measure;
- the percentile's comparison set holds only form-read, classified real projects, and the count shown equals that set's size;
- the client deliverable and every other sheet are unchanged from the recorded baseline;
- the real-project table and the threshold table contain no project name or file name from the scan store;
- the real-project table holds no two rows with identical fee-paying NFA.

Verification MUST NOT read the scan store or the name-to-id map; the name check SHALL run against a list of names supplied by the build step's own output, kept outside the repository.

Data files read: `Ref_ServiceLevelThresholds.csv`, `Ref_ServiceLevelProjects.csv`.

#### Scenario: Headcount differs from the roster

- **WHEN** the sheet's cleaning headcount differs from the roster's
- **THEN** verification SHALL fail and name the service

#### Scenario: A cut-off value

- **WHEN** a synthetic project sits exactly on a threshold
- **THEN** verification SHALL confirm it is in the higher-numbered band

#### Scenario: An inferred row in the comparison set

- **WHEN** the sheet's percentile count includes a real project whose source is "chi phí"
- **THEN** verification SHALL fail and name the service

#### Scenario: A name in the table

- **WHEN** a store project name appears in either data table
- **THEN** verification SHALL fail

#### Scenario: Duplicate NFA in the table

- **WHEN** two rows of the real-project table carry the same fee-paying NFA
- **THEN** verification SHALL fail and list the two ids
