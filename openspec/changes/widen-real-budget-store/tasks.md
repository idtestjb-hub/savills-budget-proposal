## 0. Prerequisite

- [x] 0.1 Archive `read-aggregate-rows-by-formula` (user's request needed). Then run `openspec validate --all --strict`
  and verify that it passes with this change active.

## 1. Baseline of the store and the ranges

- [x] 1.1 Copy `scan-2026-10-07\v2\` to `v4` working copies (`scan_budgets_v2.py`, `build_final_v2.py` with
  `SCAN_VERSION=v4`). Verify that a rebuild of v3 from the copies reproduces `final_v3` byte for byte on
  `file_profile`, `reconcile` and `fact_line`.
- [x] 1.2 Write `2026-10-22-p8\before.md`: the README counts of the live `Ref_RealBudgetValues.csv`, plus the
  recorded figures the verify tree and M3 report on the live data (P7 scripts). Verify that it lists the 44
  projects and every per-code count.

## 2. Scanner: old form

- [x] 2.1 Tie on `{R, E}` when `PL1` / `PL2` are missing (design D1, flag `form_cu_khong_PL`). Trace the two known
  gaps (5.0 M on E and 72.4 M on E) to their rows, and report each cause with a Vietnamese note. A gap that cannot be
  explained stays a `mismatch`. Verify with a scanner test on a small synthetic sheet (ties / gap explained / gap
  not explained), and with the v4 `reconcile.csv` rows of the two files.
- [x] 2.2 Check why the 2022 file is not catalogued (design D2, revised). Result: a hand-added code column AF
  beside a check column read as the roll-up indicator, no R / E code rows, one coded line missing. Routed to
  the other-forms reader (group 4); no change to the code-column search.

## 3. NFA

- [x] 3.1 Create `nfa_per_file.csv` beside the store (design D4) with the rows approved on 2026-10-22: the 20,944.7 /
  18,641 m² file, and the departmental-form areas read from their notes and info sheets (each with sheet, cell, and
  the user's approval date once given). Verify that each figure reads back from its cell through Excel COM.
- [x] 3.2 `build_real_budget_ranges.py`: per-file table, then the unique normalised master-list match, then the 15%
  fee check (reference rate excluding VAT at the budget year's rate). Write README lines with each file's source,
  implied rate and reference rate, and leave out `RM.AP` without an apartment NFA. Verify with new tests in
  `tests/test_build_real_budget_ranges.py`: pass, fail, no match, two matches, table wins, no fee revenue without a
  table row, and `RM.AP` left out.
- [x] 3.3 Run the check on the master-list candidates and list the result per file. Verify that the file at 61,987.75 m²
  passes, that the 54,624 m² NFA fails, and that the 2022 file's result is shown to the user for a decision if it
  fails.

## 4. Code maps

- [x] 4.1 Seed `code_maps\departmental.csv` from the departmental-form file that carries Savills codes (label →
  code), and list the labels with an amount above 0 in any of the four files that the seed leaves blank. Verify
  that every such label of the four files is in the list.
- [x] 4.2 Write `code_maps\no_code_budget.csv` for the `Operation Cashflow` sheet of the `.xlsx` year-1 budget, label by
  label, and `code_maps\q2_2022.csv` seeded from the 2022 file's own column AF and completed for its uncoded lines.
  Verify that every row with an amount above 0 in each sheet is covered.
- [x] 4.3 User approves the three maps and the NFA table rows (date recorded in each file). Record the no-code budget's
  97,237.5 m² after the fee check.
- [x] 4.4 `scan_other_forms.py` reads the files listed in `other_forms.csv` through their maps (design D3): value
  column, R and E total rows by label, period, and refusal on an unmapped label with an amount. Its outputs have the
  scanner's columns. Verify with tests on small synthetic sheets (mapped, group row, unmapped label stops the
  file, approval date recorded), and verify that each of the six files ties on R and E in the v4 `reconcile.csv` or
  gives a traced gap.

## 5. Rebuild and measure

- [x] 5.1 Build `final_v4`, and write `v4_vs_v3.md` with a `compare_v3.py`-style script. Verify that only the 11
  approved files change status or values; any other change stops for review.
- [x] 5.2 Rebuild `Ref_RealBudgetValues.csv` into `2026-10-22-p8\overlay_v4\` with `--store final_v4`. Verify that the
  name scan passes (no project or file name in the output), and that the project count and the excluded list match
  `bang-ke-26-file.md`.
- [x] 5.3 Measure in the overlay, one run after the other: the verify tree with open gates, then M3 with
  `M3_DATA_OVERLAY`. Write `2026-10-22-p8\before_after.md` with every recorded figure that moves, the medians per
  code, and the projects added per code. Verify that each movement is traced to the new projects.
- [x] 5.4 User signs off on `before_after.md`.

## 6. Go live

- [x] 6.1 Back up the live `Ref_RealBudgetValues.csv` / `README.txt` and the `_kho_quet` CSVs. Then copy the overlay
  pair and the v4 CSVs in, and point the web library's default store at `final_v4`. Verify that the README build
  line shows the v4 store, and that the web library lists the new files with their tie labels.
- [x] 6.2 Re-record the baselines once. Run `python verification/verify.py` with the gates closed and the full test
  suite. Verify that both pass, and record the counts in `docs/project-status.md`.
- [x] 6.3 Update `docs/05-decisions.md` with the rules approved on 2026-10-22, `RUNNING.md` with the store build
  steps (maps, NFA table), and the `real-budget-ranges` README text. Verify with `openspec validate
  widen-real-budget-store --strict`.
