## MODIFIED Requirements

### Requirement: The deliverable is built on the current standard template

The client budget deliverable SHALL be generated from the template file that Savills has designated
as the current standard residential budget form, held in the project's template folder. A superseded
template version SHALL be retained in the same folder, marked superseded, rather than deleted.

The deliverable's sheet set SHALL be the standard template's own sheets plus, for a project whose
budget horizon covers more than one phase, one further management-fund sheet and one further
common-area-fund sheet per additional phase. Those per-phase sheets SHALL be named to a single stated
pattern that identifies the phase each one covers, SHALL carry the same structure, formulas and row
codes as the template sheet they derive from, and SHALL resolve their cross-sheet references to the
sheets of their own phase rather than to another phase's. A project whose horizon is a single
operating year SHALL carry exactly the template's own sheet set under the template's own names.

#### Scenario: The deliverable carries the standard sheet set

- **WHEN** a budget deliverable is generated for a single-operating-year project
- **THEN** it SHALL contain every sheet the standard template defines
- **AND** the sheet names SHALL match the standard template's names

#### Scenario: A multi-phase project carries per-phase sheets

- **WHEN** a budget deliverable is generated for a project whose horizon covers more than one phase
- **THEN** it SHALL contain every sheet the standard template defines
- **AND** SHALL contain one further management-fund sheet and one further common-area-fund sheet per
  additional phase, named to the stated per-phase pattern

#### Scenario: A per-phase sheet references its own phase

- **WHEN** a per-phase sheet carries a formula that referenced another sheet on the template it
  derives from
- **THEN** that formula SHALL reference the corresponding sheet of its own phase
- **AND** SHALL NOT reference another phase's sheet

#### Scenario: A per-phase sheet keeps the template's structure

- **WHEN** a per-phase sheet is created from the template's fund sheet
- **THEN** every row code on it SHALL sit at the same position as on the sheet it derives from
- **AND** the generated deliverable SHALL contain no cell resolving to a spreadsheet error value

#### Scenario: The superseded template is kept

- **WHEN** the standard template is replaced by a newer version
- **THEN** the previous version SHALL remain in the template folder, identifiable as superseded
