## Purpose

Fixes which template the client budget deliverable is built on — Savills' current standard form —
and guarantees that adopting a new version of that form carries the full standard sheet set into
the deliverable while preserving every figure the pipeline already writes and introducing no
spreadsheet formula errors.

**Data scope**: this capability changes only which spreadsheet template the deliverable generator
opens and the sheets the deliverable contains. It reads and writes no Generation A or Generation B
reference table and changes no Fact/Dim join key, so the Copilot Studio package's live data is
unaffected. No budget figure changes in value.

## Requirements

### Requirement: The deliverable is built on the current standard template

The client budget deliverable SHALL be generated from the template file that Savills has designated
as the current standard residential budget form, held in the project's template folder. A superseded
template version SHALL be retained in the same folder, marked superseded, rather than deleted.

#### Scenario: The deliverable carries the standard sheet set

- **WHEN** a budget deliverable is generated
- **THEN** it SHALL contain every sheet the standard template defines
- **AND** the sheet names SHALL match the standard template's names

#### Scenario: The superseded template is kept

- **WHEN** the standard template is replaced by a newer version
- **THEN** the previous version SHALL remain in the template folder, identifiable as superseded

### Requirement: Switching the template preserves every figure the pipeline writes

Changing which template version the deliverable is built on SHALL NOT change the value of any budget
line the pipeline writes. Every code the pipeline populates SHALL receive the same figure, in the
same currency and unit, as before the switch. A line the pipeline does not write MAY differ if the
templates carry different built-in defaults for it, but every such difference SHALL be identified
and recorded with its cause.

#### Scenario: Pipeline-written lines are unchanged in value

- **WHEN** the same project input is run against the old template and the new template
- **THEN** every budget line the pipeline populates holds the same value in VND in both outputs
- **AND** the recorded verification baseline figures are unchanged, or are re-recorded with a stated
  reason if a spreadsheet recalculation shifts only rounding

#### Scenario: A non-written line whose template default differs is recorded, not silently accepted

- **WHEN** a line the pipeline does not write holds a different value on the new template because
  the templates ship different built-in defaults for it
- **THEN** that line, both values, and the cause SHALL be recorded in the change
- **AND** the net effect on the deliverable's totals SHALL be quantified

#### Scenario: A leaf row that moved is caught, not written blind

- **WHEN** a code the pipeline writes does not sit at the expected row in the new template
- **THEN** generation SHALL stop and name the code and the mismatch
- **AND** SHALL NOT write the figure to whatever row is now at that position

### Requirement: New sheets are carried as scaffolding without feeding totals or adding broken references

Where the standard template adds sheets the pipeline does not yet populate, those sheets SHALL be
present with their own structure and formulas. They MAY retain the template's own example values and
MAY show divide-by-empty (`#DIV/0!`) cells **while their inputs are unfilled and no change has yet
been made to fill them** — the superseded template already does. They SHALL NOT feed any figure in
the deliverable's budget totals, and switching to the new template SHALL NOT introduce any
broken-reference error (`#REF!`, `#NAME?`, `#VALUE!`) that the superseded template did not already
have.

Two further constraints apply to **any** sheet in the deliverable, not only newly added scaffolding:

- The pipeline SHALL NOT write a value into a sheet whose cells no formula anywhere in the
  deliverable reads. A figure that sheet was meant to carry SHALL instead be computed and placed
  where the deliverable actually consumes it.
- A sheet the pipeline **does** write a value into SHALL NOT ship with a spreadsheet error cell that
  filling that sheet's own input cells would have resolved.

A sheet that cannot be carried without adding a broken-reference error — for example one linked to
an external workbook — SHALL NOT be included until it can be carried cleanly.

#### Scenario: An unpopulated standard sheet is present and inert

- **WHEN** the deliverable is generated and a standard sheet has no pipeline fill yet
- **THEN** that sheet SHALL be present in the deliverable
- **AND** no budget total elsewhere in the deliverable SHALL depend on any cell of that sheet

#### Scenario: The template switch adds no broken-reference errors

- **WHEN** the blank new template is recalculated and compared with the blank superseded template
- **THEN** the new template SHALL have no `#REF!`, `#NAME?` or `#VALUE!` cell that the superseded
  template did not already have
- **AND** any additional `#DIV/0!` cells SHALL be confined to sheets whose inputs a later change fills

#### Scenario: The generated deliverable is free of formula errors

- **WHEN** a filled deliverable is generated on the new template and recalculated
- **THEN** its count of cells resolving to a spreadsheet error value SHALL not exceed the recorded
  ceiling maintained by `deliverable-total-integrity`, and that ceiling SHALL only ever be lowered

#### Scenario: The pipeline does not write to a sheet nothing reads

- **WHEN** no formula in the deliverable reads any cell of a sheet
- **THEN** the pipeline SHALL NOT write rates, counts or other values into that sheet

#### Scenario: A written helper sheet carries no resolvable error

- **WHEN** the pipeline writes a value into a helper sheet whose formulas some other sheet does read
- **THEN** that helper sheet SHALL recalculate with no error cell that its own inputs would have
  resolved

#### Scenario: A sheet that would carry errors is excluded and recorded

- **WHEN** a standard sheet cannot be carried into the deliverable without leaving unresolved
  external references or error values
- **THEN** that sheet SHALL be omitted from the deliverable template
- **AND** the omission SHALL be recorded with its reason and the change that will restore it
