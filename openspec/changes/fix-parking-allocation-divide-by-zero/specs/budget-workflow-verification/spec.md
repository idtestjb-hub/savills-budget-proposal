## MODIFIED Requirements

### Requirement: Generated workbooks are structurally sound

Verification SHALL confirm that each generated workbook opens without repair, contains the expected sheets, contains no cell resolving to an Excel error value, and carries no file-corruption artifacts.

#### Scenario: A clean workbook passes
- **WHEN** the generated workbooks contain the expected sheets and no error values
- **THEN** verification records a structural pass

#### Scenario: A formula error fails verification
- **WHEN** any cell in a generated workbook resolves to an Excel error value after recalculation
- **THEN** verification fails
- **AND** reports the sheet and cell location of at least the first such cell

#### Scenario: A corrupted file fails verification
- **WHEN** a generated workbook contains file-corruption artifacts that would trigger an Excel repair prompt
- **THEN** verification fails and identifies the affected file

Where the source template contains a formula that is undefined until an input the pipeline controls
is populated, the pipeline SHALL populate that input or fail. It SHALL NOT emit a workbook whose
error cells depend on which rows a given run happened to write, since that makes a latent defect
appear and disappear with unrelated changes.

#### Scenario: An undefined denominator stops the run
- **WHEN** the pipeline is about to write a workbook in which a template formula would divide by an
  empty value the pipeline is responsible for supplying
- **THEN** the run fails and names the cells that would be undefined
- **AND** no deliverable is produced

#### Scenario: A latent defect does not depend on which rows were written
- **WHEN** a cost line is added to or removed from what the pipeline writes
- **THEN** whether the generated workbook contains error cells does NOT change as a result
