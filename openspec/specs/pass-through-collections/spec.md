## Purpose

For a project that is already operating, water and electricity that Savills collects from residents
and pays on their behalf (thu hộ / chi hộ) are written as equal revenue and expense pairs. The
budget's revenue and expense totals then compare with the project's own budget, and the surplus does
not move.

**Data scope**: reads the intake workbook and `Costing_Method_Catalogue.csv`. The catalogue gains or
updates one entry per collect-on-behalf code. This is written once when the change is implemented,
not on every run, and no other catalogue entry changes. No Generation A or Generation B table and no
Fact/Dim key changes. No recorded baseline moves, because the standard synthetic project leaves
these fields blank. Figures are in VND.

## Requirements

### Requirement: Entered collect-on-behalf amounts are written as equal revenue and expense pairs

The intake form SHALL offer, for each product type, two optional amounts in VND per month: water
collected on behalf, and electricity collected on behalf. When the project is declared at stable
operation and an amount is entered, both workbooks SHALL write it twice, each time as the amount
× 12 spread evenly across the twelve months:
- on the matching revenue line, `RO3.<product>` for water or `RO4.<product>` for electricity;
- on the expense line that the approved pairing in the costing catalogue names for that revenue line.

The revenue line's remark and the expense line's remark SHALL each say, in Vietnamese, that the
amount is collected and paid on behalf of residents, and SHALL name the other line of the pair.

A blank amount SHALL write nothing, and the line SHALL keep its current "not estimated" treatment.

The pairs SHALL stay out of `2.2 Common area Fund`. When any amount is entered, that sheet SHALL
allocate no share of a paired expense line, and its line SHALL say in Vietnamese that the amount is
paid on residents' behalf and not shared with the common-area fund. The revenue base that sheet uses
to share every other line SHALL leave out the collect-on-behalf revenue lines, so each other line's
share is what it would be without the amounts.

#### Scenario: The common-area fund is not affected

- **WHEN** collect-on-behalf amounts are entered
- **THEN** every figure on `2.2 Common area Fund`, and `RI1` on `2. Budget-Management Fund`, SHALL
  equal the same run with those amounts left blank, within 1 VND
- **AND** the `2.2` lines of the paired expense lines SHALL carry no amount and SHALL say why

#### Scenario: A pair is written for an entered amount

- **WHEN** the project is at stable operation and a water amount is entered for apartments
- **THEN** `RO3.A` SHALL be that amount × 12
- **AND** the expense line paired with `RO3.A` in the catalogue SHALL be the same amount × 12
- **AND** each remark SHALL name the other line

#### Scenario: The surplus does not move

- **WHEN** collect-on-behalf amounts are entered for any number of products
- **THEN** total revenue and total expense on `2. Budget-Management Fund` SHALL each rise by the sum
  of the entered amounts × 12
- **AND** the surplus SHALL be the same as with those amounts left blank, within 1 VND

#### Scenario: A product with no collect-on-behalf line stops the run

- **WHEN** an amount is entered for a product that the approved pairing does not map to a revenue
  line and an expense line
- **THEN** the run SHALL stop before writing any workbook
- **AND** SHALL name the product and the utility

#### Scenario: Amounts entered without the stable-operation switch stop the run

- **WHEN** a collect-on-behalf amount is entered and the project is not declared at stable operation
- **THEN** the run SHALL stop before writing any workbook
- **AND** SHALL name the fields concerned

#### Scenario: Blank amounts leave today's budget unchanged

- **WHEN** every collect-on-behalf amount is blank
- **THEN** no `RO3.*` or `RO4.*` line, and none of their paired expense lines, SHALL carry a figure
  that this capability wrote
- **AND** every figure SHALL be the same as before this requirement

#### Scenario: A zero amount is not written

- **WHEN** an amount of 0 is entered
- **THEN** neither line of the pair SHALL be written
- **AND** the run's printed summary SHALL list the product and the utility as entered at 0
