## ADDED Requirements

### Requirement: ESI1 is priced from the insured asset value

When `ESI1 Insured Asset Value (VND)` on Project Info is above 0, the tool SHALL price `ESI1` as the value × the
premium rate per year, before VAT. It SHALL add insurance VAT in each month (10%, outside the VAT reduction) when the
financial model includes VAT, and SHALL spread the amount evenly over the 12 budget months. The premium rate SHALL be
`ESI1 Premium Rate` when it is filled in, and 0.05% when it is blank. The remark SHALL state the value, the rate, its
source (the PM's entry, or the default from the Savills guideline under Decree 105/2025/NĐ-CP), and the VAT.

#### Scenario: Default rate
- **WHEN** the value is 10,000,000,000 VND and the rate is blank
- **THEN** ESI1 before VAT SHALL be 5,000,000 VND a year, and the remark SHALL say that the default 0.05% was used

#### Scenario: Discounted rate
- **WHEN** the value is 6,707,011,785,586 VND and the rate is 0.0375%
- **THEN** ESI1 before VAT SHALL be 2,515,129,420 VND a year, rounded to the VND

### Requirement: ESI1 without an asset value stays 0 with a reason

When the value is blank, or the form does not have the field, `ESI1` SHALL stay 0, and the remark SHALL name the field
to fill in. When the PM entered 0, `ESI1` SHALL stay 0, and the remark SHALL say that the PM entered 0. A value that
is negative or not a number, or a rate that is 0, negative or above 1%, SHALL stop the run with a message naming the
field.

#### Scenario: An older form
- **WHEN** a form made before this change is run
- **THEN** every figure SHALL equal the previous run, and the ESI1 remark SHALL name `ESI1 Insured Asset Value (VND)`

#### Scenario: A rate typed as a whole number
- **WHEN** the rate is entered as 0.05 (5%)
- **THEN** the run SHALL stop and name `ESI1 Premium Rate`
