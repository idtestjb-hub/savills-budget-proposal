## MODIFIED Requirements

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
