## MODIFIED Requirements

### Requirement: A filled cost code uses the method its spec states

Where the pipeline produces a figure for a cost code that the costing specification defines, it
SHALL compute that figure by one of the methods the specification states for that code.

A figure the pipeline computes SHALL reach every workbook that reports that cost. A cost present in
one generated workbook and absent from the other is the same divergence as two different figures,
and SHALL be treated as one — a blank is harder to notice than a mismatch, because nothing invites
comparison.

Where a computed figure is an undecomposed aggregate over a section the budget form itemises, it
SHALL be placed on a row that accepts an aggregate without displacing the form's own arithmetic, and
SHALL NOT be spread across the section's individual items unless the pipeline holds data supporting
that breakdown.

#### Scenario: A contract-based code is costed as a contract

- **WHEN** the specification defines a code as a contract cost
- **THEN** the pipeline SHALL compute it as a contract value over the budget period
- **AND** SHALL NOT substitute an unrelated basis such as internal headcount

#### Scenario: Both workbooks use the same method

- **WHEN** both generators are run against the same input
- **THEN** each such code SHALL carry the same figure in both workbooks

#### Scenario: A computed cost reaches both workbooks

- **WHEN** the pipeline computes a cost category from its reference data
- **THEN** that category SHALL appear in the client deliverable and in the internal analysis
- **AND** the two SHALL carry the same figure for it
- **AND** the category SHALL NOT be reported in one workbook while left blank in the other

#### Scenario: An aggregate figure does not displace the form's own totals

- **WHEN** a computed figure covers a whole section that the budget form breaks into line items
- **THEN** the figure SHALL be written to a line item within that section
- **AND** SHALL NOT be written to a row holding the form's own subtotal formula
- **AND** the section's subtotal SHALL include the figure without that formula being altered

#### Scenario: A figure placed in a catch-all says what it does and does not cover

- **WHEN** a computed figure is written to a general or miscellaneous line item because no data
  supports allocating it across the section's specific items
- **THEN** the output SHALL state the basis of the figure and its sample size
- **AND** SHALL state which costs in that section the figure does not include, where the figure's
  own definition is narrower than the section it sits in
