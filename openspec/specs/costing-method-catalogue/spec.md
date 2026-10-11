## Purpose

Holds Savills' costing method for each budget code as a structured, version-controlled record —
method, inputs, required remark components, legal citation, source sheet — extracted from the
AI Guideline residential budget form, so the pipeline and the verification harness can consult one
method authority instead of re-reading a prose column in a workbook.

**Data scope**: this capability adds one new reference file to the repository and reads the two
Savills workbooks in `docs/` as source material. It reads no Generation A or Generation B table,
writes none, and changes no Fact/Dim join key, so the Copilot Studio package's live data is
unaffected. It changes no budget figure on its own — it is the record that later changes act on.

## Requirements


### Requirement: The catalogue records one method entry per budget code it covers

The project SHALL hold a machine-readable catalogue with, for each budget code it covers, at least:
the code, a short canonical method name, a plain-language method description, the named inputs the
method needs, whether the code's figure varies month by month with occupancy, the components its
generated remark must contain, any legal reference the remark must cite, and the guideline sheet the
instruction was read from.

#### Scenario: A covered code has a complete entry

- **WHEN** the catalogue covers a budget code
- **THEN** that code's entry SHALL state its method, its inputs, its occupancy behaviour, its
  required remark components, and its source sheet
- **AND** SHALL state a legal reference where the guideline requires the remark to cite one

#### Scenario: The catalogue is read without opening the guideline workbook

- **WHEN** the pipeline or the verification harness needs the method for a code
- **THEN** it SHALL obtain that method from the catalogue file
- **AND** SHALL NOT need to parse the AI Guideline workbook at run time

### Requirement: The catalogue is authoritative for method selection; the logic workbook for formula mechanics

Where the catalogue and `EXENSIVE LOGIC.xlsx` both describe a code, the catalogue's method name
SHALL determine which method is used, and `EXENSIVE LOGIC.xlsx` SHALL remain the source for the
detailed formula — coefficients, rounding, frequency — where the two agree on the method.

#### Scenario: The two documents name different methods

- **WHEN** the catalogue and `EXENSIVE LOGIC.xlsx` state different methods for the same code
- **THEN** the catalogue's method SHALL be the one used
- **AND** the catalogue entry SHALL record why it differs

#### Scenario: The two documents agree on method but only one carries the formula

- **WHEN** both documents name the same method and `EXENSIVE LOGIC.xlsx` carries the detailed formula
- **THEN** that formula SHALL apply
- **AND** the catalogue entry SHALL mark the relationship as mechanics-only

#### Scenario: A code the catalogue does not yet cover

- **WHEN** a code has no catalogue entry
- **THEN** `EXENSIVE LOGIC.xlsx` alone SHALL be the method authority for that code
- **AND** the code SHALL be identifiable as not yet catalogued, distinct from having no method

### Requirement: Every occupancy-driven code is flagged as such

For each code whose figure the guideline links to the resident or parking fill-up schedule, the
catalogue entry SHALL mark the code as occupancy-scaled, so that later work can compute it month by
month rather than as a flat year.

#### Scenario: A revenue or load-driven code is flagged

- **WHEN** the guideline instructs that a code's monthly figures follow the fill-up schedule
- **THEN** the catalogue entry for that code SHALL be marked occupancy-scaled

#### Scenario: A fixed code is not flagged

- **WHEN** the guideline gives a code a single annual or contract figure with no fill-up link
- **THEN** the catalogue entry SHALL NOT be marked occupancy-scaled

### Requirement: An unclear instruction is marked, not resolved by guessing

Where a guideline instruction cannot be turned into a definite method without an assumption that has
no source, the catalogue entry SHALL record the method as unclear and quote the source text, rather
than record a method the guideline does not state.

#### Scenario: An ambiguous instruction is preserved

- **WHEN** a guideline instruction is ambiguous about which method applies
- **THEN** the catalogue entry SHALL mark the method unclear and quote the instruction
- **AND** SHALL NOT record a specific method chosen by the extractor

### Requirement: The catalogue names the guideline version it was extracted from

The catalogue SHALL identify the AI Guideline file and its date, so that a later revision of the
Savills template can be detected as a divergence from the catalogue.

#### Scenario: Source identification is present

- **WHEN** the catalogue is read
- **THEN** it SHALL state the source file name and the guideline version or date it reflects

#### Scenario: The template code list has changed

- **WHEN** the current template's budget code list differs from the one the catalogue was extracted
  against
- **THEN** the difference SHALL be reportable against the catalogue's recorded source version

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

### Requirement: A method that departs from the AI Guideline records who approved it

Where the catalogue records, for a code, a method different from the one the AI Guideline
instructs, that entry SHALL state four things:
- that it departs from the guideline;
- what the guideline itself says for the code;
- who approved the departure, and on what date;
- where the decision is recorded.

Verification's method-fidelity report SHALL treat an approved departure as the expected method for
that code. It SHALL report an entry that departs from the guideline without an approval record as a
mismatch.

The collect-on-behalf codes this change writes (`RO3.*` and `RO4.*`, and the expense lines paired
with them) SHALL each carry such an entry, together with the pairing between each revenue line and
its expense line. The entry SHALL keep the guideline's "not estimated" treatment, including its
remark, as the behaviour when no amount is entered. A project that enters no amount SHALL get the
same method-fidelity result and the same remarks as before this requirement.

This writes `Costing_Method_Catalogue.csv`: entries for the collect-on-behalf codes only. It moves
no recorded baseline figure.

#### Scenario: An approved departure is visible

- **WHEN** a reader opens the catalogue entry for `RO3.A`
- **THEN** the entry SHALL say that the guideline marks the line "not estimated"
- **AND** SHALL name the approver, the date and the decision record
- **AND** SHALL name the expense line paired with it

#### Scenario: A departure without approval is a mismatch

- **WHEN** a catalogue entry records a method different from the guideline's and carries no approval record
- **THEN** the method-fidelity report SHALL list that code as a mismatch

#### Scenario: A project with no amounts is judged as before

- **WHEN** verification runs on the standard synthetic project, which enters no collect-on-behalf
  amount, after the catalogue entries change
- **THEN** its method-fidelity figure and its remark assertions SHALL be the same as before

#### Scenario: Other entries are unchanged

- **WHEN** the catalogue is compared before and after this change
- **THEN** only the collect-on-behalf entries SHALL differ
