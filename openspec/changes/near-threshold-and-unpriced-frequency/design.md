## Context

- `build_line_frequency.py` lists a code when it passes the vote rule, or when it is in `COSTING_KEEPS` (four codes
  that keep their costing frequency, each with a note). There is no list for frequencies the user sets.
- `_apply_line_frequencies` (`generate_project_budget.py`) runs on `2. Budget-Management Fund` before sheet 4 collects
  the lines. It changes only two row shapes:
  - a Monthly row with a plain-number F;
  - a row already at the table's frequency with no price (RO2a).
- The lines left for the PM are recorded in `_PM_LINES` before this step. Their fund rows are Monthly with an empty F,
  so neither shape matches them. Sheet 4 then gives them the table's frequency (`lumped_item`, design D3 of
  `default-frequency-from-real-budgets`).
- A row that is neither priced nor a PM line (ESA16 in City Garden: F blank, the template's guidance remark, 0 VND)
  also matches neither shape, so it stays Monthly while the table says Yearly.
- The near-threshold vote counts come from the office raw read of 2026-11-09 (`vote.py`, MF files):
  - ESC2: Yearly 16, Monthly 14, Quarterly 1, tie 3 (34 files);
  - ESC3: Yearly 14, Monthly 15, Half a Year 1, Quarterly 1, Optional 1, tie 2 (34);
  - ESS7: Yearly 11, Monthly 11, tie 1 (23);
  - EMA18: Yearly 9, Monthly 10 (19).

## Goals / Non-Goals

**Goals:**
- The four codes come out Yearly, with the same annual amount.
- Every Monthly row of a listed code that has no price shows the table's frequency and months, with U = 0.

**Non-Goals:**
- Changing the vote rule or the threshold.
- The other near-threshold rows the vote print shows (ERCS4 Half a Year 4/10, EED.# 2/5, ESA3/ESA4 off the form).
- A first month other than T1.
- The Common Area Fund.
- Review runs' reading of an approved budget's own frequency.

## Decisions

**D1. A second exception list, `USER_FREQUENCIES`, beside `COSTING_KEEPS`.** It holds (code, frequency, note) for
ESC2, ESC3, ESS7 and EMA18, all Yearly. The note reads: "Gần ngưỡng: người dùng chốt Hàng năm 09/11/2026, không theo
quy tắc trên một nửa."
- The source gives the counts, as for every row.
- The template-difference note is kept.
- A code in both lists is refused with an error, so one rule decides each code.
- *Alternative:* lower the threshold to 40 %. Rejected for two reasons. It would also pick up ERCS4 (Half a Year 4/10)
  and EED.# (2/5). And it changes the approved rule rather than recording a decision about four named codes.

**D2. Third shape in `_apply_line_frequencies`: an unpriced Monthly row outside `_PM_LINES`.** The shape matches when
all of these hold:
- the row's C normalises to Monthly;
- F is `None` or 0, and not a formula;
- the code is listed with a non-Monthly frequency;
- the code is not in `_PM_LINES`.

The row then gets:
- C = the table's frequency;
- H:S = references to the row-8 month headers of the months of payment, the other months cleared;
- F = 0, a blank F included (user, 2026-11-10: verify.py requires a number in F on every cyclic row, as the
  template's RO2a at 0 has); the remark left as it is (`per_time` 0, so no sentence).

This is the same write as the existing "no price" shape. The condition is widened rather than a new write path
added. The template's E formula then gives the times, and U = E − count of marked months = 0.

Two alternatives were rejected:
- Leave these rows Monthly. That is the gap found.
- Set the frequency also on PM lines here. Sheet 4 already does that, and `_link_fund_row` replaces C and H:S with
  formulas anyway. Keeping PM lines out avoids two writers for one row.

**D3. "Not Use" rows are included.** B is a formula over AC/AM/AO and does not read C or H:S. An unused row that shows
Yearly with its month marked is consistent with the form's own cyclic rows (RO2a at 0 VND does the same today).

## Risks / Trade-offs

- **[Risk] A month header in H:S of a 0-VND row reads as money to a careless eye.** → It is the form's own convention
  for cyclic rows; F and G stay blank or 0.
- **[Risk] A month-varying line whose F is 0 in month 1 is caught by D2.** → Schedule rows are not Monthly, so they
  are not matched. Ramped lines are written as Schedule, and a test covers it.
- **[Risk] Baselines move on many 0-VND rows.** → The measurement lists every row that moves. Annual totals must not
  move beyond per-time rounding. Re-record once after sign-off.
- **[Trade-off] The four codes follow the user's choice, not the data majority (40–50 %).** → The note on each row
  says so, and a later rebuild keeps them through `USER_FREQUENCIES`.

## Migration Plan

1. Rebuild the table from the saved raw read (`--from-votes`, the office machine), keeping the old file as
   `.backup-<date>`.
2. Measure before/after (5 fixtures + M3 runs, `M3_DATA_OVERLAY` for the data-only A/B).
3. User sign-off, then re-record the baselines.
4. Commit: the submodule first, then the outer repo.
5. Rebuild the City Garden package at the new commit.
6. Write a release note stacked on the pending ones.

Rollback = restore the backed-up CSV and revert the commit.
