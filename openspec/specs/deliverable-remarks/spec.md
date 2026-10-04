## Purpose

Defines how the client deliverable explains the reasoning behind its figures: a composed section
narrative on the grand-total sheet (`1. Summary`) built to the AI Guideline's own recipe, in the
guideline's own wording style, with the mandatory VAT-treatment sentence — so a PM can hand the
budget to a client and every total says where it came from.

**Generation**: this capability governs the **Generation A** deliverable-writing pipeline only
(`generate_project_budget.py`, with the shared VAT helper also used by the analysis-facing
`_opex_remark`). It reads only what the pipeline already reads, modifies no Generation A or
Generation B table, and changes no Fact/Dim join key — the Copilot Studio package's live data is
unaffected. No budgeted figure changes; remarks are text.

## Requirements

### Requirement: The grand-total sheet composes a narrative for every section total it reports

For every PART-1 total on `1. Summary` that carries a non-zero figure, the deliverable SHALL write a
composed remark in the sheet's Remarks column, generated from the project's own data — not left
blank, and not a copy of a single line item's remark. A total that is zero MAY be left without a
narrative.

#### Scenario: A non-zero section total has a narrative

- **WHEN** the deliverable is generated and a PART-1 total on `1. Summary` is non-zero
- **THEN** that total SHALL have a composed remark in the Remarks column
- **AND** the remark SHALL be derived from this project's inputs, not a fixed string that ignores
  the project

#### Scenario: A blank pull is replaced

- **WHEN** the standard template ships a `1. Summary` Remarks cell that pulls a single line's remark
  from the detail sheet, or leaves it blank
- **THEN** the pipeline SHALL overwrite it with the composed section narrative

### Requirement: An aggregate total's narrative names every child line that has a figure

Where a `1. Summary` total sums a group of detail lines (for example other operating income,
administrative expense, bank and audit, M&E operation, accreditation, repairs and maintenance), its
narrative SHALL enumerate, by item name, every child line the pipeline wrote a figure to, as a
bulleted list (one child per line, matching the AI Guideline's own worked-example format). It SHALL
NOT list a line that carries no figure.

#### Scenario: Every funded child is listed

- **WHEN** an aggregate `1. Summary` total is composed and the pipeline wrote figures to some of its
  child lines
- **THEN** the narrative SHALL name each of those child lines
- **AND** SHALL omit the child lines that carry no figure

### Requirement: A computed total's narrative follows the guideline recipe for that code

Where the costing catalogue records a composition recipe for a `1. Summary` row, the narrative for
that row SHALL contain each part the recipe lists, filling the guideline's own note text (its
`....` placeholders) with this project's own data rather than a generic paraphrase. In particular:

- the management-fee total SHALL state the chargeable area by product, the applied fee rate by
  product with its VAT status, and the developer pre-collection assumption — including how many
  months of the fee the developer collects on handover when that figure has been entered for the
  project, and describing the mechanism without a month count when it has not;
- the security and cleaning totals SHALL state the staffing positions broken out by role and the
  unit rate;
- the water, electricity and diesel totals SHALL state the assumed consumption, the tariff with the
  legal reference the catalogue names, and the occupancy basis;
- where the recipe names a fixed legal sentence, the narrative SHALL include it.

A recipe part with no corresponding project data SHALL be described qualitatively rather than
filled with an invented number.

#### Scenario: A recipe part is missing

- **WHEN** a `1. Summary` total's catalogue recipe lists parts and one is absent from the composed
  narrative
- **THEN** verification SHALL fail and name the total and the missing part

#### Scenario: A code with no recipe

- **WHEN** a non-zero `1. Summary` total has no catalogue recipe
- **THEN** the aggregate-listing requirement above SHALL still apply, and no additional part check
  SHALL be imposed

#### Scenario: A recipe part has no project data behind it

- **WHEN** a recipe part depends on a project fact the intake form has not captured (for example the
  developer's handover pre-collection term)
- **THEN** the narrative SHALL describe the underlying mechanism without a fabricated figure
- **AND** SHALL state the real value once the project's own data provides it

### Requirement: Every remark for an inclusive-of-VAT figure carries the VAT-treatment sentence

When the workbook's VAT-treatment switch (`2. Budget-Management Fund!F7`, the "Mô hình tài chính"
selector — `KHOÁN` / `KHÔNG KHOÁN` / `THU HỘ CHI HỘ`) is set so that figures include VAT, every
remark the pipeline writes for a cost or revenue figure — line-level and composed — SHALL contain
the guideline's VAT-treatment sentence, naming that the figure includes VAT and the budget year it
was estimated for. When the switch is set to the exclusive-of-VAT option (`KHOÁN`), the sentence
SHALL NOT be added. A single shared helper SHALL produce this sentence for both the line-level and
the composed remarks, keyed on the same switch.

