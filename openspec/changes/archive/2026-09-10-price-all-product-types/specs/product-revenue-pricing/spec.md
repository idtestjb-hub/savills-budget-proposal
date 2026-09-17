## Purpose

Defines how the pipeline prices management-fee revenue for every product type a project contains,
so that the client deliverable reports the same revenue as the analysis that explains it, and so
that a reader can tell which rates are real and which are substitutions.

**Data scope**: this capability changes which revenue rows are written to the generated workbooks.
It reads the existing Generation B comparable data (`Dim_Property_Residential.csv` per-product
`Fee_*` columns) and writes no data of its own; no Generation A or Generation B table is modified,
and no Fact/Dim join key changes, so the Copilot Studio package's live data is unaffected.

## ADDED Requirements

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
revenue for the same project, priced on the same basis.

#### Scenario: Both workbooks agree on total revenue

- **WHEN** both generators are run against the same input
- **THEN** the total management-fee revenue SHALL match between the two workbooks

#### Scenario: Both workbooks agree per product

- **WHEN** both generators are run against the same input
- **THEN** each product's revenue SHALL match between the two workbooks

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
