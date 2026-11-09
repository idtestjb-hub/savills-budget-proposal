## Why

A line the tool cannot price is left empty today, but its remark reads "Để ở mức 0: … Không tự đặt ra số liệu — đã
được rà soát và ghi nhận đầy đủ", nothing marks the line, and on a new-project run it has no row on the adjustment
table. A PM reads it as a cost of 0 VND rather than a figure they still have to supply (user, 2026-11-09: "xử lý các
hạng mục mà tool không xử lý được bằng cách để ô trống cho PM tự điền vào").

## What Changes

User's choices on 2026-11-09: scope A + B below (C stays at 0); the PM fills the figure on the adjustment table (web
and sheet `4. Điều chỉnh`); the line is shaded light yellow and its remark starts "PM điền".

- **Three kinds of zero line, named once.** Every place the generator leaves a line at 0 VND states which kind it is:
  - **A. No pricing method**: the 16 codes of the generator's no-method list that no other writer prices — RP3,
    EMB1, EMO6, ESC4, ESS10, ESS17, ESS18, ESS19, ESM6, ESM7, ESM9, ESM10, ESM12, ESM13, ESR, ERCS1 (the list's
    other entries are range codes, EMH3, or EMO2, which is C);
  - **B. A method exists but this project's input is missing**: EMH1 with no Savills fee terms, ESI1 with no insured
    asset value, EMH3 on an existing project with no duty roster and no approved prior figure, and a real-budget
    range code (EMB4, ESC1, ESC2, ESC5, ESS7, ESS12, ESS23) when fewer than 10 real budgets carry it, the values file
    is missing, or the project has no fee-bearing NFA;
  - **C. Genuinely 0 for this project**: no pool, no tower, in-house pool staff, a lump staff budget, no night-shift
    position, EMO2 in year 1, a 0 % contingency rate, a value the PM entered as 0.
- **A and B lines are left for the PM.** The unit price and the twelve month cells on `2. Budget-Management Fund`
  stay blank (no 0 typed in), those cells are shaded light yellow, and the remark reads "PM điền: <why the tool could
  not price it>". `2.2 Common area Fund` carries the same remark lead on its share of the line. Totals read the blank
  cells as 0 until the PM fills them, so `1. Summary` still ties to the detail sheets and no Excel error appears.
- **Every A and B line has a row on the adjustment table, on every run.** Today only a Review run adds rows for codes
  the tool left at 0, and only when the approved budget priced them. After this change, a new-project run and a Review
  run both add a row for every A and B line, marked "PM điền", with the "Nhập số" type ready; the web table shows these
  rows by default (never hidden behind "Mã công cụ ra 0") and counts how many are still empty.
- **C lines are unchanged**: 0 VND with "Để ở mức 0: <reason>".
- **The internal analysis lists the lines waiting for the PM** (code, item, kind, reason).
- **Verification** checks, on every sample run, that each A and B line is blank, shaded, carries the "PM điền" remark
  and has an adjustment row, and that no C line was turned into a PM line.

## Capabilities

### New Capabilities
- `pm-filled-lines`: which lines the tool leaves for the PM, how such a line looks on the deliverable, and how
  verification confirms it.

### Modified Capabilities
- `guideline-required-line-items`: a Required code with no basis to price is left for the PM instead of stated as 0;
  the common-area remark follows the same lead.
- `budget-adjustment-sheet`: rows for the lines left to the PM on every run, not only for approved codes on a Review.
- `budget-web-adjust-table`: the "PM điền" mark, shown by default, and the count of lines still empty.

## Impact

- Changed: `generate_project_budget.py` (the zero-reason writer gains the kind; the no-method loop, EMH1, ESI1, EMH3
  and the real-budget range writer pass it; the blank-and-shade step), `real_budget_ranges.py` (which reasons are B),
  `fill_common_area_fund_sheet` remark lead, `review.py` / `budget_adjustment.py` (rows for PM lines on every run),
  `webapp/adjust.py` and `webapp/static/index.html` (mark, default view, count), the internal analysis writer,
  `verification/checks.py` + `verify.py`, docs/32, webapp README.
- Figures: none. Every A and B line is 0 VND today and reads 0 until the PM types a figure; baselines that record a
  typed 0 in these cells will be re-recorded as blank. Measured before/after on the samples and on one Review run is
  a task, and the PM signs it off before archive.
- Remark text on the client deliverable changes for the A and B lines ("Để ở mức 0" → "PM điền").
- Needs a budget-web deploy by [Hub] and a site package rebuild at the same commit; not part of this change.
