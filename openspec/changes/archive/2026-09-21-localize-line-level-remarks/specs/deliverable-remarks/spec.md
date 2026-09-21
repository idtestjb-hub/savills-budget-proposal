## MODIFIED Requirements

### Requirement: The composed summary narratives are Vietnamese

Each composed `1. Summary` narrative SHALL be written in Vietnamese, matching the language and
wording style of the AI Guideline's own note text and the worked sample's demonstrated usage. Every
line-level remark on the detail sheet (`2. Budget-Management Fund`/`2.2 Common area Fund`, column T)
that the pipeline writes SHALL also be written in Vietnamese — both a computed cost/revenue narrative
(where the pipeline priced the code from this project's own data) and a flagged-zero / no-method
remark (where the pipeline explains why a code was left at zero). A flagged-zero remark's Vietnamese
text SHALL describe the reason in plain terms and SHALL NOT name an internal source file (for example
`Costing_Method_Catalogue.csv`) or other engineering artifact; that citation MAY be kept in a code
comment for engineering reference but not in the cell text. The VAT-treatment sentence SHALL also be
Vietnamese, as before.

#### Scenario: A composed narrative is Vietnamese

- **WHEN** a `1. Summary` narrative is composed
- **THEN** it SHALL be written in Vietnamese
- **AND** SHALL NOT require an English counterpart to be understood

#### Scenario: A computed line-level remark is Vietnamese

- **WHEN** the pipeline writes a line-level remark on the detail sheet for a code it priced from this
  project's own data
- **THEN** that remark SHALL be written in Vietnamese
- **AND** SHALL NOT require an English counterpart to be understood

#### Scenario: A flagged-zero remark is Vietnamese and names no internal file

- **WHEN** the pipeline writes a remark stating that a code has no pricing method and was left at zero
- **THEN** that remark SHALL be written in Vietnamese
- **AND** SHALL NOT name an internal source file or other engineering artifact in the cell text

### Requirement: Verification confirms remark content on every run

Verification SHALL open the generated deliverable, and fail when: a non-zero `1. Summary` PART-1
total has no composed narrative; an aggregate total's narrative omits a child line that has a
figure; a total's catalogue recipe part is absent from its narrative; a composed narrative carries
no Vietnamese content; a non-blank line-level remark carries no Vietnamese content; a line-level
remark names an internal source file or artifact in its text; or, on an inclusive-of-VAT run, a
written remark for a figure lacks the VAT-treatment sentence. This check SHALL run on every
verification run and SHALL NOT depend on a recorded numeric baseline.

#### Scenario: A missing narrative fails the run

- **WHEN** verification runs and a non-zero PART-1 total on `1. Summary` has no composed narrative
- **THEN** verification SHALL fail and name the total

#### Scenario: An unlisted funded child fails the run

- **WHEN** an aggregate total's narrative does not name a child line that carries a figure
- **THEN** verification SHALL fail and name the total and the omitted child

#### Scenario: A non-Vietnamese line-level remark fails the run

- **WHEN** verification runs and a non-blank line-level remark carries no Vietnamese content
- **THEN** verification SHALL fail and name the code and the row

#### Scenario: A line-level remark naming an internal file fails the run

- **WHEN** verification runs and a line-level remark's text names an internal source file or artifact
- **THEN** verification SHALL fail and name the code, the row, and the artifact named

#### Scenario: Remarks are not a baselined figure

- **WHEN** a verification run compares the deliverable to its recorded baselines
- **THEN** the remark-content check SHALL run independently of that comparison, and changing a
  remark's wording SHALL NOT move any baselined figure
