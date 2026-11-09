## MODIFIED Requirements

### Requirement: A Review adds a row for every approved code the tool left at zero
After the generators of a Review run, every on-form code that carries an approved figure (at least 0.5 VND in
absolute value) and a tool figure of 0 SHALL get a total row on sheet `4. Điều chỉnh` with one lumped detail row
(quantity 1 locked, original unit price 0, original amount 0) and its fund row's month cells linked to that total
row, so the PM can adjust it on the web or in Excel. A code whose row cannot be found on the fund sheet SHALL be
named in the run log and skipped. A new-project run SHALL NOT add such rows for zero lines (kind C); lines left for
the PM get their rows on every run (requirement "Every line left for the PM has a row on every run"). Untouched, a
zero row SHALL leave every month cell at 0, so the deliverable's figures are the generator's.

#### Scenario: Zero rows present
- **WHEN** a Review run's approved budget prices ESS38 at 3,175,200,000 VND and the tool prices it at 0
- **THEN** sheet `4. Điều chỉnh` has a total row ESS38 with "Thành tiền gốc" 0 and one detail row, and the fund
  row's twelve months read 0 after Excel recalculates

#### Scenario: Month link for a zero original
- **WHEN** a fund row linked to a zero row is recalculated after the PM types a "Nhập số" figure
- **THEN** each month cell equals that figure / 12, and `1. Summary` and the contingency lines follow

#### Scenario: New-project run unchanged
- **WHEN** "Tạo ngân sách" runs for a new project
- **THEN** sheet `4. Điều chỉnh` holds the same rows as before this change, plus one row per line left for the PM

## ADDED Requirements

### Requirement: Every line left for the PM has a row on every run
On every run, new project and Review alike, each line left for the PM (capability `pm-filled-lines`) SHALL get a
total row on sheet `4. Điều chỉnh` with one lumped detail row (quantity 1 locked, unit price empty, type "Nhập số")
whose yellow input cell is empty, and its fund row's unit-price and month cells linked to it so they show nothing
until the PM types a figure. The total row SHALL be marked "PM điền". When the PM types an annual figure, the fund
row's months SHALL equal that figure / 12 (or follow the line's frequency) and `1. Summary` and the contingency lines
SHALL follow, with no Excel error while the cell is empty. A line left for the PM that also carries an approved figure
on a Review SHALL get one row, not two.

#### Scenario: New project
- **WHEN** "Tạo ngân sách" runs and ESM6 is left for the PM
- **THEN** sheet `4. Điều chỉnh` has an ESM6 total row marked "PM điền" with an empty yellow detail cell, and the
  fund row's F and H–S show nothing

#### Scenario: PM types a figure in Excel
- **WHEN** the PM types 24,000,000 VND in ESM6's detail cell and Excel recalculates
- **THEN** each ESM6 month on `2. Budget-Management Fund` reads 2,000,000 VND and `1. Summary` includes 24,000,000 VND

#### Scenario: Review with an approved figure
- **WHEN** a Review's approved budget prices ESC4 at 50,000,000 VND and the tool left ESC4 for the PM
- **THEN** sheet `4. Điều chỉnh` has exactly one ESC4 total row, marked "PM điền", showing the approved figure
