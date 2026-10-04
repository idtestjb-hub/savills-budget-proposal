## Purpose

Defines what building the input form may do to a project input workbook that already exists, so that
a filled-in project cannot be replaced by placeholder data by accident.

**Data scope**: this capability governs one script that writes the blank intake workbook. It reads
no project data, changes no generated figure, affects neither Generation A nor Generation B
reference tables, and changes no Fact/Dim join key, so the Copilot Studio package's live data is
unaffected.

## Requirements

### Requirement: An existing project input is never replaced without an explicit force

Building the input form SHALL NOT replace a project input workbook that already exists in the
reports folder unless the person running it asks for that explicitly. When no such workbook exists,
building the form SHALL work as before.

#### Scenario: First-time creation is unchanged
- **WHEN** the input form is built and the reports folder has no project input workbook
- **THEN** a new blank form is written to that folder
- **AND** the run reports success

#### Scenario: An existing project input stops the build
- **WHEN** the input form is built without the force option and a project input workbook already exists
- **THEN** the run stops before building anything and reports failure
- **AND** the message names the existing file and says how to force a rebuild
- **AND** the existing file is unchanged in both content and modification time
- **AND** no new file is created in the reports folder

### Requirement: A forced rebuild keeps a dated backup first

When the person running the build explicitly forces it over an existing project input workbook, the
build SHALL first save a copy of that workbook in the same folder, named so that the date and time
are visible, and SHALL replace the workbook only after that copy exists.

#### Scenario: Forced rebuild backs up, then replaces
- **WHEN** the input form is built with the force option over an existing project input workbook
- **THEN** a backup file with the same content as the workbook before the build appears beside it
- **AND** the workbook is then replaced by the new blank form

#### Scenario: A failed backup prevents the overwrite
- **WHEN** the backup copy cannot be made during a forced rebuild
- **THEN** the existing workbook is left unchanged
- **AND** the run reports failure and says why
