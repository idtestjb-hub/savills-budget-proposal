# real-budget-ranges Specification

## Purpose
Prices budget lines the tool has no other source for from what Savills projects actually budget. It turns the
real-budget scan store into an anonymous range per code, and keeps the project being budgeted out of its own range.

## Requirements

### Requirement: The scan store becomes one anonymous per-project data file

A build step SHALL read the real-budget scan store and write one data file with one row per project and code. Each
row SHALL hold:
- an anonymous project id;
- the budget year the value came from;
- the value in VND per m² of fee-paying NFA per month, excluding VAT, before and after bringing it to 2027 prices;
- the CPI factor used.

The store SHALL be built with the leaf-line and tie rules of `budget-workbook-aggregate-rows`, and SHALL record for
each sheet its tie state and the explanation note.

The store SHALL be read under these rules:
- only each file's main operating-fund sheet, read directly from Excel, and only when its leaf lines tie to the
  sheet's total rows, directly or after explanation;
- no scanned PDF, no converted xlsb, no file whose content duplicates another;
- one file per project, the one with the latest budget year;
- a file with no project name counts as its own project and is flagged;
- the amount is divided by the period's real number of months and by the file's fee-paying NFA, and VAT is taken out
  at each code's own rate.

A zero or blank amount SHALL NOT be written as a value. The file SHALL instead record, per code, how many projects
carry the line and how many show it as 0 or blank.

The data file SHALL carry no project name, file name, address or other identifying text. It SHALL be written under
`Budget_Agent/data/`, outside the code folder that is pushed to GitHub. The store and the name-to-id map SHALL stay
in `Savills-local`.

Data files read: the scan store in `Savills-local` (build step only). Data files written:
`Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv`. Recorded baseline figures can move when a project
enters or leaves a range or its values change; the before/after is measured and signed off.

#### Scenario: A project with two budget years

- **WHEN** the store holds a project's 2025 and 2026 budgets
- **THEN** only the 2026 file SHALL give that project's values

#### Scenario: A line budgeted at zero

- **WHEN** a project's main sheet carries `ESS7` at 0
- **THEN** no `ESS7` value SHALL be written for it, and the count of projects showing `ESS7` as 0 or blank SHALL
  include it

#### Scenario: The data file is anonymous

- **WHEN** the data file is written
- **THEN** none of the store's project names or file names SHALL appear in it

#### Scenario: A main sheet that ties after a filter

- **WHEN** a project's main sheet ties only after a filter
- **THEN** its values SHALL be written like those of a sheet that ties directly

#### Scenario: A main sheet that does not tie

- **WHEN** a project's main sheet does not tie, directly or after explanation
- **THEN** the project SHALL be left out, and the build log SHALL say so

### Requirement: Older budgets are brought to 2027 prices with a sourced CPI

Each value SHALL be multiplied by the product of the annual average CPI changes from its budget year up to 2027.
Each year's rate SHALL be read from a table that names its source: Cục Thống kê's published annual average, or for a
year not yet published, the stand-in the user approved, marked as such.

Data files read: `Budget_Agent/data/generation_B_verified/Ref_CPI_VN.csv`.

#### Scenario: A 2025 budget

- **WHEN** a value comes from a 2025 budget
- **THEN** it SHALL be multiplied by (1 + the 2026 rate) × (1 + the 2027 rate), and both rates and their sources
  SHALL be shown on the internal `Real-Budget Ranges` sheet

#### Scenario: A 2027 budget

- **WHEN** a value comes from a 2027 budget
- **THEN** its factor SHALL be 1

### Requirement: A range leaves out the project itself and its outliers, and needs 10 projects

For each code it prices, the tool SHALL form the range from the data file:
1. Leave out the project being budgeted, when its name or its fee-paying NFA matches a project in the file.
2. Leave out values below P25 − 1.5 × (P75 − P25) or above P75 + 1.5 × (P75 − P25).
3. Use the range only when at least 10 projects remain.

P25, the median and P75 SHALL be computed from the projects that remain. The ids left out, and why, SHALL be listed
on the internal sheet.

#### Scenario: The project is in the store

- **WHEN** an Existing project whose own budget is in the store is run
- **THEN** its value SHALL NOT be part of any range, and the internal sheet SHALL say it was left out as the project
  itself

#### Scenario: Too few projects

- **WHEN** fewer than 10 projects remain for a code after the exclusions
- **THEN** that line SHALL stay at 0, and its reason SHALL say that fewer than 10 real budgets carry it

### Requirement: Which codes are priced from the range

The range SHALL price these codes on `2. Budget-Management Fund`, in both project modes:
- `EMB4` (operation audit), `ESS12` (pest control), `ESC5` (Tết decoration);
- `ESS7` (façade cleaning), only when the input has at least one tower ("Tower Count" ≥ 1);
- `ESS23` (outsourced pool staff), only when the input says the project has a swimming pool and the roster
  employs no pool staff in-house;
- `ESC1` (events) and `ESC2` (fire drill), as a flagged stand-in for the guideline's count × price per event.

The figure SHALL be: median (VND per m² per month, 2027 prices, excluding VAT) × the project's fee-paying NFA × 12
months, with the budget-year VAT added when the deliverable is on an inclusive basis. `2.2 Common area Fund` SHALL
follow its existing allocation of these lines.

`ESI1`, `EMH1` and `EMH3` SHALL NOT be priced from the range. The internal sheet SHALL show their range next to the
tool's figure as a cross-check.

A figure the tool already gets from the input or another source SHALL NOT be replaced by the range.

#### Scenario: A project without a pool

- **WHEN** the input says "Has Swimming Pool? = No"
- **THEN** `ESS23` SHALL stay at 0 with its existing reason

#### Scenario: Pool staff already on the roster

- **WHEN** the project has a pool and its Staffing Demand has an in-house pool attendant
- **THEN** `ESS23` SHALL stay at 0, and its reason SHALL say the pool staff are already on `A1. Staff Cost`

#### Scenario: Staff cost carried as one approved lump

- **WHEN** an Existing project with a pool has its staff cost as one approved lump and no A1 position rows
- **THEN** `ESS23` SHALL stay at 0, and its reason SHALL say the approved lump may already include pool staff

#### Scenario: The input name carries a trailing note

- **WHEN** the input names the project "X (REBUILT AS NEW PROSPECT)" and the data file holds project X
- **THEN** X's entry SHALL be left out as the project itself

#### Scenario: A low-rise project

- **WHEN** the input's "Tower Count" is 0
- **THEN** `ESS7` SHALL stay at 0, and its reason SHALL say the project has no tower

#### Scenario: Events

- **WHEN** `ESC1` is priced from the range
- **THEN** the analysis SHALL flag it as a stand-in until the PM enters the number and price of events

### Requirement: The analysis shows every range it used

The internal analysis workbook SHALL carry a `Real-Budget Ranges` sheet. For each code priced or cross-checked it
SHALL list:
- the projects used (anonymous ids) and their values;
- those left out and why;
- P25, the median and P75;
- the CPI factors and their sources;
- the VAT rate;
- the figure written to the deliverable, or the tool's own figure for a cross-check.

The sheet is internal and SHALL NOT be part of the client deliverable.

#### Scenario: The sheet ties to the deliverable

- **WHEN** a code is priced from the range
- **THEN** the figure on the sheet SHALL equal the code's line on `2. Budget-Management Fund`

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
