## MODIFIED Requirements

### Requirement: The two workbooks report the same revenue

The client deliverable and the internal analysis workbook SHALL report the same management-fee
revenue for the same project. Both SHALL derive their rates from comparable projects selected and
ranked on the **same size measure — the project's total building net floor area (Total NFA, in
m²)** — so that neither workbook can pick different comparable projects, or weight them
differently, for the same input. Where one workbook shows its comparables to the reader, it SHALL
present them ranked by their distance from this project's Total NFA and label that as the matching
basis.

#### Scenario: Both workbooks agree on total revenue

- **WHEN** both generators are run against the same input
- **THEN** the total management-fee revenue, in VND, SHALL match between the two workbooks within
  rounding

#### Scenario: Both workbooks agree per product

- **WHEN** both generators are run against the same input
- **THEN** each product's revenue, in VND, SHALL match between the two workbooks within rounding

#### Scenario: Both workbooks select the same comparable projects

- **WHEN** both generators are run against the same input
- **THEN** the set of comparable projects each uses to derive the management-fee rate SHALL be the
  same set
- **AND** any comparables table shown to a reader SHALL be ordered by distance from this project's
  Total NFA

#### Scenario: An apartment-dominant project's rate barely moves

- **WHEN** a project's Apartment NFA is at or close to its Total NFA
- **THEN** its derived management-fee rate SHALL move little or not at all from what the pipeline
  produced before this change

#### Scenario: A mixed-use project's deliverable rate moves onto the analysis basis

- **WHEN** a project has substantial non-apartment area (for example parking, retail or office) so
  its Apartment NFA is well below its Total NFA
- **THEN** the client deliverable's derived management-fee rate SHALL change to the value the
  analysis workbook derives for that project
- **AND** the change SHALL be recorded for a named real project with both the before and after
  values in VND

## ADDED Requirements

### Requirement: Verification enforces the two workbooks' revenue agreement

Verification SHALL run both generators against the synthetic sample and fail if their total
management-fee revenue, any product's revenue, or the derived management-fee rate disagree beyond
rounding. This check SHALL run on every verification run, not only when a recorded baseline is
being compared.

#### Scenario: The two generators agree

- **WHEN** verification runs and both generators select the same comparables and derive the same
  management-fee revenue for the sample project
- **THEN** verification records a pass for the cross-generator revenue check

#### Scenario: The two generators disagree

- **WHEN** the two generators derive different management-fee revenue, or different per-product
  revenue, or a different rate, for the sample project
- **THEN** verification fails
- **AND** names the figure that disagrees, with each workbook's value in VND
