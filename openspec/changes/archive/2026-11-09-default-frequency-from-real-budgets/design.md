## Context

- `Ref_LineFrequency.csv` is built by `build_line_frequency.py` from the template's column C and a hard-coded
  `COSTING` list (ESM2, ESM3, ESM5, ESC12, ESM25), and read by `line_frequency.load_table()`.
- The generator applies it in `_apply_line_frequencies` (`generate_project_budget.py`) to two shapes only: a Monthly
  line with a plain-number F, and a line already at the table's frequency with no price. A line left for the PM has
  an empty F on a Monthly template row, so it matches neither and stays Monthly.
- Lines left for the PM get a row on sheet 4 through `budget_adjustment.add_pm_rows` → `lumped_item`, which reads the
  fund row's C and uses the table only when C is blank or Optional; `_link_fund_row` then makes C, F, H:S of the fund
  row formulas into sheet 4 (`fund_price_formula`, `fund_month_formula`). Under a cyclic frequency, H:S of the paid
  months show the row-8 month header (as the form's own cyclic rows do) and G = F × times.
- `shade_pm_fund_row` sets fill and the number format `#,##0;-#,##0;;@` on F and H:S; `check_pm_lines` asserts the 12
  months sum to 0 before typing and to 24,000,000 VND after typing on sheet 4.
- The raw read of 2026-11-09 (`read_freq.py`, `vote.py`) lives outside the repository on the office machine.

## Goals / Non-Goals

**Goals:** the table follows the approved rules and is rebuildable from the repository on the office machine; the
lines left for the PM get the same default as priced lines; no annual figure moves beyond per-time rounding.

**Non-Goals:** choosing a first month other than T1 from the data; defaults for the Common Area Fund (none passes the
threshold; its shares stay Monthly); changing the near-threshold codes (ESC2, ESC3, ESS7, EMA18); Review runs'
handling of an approved budget's own frequency.

## Decisions

**D1. One builder, three sources in order.** `build_line_frequency.py --store <scan store> --root <budget root>`:
1. read the frequency column of every MF and CA budget sheet of the files mapped in `real_budget_ranges_map.csv`
   (logic of `read_freq.py`: header "Frequency"/"Tần suất" in C, D or E; files opened through
   `review_import.open_workbook` for the defined-name repair), writing the raw read only to `--workdir` (ZWork);
2. vote per the rules (MF decides; CA counted and printed for reference);
3. apply the exceptions list `COSTING_KEEPS` (ESC12, ESM2, ESM5, ESM25 with the costing source and the user's
   decision date) and drop codes not in `review_import.template_codes()['MF']`.
The template's column C is no longer a source of a default (rule 4); it is still read to note where the table
differs from the template. `--from-votes <csv>` rebuilds from a saved raw read without the store, for tests.

**D2. Source text without names.** `source` = "real budgets: Yearly 22 of 39 MF files (16 Monthly, 2 tie)"; for an
exception, "costing: <constant or remark> (exception to the real-budget rule, user 2026-11-09); real budgets: …".
No file id, project name or path. The builder checks the written CSV against the store's project names and fails on
a match (the leak scan of `site_data.py`).

**D3. Lines left for the PM take the table's frequency on sheet 4.** In `lumped_item`, a PM line (called from
`add_pm_rows`) uses the table's default when the fund row's C is Monthly or blank and the table lists a non-Monthly
frequency. `_link_fund_row` is unchanged: the fund row reads frequency, price and months from sheet 4. Alternative
considered: set C and H:S in `_apply_line_frequencies` — rejected, `_link_fund_row` overwrites them right after.

**D4. Shading of a cyclic PM row.** F stays shaded with the blank-zero format. H:S of a cyclic PM row keep the row-8
month format (they show the month of payment, as on any cyclic row) and are not shaded; only Monthly and Schedule PM
rows keep shaded H:S. This avoids a date shown as a number in a yellow cell.

**D5. Verification of a cyclic PM row.** Before typing: G = 0 and no error; H:S may hold month headers. After typing
24,000,000 VND on sheet 4: G = 24,000,000 VND and F = 24,000,000 ÷ times; for Monthly/Schedule rows the existing
month-sum check stays. `pm_line_problems` accepts header references in H:S of a cyclic PM row (not "ô có số").

**D6. The PM's figure saved on the web writes the sentence.** `_pm_remark` (runs after a save of a PM line) ends the
remark with `lf.with_sentence(remark, freq_sentence(item, amount))` when the line's frequency is not Monthly, so a
filled Yearly line reads "… Hàng năm, 1 lần/năm × <số> VND/lần, chi vào T1". A figure typed in Excel only is caught
by the stale-remark flag (and the fix button of change `fix-stale-frequency-remarks`).

**D7. A template row whose code leaves the table goes to Monthly.** Found while measuring (2026-11-09): with RO2a
out of the table, `_apply_line_frequencies` skipped it and the deliverable kept the template's own row (Half a Year
with only T4 marked, the form's times check off by one). `_template_cycle_to_monthly` now writes such a row Monthly:
C = Monthly, the month references in H:S cleared, a plain-number F turned into the monthly figure of the same year
(F × times ÷ 12); a formula C or F is left alone. RO2a is the only such row on the 2027 form.

## Risks / Trade-offs

- [Real budgets vote Yearly for a line the tool prices as a monthly service] → only EMB4 and ESC5 are priced lines
  that move; the measured before/after shows their month spread for sign-off.
- [The store read takes minutes and needs the office machine] → the table is committed; rebuilding is only needed
  when the store changes; `--from-votes` covers tests.
- [Older deliverables built before this change] → unchanged; the table only acts when a budget is generated.
