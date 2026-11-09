## Context

See proposal.md, "Why". What the code does today (read 2026-11-06):

- The 2027 form, on both fund sheets: C = Frequency (list "Monthly, Quarterly, Half a Year, Yearly, Optional,
  Schedule"), D = number of times for Optional (list 1..11), E = times a year (formula on C and D), F = unit price per
  time, G = `IF(C="Schedule", SUM(H:S), F*E)`, H:S = "Lần 1..12" (a month of payment, picked from the period's month
  headers H8:S8, or the amount of each month under Schedule), the month spread = AQ:BB on `2. Budget-Management Fund`
  (H8:S8 = AQ10:BB10) and AL:AW on `2.2 Common area Fund` (H8:S8 = AL10:AW10; read 2026-11-07), U = times check
  `E - IF(C<>"Monthly", COUNTA(H:S), 12)`, V = total check `SUM(AQ:BB)=G`.
- `generate_project_budget.py` writes C = Monthly with F, or C = Schedule with 12 amounts. It sets C to Monthly only
  where the template left it blank (`_activate_common_area_passthrough_rows`, around line 4033) and leaves a template value alone.
- `adjustment_detail._row_figures` keeps only Monthly and Schedule rows, so a template Quarterly / Half a Year / Yearly
  line never reaches sheet 4. `review.add_zero_rows` forces any other value to Monthly.
- `budget_adjustment` keeps the original frequency in hidden column R and the 12 original month figures in S:AD of
  each total row. It links the fund row's H:S (and F for Monthly) as "original month × new / original ratio". That is
  only right while H:S hold amounts. Under a cyclic frequency H:S hold month headers, so they cannot be scaled.
- The web (`webapp/adjust.py`) reads sheet 4 and writes back only D, L, J, K and the Remark (column T of the fund
  sheet). Its preview in `index.html` repeats the column M formula.

## Goals / Non-Goals

**Goals:**
- One frequency per code, entered on the web or on sheet 4, that drives the fund row exactly as a hand-filled form
  would, offline in Excel as well as on the web.
- No figure moves when nothing is set. Only F and the month spread move on the lines the default table changes.

**Non-Goals:**
- A frequency per detail row (posts, devices): the form has one frequency per code row.
- Reading column C of the 55 real budgets for defaults (later change, see Open Questions).
- Changing the form's AQ:BB spread formulas or its lists.

## Decisions

**D1. Write the form's own cells, not a converted Schedule.** A cyclic line is written as C = Quarterly, F = per-time
price and H:S = month headers. The alternative was to always write Schedule with 12 amounts, which is simpler: the
current ratio link would work unchanged. It was rejected because the client would read "Schedule" instead of
"Quarterly, 4 lần × 3,5 triệu", and the form's E column would be wrong. That defeats the purpose.

**D2. New sheet-4 cells are appended after AD.** The new columns are AE = Tần suất mới, AF = Tháng đầu, AG = Số lần mới
(computed; for Optional the count of ticks), AH:AS = 12 month inputs (a tick "x" for Optional, VND for Schedule),
and hidden helpers AT = Số lần gốc, AU = Tháng đầu gốc, AV = frequency in use (AE, else the original), AW = first
month in use (AF, else the original while the frequency allows it, else T1), AX = month step. (Applied 2026-11-07:
the running-count helpers first planned here were not needed, see D4.) They sit to the right of the hidden block, so no existing column, key or
formula moves. The web's `COL` map grows, and the upgrade of an older sheet only adds cells. Inserting them next to D
would read better in Excel, but it would shift every column the web, the tests and older files rely on. The
visible-in-Excel order is handled by freezing panes and a short guide line; the web shows them where the spec says.

**D3. The new amount uses a times ratio.** Total row M = (the current M formula) × AG / AT, or SUM(AH:AS) under
Schedule. Detail rows keep their meaning: SL × đơn giá is still the annual amount at the original frequency. The
alternative was to re-define detail unit prices as per-time prices. That would change every existing detail row and
the "Số lượng / Đơn giá" behaviour PMs already use.

**D4. Fund-row cells are formulas into sheet 4, so offline Excel edits flow.** On a linked row:
- C = `IF(AE="", original, AE)` (the original is the value in column R);
- D = the Optional count;
- F = M ÷ times (blank under Schedule);
- each H:S cell of month m (its own column) = under Schedule, month input m (or the earlier link while AE is
  blank); under Monthly, the earlier link while AE is blank, else ""; under Optional, the row-8 header of its own
  column when month input m is ticked; under a cyclic frequency, that header when m ≥ first month and (m − first)
  is a multiple of the step, else "".

(Applied 2026-11-07.) Testing each month cell by its own position needs no running count and no MATCH: the form's
spread (AQ:BB / AL:AW) matches a header wherever it sits in H:S, so the payment months are written in the columns
of the months, as the template's own rows do. A blank AE reproduces the earlier link (D2 of `budget_adjustment`), so
an untouched row is identical to before.

The trap: COUNTA counts a formula that returns "" as filled, so the form's own U check would always see 12. On a
linked row U is rewritten to `E - IF(C<>"Monthly", SUMPRODUCT(--(H:S<>"")), 12)`, which counts the same cells a hand
filler would. V is unchanged. verify.py checks U and V on every written line (spec budget-workflow-verification).
Alternative considered: write static values on web save only. It is simpler, but the user chose sheet 4 as an input
too, and a static fund row would ignore an offline edit.

**D5. Generation writes static values.** At generation the frequency is known, so C, D, F and H:S are written as plain
values (H:S as references to the row-8 month headers, the way the template's own rows do, `=K8`). Sheet 4 then links
them as in D4. This keeps the deliverable readable when sheet 4 is not used. (Applied 2026-11-07: the pass runs right
before `adjustment_detail.collect`, so sheet 4 records the cyclic frequency, months and price per time as the
original; the first run had it after the narratives, and sheet 4's link then turned the lines back to Monthly in
Excel. The price per time is rounded from the line's exact annual amount, user's choice: 15,400,000 a year gives
3,850,000 × 4, and G moves only by the old monthly rounding, a few VND. Common-area shares are left Monthly: their F
reads the fund line's monthly average, column AL.)

**D6. The default table is small, hand-reviewed and in data/.** `Ref_LineFrequency.csv` (code, frequency, times,
first_month, source, note) is built by an office script `build_line_frequency.py` from two sources:
- the template's column C values other than Monthly, with the template's month cells read back to a first month;
- the per-year counts the tool already prices with (ESM25 = 4, ESM3 and ESM5 tests a year, ESC12 = 1, ESM8 yearly
  fee, ...), found by reading the costing code and the method catalogue.

The user reviews the table before it is used, like the utility usage table. Generation and Review read it through one
small module, `line_frequency.py`, which also holds the month rule and the Vietnamese sentence. The file joins `KEEP`
in `site_data.py` (it holds no project name, so no mask is needed). A dict in code was considered instead, but a CSV
lets the user and PMs review and edit it without a release.

**D7. The web mirrors the Excel rule in one place.** `webapp/adjust.py` gains the five new inputs in `read_items`,
`_validate` and `apply_edits`. `index.html` gains the Tần suất cell, the Tháng đầu list labelled from the period
months, 12 tick boxes and 12 amount cells. The preview function `new_amount` takes the times ratio. A shared test
recalculates a saved file in Excel and compares it with the preview, the pattern the adjust tests already use.

**D8. The remark sentence is replaced, not appended twice.** The frequency sentence starts with a fixed lead ("Hàng
quý,", "6 tháng/lần,", "Hàng năm,", "<n> lần/năm,", "Chi theo lịch từng tháng") and is written as the last sentence of
the remark. When the PM changes the frequency on the web, that last sentence is replaced (or removed for Monthly) and
the PM's own remark text is kept. An offline Excel edit does not rewrite the remark. The web reports it the next time
the run is opened ("Remark chưa theo tần suất mới").

## Risks / Trade-offs

- [Template row RO2a is Half a Year with one month cell filled (generate_project_budget.py ~3316)] → the table gives
  RO2a two months explicitly. verify's U check catches any other template row in the same state.
- [Formulas in C and D bypass the form's dropdown lists] → the web and sheet 4 validate the input. Typing over C by
  hand on the fund sheet breaks the link, the same as typing over a linked month cell does today. The guide line says
  so.
- [Excel recalculation order: C is now a formula feeding E, F and G] → there is no circular reference (sheet 4 reads
  the original values from its own hidden columns, never from the fund row). A test opens the file in Excel through
  COM and checks there are no #VALUE!, #REF! or #DIV/0! errors.
- [The times ratio when the original is Schedule with zeros in some months] → the original counts as 12, so a Schedule
  original changed to Quarterly takes 4 ÷ 12 of the annual amount. A scenario test pins it, and the PM sees the
  difference on the row.
- [An older run opened offline before any web save has no frequency cells] → there is nothing to edit until the web
  upgrades it. Same behaviour as the earlier sheet-4 upgrades.
- [Generators share one temp file] → no parallel runs during the measurement (known trap).

## Migration Plan

1. Archive `adjust-rows-for-zero-tool-codes` first (same sheet and table).
2. Apply. Measure before/after on the standard sample and the City Garden Review (annual figures equal, F and months
   listed per defaulted code). The user signs off. Re-record the baselines once.
3. Rebuild the site package at the commit. Write a release note for [Hub] to deploy budget-web.

Rollback: redeploy the previous release. Files saved with the new cells stay readable by the old web, which ignores
columns after AD; their fund rows keep working formulas.

## Measured

**Default table, 2026-11-07 (tasks 1.1-1.2).** The template's fund sheets carry four non-Monthly lines: RO2a Half a
Year (one month cell, T4), ESC1 Schedule, ESC12 Yearly (T1), ESM25 Quarterly (T1, T4, T7, T10); `2.2 Common area Fund`
has none. User's choices: every cyclic line starts in T1, as the template's rows do; the table also takes ESM2 (Half a
Year, remark "6 tháng/lần"), ESM3 (Half a Year, 2 đợt/năm), ESM5 (Quarterly, 4 đợt/năm) and RO2a (Half a Year, both
months T1 and T7 so the form's U check is 0; amount stays 0). ESC1 stays Schedule (not listed). Table: 6 rows (ESC12,
ESM2, ESM25, ESM3, ESM5, RO2a), each with its source. Accepted by the user as listed.

**Before / after, 2026-11-07 (tasks 0.2, 5.2); user signed off 2026-11-09 (task 5.3).** Before = commit a9506ac, after =
the working tree, on the five fixtures and the City Garden Review (ZWork chains, kept in
`Savills-localackupsudget-agent6-11-07-line-frequency-measure`). Every fixture: sheet 4 lists the same number
of lines; 5 lines defaulted (ESC12 Yearly 15,400,000 x 1; ESM2 Half a Year 12,500,000 x 2; ESM3 Half a Year 4,056,000
x 2; ESM5 Quarterly 2,732,000 x 4; ESM25 Quarterly 3,850,000 x 4, all from T1); 4 annual figures moved by the old
monthly rounding (ESC12 +4, ESM2 +4, ESM25 +4, ESM5 -4 VND), no other figure moved. City Garden Review: same 196 lines,
same counts, same top 10 and 82 abnormal codes; tool totals move by about 0.01 VND, one abnormal diff by 8 VND. Excel
check `check_line_frequency` on the after standard sample: 0 differences (3 Half a Year, 2 Quarterly, 1 Yearly lines;
five sheet-4 edits tie). Web, local run on the after Review: EMA7 Monthly -> Quarterly T3 previews 4/12 (21,515,788),
saves in 26 s with 0 error cells, reopens as Quarterly / T3 with the remark sentence; Excel reads C Quarterly, E 4,
F 5,378,947, G = AK = 21,515,788, U 0, V TRUE. Baselines re-recorded once after the sign-off.

## Open Questions

- Whether to read column C of the 55 real budgets to refine the defaults (counts per code). This is deferred to a
  later change. It changes only the table's content, not this design.
