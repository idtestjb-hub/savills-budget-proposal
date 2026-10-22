## Why

The tool reads real Savills budget workbooks in two places: Budget Review reads last year's approved budget, and the
real-budget scan store feeds the anonymous budget ranges and the web library. Both decide which coded rows are
totals of other rows (aggregate rows) from the code alone: a row is dropped only when the rows that share its code
prefix add up exactly to it. Real files break that rule:
- **MT EASTMARK:** `RO4` is `SUBTOTAL` over rows 48:55, which takes in `RO4.x` and `RO5`. The rows under `RO4`
  do not add up to it, so `RO4` stays in and 305,945,102 VND is counted twice.
- **DRAGON HILL 2:** the file was saved with a filter that hides 699 of 706 rows. Every `SUBTOTAL` cell holds 0, so
  the file's own R and E rows cannot be tied.
- **GOLDEN MANSION:** `RO2` uses `SUM` instead of `SUBTOTAL`. The file's own R row counts it twice, and the reader
  reports a 1,820,000 VND gap.

On 2026-10-21 the user approved recognising aggregate rows by the formula in the cell. This has to come before change
2 (`carry-forward-all-lines`), which carries every approved line into the new year from this reader.

Budget Review also stops on MT EASTMARK before reaching the lines, for two other reasons the user chose to fix in the
same change:
- it picks a hidden scenario sheet (`2. Budget-Management Fund (OP3)`) over the visible `2. Budget-THCN`;
- on that sheet it accepts a year column where R is 0, because 0 = 0 counts as tying.

## What Changes

- **Aggregate rows by formula.** A coded row whose value cell holds `SUBTOTAL(...)` or `SUM(range)` (array formulas
  included) over a range that covers at least one other coded row is an aggregate row:
  - it is never counted;
  - its cached value is not used;
  - the coded rows inside the range are its children.

  A row with a typed-in number is still dropped as today when its same-prefix children add up exactly to it.
- **Explained ties.** When the leaf sum does not equal the file's own R or E row, the reader recomputes that cell the
  way Excel does: `SUBTOTAL` skips rows hidden by a filter, and counts a second time a parent written with `SUM`
  or a parent that carries the same figure as its children.
  - If the recomputed figure equals the cached cell to within 1 VND, the sheet ties "after explanation", with the
    reason as a Vietnamese note:
    - "ô tổng bị bộ lọc che (N dòng ẩn)";
    - "lỗi file: <mã> dùng SUM, tổng của file cộng trùng <số> VND";
    - "lỗi file: <mã> trùng số với dòng con, tổng của file cộng trùng <số> VND" (added 2026-10-21 during apply:
      GOLDEN MANSION's `RO2` turned out to be a month sum like any line, holding the same 1,820,000 VND as `RO2a`).
  - The file's own figures are never changed.
- **Which sheets count as tying.** A sheet that ties after explanation counts as tying everywhere a tying sheet is
  required: the Review import, the real-budget ranges, the web library label.
- **Budget Review sheet choice.** Budget Review prefers a visible fund sheet over a hidden one.
- **Year column.** Budget Review no longer accepts a year column with R at 0 while another column of the same sheet
  carries revenue.
- **Rebuild.** The scan store is rebuilt into a new folder from the same source files. The anonymous data file
  `Ref_RealBudgetValues.csv` is rebuilt from it, and the web library reads the new store.
- **Labels.** The web library and the Review import notes show the two new tie states with their reason.

Not in this change:
- multi-phase sheets that have no R / E rows (`2. Budget-MF Phase 01`);
- the month count of GOLDEN MANSION's Management Fund sheet (1 month column found instead of 7);
- PDF and xlsb sources.

## Capabilities

### New Capabilities
- `budget-workbook-aggregate-rows`: how a real budget workbook's coded rows are split into leaf lines and aggregate
  rows, and how a sheet's leaf sum is tied to its own R and E rows, including the two explained-tie cases. Shared by
  Budget Review and the real-budget scan store.

### Modified Capabilities
- `budget-review-workflow`: the requirement "Last year's approved budget is read by line code" changes:
  - aggregate rows are recognised by formula;
  - explained ties are accepted and noted;
  - a visible fund sheet is preferred;
  - a year column with R at 0 is refused when another column carries revenue.
- `real-budget-ranges`: the requirement "The scan store becomes one anonymous per-project data file" now accepts a
  main sheet that ties after explanation, and the store is built with the aggregate-row rules.

## Impact

- **Code:**
  - a new shared module in `source_code/` for aggregate rows and tie explanation;
  - `review_import.py` (fund sheet reading, sheet choice, year column);
  - `webapp/library.py` (tie labels).
- **Scan store scripts** (in `Savills-local\budget-test\scan-2026-10-07\v2\`, outside git):
  - `scan_budgets_v2.py` calls the shared module;
  - `build_final_v2.py` maps the new tie states.
- **Data:**
  - a new store folder `final_v3` in `Savills-local`; `final_v2` is kept for rollback;
  - `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv` is rebuilt.
- **Figures:**
  - Lines priced from the real-budget ranges (`EMB4`, `ESS12`, `ESC5`, `ESS7`, `ESS23`, `ESC1`, `ESC2`, `RM.AP`) can
    move when a project joins or leaves a range, or when its values change. So can the cross-check ranges of
    `ESI1`, `EMH1` and `EMH3` on the internal sheet.
  - A before/after is measured on the three samples and the four real projects. The PM signs it off before archive.
- **Web:** the library and labels change on the server only after a release note and a [Hub] deploy.
