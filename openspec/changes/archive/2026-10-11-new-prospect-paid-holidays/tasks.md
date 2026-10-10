## 1. Calendar

- [x] 1.1 `vn_holidays.holidays_in_month` returns the days paid under the law in force on each day (24 November from 2026); the module states both legal texts. Verify: unit tests for November 2025, 2026 and 2027, and that `paid_holidays` (Existing-project mode) is unchanged.

## 2. Naming the law

- [x] 2.1 The roster's `Setup` sheet carries a note naming Labour Code 2019 Article 112 clause 1 and Nghị quyết 28/2026/QH16 Article 2. Verify: the generated roster shows the note.
- [x] 2.2 The input form's reference block lists the paid holidays of 2026 and 2027 under the same rule and names both texts. Verify: a form built in a temporary folder lists 12 days for each year.

## 3. Verification

- [x] 3.1 New prospect before and after on the standard and three-product samples: the only differences are the roster note and any November roster. Verify: cell comparison; `verify.py` passes; the baseline is re-recorded only if a recorded figure moves, with the reason in `docs/05-decisions.md`.
