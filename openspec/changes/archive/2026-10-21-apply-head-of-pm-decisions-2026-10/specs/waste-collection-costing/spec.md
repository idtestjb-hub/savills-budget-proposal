## MODIFIED Requirements

### Requirement: `B2.6`'s remark states the weight assumption and its legal basis

The `B2.6` remark SHALL state the assumed waste weight per unit per day and cite QĐ 65/2026/QĐ-UBND as the basis for
the three-part unit price, in the guideline's own wording. It SHALL also state the VAT rate added for the budget's
months.

#### Scenario: The remark states the assumption and citation

- **WHEN** `B2.6` carries a non-zero figure
- **THEN** its remark SHALL state the per-unit-per-day weight assumption used
- **AND** SHALL cite QĐ 65/2026/QĐ-UBND as the basis for the collection/transport/treatment unit price
- **AND** SHALL state the VAT rate applied

## ADDED Requirements

### Requirement: The waste unit price follows the decision in force

The household-waste unit price SHALL be the one in force for the budget period: under QĐ 65/2026/QĐ-UBND (01/09/2026 to
30/06/2027), group 1 = 486 + 180 + 421 = 1,087 VND/kg excluding VAT. VAT SHALL be added by month from the dated rate
source.

#### Scenario: A 2027 budget

- **WHEN** `ESS9` is priced for a January–December 2027 budget
- **THEN** each month SHALL use 1,087 VND/kg times 1.10
