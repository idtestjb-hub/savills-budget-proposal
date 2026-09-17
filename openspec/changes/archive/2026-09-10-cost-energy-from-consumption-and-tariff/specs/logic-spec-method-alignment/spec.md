## ADDED Requirements

### Requirement: A quantity-times-price method holds both halves, not their product

Where the costing specification states a method as a quantity multiplied by a price, the pipeline
SHALL hold the quantity and the price as separate values and SHALL compute the figure from them. It
SHALL NOT store or reuse only their product.

#### Scenario: The two halves are stored separately

- **WHEN** reference data is extracted for a cost the specification prices as quantity × price
- **THEN** the quantity and the price SHALL each be stored as a value with its unit named
- **AND** neither SHALL be recoverable only by dividing one recorded figure by another

#### Scenario: A price change moves the figure

- **WHEN** the price for such a cost is updated
- **AND** the pipeline is run again against an unchanged project input
- **THEN** the generated figure SHALL change in proportion to the price change

#### Scenario: Both halves appear on the output

- **WHEN** such a cost is written to a generated workbook
- **THEN** its note SHALL state the quantity assumed, the price applied, and the sample size behind
  each
- **AND** a reader SHALL be able to tell whether a figure is wrong because of the quantity or
  because of the price

#### Scenario: An unrecoverable price is disclosed, not invented

- **WHEN** the specification's method needs a price that the reference data does not record
- **THEN** the pipeline SHALL NOT substitute an assumed or externally guessed price
- **AND** SHALL state which cost could not be split and what it fell back to

### Requirement: A price that changes over time carries the date it was current

Any rate the pipeline applies that is expected to change over time SHALL be stored with the date it
was known to be current, and that date SHALL be reported wherever the resulting figure is.

#### Scenario: The rate's age is visible on the output

- **WHEN** a figure is produced from such a rate
- **THEN** the output SHALL state when that rate was current
- **AND** SHALL NOT present the figure as though the rate were verified as of the run

#### Scenario: A stale rate is visible rather than silent

- **WHEN** a rate's recorded date is older than the budget year being generated
- **THEN** the output SHALL make that visible to a reader of the generated workbook
