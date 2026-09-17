## MODIFIED Requirements

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
