## ADDED Requirements

### Requirement: The catalogue covers every code the guideline instructs on remark content

The catalogue SHALL hold an entry for every budget code whose `AI GUIDELINE` column in the source
form gives an instruction — not only the codes catalogued so far. Where an instruction states the
components a code's remark must contain, those components SHALL be recorded in the code's entry.

**Generation**: this adds rows and fields to the existing reference file only. It reads no Generation
A or Generation B table and changes no Fact/Dim join key.

#### Scenario: An instructed code is in the catalogue

- **WHEN** the source form's `AI GUIDELINE` column gives an instruction for a budget code
- **THEN** the catalogue SHALL have an entry for that code
- **AND** the entry SHALL record the components the instruction says its remark must contain

#### Scenario: A benchmark instruction is recorded as such

- **WHEN** the instruction says to price a code by benchmarking a comparable project
- **THEN** the entry SHALL record that the method is a comparable benchmark, so the remark states
  which comparable and on what basis

### Requirement: The catalogue records the composition recipe for each grand-total narrative

For every `1. Summary` row whose `AI GUIDELINE` column gives a composition recipe, the catalogue
SHALL record that recipe: the ordered parts the row's narrative must contain, which of the project's
inputs each part is drawn from, and any fixed sentence (legal or standard wording) the narrative
must include.

#### Scenario: A summary recipe is recorded

- **WHEN** a `1. Summary` row's `AI GUIDELINE` column lists the parts its narrative must contain
- **THEN** the catalogue SHALL record those parts in order, with the input source for each

#### Scenario: A fixed legal sentence is recorded verbatim

- **WHEN** a summary recipe names a fixed sentence the narrative must include (for example the
  accreditation rows' Housing Law reference)
- **THEN** the catalogue SHALL hold that sentence verbatim, so the pipeline emits it unchanged

### Requirement: The catalogue records the VAT-treatment sentence rule

The catalogue SHALL record the guideline's rule that a remark for an inclusive-of-VAT figure must
carry a VAT-treatment sentence, the exact sentence to use, and the workbook cell that selects the
VAT treatment.

#### Scenario: The VAT rule is available without the workbook

- **WHEN** the pipeline or the verification harness needs the VAT-treatment sentence and the cell
  that governs it
- **THEN** it SHALL obtain both from the catalogue
- **AND** SHALL NOT need to parse the AI Guideline workbook at run time
