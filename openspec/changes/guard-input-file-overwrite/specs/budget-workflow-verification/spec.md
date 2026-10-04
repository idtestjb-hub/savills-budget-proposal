## ADDED Requirements

### Requirement: Verification confirms the input-form guard

Verification SHALL confirm, on every run, that building the input form refuses to replace an
existing project input workbook without the force option, and that a forced rebuild keeps a backup.
This confirmation SHALL use a temporary folder only and MUST NOT read, create, alter or delete any
file in the live reports folder.

#### Scenario: The guard holds
- **WHEN** verification builds the form twice in a temporary folder, once without and once with the force option, over a stand-in input workbook
- **THEN** the first build is refused and leaves the stand-in unchanged
- **AND** the second build leaves a backup equal to the stand-in's earlier content and replaces the stand-in
- **AND** verification records a pass for this section

#### Scenario: A weakened guard fails verification
- **WHEN** the unforced build overwrites the stand-in workbook
- **THEN** verification fails and says the input-form guard did not hold

#### Scenario: The live reports folder is untouched
- **WHEN** this section runs while a live project input workbook exists
- **THEN** that workbook is unchanged in content and modification time
