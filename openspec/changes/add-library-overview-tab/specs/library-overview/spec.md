## Purpose
The Budget web shows, on one page, how many real-budget store files exist per budget year, how they are classified and why files are left out, so users can judge how much real data the tool stands on.

## ADDED Requirements

### Requirement: A tab summarises the store on one page
The Budget web SHALL offer a tab named "Kho ngân sách" that shows, for the whole store (every row of `dim_file.csv`, 87 on 2026-10-22): the number of files per budget year, split by class; a table of reasons with counts; and a table by file type (xlsx, pdf, xlsb, zip) split by class. Files whose budget year is unknown SHALL appear in a "Chưa rõ" column, never dropped. The counts in each table SHALL add up to the total shown. The tab follows the Savills palette and Arial, shows no logo, and uses no gridlines or in-chart title.

#### Scenario: Totals tie
- **WHEN** a user opens the tab on the 87-file store
- **THEN** the per-year counts, the reason table and the file-type table each sum to 87, including the "Chưa rõ" column

#### Scenario: Unknown year
- **WHEN** a store file has no budget year
- **THEN** it is counted under "Chưa rõ" and not left out of the totals

### Requirement: Two views with their own classification
The tab SHALL offer a view "Dùng cho Review" and a view "Dùng cho bảng giá thực tế". In the first, each file is "chọn được" or "không chọn được" with the reason that the Review tab shows. In the second, each file is "Dùng" (a project of the price table), "Gộp" (the same project as a newer file) or "Loại", with a reason. A file the price table used for most codes but not for `RM.AP` is "Dùng" with its own reason line. Two files with the same name but NFA more than 5% apart are two projects, each "Dùng". The number of "Dùng" files in the second view SHALL equal the number of projects in `Ref_RealBudgetValues.csv`.

#### Scenario: Review view matches the picker
- **WHEN** the first view is shown
- **THEN** its "chọn được" count equals the `selectable` count that `/api/library` returns

#### Scenario: Price-table view matches the data file
- **WHEN** the second view is shown for the store the price table was built from
- **THEN** its "Dùng" count equals the number of distinct projects in `Ref_RealBudgetValues.csv`

### Requirement: The overview endpoint returns aggregates only
`GET /api/library/overview` SHALL require the same login as `/api/library` and SHALL return counts only. It SHALL NOT return a file name, project name, file path, store id or any cell value from a budget, and its output SHALL pass the same name check the builder applies to its outputs.

#### Scenario: Not logged in
- **WHEN** a request without a valid session calls the endpoint
- **THEN** it is refused as `/api/library` is

#### Scenario: No names in the response
- **WHEN** the endpoint answers for the full store
- **THEN** no string in the response equals or contains a store file name, project name or path

### Requirement: A missing or stale usage file hides the second view only
When `Ref_RealBudgetUsage.csv` is missing, unreadable, or lists store ids that are not all in `dim_file.csv` (or `dim_file.csv` has files the usage file does not list), the endpoint SHALL still answer the first view, mark the second view as unavailable with a plain reason, and the tab SHALL show that reason instead of the second view. A missing store SHALL give an empty page with a plain message, not an error page.

#### Scenario: Usage file absent
- **WHEN** the server has no `Ref_RealBudgetUsage.csv`
- **THEN** the tab shows the first view and the text that the second view is not available until the price table is rebuilt

#### Scenario: Usage file older than the store
- **WHEN** the store has a file the usage file does not list
- **THEN** the second view is marked unavailable and names how many files are not listed

### Requirement: The change moves no figure
Adding the tab and the usage file SHALL NOT change `Ref_RealBudgetValues.csv`, any range, any generated workbook or any recorded verification baseline.

#### Scenario: Price data unchanged
- **WHEN** the builder is run on the 2026-10-22 store before and after this change
- **THEN** `Ref_RealBudgetValues.csv` is byte-identical
