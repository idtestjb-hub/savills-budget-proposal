## Context

See proposal.md for why; requirements are in `specs/budget-review-workflow/spec.md`. Naming from the PM's seat: N =
the running year whose approved budget is reviewed, N-1 = the year before, N+1 = the year the tool builds.

Today `review_import.read_prior_budget()` opens the file with cached values (`data_only`), picks per fund sheet one
year column (`HDR_PRI` headers, ties to R and E; `HDR_BAD` rejects "approved", "actual", "expected" headers on purpose),
reads leaf lines by `budget_rows` rules, and skips report sheets (`sheet_kind` 'report'). `review.assemble()` builds
rows per (fund, section) from plain data; `build_review_sheet()` writes `review.COLUMNS`; `webapp/adjust.py` reads the
`Review` sheet back by **position** (column 5 = Duyệt N converted) and the years from A1.

The scan store (`Savills-local\budget-agent\scan-2026-10-07\v2\scan_budgets_v2.py`, `build_final_v2.py`) already
classifies such columns (`classify()`: approved_prior / expected_year / expected_rest / actual), parses their periods,
ties them, flags unusable ones and picks a primary column per (file, fund, measure, period). Its results on the 87 store
files are the reference for this change.

## Goals / Non-Goals

**Goals:**
- Read the three columns from the same workbook and the same leaf rows as Duyệt N, so lines line up without code
  matching across files.
- Same recognition and flag rules as the scan store, so the Review and the store agree on which files have the columns.

**Non-Goals:**
- A separate N-1 file, any page control to pick columns, annualising the actual, using the columns in the generators.

## Decisions

