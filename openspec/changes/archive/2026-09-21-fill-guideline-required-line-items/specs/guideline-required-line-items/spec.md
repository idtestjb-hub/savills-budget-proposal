## Purpose

Ensures the deliverable actually prices every budget-line code the AI Guideline classifies as
"Bắt buộc/Required," sourcing each one from the most itemized real comparable-property data
available rather than settling for a blended figure when a more detailed source exists.

## ADDED Requirements

### Requirement: Every code the AI Guideline classifies as Required is recorded

The pipeline's reference data SHALL carry a recorded Required/Optional/Standard classification for
every budget-line code the AI Guideline defines one for, transcribed directly from the guideline's
own classification column — not inferred, not guessed.

#### Scenario: A code's classification is looked up

- **WHEN** the pipeline or a verification check needs to know whether a code is Required
- **THEN** it SHALL read that classification from the recorded reference, sourced from the
  guideline file's own column, not from a hardcoded guess

### Requirement: Every Required code carries a non-zero figure on the deliverable

For every code the recorded reference classifies as Required, the generated deliverable SHALL
carry a non-zero figure for that code, UNLESS the project genuinely has no basis for that cost
(for example, a pool-related Required code on a project with no pool).

#### Scenario: A Required code with an available pricing method is filled

- **WHEN** the deliverable is generated and a Required code has a pricing method recorded in the
  costing catalogue
- **THEN** that code's own leaf row SHALL carry the resulting figure — not folded into an
  unrelated catch-all row instead of its own line

#### Scenario: A Required code genuinely does not apply to this project

- **WHEN** a Required code's basis does not exist for this specific project (e.g. no pool, no
  garden)
- **THEN** that code MAY be zero, and the reason SHALL be stated rather than silently left blank

### Requirement: A Required code is priced from the most itemized comparable source available

Where more than one real comparable-property source could inform a Required code's pricing, and
those sources disagree on granularity — one gives a single blended figure across several line
items, another carries the individual line items separately — the pipeline SHALL price from the
itemized source, not the blended one, and SHALL show the itemized breakdown rather than
re-collapsing it into one figure.

#### Scenario: One comparable source is blended and another is itemized

- **WHEN** a Required code family's only currently-used comparable source gives one combined
  figure across several of that family's individual codes, and another available comparable
  source has each of those codes priced separately
- **THEN** the pipeline SHALL price the individual codes from the itemized source

#### Scenario: Only a blended source exists

- **WHEN** no comparable source carries the itemized breakdown for a Required code family
- **THEN** the pipeline MAY continue to fold that family into a catch-all, and SHALL state on the
  catch-all's remark that the underlying source was blended, not itemized

### Requirement: Verification confirms every Required code is filled

Verification SHALL open the generated deliverable, and fail when a code the recorded reference
classifies as Required carries a zero figure with no stated reason. This check SHALL run on every
verification run.

#### Scenario: An unexplained zero on a Required code fails the run

- **WHEN** verification runs and a Required code is zero with no stated reason for this project
- **THEN** verification SHALL fail and name the code
