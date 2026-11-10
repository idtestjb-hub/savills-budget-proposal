## Why

Two gaps came out of the checks of 2026-11-09 (session P29) on the default frequency table built by
`default-frequency-from-real-budgets`:
- four codes sit just under the "more than half" rule in the 55 real budgets (Yearly in 40–50 % of the MF files that
  carry them) and stay Monthly. The user decided (2026-11-09) that they are budgeted Yearly.
- ESA16 is listed Yearly, but in the City Garden run it stayed Monthly. Its row has no price, is not a line left for
  the PM and keeps the template's guidance remark, so neither shape `_apply_line_frequencies` changes matches it. The
  amount is 0, so no figure moves, but the row does not show the table's frequency.

## What Changes

- **Four codes default to Yearly as user-chosen exceptions** (user, 2026-11-09). Counts are from the MF files of the
  real budgets: ESC2 (Fire drill) 16 of 34, ESC3 (Annual General Meeting) 14 of 34, ESS7 (External cleaning) 11 of
  23, EMA18 (Business licence tax) 9 of 19.
  - The builder lists them like the four costing exceptions: the row's note states the user's choice, the source
    gives the counts, and the first month is T1.
  - The table grows from 11 to 15 codes.
- **An unpriced Monthly row of a listed code takes the table's frequency.**
  - Applies when the row's F is blank or 0 and the line is not left for the PM, for example ESA16.
  - The row gets C = the table's frequency and the months of payment in H:S (the row-8 month headers), so the form's
    times check (U) is 0.
  - F is written 0 (a blank F too; user, 2026-11-10) and the remark is unchanged: no price, so no frequency
    sentence is added.
  - Lines left for the PM keep their current path (sheet 4).
- **Measured before/after** on the five fixtures and the M3 real-project runs, as in `default-frequency-from-real-budgets`.
  Recorded baselines are re-recorded once, after the user's sign-off.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `line-frequency`: the table's exceptions gain the four user-chosen Yearly codes, and an unpriced Monthly row of a
  listed code takes the table's frequency and months.

## Impact

- **Code:**
  - `build_line_frequency.py`: a second exception list, for user-chosen frequencies.
  - `generate_project_budget.py` (`_apply_line_frequencies`): a third shape, the unpriced Monthly row outside
    `_PM_LINES`.
  - Tests for both.
- **Data written:** `data/generation_B_verified/Ref_LineFrequency.csv` (15 rows, counts only). The old file is kept
  beside it as `.backup-<date>`.
- **Recorded baselines:** annual figures stay the same, apart from per-time rounding of a few VND.
  - The priced lines of the four codes move: C, F (price per time), the month spread and the remark sentence.
  - Unpriced rows of listed codes gain C and their months, still at 0 VND.
  - The Common Area Fund is not touched.
- **Release:** stacks on the pending budget-web release notes (902399f, 27e2ea3, 9b33469, 268daec). It is deployed by
  [Hub] together with them, never alone.
