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

### Requirement: Each product's applied rate is decided once per run and shared by both workbooks

For each product a project prices, the pipeline SHALL decide the applied management-fee rate (VND
per m² per month) and the source of that rate exactly once per run. Every figure, remark and table
in either workbook that uses or shows a product's rate SHALL take it from that one decision. This
covers:
- the revenue rows on `2. Budget-Management Fund`;
- the `0. Info` fee table and its complete-total note;
- the `Comparison` sheet;
- the analysis workbook's `Management Fee`, `Comparison` and `Summary` sheets.

The order of sources SHALL be the same in both workbooks:
1. the comparable-derived rate, with the existing location rate-swing cap;
2. for a non-Apartment product with no comparable rate, the project's applied Apartment rate;
3. for Apartment, when no comparable carries an Apartment rate, the blended whole-property rate.
   Today only the deliverable has this step; the analysis workbook SHALL use the same one.

On its own, this requirement SHALL move no figure. It reads no data file the pipeline does not
already read, writes none, and no recorded baseline moves.

#### Scenario: Every place that shows the Apartment rate shows the same value

- **WHEN** both generators run against the same input
- **THEN** the Apartment rate SHALL be identical, in VND per m² per month, in each of these places:
  `0. Info` (Apartment fee cell), the `RM.AP` remark, the deliverable's `Comparison` sheet, and the
  analysis workbook's `Management Fee`, `Comparison` and `Summary` sheets

#### Scenario: Consolidation moves no figure

- **WHEN** the deliverable and the analysis workbook are generated before and after this requirement
  is implemented, from the same input, for the standard synthetic project and for one more project
  with at least three priced products
- **THEN** every formula and every number SHALL be identical between the before and after copies
- **AND** the comparison SHALL be recorded cell by cell

#### Scenario: The no-comparable fallback agrees across workbooks

- **WHEN** no comparable in the master table carries an Apartment rate
- **THEN** both workbooks SHALL apply the same fallback rate
- **AND** both SHALL say that the rate is a fallback

### Requirement: An entered real rate wins over the comparable-derived rate

The intake form SHALL offer two optional fields for each product type the pipeline prices:
- the product's real management-fee rate, in VND per m² per month;
- the VAT basis of that rate, either "includes VAT" or "excludes VAT".

Where a rate is entered for a product that has chargeable area, both workbooks SHALL price that
product at the entered rate. The entered rate SHALL rank ahead of the comparable-derived rate and
the Apartment-rate fallback, and the location rate-swing cap SHALL NOT apply to it. An entered
Apartment rate SHALL also be the fallback for any product that has neither an entered rate nor a
comparable rate.

The rate SHALL be applied as entered, with no VAT conversion. Where the entered VAT basis differs
from the basis the deliverable states for its figures, the line's remark and the run's printed
summary SHALL both say so.

A product with no entered rate that has its own comparable rate SHALL be priced exactly as it was
before this requirement. A product with neither SHALL follow the project's applied Apartment rate,
as before; that rate is the entered one when Apartment's rate is entered. The comparables SHALL
still be shown for reference, and any comparison against them SHALL name the entered rate as the
PM's figure.

This reads the intake workbook only, writes no data file, and moves no recorded baseline: the
standard synthetic project enters no rate.

#### Scenario: An entered rate is used in both workbooks

- **WHEN** a rate and its VAT basis are entered for a product with chargeable area
- **THEN** that product's revenue in both workbooks SHALL be the entered rate × the product's net
  floor area × 12, in VND
- **AND** the two workbooks SHALL agree on it within rounding

#### Scenario: An entered rate is not capped

- **WHEN** the entered rate differs from the comparable-derived rate by more than the rate-swing cap
- **THEN** the entered rate SHALL be applied unchanged

#### Scenario: The remark names the source and the VAT basis

- **WHEN** a product is priced at an entered rate
- **THEN** its remark SHALL say, in Vietnamese, that the rate is the actual rate entered by the PM
  and SHALL state its VAT basis
- **AND** SHALL NOT name comparable projects as the rate's source

#### Scenario: A VAT basis that differs from the deliverable is disclosed

- **WHEN** the entered VAT basis differs from the basis the deliverable states for its figures
- **THEN** the line's remark and the run's printed summary SHALL each state the difference
- **AND** the rate SHALL NOT be converted

#### Scenario: A rate without its VAT basis stops the run

- **WHEN** a rate is entered for a product and its VAT-basis field is blank
- **THEN** the run SHALL stop before writing any workbook
- **AND** SHALL name the product whose VAT basis is missing

#### Scenario: A blank or zero rate means "not entered"

- **WHEN** a product's rate field is blank or 0
- **THEN** that product SHALL be priced as it was before this requirement
- **AND** the run's printed summary SHALL list the products priced from comparables

#### Scenario: An invalid rate stops the run

- **WHEN** a product's rate field holds text or a negative number
- **THEN** the run SHALL stop and name the product and the value

#### Scenario: A rate entered for a product with no area

- **WHEN** a rate is entered for a product whose chargeable area is 0 or blank
- **THEN** no revenue SHALL be written for that product
- **AND** the run's printed summary SHALL name the product as having a rate but no area

#### Scenario: A product without an entered rate is unchanged

- **WHEN** a project enters a rate for one product and not for another product that has its own
  comparable rate
- **THEN** the second product's rate and revenue SHALL be the same as before this requirement

#### Scenario: A fallback-priced product follows the entered Apartment rate

- **WHEN** Apartment's rate is entered and another product has neither an entered rate nor a
  comparable rate
- **THEN** that product SHALL be priced at the entered Apartment rate
- **AND** its remark SHALL say it uses the project's Apartment rate as a substitute
