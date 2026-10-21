## ADDED Requirements

### Requirement: A Required code with no usable pricing input is priced from real Savills budgets

When a Required code has no pricing method recorded in the costing catalogue, or has one the input form cannot feed
(for example a count of events the form does not ask for), the pipeline SHALL price it from the real-budget range
(capability `real-budget-ranges`) instead of leaving it at 0. This applies when the range is usable: at least 10
projects after the exclusions. The range comes from the latest budget of every usable Savills project in the scan
store. It replaces the earlier limit to the 8 detailed budgets, as the user decided on 2026-10-12.

A Required code the range cannot price (fewer than 10 projects, or a basis that does not exist on this project, such
as a pool line without a pool) SHALL stay at 0 with its stated reason, as before.

Data files read: `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv`,
`Budget_Agent/data/generation_B_verified/Ref_CPI_VN.csv`. Recorded baseline figures move on the standard sample
(design D7).

#### Scenario: Pest control on the standard sample

- **WHEN** the standard sample is generated and `ESS12` has at least 10 projects in its range
- **THEN** `ESS12` SHALL carry a non-zero figure on its own leaf row, priced from the range

#### Scenario: Asset insurance is not priced from the range

- **WHEN** the standard sample is generated
- **THEN** `ESI1` SHALL keep its guideline method (asset value × premium rate), and stay at 0 with its reason while
  the form has no asset value
