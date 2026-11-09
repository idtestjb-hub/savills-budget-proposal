## Context

The generator leaves a line at 0 VND in four places, all through `_write_zero_reason` (remark "Để ở mức 0: …"): the
no-method loop (`_FLAGGED_NO_METHOD`), the real-budget range writer (`_write_real_budget_range_lines`, reasons from
`real_budget_ranges.py`), the single-code writers (EMH1 `savills_fee.ZERO_REASON_VI`, ESI1, ESI2, EMH3 new and
existing, contingency) and EMO2 inside the no-method list. In the deliverable the no-method rows already have empty
F and H–S (measured 2026-11-09 on the ZZ Sample Residence verify output: RP3, EMO6, ESC4, ESS17, ESM6 rows hold only
the template formulas and the remark). Sheet `4. Điều chỉnh` gets rows for zero-tool codes only on a Review run and
only for codes with an approved figure (`review.add_zero_rows`, `zero_tool_rows`). Excel G on a fund row is
`=IF($C="Schedule",SUM(H:S),F*E)`, so F must stay numeric or empty: a linked F that returns "" gives #VALUE!.

User decisions 2026-11-09: scope A + B, C stays 0; the PM fills on the adjustment table (web + sheet 4); light yellow
shading and a "PM điền" remark.

## Goals / Non-Goals

**Goals:** one place decides the kind of each zero; A/B lines read as "to fill", not as 0; the PM can fill every
A/B line from the adjust table on any run; no figure moves until the PM types one.

**Non-Goals:** pricing any new code; changing which codes are A/B beyond the list in the spec; changing the Review
comparison, abnormal flags or top-10 (they still compare the tool's 0 with the approved figure); a 2028 form.

## Decisions

**D1. The kind travels with the reason.** `_write_zero_reason(ws, row, code, reason, kind)` with kind `'pm'` or
`'zero'` (no default, so every caller decides). `'pm'` writes "PM điền: <reason>" and records the line in a run-level
`_PM_LINES` {code: (fund row, kind letter A/B, reason)}; `'zero'` keeps "Để ở mức 0: <reason>" and `_ZERO_REASONS`.
The common-area writer (`fill_common_area_fund_sheet`) reads both maps and picks the lead. Alternative considered: a
separate `_write_pm_line` function — rejected, the callers would duplicate the remark/common-area bookkeeping.

**D2. Range reasons carry their kind.** `real_budget_ranges` results gain `pm_fill: bool`: True for no values file,
no fee-bearing NFA, fewer than 10 budgets; False for no pool, no tower, in-house pool staff, lump staff. The reason
strings lose the "Để 0: " prefix inside the writer, as today.

**D3. Blank cells that stay numeric.** On a PM line the generator writes nothing into F and H–S (it already writes
nothing on A lines; B writers that type 0 stop doing so). Sheet-4 linking (D4) then puts formulas in F and H–S that
return 0 while the PM's cell is empty; those cells get the number format `#,##0;-#,##0;;@` (zero shows nothing, the
same format `_normalise_all_remark_columns` already uses) and the fill `budget_adjustment.FILL_INPUT` (FFF2CC, the
sheet-4 input yellow). G then evaluates to 0 and shows the template's "-", `1. Summary` and contingency see 0, and no
cell shows an error. Alternative: formulas returning "" — rejected, G = F*E gives #VALUE!.

**D4. PM rows on sheet 4 on every run.** `review.add_zero_rows` is generalised (moved to `budget_adjustment` as
`add_lumped_rows(deliverable, rows, mark)`) and called (a) by the generation step of every run for the `_PM_LINES`
codes, with mark "PM điền", detail unit price empty, type "Nhập số"; (b) by Review for the remaining approved
zero-tool codes, skipping codes already added in (a) so a code gets one row. The total row stores the mark and the
reason in a hidden helper column so the web can read them back from the saved workbook.

**D5. Web.** `webapp/adjust.py` reads the mark/reason; `index.html` shows a "PM điền" badge, the reason as tooltip,
"Thành tiền gốc" empty, never hides these codes behind "Mã công cụ ra 0", adds the toolbar count "N dòng chờ PM điền"
and a filter. On save of a PM line with a figure, the fund remark is rewritten to "Số do PM nhập: <figure> VND/năm.
Công cụ không tính được: <reason>"; cleared again, it returns to "PM điền: <reason>".

**D6. Analysis.** A new block "Dòng chờ PM điền" on the analysis's existing Review/notes sheet (exact sheet chosen at
apply, following docs/32), listing code, item (VI), kind, reason, and the count.

**D7. Verification.** `checks.check_pm_lines(paths)`: for each `_PM_LINES` code recorded in the run log, F/H–S hold
no typed number (empty or a sheet-4 link), are filled FFF2CC, T starts "PM điền:", sheet 4 has its row; no kind-C
reason line starts "PM điền"; no A/B code's T starts "Để ở mức 0". Wired into verify.py for the standard, existing
and operating samples. The run log records the PM lines (code, kind) so the check does not re-derive them.

## Risks / Trade-offs

- [A remark rule in docs/11–13 or a verify check expects "Để ở mức 0" on these codes] → update those checks in the
  same change; the client-facing wording scan must accept "PM điền".
- [Baselines record a typed 0 or the old remark] → figures do not move; re-record only the cells that change, with the
  before/after list in the measurement summary.
- [ESR is a section rollup row, not a leaf] → checked at apply: on the current form ESR has the leaf =SUM annual, so it
  gets its sheet-4 row like the others. A line that is not a plain leaf would keep its shading and remark only, and
  the generator prints it.
- [Older deliverables] → `upgrade()` does not add the AY/AZ columns (that would change the header row of every older
  sheet on each web save); the web reads a missing mark as "not a PM line", which is what an older run is.
- Implementation notes: the shared builder is `budget_adjustment.lumped_item` + `add_pm_rows` (the design's
  `add_lumped_rows`); the kind is passed as 'A'/'B'/'C' rather than 'pm'/'zero' so the analysis can show it.
- [Site packages hide the internal analysis] → the new block is in the analysis only; the web count serves the site.

## Migration Plan

No data migration. Older deliverables keep their "Để ở mức 0" remarks; the web upgrade path (`upgrade()`) adds the
mark column when it saves into an older sheet 4 but does not invent PM rows. Rollback = revert the commit.