#### Scenario: Inclusive-of-VAT run

- **WHEN** `2. Budget-Management Fund!F7` selects an inclusive-of-VAT treatment (`KHÔNG KHOÁN` or
  `THU HỘ CHI HỘ`) and the pipeline writes a remark for a figure
- **THEN** that remark SHALL contain the VAT-treatment sentence with the budget year

#### Scenario: Exclusive-of-VAT run

- **WHEN** `2. Budget-Management Fund!F7` selects the exclusive-of-VAT treatment (`KHOÁN`)
- **THEN** no remark SHALL carry the VAT-treatment sentence

### Requirement: `0. Info` states each priced product's area basis

For every product row `0. Info` prices (Apartment/Officetel/Office/Shophouse and any other product
with a fee-table row), the deliverable SHALL write a remark stating the area's basis and the year
it was last confirmed, using the project's own "Area basis / drawing reference" intake field when
the PM has supplied one. When that field is blank, the remark SHALL say the area is PM-supplied
without inventing a drawing or legal citation.

#### Scenario: A PM-supplied area basis is shown

- **WHEN** the deliverable is generated and the PM has entered an area basis / drawing reference
  for a priced product
- **THEN** that product's `0. Info` remark SHALL state the basis text and the confirmation year
  entered

#### Scenario: No area basis was supplied

- **WHEN** a priced product has no area basis / drawing reference entered
- **THEN** its `0. Info` remark SHALL state the area is PM-supplied, without a fabricated drawing
  or legal citation

### Requirement: `A2`/`A3` carry every canonical position's duty description

The standard deliverable template already carries the AI Guideline's full duty description for
every canonical Security (`A2`) and Cleaning (`A3`) position, as its own shipped content — the
pipeline SHALL NOT overwrite it, and SHALL NOT need to write it. The deliverable SHALL still carry
that description, unmodified, for every canonical position the template defines.

#### Scenario: A canonical position keeps its template description

- **WHEN** the deliverable is generated
- **THEN** every canonical position defined on `A2`/`A3` SHALL still carry the template's own duty
  description, exactly as shipped

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

### Requirement: Unit labels inside a Vietnamese remark are Vietnamese

A consumption figure quoted in a Vietnamese remark (on `1. Summary` or a fund sheet's column T)
SHALL carry its unit in Vietnamese: "m3/tháng" for water, "kWh/tháng" for electricity, "lít/tháng"
for diesel. The unit's source data and the internal analysis workbook MAY keep their English units;
only the client-facing Vietnamese text changes.

#### Scenario: The water remark quotes monthly consumption

- **WHEN** the pipeline writes the water (EEW) remark
- **THEN** the consumption figure SHALL read in "m3/tháng", not "m3/month"

#### Scenario: The electricity and diesel remarks quote monthly consumption

- **WHEN** the pipeline writes the electricity (EEE) or diesel (EED) remark
- **THEN** the consumption figure SHALL read in "kWh/tháng" or "lít/tháng" respectively

#### Scenario: A remark still carrying an English unit fails verification

- **WHEN** verification runs and a composed energy narrative on `1. Summary` lacks its Vietnamese
  unit ("m3/tháng" for water, "kWh/tháng" for electricity, "lít/tháng" for diesel)
- **THEN** verification SHALL fail and name the narrative and the missing part

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

### Requirement: Verification confirms the extended remark coverage

Verification SHALL open the generated deliverable, and fail when: a priced `0. Info` product has no
area-basis remark; or a canonical `A2`/`A3` position (per the recorded canonical-position reference)
does not carry its duty description. This check SHALL run on every verification run and SHALL NOT
depend on a recorded numeric baseline, matching the existing remark-content check's independence
from baseline comparison.

#### Scenario: A missing `0. Info` remark fails the run

- **WHEN** verification runs and a priced product on `0. Info` has no area-basis remark
- **THEN** verification SHALL fail and name the product

#### Scenario: A missing canonical description fails the run

- **WHEN** verification runs and a canonical `A2`/`A3` position does not carry its recorded duty
  description
- **THEN** verification SHALL fail and name the position
