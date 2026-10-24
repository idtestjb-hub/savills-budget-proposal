## Context

The scan store is built outside the repo, in `Savills-local\budget-test\scan-2026-10-07\v2\`:
- `scan_budgets_v2.py` reads each workbook. It imports `budget_rows.py` from `source_code` for the leaf and tie
  rules (`BUDGET_ROWS_SRC`).
- `build_final_v2.py` writes the CSV store (`final_v3` today). It picks the main sheet: the visible MF budget sheet
  that ranks best on tie, period and non-zero lines.

`build_real_budget_ranges.py`, in the repo, turns the store into `Ref_RealBudgetValues.csv`. Its rules are in the
`real-budget-ranges` spec.

Why the 11 files fail today:
- **Tie needs PL rows.** The scanner sets `anchored` only when R, E, `PL1` and `PL2` rows all exist
  (`scan_budgets_v2.py:353`). Old forms have R and E but no `PL` rows, so their sheets are `no_anchor` / low even
  where R and E tie exactly.
- **A hand-added code column (confirmed 2026-10-22).** The 2022 file is not on the Savills form. Someone added a
  code column (AF, "code Budget") beside a check column (AE, "Hương check", 0 on every row). The scanner reads the
  column left of the code column as the roll-up indicator, so every row counts as a roll-up and the sheet is
  dropped (fewer than 10 leaves).
  - The sheet has no R / E code rows; its totals are the labelled rows "REVENUES" and "EXPENDITURES".
  - One line with an amount has no code ("Electricity of basement", 40 M VND).
  - So it is a form of its own, with its code column as a first map. It goes through D3, not through a scanner
    rule.
- **Departmental form.** The developer's form numbers its items `A1`, `B1`, `C1`, `D1`… (column A or B). Only one
  of the four files adds Savills codes in column A. In the other three, the codes are classed as fund `OTHER`, and
  no value column is found.
- **No codes.** The `.xlsx` year-1 budget of one project lists items by label only, with a 14-month year 1
  (10/2023–12/2024).
- **No NFA.** The info sheet of the standard form is left at 0 in many 2026 files. The NFA is either in the master
  list, or written elsewhere in the file (`1. Summary` row "Diện tích thu phí", a fee sheet, a note on the fee line).

The scope list, with every file, its cause and its fix, is `Savills-local\budget-test\2026-10-22-p8\bang-ke-26-file.md`.

## Goals / Non-Goals

**Goals:**
- Bring the 11 approved files into the store with the same tie and VAT rules as every other file.
- Keep each new path explicit and auditable: no file enters on a guessed NFA or a guessed code.

**Non-Goals:**
- No change to `budget_rows.py` or Budget Review. The old-form tie and the code maps are store-only.
- No change to how the tool uses a range (floors, outliers, codes in scope).
- The `.xlsb` and PDF rules stay as they are.

## Decisions

1. **Old-form tie in the scanner, not in `budget_rows.py`.** When `PL2` is missing (the two 2021 files have `PL1`
   and `PL3`, no `PL2`) but R and E rows exist, the scanner ties the value column on `{R, E}` through `budget_rows.explain_tie(sections=['R','E'])`. That
   function already takes the sections as an argument. The sheet's status is `ok` / `ok_filter` / `ok_double_count`
   or `mismatch` as usual, with a flag `form_cu_khong_PL`.
   - Alternative: relax `anchored` inside `budget_rows`. Rejected, because that module is shared with Budget Review,
     which the user did not ask to change.
   - The two known gaps (5.0 M and 72.4 M on E) were traced on 2026-10-22: they are the `ES#` / `EM#` lines
     ("always a leaf" on the standard form), which the scanner's no-anchor branch skipped because they carry an
     indicator. With the anchored leaf rules both sheets tie to 1 VND. A gap that cannot be explained still keeps a
     file out.
