## ADDED Requirements

### Requirement: The builder records how each store file was used
Besides `Ref_RealBudgetValues.csv` and `README.txt`, the builder SHALL write `Ref_RealBudgetUsage.csv` in the same folder: one row per file of the store, with the store file id, a usage of `used`, `merged` or `left_out`, a reason code, and for `merged` the store id of the file it was merged into. Reason codes SHALL cover at least: used in full, used as a second project of the same name, used without `RM.AP`, merged into a newer file, scanned PDF, converted xlsb, content duplicate, no main fund sheet, main sheet not tied to its totals, no fee-paying NFA, no budget period or year. The file SHALL hold store ids only: no file name, project name or path, and the builder's name check SHALL cover it. Every store file SHALL have exactly one row, and the number of `used` rows SHALL equal the number of projects written to `Ref_RealBudgetValues.csv`.

#### Scenario: One row per file
- **WHEN** the builder runs on the 87-file store of 2026-10-22
- **THEN** `Ref_RealBudgetUsage.csv` has 87 rows with 55 `used`, 3 `merged` and 29 `left_out`, and its ids match `dim_file.csv`

#### Scenario: Usage file agrees with the README
- **WHEN** the builder finishes
- **THEN** every id listed in the README under "Files excluded or merged" has the matching usage and reason in `Ref_RealBudgetUsage.csv`

#### Scenario: Names stay out
- **WHEN** a store project name or file name would appear in the usage file
- **THEN** the builder refuses to write, as it does for the other two outputs

#### Scenario: Values file unchanged
- **WHEN** the builder runs with and without the usage output on the same store
- **THEN** `Ref_RealBudgetValues.csv` is byte-identical
