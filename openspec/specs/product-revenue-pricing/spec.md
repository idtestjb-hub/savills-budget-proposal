## Purpose

Defines how the pipeline prices management-fee revenue for every product type a project contains,
so that the client deliverable reports the same revenue as the analysis that explains it, and so
that a reader can tell which rates are real and which are substitutions.

**Data scope**: this capability changes which revenue rows are written to the generated workbooks.
It reads the existing Generation B comparable data (`Dim_Property_Residential.csv` per-product
`Fee_*` columns) and writes no data of its own; no Generation A or Generation B table is modified,
and no Fact/Dim join key changes, so the Copilot Studio package's live data is unaffected.

## Requirements

### Requirement: Every product a project contains is priced

The pipeline SHALL price management-fee revenue for each product type the project reports an area
for, not for Apartment alone. Each product's revenue SHALL be written to that product's own row in
the client deliverable.

#### Scenario: A mixed-use project prices every product

- **WHEN** a project reports chargeable area for more than one product type
- **THEN** each of those products SHALL have its own revenue figure in the client deliverable
- **AND** the total management-fee revenue SHALL be the sum of those figures

#### Scenario: A product with no area is left alone

- **WHEN** a project reports zero or no area for a product type
- **THEN** that product's revenue row SHALL be left blank rather than written as zero

#### Scenario: An Apartment-only project is unaffected

- **WHEN** a project contains only Apartment area
- **THEN** its total management-fee revenue SHALL be unchanged from what the pipeline produced before
  this capability existed

### Requirement: The two workbooks report the same revenue

The client deliverable and the internal analysis workbook SHALL report the same management-fee
revenue for the same project. Both SHALL derive their rates from comparable projects selected and
ranked by the **same matching method** — the project's total building net floor area (Total NFA, in
m²) refined by the project's own location — so that neither workbook can pick different comparable
projects, or weight them differently, for the same input. Location ranking SHALL account for the
project's district and city in addition to Total NFA, such that a comparable in the same district as
the project SHALL rank at least as favorably as an equally-NFA-distant comparable in a different
district. Within whichever district/city tier a comparable already falls into, one whose Total NFA
sits within the size-similarity band of the project's own Total NFA SHALL rank at least as favorably
as an otherwise-equivalent comparable that does not, and this preference SHALL be checked before
verification status — a comparable within the size-similarity band SHALL NOT be outranked by one
outside it purely because the latter is individually-verified. Within whichever district/city tier,
size-similarity grouping, and coordinate-precision grouping a comparable already falls into, a
comparable backed by a real, individually-verified budget workbook SHALL rank at least as favorably
as an otherwise-equivalent comparable that is not, but this preference SHALL NOT let an
individually-verified comparable outrank a real, more location-precise comparable — precision-of-match
takes priority over verification status, not the reverse. Ranking SHALL NOT fail, error, or return an
empty comparable set solely because no candidate clears the size-similarity band — it SHALL fall back
to the nearest available comparable by Total NFA. Where one workbook shows its comparables to the
reader, it SHALL present them in the same ranked order the matching method produces, SHALL label the
matching basis actually used (not always "Total NFA" — the label SHALL reflect location when location
narrowed the pool, and SHALL state when a shown comparable is individually-verified), and SHALL state
when a shown comparable's Total NFA differs from the project's own by more than the size-similarity
band.

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
  same set, in the same order
- **AND** any comparables table shown to a reader SHALL be ordered by the matching method actually
  used and labelled accordingly

#### Scenario: A same-district comparable is preferred over an equally-close different-district one

- **WHEN** the comparable pool contains two projects equally distant from this project's Total NFA,
  one in this project's own district and one in a different district
- **THEN** the same-district comparable SHALL rank at or above the different-district comparable

#### Scenario: A project's own district has no comparable

- **WHEN** no comparable project shares this project's district or city
- **THEN** ranking SHALL fall back to today's Total-NFA-only ordering, refined by the size-similarity
  preference below