2. **No general change to the code-column search** (revised 2026-10-22, after task 2.2's check). Widening the
   search or moving the indicator column would change how every catalogued Savills-form sheet is read, for one file
   that is not on the form. The 2022 file goes through D3 instead.
3. **Code maps as reviewed CSVs beside the store, read by one reader for other forms.**
   - `code_maps\<form>.csv` holds `label_norm, label_shown, code, source, note`, and the file's header carries the
     approval date. `code` may be `(nhóm)` for a group row, which is never a line.
   - `other_forms.csv` lists each file read this way: store id, sheet, label column, value column, the labels of the
     R and E total rows, the period, and the map.
   - A separate module (`scan_other_forms.py`) reads them. Its outputs (catalogue, lines, reconcile) have the same
     columns as the scanner's, so `build_final_v2.py` treats them like any sheet.
   - The tie decides whether the map is right: the mapped leaf lines must add up to the R and E rows, as for every
     sheet. A group row counted as a line, or a line left out, shows as a gap.
   - **Group rows by formula, not by item number** (found 2026-10-22). In one file "D2 Staffing Cost" (5.8 bn) is
     followed by "D2.1" (80 M), but D2 is not D2.1's total. A row is a group when its value cell is a vertical
     `SUM` / `+` over other rows of the same column. Leaf cells sum the month columns horizontally, or hold a
     constant.
   - **Map key.** The key is the normalised English label. When a label repeats among the leaves of one sheet, the
     key is the nearest group above plus the label. For example, "Repairing Cost" sits under several system groups
     with different codes.
   - **Section ends.** E ends at the profit row (its formula subtracts II from I). Lines after it are not read, for
     example the corporate income tax on extra revenue.
   - **Handover-year files (user's choice 2026-10-22).** Two departmental files have pre-opening months inside their
     budget year. Only the month columns of operation are read: 10 months for one, 7 for the other. Each month
     column ties on its own R and E rows. The period is the operating months, flagged "kỳ N tháng" like any short
     period. The pre-opening months are not read.
   - **2022 file:** the map is seeded from its own code column AF, completed by hand for the lines without a code.
     - Value column: K, "Total Budget of Year", 05/2022–04/2023.
     - Anchors: the "REVENUES" and "EXPENDITURES" rows.
   - **Departmental form:** the map is seeded from the one file with Savills codes (column A next to its item label),
     then completed by hand for the labels it leaves blank (for example "Night, Public holiday shift", "Uniform").
     The match is by normalised label, because item numbers shift between files (the same label is `C6` in one
     file and `C7` in another).
     - Value column: "Cộng năm / Total Year" of the budget period block ("Ngân sách dự toán từ MM/YYYY đến MM/YYYY").
     - Anchors: the section rows "REVENUE / DOANH THU" (R) and "OPERATING COSTS / CHI PHÍ VẬN HÀNH" (E).
     - Pre-opening and HOV columns are not read.
   - **No-code budget:** the map is written by hand, label by label, for its `Operation Cashflow` sheet. The period
     is the 14-month year 1. The amount per month divides by 14, as the store does for every period of real
     length.
   - The scanner refuses a file of either form when an item with an amount above 0 has no map row (spec).
   - Alternative: write Savills codes into copies of the workbooks. Rejected, because it changes source files and
     hides the mapping.
4. **NFA: per-file table first, then the master list, both checked.**
   - `nfa_per_file.csv` sits beside the store: `file_id, nfa_fee, nfa_apartment, source_sheet, source_cell,
     ref_rate, ref_rate_vat, approved_on, note`. The scanner never writes to it.
   - `build_real_budget_ranges.py` does the master-list match, with the store's `project_map` name, normalised. The
     name stays inside the build and never reaches the output.
   - The fee check is done by the build:
     - implied rate = Σ `RM.*` per month excluding VAT ÷ NFA;
     - reference = the master rate excluding VAT (÷ 1 + VAT of the budget year per `vat_cut_periods.csv`, when
       `MgmtFeeVAT` = `incl_VAT`), or the table's `ref_rate`;
     - pass when |implied ÷ reference − 1| ≤ 0.15.
   - Expected per file, from the checks of 2026-10-22:
     - one file passes on the master list (implied 17,130, reference 17,130);
     - one passes only on the rate written in the file, because the master rate (13,500) predates the file's 16,600;
     - one file with no fee revenue enters through the table, as approved (20,944.7 m²);
     - the four departmental-form files enter through the table, with the areas written in their fee-line notes or
       info sheet;
     - the two old forms take the store's own "I." group, as today, and need no fallback;
     - the no-code budget's profile sums its product rows to 291,712.4 m². That includes a 97,237.5 m² "Management
       Fee" row, which equals apartments 94,849.2 + shophouse 2,388.2. Task 4.3 records the 97,237.5 in the table
       after the fee check;
     - the 2022 file is not checked yet. Its fee lines include basement-parking and land-area fees, so the master
       rate may not be a fair reference. Task 3.3 checks it; if it fails, the user decides.
   - Alternative: let the scanner write the master NFA into `file_profile`. Rejected, because it mixes sources in
     one column and loses where the NFA came from.
5. **New store folder.** The store is rebuilt to `final_v4`; `final_v3` is kept. The `v3`→`v4` comparison
   (`compare_v3.py` pattern) lists every file whose status, main sheet, NFA or values change. Only the 11 approved
   files may change. Any other change stops the build for review.
6. **Measure in an overlay, as P7.** `Ref_RealBudgetValues.csv` is rebuilt into `2026-10-22-p8\overlay_v4\`. Then:
   - the verify tree with open gates (`run_verify_tree.py --open-gates`), then M3 with `M3_DATA_OVERLAY`, run one
     after the other (Excel COM);
   - a before/after table per recorded figure;
   - live and baselines only after the user signs off.

7. **Found while applying D3 (2026-10-22, all six files tie to 1 VND on R and E):**
   - A group row is a pure vertical aggregate in its value cell or its first month cell: `SUM(a:b)`, `SUBTOTAL(9,a:b)` or a `+`
     chain of same-column cells. A line that is a percentage of other lines (`=0.1*SUM(...)`, "Misc 10%", the VAT line) is a
     leaf. In the 2026 departmental file the sub-group rows carry horizontal year-total formulas, so the month cell decides.
   - Q2 Thảo Điền 2022: E is the `EXPENDITURES` block plus the `MAINTENANCE` block (rows 29 and 111); a profit row sits between
     them. "Corporate Incomes Tax on Estimated Profit" is a cost line, not the profit row.
   - Handover-year files read their operating months only: 10 months (10/2023-07/2024) and 7 months (01-07/2023).
   - MWH: the period is 10/2023-12/2024 and the month count is set to 14 in `other_forms.csv` (October has 4 days); the budget
     year is 2024 by the rule (12 of the 15 calendar months).
   - Fee check for files whose fee revenue mixes products (apartments, shops, nursery, villas, parking): the reference rate in
     `nfa_per_file.csv` is the area-weighted average of the rates written in the file itself. With the apartment rate alone,
     the 2026 departmental file reads +21.1% and the 2022 file +22.2% and both would be left out.
   - The old-form tie also moves one more file from `no_anchor` to tied (Verosa Park 20.9). It adds no project: the 2027
     file of the same project is kept.

## Risks / Trade-offs

- [The departmental-form map hides a judgement per label] → The user approves the map. Every mapped amount above 0
  is listed in the before/after with its code.
- [Master-list names collide (several phases, or "Dragon Parc 1/2")] → A match must be unique; two candidates leave
  the file out with "trùng tên master".
- [The 15% band is wide enough to pass a wrong NFA that is off by under 15%] → Accepted as approved. The README
  shows the implied rate and the reference rate of every file that took a fallback NFA.
- [2021–2022 budgets carry older practice (rates, contract models)] → They enter under the CPI rule like any older
  year. The README already counts budget years. The outlier rule (1.5×IQR) still applies.
- [The no-code budget's 14-month year 1 mixes the opening months in] → Per-month division is by 14 real months. It is
  flagged with the period flag the README already prints.

## Migration Plan

1. Prerequisite: archive `read-aggregate-rows-by-formula` (signed off 2026-10-21), so that the `real-budget-ranges`
   main spec is current before this delta.
2. Build `final_v4` beside `final_v3`, then the overlay `Ref`. Measure, then sign-off.
3. Go live:
   - copy the overlay `Ref_RealBudgetValues.csv` and `README.txt` into `Budget_Agent/data/real_budget_ranges/`, with
     a dated backup of the old pair;
   - copy the v4 CSVs into `input\budget_planning\_kho_quet\` (backup as on 2026-10-22);
   - point the web library at `final_v4`.
4. Re-record the baselines once; run verify with the gates closed.
5. Rollback: restore the backed-up `Ref` pair and the `_kho_quet` CSVs; `final_v3` is untouched.
