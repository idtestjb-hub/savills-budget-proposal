## Why

The real-budget ranges are built from 44 of the 87 files in the scan store. On 2026-10-22 the user asked which of
the files left out could be recovered, file by file. 26 were checked: 10 have no fee-paying NFA, 11 have no main
operating-fund sheet, and 5 have a main sheet that does not tie. Eleven of them are real residential budgets that
fail only on how the store reads them:
- the NFA is missing from the file but is known elsewhere, or written in the file outside the info sheet;
- the old form (2021–2022) has no `PL1` / `PL2` rows, so the scanner never ties the sheet, although its R and E rows
  are there;
- the code column sits far to the right of the item column;
- four budgets of one developer use their own departmental form with their own item numbers, and one budget has
  no codes at all.

The user approved the scope and the rules on 2026-10-22 (four answers and one follow-up below). More projects per
range make every median and P25–P75 steadier, and bring more codes over the 10-project floor.

## What Changes

- **NFA from the master list, checked.** A file whose own profile has no fee-paying NFA can take the NFA of the
  master list (`Dim_Property_Residential.csv`) when:
  - the names match after removing accents, case and punctuation;
  - the fee rate it implies (management-fee revenue per month excluding VAT ÷ NFA) is within 15% of the master
    list's rate or of the rate written in the file.

  Otherwise the file stays out and the build log says why. The check matters: on 2026-10-22 two master-list NFAs
  were wrong (one larger than its GFA, one giving a rate five times the real one).
- **NFA written elsewhere in the file.** Where the file states its NFA outside the info sheet (a summary row, a
  note on the fee line), the reviewed figure is recorded once per store file, with the cell it came from. One case
  was chosen by the user: apartments + retail + shophouse, without the developer's parking (20,944.7 m²), matching
  the store's rule of the "I." products group without parking.
- **Old form without `PL` rows.** A sheet with R and E rows but no `PL1` / `PL2` ties on R and E alone. It must tie
  to 1 VND, or the gap must be traced to its row and explained (Vietnamese note). Otherwise it stays out.
- **Code column anywhere.** The scanner finds the code column wherever it sits in the sheet.
- **Departmental form through a code map.** The developer's departmental budget form (item numbers `A1`, `B1`,
  `C1`, `D1`…) is read through a map from item label to Savills code. The map is built from the one file of that
  form that carries Savills codes, completed by hand, and approved by the user before it is used. The same applies to
  the one budget that has item labels and no codes (its `.xlsx` year-1 budget; the `.xlsb` report stays out, as
  today).
- **Rebuild and sign-off.** The store is rebuilt into a new folder (`final_v4`) from the same sources, and
  `Ref_RealBudgetValues.csv` is rebuilt from it into an overlay. Every movement of a recorded figure is measured
  before/after. The user signs off before the file goes live. Expected: up to 55 projects instead of 44.

Left out, as approved (15 files): park, infrastructure and villa-area budgets with no fee revenue and no NFA (5), a villa
compound without NFA and with two operating models, an office tower, a budget charged per unit, a 2019
summary-only budget, a capex purchase form, the multi-phase budget (as decided 2026-10-21), and four files that only
duplicate a project already in the store.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `real-budget-ranges`: three new store rules (a checked NFA when the file has none, the old-form tie on R and E,
  other forms through an approved code map). The existing rules (main sheet only, ties, no PDF or xlsb, one file per
  project, latest year, anonymity) are unchanged.

## Impact

- Scanner and store build in `Savills-local\budget-test\scan-2026-10-07\v2\` (`scan_budgets_v2.py`,
  `build_final_v2.py`), outside the repo. New `final_v4\` store. The code maps and the per-file NFA table stay in
  `Savills-local` with the store, because they are read from confidential workbooks.
- `build_real_budget_ranges.py`: master-list NFA with the fee check, the per-file NFA table, README counts and
  reasons. Tests in `tests/test_build_real_budget_ranges.py`.
- Data: `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv` and `README.txt` rebuilt (live only after
  sign-off); `input\budget_planning\_kho_quet\` refreshed with the v4 CSVs.
- Figures: every code priced from a range can move (`EMB4`, `ESS12`, `ESC5`, `ESS7`, `ESS23`, `ESC1`, `ESC2`,
  `RM.AP`, and the cross-checks `ESI1`, `EMH1`, `EMH3`). Baselines are re-recorded once, after sign-off.
- Order: `read-aggregate-rows-by-formula` (signed off 2026-10-21) should be archived first, since both changes touch
  the `real-budget-ranges` spec.