- **AND** SHALL NOT fail, error, or return an empty comparable set

#### Scenario: A similarly-sized comparable is preferred over a badly-sized verified one

- **WHEN** the comparable pool, within the same district/city tier, contains a candidate whose Total
  NFA sits within the size-similarity band of the project's own Total NFA and is not
  individually-verified, and another candidate that IS individually-verified but whose Total NFA
  sits outside that band
- **THEN** the similarly-sized, non-verified candidate SHALL rank at or above the badly-sized,
  verified one

#### Scenario: No candidate clears the size-similarity band

- **WHEN** every candidate in the project's own district/city tier sits outside the size-similarity
  band
- **THEN** ranking SHALL fall back to the nearest available comparable by Total NFA, exactly as it
  did before this requirement existed
- **AND** SHALL NOT fail, error, or return an empty comparable set

#### Scenario: A comparable outside the size-similarity band is disclosed

- **WHEN** a comparable shown to the reader has a Total NFA more than the size-similarity band away
  from the project's own
- **THEN** the matching-basis text SHALL state that its size differs beyond the band, in the
  language the surrounding text is written in

#### Scenario: An individually-verified comparable is preferred over an equally-ranked one that isn't

- **WHEN** the comparable pool, within the same district/city tier, size-similarity grouping, and
  coordinate-precision grouping, contains both an individually-verified project and one that is not
- **THEN** the individually-verified comparable SHALL rank at or above the non-verified one

#### Scenario: A precise location match is not displaced by verification status

- **WHEN** a real, coordinate-precise comparable exists for the project and an individually-verified
  comparable exists only outside that precision grouping (a different tier, or no usable coordinates)
- **THEN** the coordinate-precise comparable SHALL still rank ahead of the individually-verified one

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

### Requirement: A product without a real rate falls back to the Apartment rate, and says so

Where the comparable data holds no per-product rate for a product type, the pipeline SHALL price it
at the project's derived Apartment rate. It MUST NOT invent, interpolate or guess a rate.

#### Scenario: A product with a real rate uses it

- **WHEN** the comparable data holds a per-product rate for a product the project contains
- **THEN** that product SHALL be priced at its own derived rate
- **AND** the output SHALL identify the comparables the rate came from

#### Scenario: A product without a real rate falls back

- **WHEN** the comparable data holds no per-product rate for a product the project contains
- **THEN** that product SHALL be priced at the derived Apartment rate
- **AND** the output SHALL state that this is a substitution and that no product-specific rate exists

#### Scenario: The reader can tell the two apart

- **WHEN** a budget contains both a really-rated product and a fallback-rated one
- **THEN** the output SHALL distinguish them, so no fallback is presented as a real product rate

### Requirement: The intake form can express every product the pipeline prices

The intake form SHALL provide a field for each product type the pipeline is able to price, so that a
project containing that product can be quoted.

#### Scenario: A project with villas can be quoted

- **WHEN** a project contains villa area
- **THEN** the intake form SHALL provide somewhere to record it
- **AND** the generated budget SHALL price it

#### Scenario: Products the pipeline cannot price are not offered

- **WHEN** a product type has no revenue row the pipeline writes
- **THEN** the intake form SHALL NOT imply that entering an area for it will produce revenue

### Requirement: The revenue change is measurable and deliberate

The effect of this change on reported revenue SHALL be visible and recorded, not absorbed silently.

#### Scenario: Verification detects the change

- **WHEN** verification is run after this change with the previously recorded baseline in place
- **THEN** it SHALL fail
- **AND** it SHALL name each figure that moved, with its recorded and current values

#### Scenario: The baseline is re-recorded with a reason

- **WHEN** the differences have been reviewed and accepted
- **THEN** the baseline SHALL be re-recorded with a stated reason identifying this change
- **AND** verification SHALL pass on the following run
