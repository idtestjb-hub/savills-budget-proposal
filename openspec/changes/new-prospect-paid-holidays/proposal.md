## Why

New prospect counts the 11 public holidays of Labour Code 2019 Article 112 for every year. Since 01/07/2026, Nghị quyết
28/2026/QH16 Article 2 adds 24 November ("Ngày Văn hóa Việt Nam") as a paid day off, so the law gives 12 days. The user
decided on 2026-10-10 that New prospect follows the law, with no separate sign-off, and that the output names the law
(`docs/05-decisions.md`).

## What Changes

- The holidays computed for a roster month are the days the law in force on that day makes paid: Article 112's 11 days,
  plus 24 November from 2026. Dates a PM types on `Roster Setup` still replace the computed list.
- The roster's `Setup` sheet names the law next to the holiday dates.
- The input form's reference block lists the paid holidays of 2026 and 2027 under the same rule and names both texts.
- Existing-project mode is unchanged: an approved prior-year budget keeps the calendar of the law in force on 1 January
  of that year (`vn_holidays.paid_holidays`).

## Capabilities

### New Capabilities
- `paid-holiday-calendar`: which days a generated budget counts as paid public holidays, and how it names the law.

### Modified Capabilities

## Impact

- `vn_holidays.py` (`holidays_in_month`), `generate_project_budget.py` (roster `Setup` note),
  `build_project_input_form.py` (reference block), `tests/test_vn_holidays.py`.
- Figures move only for a roster month that contains 24 November from 2026. The standard sample rosters September 2026,
  so its recorded baseline does not move; the roster's `Setup` sheet gains the law note.