1. **Port the scan's column rules into the product, not import the scan.** A new module `review_measures.py` holds
   `classify(header)`, the period parser and the flag/primary rules, copied from `scan_budgets_v2.py` /
   `build_final_v2.py` with their regexes, and unit-tested on the header texts the store found (top headers per
   measure). One deliberate difference: a year in the column's own header is read before the
   month-group label, because the label can pick up the sheet's Starting Month cell (the store read "Expected Report
   Year 2025" under a 01/2026 head cell as 01/2026). On the store's 1,402 headers `classify()` gives the same class.
   *Amended 2026-10-28 (user's choice "Kho + web", task 7):* the period rule is one function for both. `parse_period`
   takes the column's measure: an approved or expected column takes the year of its header even when the header also
   writes a month in another style ("From 01,2024 to 12.2024", which the range pattern misses); an actual column takes
   a bare month of its header ("01/2025 Actual") before the group label; two years in a header → the last one. The
   scan (`scan_budgets_v2.py`) now imports `review_measures.parse_period` from the source folder it already reads
   `budget_rows.py` from, so the two cannot drift; its build log records both files. *Alternative:* import from `Savills-local`. Rejected: the scan lives outside the repo and the server has no
   copy.

2. **Read on the fund sheet and its report sheet, keep the fund's leaf rows.** For each fund the reader already picks a
   sheet and its leaf rows. Measure columns on that sheet use the same rows directly. On a report sheet (2.1 / 2.2.1)
   the rows are matched by code within section (the report sheet repeats the code column); a code missing there is
   blank. Primary choice per measure: ties → longest period → report sheet → visible → more figures (the scan's order, plus
   the period length so that a cumulative actual is taken before a one-month "Actual 3" column; the scan keeps one
   primary per period instead).

3. **Year check against N from the file, not from the template.** N is `prior.budget_year` (already derived). All three
   columns must be of N-1 (decided 2026-10-26 after the store showed that the primary actual and expected columns of a
   year-N file are of N-1 in 60 of 71 and 44 of 83 cases: a budget of N is written during N-1): approved and expected by
   the year with most months, actual by the year its period ends. The 2026 file whose approved column reads 2026 is
   rejected with a note. N comes from the sheet's "Budget Year" or Starting / Ending Month cells (as the store reads it),
   else from the month columns: on a file where the year-column search takes the "Average Month … 12/2025" header as the
   only month (found 2026-10-26 on a 2026 store file), the month columns say 2025 while the head cells say 2026. The
   Review's year labels (A1 title, "Duyệt NS N", "Công cụ NS N+1") follow the same N so that the N and N-1 headers never
   carry the same year; no figure, tie or form cell changes. The month-column search itself is not changed here.

4. **`assemble()` gains optional per-line measures.** Prior lines carry `measures = {'n1': v, 'actual': v,
   'expected': v}` (missing key = no column). Rows gain `n1`, `actual`, `expected` (converted), their factors and the
   three % — Duyệt N / Duyệt N-1, Dự kiến N-1 / Duyệt N-1, Duyệt N / Dự kiến N-1 — (None when base 0/missing; actual
   never in a %). Ties for the three columns are appended with `info=True`;
   `run()` counts only non-info ties for the exit code. No-column files leave every existing figure untouched.

5. **Sheet layout: new block before Duyệt N, readers by header.** Columns: Mã, Hạng mục, Duyệt N-1, Thực tế
   N-1 (period, months), Dự kiến N-1, the three existing Duyệt N columns, Công cụ N+1, Chênh, %, three new %, Cách ra số, Ghi
   chú. `adjust.approved_by_key()` finds "Duyệt NS {N} (quy đổi)" on the header row; new `measures_by_key()` reads the
   three new columns by header. A1 title unchanged so `review_years()` keeps working.
   *Alternative:* append at the far right, no reader change. Rejected: the user's order is N-1 → N → N+1.

6. **VAT.** Each column takes the VAT basis of the sheet it is on (report sheets: the fund sheet's basis unless the
   scan-style evidence on that sheet says otherwise) and the per-line factor of `review.vat_factor()` on its own months
   (the actual's months; the months of N-1 for the other two).

7. **Run-chain and upload Reviews.** A Review of the tool's own deliverable (a new-year run) finds no such columns
   (the generator leaves them empty) and shows them blank; nothing special is needed.

8. **Lines grouped as on the form, with subtotals (added 2026-10-27, user's choices).** On the Review sheet each line
   sits in the groups of the 2027 template, nested to every level the form has (for example EM > EMH > EMH2;
   ER > ERF > ERF1 > ERF1.1). The groups come from the template itself: a group row is a code row whose annual cell is
   `SUBTOTAL(9, range)`, and a row's group is the smallest such range that holds it (so EM# sits in EM, not in EMO);
   sections R and E stay the existing section rows. `review_import.template_groups()` reads this once and
   `group_chain()` gives a line its groups; a line whose code is itself a group code (an older file's single RO2
   row) sits inside that group. Each group shown gets one summary row above its lines, as on the form, reading
   "Cộng <code>" with the form's group name: `=SUBTOTAL(9, …)` over the rows below it in every money column (nested
   summary rows are skipped by SUBTOTAL), the four % recomputed on those cells, and blank N-1 columns when the file
   has no such column. Excel outline levels follow the depth, summary row above (`summaryBelow = False`), so each group
   folds with +/-. Codes not on the 2027 form stay in their own block at the end of the section, under a summary row
   "Cộng ngoài form", never guessed into a group by prefix. Only groups with a shown line appear. The section totals
   ("Tổng R / E", "Thặng dư") stay static figures; ties, summaries, `review_summary.*` and the web are unchanged:
   the summary rows' column A never reads as a bare code, so the web's code reader skips them.
   *Alternatives:* only the smallest or only the top-level group; static figures; no outline. Rejected by the user.

## Risks / Trade-offs

- [Report-sheet columns are formulas; a file saved by a tool other than Excel has no cached values] → the column reads
  empty, flagged "chua_dien" like the scan, and stays blank. Upload of such files already goes through `recalc` only
  for run-chain Reviews; accepted.
- [Headers outside the scan's vocabulary] → the column is not found and stays blank; the import notes list the
  unrecognised measure-like headers so the rules can grow.
- [Two copies of the rules (scan and product) drift] → a test compares, on the store's top headers per measure, the
  product's `classify()` with the store's recorded `measure`; the store is rebuilt rarely.
- [Wider sheet] → seven more columns; widths and number formats as the existing ones, freeze panes after Hạng mục.

## Migration Plan

Budget-web release through [Hub] after the full test suite and verify.py PASS; rollback = previous release
(`setup-budget-web.ps1 -Rollback`). Runs made before the deploy keep their old Review sheet; the adjust page reads both
layouts.
