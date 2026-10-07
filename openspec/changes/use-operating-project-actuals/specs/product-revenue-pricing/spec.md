## ADDED Requirements

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
