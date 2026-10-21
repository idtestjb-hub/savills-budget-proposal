## ADDED Requirements

### Requirement: The data file carries the apartment management-fee rate of each real budget

The build step SHALL write one more code, `RM.AP`, for each project of the store whose main operating-fund
sheet carries the apartment management-fee line with an amount above 0 and whose profile holds an apartment
NFA above 0. Its value SHALL be the full apartment management fee per month, excluding VAT, divided by the
project's **apartment** NFA, where the full fee is the amount collected on `RM.AP` plus the amount the developer
pays on `RM.0A` for units not yet handed over (0 when the sheet has no such line). The row SHALL be marked as a
rate per m² of apartment NFA, so that the tool never multiplies it by the fee-paying NFA. All other rules of the
data file (one file per project, the latest year, zero or blank counted not valued, CPI factor to 2027,
anonymity) SHALL apply unchanged.

Data files read: the scan store in `Savills-local` (build step only). Data files written:
`Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv` and its `README.txt`, rebuilt.

#### Scenario: A year-1 budget with a developer share

- **WHEN** a 2027 budget carries `RM.AP` at 1,945,216,130 VND per month and `RM.0A` at 549,503,325 VND per month,
  excluding VAT, and an apartment NFA of 181,662.2 m²
- **THEN** its `RM.AP` value SHALL be (1,945,216,130 + 549,503,325) ÷ 181,662.2 = 13,733 VND per m² per month,
  with a CPI factor of 1

#### Scenario: A budget without an apartment NFA

- **WHEN** a store file carries `RM.AP` above 0 but its profile has no apartment NFA
- **THEN** no `RM.AP` value SHALL be written for it, and the README SHALL count it as left out for that code

#### Scenario: Scope on the store of 2026-10-07

- **WHEN** the build runs on the store as scanned on 2026-10-07
- **THEN** `RM.AP` SHALL have a value for 24 projects (budget years 2025: 7, 2026: 13, 2027: 3, 2028: 1), and an
  independent SQL count with the same rules SHALL agree

### Requirement: The tool forms the apartment-rate range and exposes it as a rate

For `RM.AP` the tool SHALL form the range exactly as for the other codes (the project itself left out by name
key or by fee-paying NFA within 0.5%, IQR outliers dropped once, at least 10 projects, PERCENTILE.INC) and SHALL
expose the median, P25 and P75 as a rate in VND per m² of apartment NFA per month at 2027 prices, excluding
VAT. It SHALL NOT compute an annual amount for `RM.AP` from the fee-paying NFA; the revenue rows take the rate.

The internal `Real-Budget Ranges` sheet SHALL show `RM.AP` with the role "rate", every project id with its value,
the ones left out and why, and the rate the tool applied after the VAT conversion.

#### Scenario: The project itself is in the store

- **WHEN** one of the four real M3 projects is run with its own fee-paying NFA
- **THEN** its own `RM.AP` value SHALL be left out as the project itself, and the sheet SHALL say so

#### Scenario: The sheet shows the rate, not an amount

- **WHEN** the analysis workbook is generated
- **THEN** the `RM.AP` row of the `Real-Budget Ranges` sheet SHALL show the median in VND per m² per month and
  the applied rate including VAT, and no figure labelled as an annual amount
