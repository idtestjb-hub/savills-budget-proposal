# Measured effect — `B2.6` / waste-collection-costing track (ESS9)

**Date:** 2026-09-21
**Tracks 1 and 2 of this change (`0. Info`, `A2`/`A3`) are display-only — no figure moves. This
covers only track 3 (`B2.6`).**

## Method

Isolated run (`verification/run_workflow.py`) against the real, live intake form
(`Budget_Agent/reports/Project_Budget_Input.xlsx`, project "Diamond Skyline"), nothing in
production touched (hash-verified before/after). Both generators run, then full Excel
(COM) recalculation.

**Not Wayne Tower, as the task originally named** — Wayne Tower's own example workbook
(`EXAMPLE - Wayne Tower Thu Thiem.xlsx`) no longer exists anywhere in this repository; checked
`Budget_Agent/reports/` directly. Diamond Skyline is the current live project and the same one
every other measurement this week (`prefer-similar-size-comparables`, the export audit) used.

## Figure

- **ESS9 (Normal domestic garbage collection, QĐ 67/2025): 624,928,404 VND/year**
  (52,077,367 VND/month), computed on Diamond Skyline's real product mix — 600 apartment units,
  5 shophouse units.
- Formula: `(600 × 2.63 kg/unit/day + 5 × 3.945 kg/unit/day) × 30 days × 1,086.49 VND/kg`
  (1,086.49 = 485.97 collection + 180.07 transport + 420.45 treatment, QĐ 67/2025/QĐ-UBND).
- Hand-check: 600×2.63×30×1,086.49 ≈ 51,433,529; 5×3.945×30×1,086.49 ≈ 642,892; sum ≈
  52,076,420 — matches the written 52,077,367 within floating-point rounding.
- **This is a pure new-cost addition** — ESS9 was 0 (flagged "no method yet") before this change,
  now real. Year-1 surplus moves by the same 624,928,404 VND/year, since nothing else in the
  deliverable derives from ESS9's value.

## Verification run

- `check_artifacts`: clean, no corruption.
- `check_formula_errors`: method `excel-recalculation` (COM, not the weaker openpyxl fallback);
  0 new errors (5 pre-existing/inherited, same as the recorded baseline).
- `check_summary_reconciles`: **failed once, then passed after a real fix** — see below.
- `check_remark_content`: passes clean, including the new ESS9-remark-presence assertion.

## Found and fixed in passing: `check_summary_reconciles`'s row-31 matcher

Pricing ESS9 surfaced a real, reproducible `check_summary_reconciles` failure:
`'1. Summary'!H31 (ESS16) vs fund children` — Summary showed 888,928,404, the check's own
Python-side reconstruction of "H31's children" showed only 264,000,000 (ESS16 alone). Difference:
624,928,404 — exactly the new ESS9 figure.

Root cause: `verification/checks.py`'s `_SUMMARY_RECONCILE_ROWS` matched row 31 to fund code
`ESS16` alone (`('=ESS16',)`). The real Excel formula behind `H31` is
`'2. Budget-Management Fund'!AK144 - H29 - H30` — the whole ESS section total, minus Security
(ESS1, row 29) minus Cleaning (ESS4, row 30). That narrow matcher only ever produced the correct
total because every other code in that bucket (including ESS9) was zero until now — the same
failure class as the 2026-09-14 EMH2/EMH4 fix already recorded in this file's history.

Fixed by extending `_fund_code_match()` with an exclusion syntax (`!X` / `!=X`, checked before any
include) and correcting the matcher to `('ESS', '!=ESS1', '!=ESS4')`. Re-verified:
`check_summary_reconciles` now returns `ok=True`, 0 differences, including the previously-failing
row.

## Sign-off

**Presented in chat 2026-09-21 — awaiting sign-off.** Once given: record ESS9 in
`verification/baselines/deliverable_baseline.json` as a fresh addition (task 4.2), then `verify.py`
should PASS end to end (structural checks already confirmed clean above; only the baseline
addition remains).
