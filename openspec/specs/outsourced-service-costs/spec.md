## Purpose

Defines how the pipeline prices the three outsourced service contracts — security, cleaning and
landscape — and how that cost basis differs from in-house Savills payroll, so that a vendor's price
is never loaded with an employer contribution the client is not charged twice for.

**Data scope**: this capability changes how an existing cost is calculated in the generated workbooks. It reads Generation B reference rates (Fact_MasterRateCard.csv, SERVICE domain) as it already did and writes no data of its own; no Generation A or Generation B table is modified, and no Fact/Dim join key changes, so the Copilot Studio package's live data is unaffected.

## Requirements

### Requirement: Outsourced service lines carry no employer insurance loading

Security, cleaning and landscape SHALL be priced as outsourced vendor contracts. Their cost SHALL
NOT include an employer social, health or unemployment insurance contribution, because the vendor
rates used already incorporate the vendor's own staffing costs.

#### Scenario: Security cost excludes the employer contribution

- **WHEN** a budget is generated for a project with security positions
- **THEN** the security cost line SHALL equal the sum of its positions' headcount, rate and coverage
  with no employer insurance multiplier applied
- **AND** the same figure SHALL appear in both the client deliverable and the analysis workbook

#### Scenario: Cleaning and landscape are treated the same way

- **WHEN** a budget is generated for a project with cleaning or landscape positions
- **THEN** each of those cost lines SHALL likewise exclude any employer insurance contribution

#### Scenario: A project with no landscape area

- **WHEN** a project has no garden or landscape area, so no landscape positions exist
- **THEN** the landscape cost line SHALL remain zero and be left blank, as it is today

### Requirement: In-house staff cost retains the employer contribution

Every roster position that is not one of the three outsourced services SHALL continue to carry the
employer insurance contribution, because those positions are genuine Savills payroll.

#### Scenario: Savills staff cost keeps the loading

- **WHEN** a budget is generated
- **THEN** the Savills staff cost line SHALL include the employer insurance contribution at the rate
  evidenced in the payroll data
- **AND** it SHALL equal the loaded cost of every roster position except security, cleaning and
  landscape

#### Scenario: No position is counted twice or dropped

- **WHEN** the outsourced lines and the Savills staff cost line are added together
- **THEN** every roster position SHALL be represented exactly once
- **AND** no position SHALL be omitted from both

### Requirement: The cost basis is stated on the output

A reader of the generated budget SHALL be able to tell, without access to the source code, that the
outsourced service lines exclude employer contributions and why.

#### Scenario: Remarks state the basis

- **WHEN** a budget is generated
- **THEN** the remark on each outsourced service line SHALL state that the figure is an outsourced
  vendor cost carrying no employer insurance contribution
- **AND** the remark on the Savills staff cost line SHALL state that it does include one

### Requirement: The two workbooks agree on service cost

The client deliverable and the internal analysis workbook SHALL report the same cost basis for the
three outsourced services, so that the analysis explains the deliverable rather than contradicting
it.

#### Scenario: Both outputs report the same service costs

- **WHEN** both generators are run against the same input
- **THEN** the security, cleaning and landscape cost figures SHALL match between the two workbooks
- **AND** neither workbook SHALL apply a loading the other omits

### Requirement: The change in figures is measurable and deliberate

The effect of this change on the budget SHALL be visible and recorded, not absorbed silently.

#### Scenario: Verification detects the change

- **WHEN** verification is run after this change with the previously recorded baseline in place
- **THEN** it SHALL fail
- **AND** it SHALL name each figure that moved, with its recorded and current values

#### Scenario: The baseline is re-recorded with a reason

- **WHEN** the differences have been reviewed and accepted
- **THEN** the baseline SHALL be re-recorded with a stated reason identifying this change
- **AND** verification SHALL pass on the following run
