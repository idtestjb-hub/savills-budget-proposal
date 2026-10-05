## ADDED Requirements

### Requirement: The management-fee revenue hand-check covers every priced product

Verification SHALL recompute the management-fee revenue of the synthetic project independently, as
the sum over every product the tool can price (apartment, officetel, office, shopping mall, retail,
shop apartment, shophouse, villas, nursery) of that product's net floor area from the input file
times its monthly fee per square metre, times 12 months, and compare the sum with the figure on the
deliverable. The result SHALL agree to within 1 VND. A product with an area of 0 in the input
contributes 0.

A product that has an area in the input but no numeric fee in the workbook's pricing table is
unpriced. It SHALL contribute 0 to the expected figure, and the check's description SHALL name each
unpriced product, so that the omission is visible rather than silent. An unpriced product on its own
SHALL NOT make the check fail.

#### Scenario: A project with an officetel passes

- **WHEN** the synthetic project has apartment, officetel and shophouse areas and all three are priced
- **THEN** the expected revenue includes the officetel (its area times its fee times 12)
- **AND** the check passes when the deliverable's figure agrees to within 1 VND

#### Scenario: A product with an area but no fee is named

- **WHEN** a product has an area in the input but no numeric fee in the pricing table
- **THEN** it contributes 0 to the expected revenue
- **AND** the check's description names it as unpriced
- **AND** the check does not fail for that reason alone

#### Scenario: An input area that disagrees with the workbook fails the check

- **WHEN** any priced product's area in the input file differs from the area in the workbook by more
  than 0.5 m²
- **THEN** the check fails and says it is not anchored to the input file

#### Scenario: A product row cannot be found in the input file

- **WHEN** the input file has no row for one of the nine products
- **THEN** the check fails and names the missing label
- **AND** does NOT compute its expectation from the workbook it is checking
