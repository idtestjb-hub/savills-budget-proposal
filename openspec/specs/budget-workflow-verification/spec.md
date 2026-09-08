## Purpose

Provides a repeatable way to confirm that the core budget-generation workflow still runs and still produces the same figures, using synthetic data only, so that later changes to budget rules can be reviewed with evidence rather than by manually reading spreadsheets.

**Data scope**: this capability reads existing data and produces no new data of its own. It affects neither Generation A nor Generation B reference tables, and it does not change any Fact/Dim join key, so the Copilot Studio package's live data is unaffected.

## Requirements

### Requirement: Verification never touches production data

Verification SHALL operate entirely on synthetic sample data. It MUST NOT read, overwrite, or otherwise modify the live project input workbook, the generated analysis workbook, or any client deliverable.

#### Scenario: Production input is left untouched
- **WHEN** verification is run while a live project input workbook exists
- **THEN** that workbook is unchanged in both content and modification time
- **AND** no file in the shared reports or deliverable folders is created, altered, or deleted

#### Scenario: Verification works with no production data present
- **WHEN** verification is run on a machine where no live project input workbook exists
- **THEN** verification still completes and reports a result

### Requirement: Verification exercises the complete core workflow

Verification SHALL run the full core workflow for the synthetic project — both the client-deliverable generator and the internal analysis generator — in the order the documented run procedure specifies.

#### Scenario: Both outputs are produced
- **WHEN** verification is run against the synthetic sample project
- **THEN** both a client-format budget workbook and an internal analysis workbook are produced
- **AND** both carry the synthetic project's name

#### Scenario: A partial run is reported as a failure
- **WHEN** one of the two generators fails to complete
- **THEN** verification fails and names which generator did not complete

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

### Requirement: Numeric results are compared against a recorded baseline

Verification SHALL compare an agreed set of headline figures from the synthetic run against previously recorded baseline values. All figures SHALL be expressed in VND with the unit stated.

#### Scenario: Unchanged figures pass
- **WHEN** every compared figure matches its recorded baseline
- **THEN** verification records a numeric pass

#### Scenario: A changed figure fails and is identified
- **WHEN** any compared figure differs from its recorded baseline
- **THEN** verification fails
- **AND** reports the figure's name, its baseline value in VND, and its current value in VND

#### Scenario: An intentional change can be re-baselined
- **WHEN** a figure has changed because of an approved change and the baseline is deliberately updated
- **THEN** the new value is recorded together with a stated reason
- **AND** subsequent runs compare against the updated baseline

### Requirement: Verification reports its own strength honestly

Verification SHALL report which checking method was actually used. When full Excel recalculation is unavailable and a weaker file-level inspection is used instead, verification MUST state this explicitly rather than presenting a reduced check as a full one.

#### Scenario: Full recalculation is available
- **WHEN** Excel recalculation can be performed
- **THEN** the result states that a full recalculation check was performed

#### Scenario: Full recalculation is unavailable
- **WHEN** Excel recalculation cannot be performed
- **THEN** the result states that only a reduced check was performed
- **AND** states that formula errors visible only on recalculation were not detectable in this run

### Requirement: The real run procedure is documented and accurate

The change SHALL provide written documentation of how the project is actually run today, naming the real entry points in the order they must be executed, including the requirement to run both generators after any input change.

#### Scenario: Documented steps produce a working result
- **WHEN** a person follows the documented run procedure from a clean starting state
- **THEN** the workflow completes and produces both outputs

#### Scenario: The both-generators requirement is stated
- **WHEN** a reader consults the documented run procedure
- **THEN** it states that running only one generator leaves the two outputs describing different projects

### Requirement: Datasets present but unread are recorded without being connected

The change SHALL record an inventory of datasets that exist in the repository but are not read by the pipeline at runtime, each with evidence. It MUST NOT connect any of them, because doing so would move budget figures.

#### Scenario: An unread dataset is listed with evidence
- **WHEN** a dataset exists in the repository and no runtime code path reads it
- **THEN** it appears in the inventory with the evidence establishing that it is unread

#### Scenario: Recording an unread dataset changes no figure
- **WHEN** the inventory is produced
- **THEN** every baseline figure is unchanged
- **AND** no previously unread dataset has become read by the pipeline
