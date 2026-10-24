## Context

The leaf-line logic exists in three copies:

| Copy | Location | Version |
|---|---|---|
| Scan v1 | `Savills-local\budget-test\scan-2026-10-07\scan_budgets.py` | outside git |
| Scan v2 (builds today's store `final_v2`) | `v2\scan_budgets_v2.py` in the same folder; imports constants from v1 | outside git |
| Review | `review_import.py` (`read_fund_sheet`) | in git |

All three:
- read values only (`data_only=True`);
- find leaves as coded rows without an indicator;
- drop a leaf as a roll-up only when its same-prefix children sum to it in that column (`kids` / `gone` in
  `col_sums`).

The store's main-sheet choice (`build_final_v2.py`) already prefers visible sheets; Review's `choose_fund_sheets`
does not.

Today's store: 62 files have a main sheet, with these tie states:

| Tie state | Files |
|---|---|
| `ok` | 54 |
| `mismatch` | 3 (MT EASTMARK, DRAGON HILL 2, GOLDEN MANSION) |
| `no_anchor` | 5 |

The ranges take only files whose `primary_confidence` is `high`. `build_final_v2.py` maps `ok` → `high`.

Evidence and the approved rules: see proposal.md. Probe scripts:
- `Savills-local\budget-test\2026-10-21-p6-g10\probe_*.py`;
- `...\2026-10-21-p7\probe_review_read.py`.

## Goals / Non-Goals

**Goals:**
- One implementation of the aggregate-row and tie rules, used by Review and by the store build.
- The store rebuild is reproducible from a recorded commit of that implementation.

**Non-Goals:**
- Moving the scan scripts into git. Folding v1 into v2.
- Multi-phase sheets without R/E rows.
- PDF and xlsb sources.
- The month-column count.
- Re-reading files the store already marks as content duplicates.

## Decisions

**D1. A shared module `budget_rows.py` in `source_code/`.**
- **What it holds:** pure functions over a grid of cached values plus a grid of formulas:
  - `find_aggregates(...)`: code rows → {row: children rows} from `SUBTOTAL` / `SUM` ranges in a column;
  - `dropped(...)`: which leaves count in a column; the formula rule first, then the existing prefix fallback for
    typed-in parents;
  - `double_counted(...)`: the rows dropped here that the file's SUBTOTAL still counts (a SUM aggregate, or a
    prefix-dropped parent whose cell is not a SUBTOTAL);
  - `explain_tie(...)`: direct / filter / double count / none, plus the Vietnamese notes;
  - `sheet_layout(...)`: hidden rows and the auto-filter of named sheets, from the workbook XML.
- **Who uses it:**
  - `review_import.read_fund_sheet` calls it;
  - `scan_budgets_v2.scan_sheet` imports it by putting the `source_code` path on `sys.path` (the script already runs
    from a fixed local folder).
- **Alternative:** patch all three copies. Rejected: they drifted once already. Review copied v1's rules, and its
  docstring promises "the way the real-budget scan store does".

**D2. Formulas come from a second, non-`data_only` read of the same sheet.**
- openpyxl gives a formula as a string, or as an `ArrayFormula` whose `.text` is the formula. Both are parsed.
- Range parsing reads `SUBTOTAL(<fn>, ref[, ref…])` and `SUM(ref[, ref…])`:
  - only same-sheet, same-column ranges or cell lists count;
  - for `SUBTOTAL`, function 9 / 109 only;
  - for `SUM`, a single cell that points at one coded row also counts, so `=SUM(AK40)` makes row 40 a child.
- `+`-chains of cells (`=AK48+AK49`) are not treated as aggregates in this change: no evidence of them in the 3
  mismatching files. Parsing them would widen the A/B for nothing.
- **Cost:** about twice the read time per sheet. Acceptable: the store build is a one-off batch, and Review reads one
  file.
- **Alternative:** read the XML directly. Rejected as more code for the same result.

**D3. The value column is chosen after aggregate rows are dropped.**
- The column search keeps its order: passing columns, then headers. The test for "passes" becomes a direct tie or
  a tie after explanation.
- A direct tie ranks before an explained one; then the existing header priority applies.
- In Review, a column with R = 0 is passed over when another passing column has R ≠ 0.

**D4. Hidden rows and the auto-filter come from the sheet XML (`sheet_layout`).** openpyxl's read-only mode, used for
both reads, keeps neither; a full load of a 45-sheet workbook would cost far more.
- The cached values come from the `data_only` read.
- The filter case counts as a filter only when the sheet has an `auto_filter.ref`, or more than half the rows between
  R and PL1 are hidden. A sheet with a few manually hidden rows and a gap is reported as no tie.
- The recompute leaves out every hidden leaf. `SUBTOTAL(9)` counts manually hidden rows; `SUBTOTAL(109)` and a
  filter do not.

**D5. Tie states in the store.**
- `reconcile.csv` gets `status` values `ok`, `ok_filter`, `ok_double_count`, `mismatch`, `no_anchor`, `no_value_col`,
  `empty`, plus a new `note` column.
- `build_final_v2.py` maps `ok*` → confidence `high`, so `build_real_budget_ranges.py` needs no change.
- The web library maps the two new states:
  - label: "Khớp tổng (đã giải thích)";
  - the note is shown under it, beside the existing sentences for `mismatch` / `no_anchor`.

**D6. The rebuilt store goes to `final_v3\` and `tables_v3\`.**
- `final_v2` stays for rollback.
- The web library's default store path and the ranges build both point at `final_v3`.
- The build log records the `budget_rows.py` commit hash.

## Risks / Trade-offs

- **[Risk] A file that ties today could change state.** A formula parent was kept, and its tie was a coincidence.
  → Mitigation: `compare_v2.py`-style A/B of `fact_line` and `reconcile`, v2 against v3, over every file. Each moved
  line is listed with its file and code before the ranges are rebuilt.
- **[Risk] The second workbook read fails on files openpyxl only opens after stripping.** → Mitigation: read formulas
  from the same stripped copy.
- **[Risk] Range medians shift.** → Mitigation: before/after of `Ref_RealBudgetValues.csv` and of the deliverables of
  the three samples and the four real projects (M3 runner). The PM signs off.
- **[Trade-off] The store scripts stay outside git.** Their link to the shared module lives in the code path and the
  build log, not in version control.

## Migration Plan

1. Merge to `main`.
2. Rebuild `final_v3`, then `Ref_RealBudgetValues.csv`.
3. Get the before/after signed off.
4. Re-record the baselines once.
5. Write a release note for budget-web (the library store path and labels), which the [Hub] session deploys.

Rollback:
- point the store path back at `final_v2`;
- restore `Ref_RealBudgetValues.csv` from git;
- revert the commit.
