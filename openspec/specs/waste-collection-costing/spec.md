## Purpose

Prices the `B2.6` domestic-waste-collection line (`ESS9`) the standard form's own AI Guideline column instructs (weight per unit per day, the three-part unit price of QĐ 65/2026/QĐ-UBND, 1,087 VND/kg, read from the dated tariff table), and writes its guideline-driven remark.

## Requirements

### Requirement: The deliverable prices domestic waste collection for every project with residential units

For any project with apartment (or other residential) units, the deliverable SHALL compute a
`B2.6` waste-collection cost from the project's unit count, the guideline's assumed waste weight
per unit per day, and the QĐ 67 three-part unit price (collection, transport, treatment). A
project with no residential units MAY leave the line at zero.

#### Scenario: A residential project gets a priced waste-collection line

- **WHEN** the deliverable is generated for a project with apartment units
- **THEN** `B2.6` SHALL carry a non-zero figure computed from the unit count, the assumed
  per-unit waste weight, and the QĐ 67 unit price

#### Scenario: A project with no residential units is left at zero

- **WHEN** the deliverable is generated for a project with no residential (apartment-type) units
- **THEN** `B2.6` MAY be left at zero rather than priced from a zero unit count

### Requirement: `B2.6`'s remark states the weight assumption and its legal basis

The `B2.6` remark SHALL state the assumed waste weight per unit per day and cite QĐ 65/2026/QĐ-UBND as the basis for
the three-part unit price, in the guideline's own wording. It SHALL also state the VAT rate added for the budget's
months.

#### Scenario: The remark states the assumption and citation

- **WHEN** `B2.6` carries a non-zero figure
- **THEN** its remark SHALL state the per-unit-per-day weight assumption used
- **AND** SHALL cite QĐ 65/2026/QĐ-UBND as the basis for the collection/transport/treatment unit price
- **AND** SHALL state the VAT rate applied

### Requirement: The new figure is measured and disclosed before it ships

Because `B2.6` was previously always zero, the first run that prices it moves the year-one surplus
by a real amount. That amount SHALL be measured on at least one real project and shown to the Head
of PM before this capability is archived.

#### Scenario: The new figure is presented before archive

- **WHEN** this capability is ready to archive
- **THEN** the VND amount `B2.6` adds SHALL have been measured on a real project and shown to the
  Head of PM

### Requirement: The waste unit price follows the decision in force

The household-waste unit price SHALL be the one in force for the budget period: under QĐ 65/2026/QĐ-UBND (01/09/2026 to
30/06/2027), group 1 = 486 + 180 + 421 = 1,087 VND/kg excluding VAT. VAT SHALL be added by month from the dated rate
source.

#### Scenario: A 2027 budget

- **WHEN** `ESS9` is priced for a January–December 2027 budget
- **THEN** each month SHALL use 1,087 VND/kg times 1.10
