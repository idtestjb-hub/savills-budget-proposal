## Why

The default frequency of a code in a new budget (`Ref_LineFrequency.csv`, 6 codes) comes today from the 2027 template's
own column C and from the counts the costing code prices with. How PMs actually budget a line was never measured. On
2026-11-09 the frequency column of all 55 mapped real budgets was read (239/239 fund sheets): several lines the tool
writes Monthly are paid once or twice a year in most real budgets (cleaning of the water tank, hazardous waste, the
maintenance of building equipment), and one template default (RO2a, Half a Year) is Monthly in every real budget that
carries it. The user approved rules for a table built from that read (`docs/05-decisions.md`, "Default frequency
from the 55 real budgets", and the answers of 2026-11-09 recorded under it).

## What Changes

- **The default table is built from the real budgets.** For each code, one vote per real budget file, from the
  Management Fund sheets only (budget sheets, lines with a non-zero amount; Schedule not counted; a file whose MF
  sheets give two frequencies equally often votes for nothing). A code takes a non-Monthly frequency when at least 5
  files carry it and that frequency has more than half of the votes; otherwise it is Monthly.
- **Four exceptions keep the frequency their costing counts** (user, 2026-11-09): ESC12 Yearly ("một lần/năm"),
  ESM2 Half a Year ("6 tháng/lần theo Nghị định 40/2019/NĐ-CP"), ESM5 Quarterly (4 rounds a year), ESM25 Quarterly.
- **Codes not on the 2027 form are left out** (ESA1).
- **Resulting table, 11 codes (was 6):** Yearly ESC4, ESC5, ESS10, EMB4, ESA16, ESC12; Half a Year ESM3, ERCS1, ESM2;
  Quarterly ESM5, ESM25. RO2a goes back to Monthly. Every cyclic line still starts in T1. Each row states its source
  as counts only ("real budgets: Yearly 22 of 39 MF files"), with no project name or file name.
- **The default also applies to the lines left for the PM** (ESC4, ESS10, ERCS1 today; EMB4 and ESC5 when the range
  data is too thin): their fund row and their row on sheet `4. Điều chỉnh` carry the default frequency and its months
  of payment; the price stays blank until the PM types an annual figure, which is then paid at the table's times
  (once in T1 for Yearly). When the PM's figure is saved on the web, the remark gains the frequency sentence.
- **The read of the 55 budgets moves into the repository** as part of `build_line_frequency.py` (office-only, as
  today): it reads the mapped files listed in `real_budget_ranges_map.csv`, so the table can be rebuilt; the raw read
  and the votes stay on the office machine and are never committed.
- **Measured before/after** on the standard sample and the four real projects of the earlier changes; recorded
  baselines re-recorded once after the user's sign-off.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `line-frequency`: the default table's source, rules, exceptions and coverage of the lines left for the PM.
- `pm-filled-lines`: a line left for the PM may carry a cyclic frequency; how it looks and how verification checks it.

## Impact

- **Code:** `build_line_frequency.py` (store read, votes, exceptions, form filter), `budget_adjustment.py`
  (`lumped_item` / `add_pm_rows`: a PM line takes the table's frequency; shading of a cyclic PM row),
  `generate_project_budget.py` (`_apply_line_frequencies` leaves PM lines to sheet 4, unchanged otherwise),
  `webapp/adjust.py` (`_pm_remark` adds the frequency sentence when a PM figure is saved on a non-Monthly line),
  `verification/checks.py` (`pm_line_problems`, `check_pm_lines` for a cyclic PM line).
- **Data files read:** the 55 mapped real budgets (office machine, read only), `real_budget_ranges_map.csv`, the 2027
  template. **Written:** `data/generation_B_verified/Ref_LineFrequency.csv` (11 rows, counts only).
- **Recorded baselines:** annual figures do not move, except the per-time rounding of a priced line now cyclic (a few
  VND, as in `add-line-frequency`); the month spread, F (price per time) and the remark of EMB4 and ESC5 (when priced)
  move; RO2a's row goes back to Monthly at 0 VND; lines left for the PM stay at 0 VND. Baselines are re-recorded once
  after the user's sign-off.
