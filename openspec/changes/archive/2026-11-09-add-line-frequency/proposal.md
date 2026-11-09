## Why

Many budget lines are not spent evenly every month: a wastewater cross-check each quarter, a bank interest payment
twice a year, an environmental response plan once a year, events in the months they happen. The 2027 form already
handles this. Column C (Frequency) of both fund sheets takes Monthly, Quarterly, Half a Year, Yearly, Optional or
Schedule, and the form spreads the money over the months by itself. The tool, however, writes only Monthly or
Schedule. The PM cannot set a line's frequency on the adjustment table (web or sheet `4. Điều chỉnh`). Lines whose
template frequency is anything else (for example RO2a Half a Year, ESC12 Yearly, ESM25 Quarterly) are left off that
table, and a Review line added for a code the tool priced at 0 is forced to Monthly. The user asked for the frequency
to be entered on the form on 2026-11-06 and chose the rules the same day (see below).

## What Changes

- **Six frequencies, the form's own.** Monthly, Quarterly, Half a Year, Yearly, Optional (a number of times in the
  year, the same amount each time, in the months picked) and Schedule (an amount typed for each month). Each code has
  one frequency, set on its total row.
- **Changing the frequency keeps the price per time.** The annual amount follows the number of times, as the form's
  own formula does (Total = unit price per time × number of times). For example, 3,500,000 VND a month (42,000,000
  VND/year) changed to Quarterly gives 4 × 3,500,000 = 14,000,000 VND/year. The change shows in the Chênh lệch
  column like any other adjustment.
- **The months are picked from a first month.** Quarterly, Half a Year and Yearly take one "Tháng đầu" (default: the
  first month of the budget period) and repeat every 3, 6 or 12 months inside the period. Optional takes the months
  ticked, and their count is the number of times. Schedule opens 12 amount cells.
- **The fund sheet is written the form's way.** C (Frequency), D (number of times for Optional), F (unit price per
  time) and the month cells H:S hold what a PM would type by hand, so the form's own month spread and its two checks
  (U: number of times, V: total) work and the client reads "Quarterly, 4 lần × 3,5 triệu".
- **Entered on the web and on sheet 4.** The web adjust table gets Tần suất, Tháng đầu and the month picker on each
  code row. Sheet `4. Điều chỉnh` gets the same input cells, so a PM working offline in Excel can set them too. An
  older sheet 4 is upgraded when the web saves into it.
- **Every written line is adjustable, whatever its frequency.** Lines with a template frequency other than Monthly or
  Schedule join the adjustment table. A Review line added for a zero-tool code takes its default frequency instead of
  being forced to Monthly.
- **A default frequency when a new budget is generated.** A new reference file, `Ref_LineFrequency.csv`, lists the
  default frequency, number of times and first month per code. It is built from the template's own column C and from
  the counts the tool already prices with (ESM25 4 times a year, ESC12 once a year, ...). Reading column C of the 55
  real budgets is out of scope (a later change). A defaulted line keeps its annual amount: only the per-time price and
  the month spread change.
- **Remarks.** A line that is not Monthly states its frequency in Vietnamese on the deliverable, for example "Hàng
  quý, 4 lần/năm × 3,500,000 VND/lần, chi vào T3, T6, T9, T12".
- **Figures.** Annual figures do not move unless the PM changes a frequency. Per-time prices (column F) and the month
  spread do move on the defaulted lines. The before/after is measured on the standard sample and the City Garden
  Review and signed off by the user before the baselines are re-recorded once.

## Capabilities

### New Capabilities
- `line-frequency`: the six frequencies and what each writes on the fund sheet; the first-month rule inside the
  budget period; the default frequency per code for a new budget and its source file; the Vietnamese frequency
  sentence on the remark.

### Modified Capabilities
- `budget-adjustment-sheet`: sheet 4 gets the frequency input cells on each total row; the new amount follows the
  number of times; Schedule replaces the adjustment type; every written line is listed whatever its frequency; the
  upgrade of an older sheet adds the new cells.
- `budget-web-adjust-table`: the web adjust table shows and edits Tần suất, Tháng đầu, the Optional months and the
  Schedule amounts, with the same preview and validation as the Excel formulas.
- `budget-review-workflow`: a line added for a zero-tool code takes the code's default frequency.
- `budget-workflow-verification`: verification confirms the form's two frequency checks (U and V) on every written
  line and exercises each frequency through sheet 4.

## Impact

- Code: `generate_project_budget.py` (writing C/D/F/H:S per frequency), `adjustment_detail.py` (collects every
  frequency), `budget_adjustment.py` (new sheet-4 columns, formulas, fund-row links, upgrade), `review.py` (zero-row
  default), `webapp/adjust.py` and `webapp/static/index.html` (table columns, picker, preview, save), remarks,
  `verification/verify.py` and tests.
- Data: new `Budget_Agent/data/generation_B_verified/Ref_LineFrequency.csv` (read by generation and Review); it joins
  the site package's KEEP list in `site_data.py`. The template is read, not changed.
- Baselines: annual figures unchanged by default; per-time prices and month figures of the defaulted lines move;
  re-recorded once after sign-off.
- Depends on: change `adjust-rows-for-zero-tool-codes` (the "Nhập số" type) being archived first, since both change
  sheet 4 and the web adjust table.
- Server: the budget web needs a deploy by [Hub] after this change, like any web change.
