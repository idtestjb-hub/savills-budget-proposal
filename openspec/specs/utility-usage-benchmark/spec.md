# utility-usage-benchmark Specification

## Purpose
Sets a new prospect's electricity, water and diesel usage per m² from the hand-checked usage of many real projects,
not from one reference budget, and discloses the basis on the budget.

## Requirements

### Requirement: Usage rows are checked by hand before use

The usage benchmark SHALL read only rows of a usage table in the outer data folder, one row per project and utility,
each carrying: the store file id and project id, the utility (electricity, water, diesel), the monthly quantity and
its unit (kWh, m³, litres), the period the source states (month, year, budget average) and how it was turned into a
monthly figure, the NFA in m² the quantity covers and where that NFA comes from, the source sheet and cell, the check
result (accepted or rejected), the reason, and who checked it and when. A row SHALL count only when its check result is
"accepted". Only projects of the 55 in `real_budget_ranges_map.csv` SHALL appear. Rows the store scan flagged and the
checker rejected SHALL stay in the table with their reason. Nothing writes the table at run time.

#### Scenario: A rejected row

- **WHEN** a water row is marked rejected with reason "m³ is the unit of a price line, not a quantity"
- **THEN** the row SHALL NOT enter the median and SHALL stay in the table

#### Scenario: A file outside the 55

- **WHEN** a store file not in `real_budget_ranges_map.csv` carries usage rows
- **THEN** none of its rows SHALL appear in the table

### Requirement: Usage per m² is the median after removing outliers

For each utility, the usage per m² per month SHALL be the median of the accepted projects' usage per m² (monthly
quantity ÷ NFA), after dropping values below Q1 − 1.5 × IQR or above Q3 + 1.5 × IQR of the accepted values. A project
SHALL count once per utility. The new prospect's monthly usage SHALL be that median times its own NFA.

#### Scenario: Seven projects with one outlier

- **WHEN** seven accepted electricity rows give 2.1, 2.4, 2.5, 2.6, 2.8, 3.0 and 9.5 kWh/m²/month
- **THEN** 9.5 SHALL be dropped and the usage SHALL be the median of the other six, 2.55 kWh/m²/month

### Requirement: Too few projects fall back to the utilities base, disclosed

When fewer than five accepted projects remain for a utility after outlier removal, that utility SHALL use the
utilities base project's usage per m² as before, and the remark SHALL say that the benchmark had too few projects and
which basis was used.

#### Scenario: Three diesel projects

- **WHEN** only three accepted diesel rows remain
- **THEN** diesel usage SHALL come from the utilities base project and the remark SHALL say so

### Requirement: The budget discloses the usage basis

The remark of each new-prospect energy line SHALL state the usage per m², the number of projects behind it, and the
price used with its month and source. The internal analysis SHALL list the projects that entered the median with their
usage per m², by store project id (no project name), and the projects the outlier fence dropped.

#### Scenario: Electricity remark

- **WHEN** electricity is priced from a 12-project median
- **THEN** its remark SHALL read in Vietnamese with the kWh/m²/month figure, "12 dự án", the EVN price and its month
