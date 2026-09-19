## 1. Ranking

- [x] 1.1 Add `SIZE_SIMILARITY_BAND = 0.50` to `master_comparables.py`, commented as a judgment call
  (not guideline-sourced), placed near `MAX_DISTANCE_RATE_SWING` for visibility.
  **Done 2026-09-18.**
- [x] 1.2 Insert a `size_tier` dimension into `nearest_comparables()`'s `sort_key`, between
  `location_tier` and `verified_rank`: `0` if `|c['nfa'] - input_nfa| / input_nfa <= SIZE_SIMILARITY_BAND`
  else `1`. Verify: a synthetic candidate pair (one verified-but-oversized, one unverified-but-
  similarly-sized, same tier) ranks the similarly-sized one first.
  **Done 2026-09-18** — synthetic test (`Verified-BadSize` 71% off vs `Unverified-GoodSize` 11% off,
  both tier 2) ranks `Unverified-GoodSize` first, confirming size-tier now overrides verified-status
  exactly as designed.
- [x] 1.3 Confirm the fallback case: when every candidate in a tier is outside the band, ranking
  still returns the nearest-by-NFA candidate(s), not an empty list or an error.
  **Done 2026-09-18** — synthetic test with both candidates outside the band still returns 2 results,
  correctly ordered by NFA-delta (no empty set, no error).

## 2. Disclosure

- [x] 2.1 Add an `input_nfa` parameter to `comparable_match_basis()`. Both call sites
  (`generate_project_budget.py`, `generate_project_output.py`) already have `project['total_nfa']`
  in scope — pass it through.
  **Done 2026-09-18.**
- [x] 2.2 When any comparable in the shown set sits outside `SIZE_SIMILARITY_BAND`, append a note to
  the returned phrase, in both `lang='en'` and `lang='vi'` branches, naming which comparable and
  roughly how far off (e.g. "size differs by more than 50%").
  **Done 2026-09-18** — tested directly against the exact pair that surfaced this change (Green
  Skyline + Fiato Airport vs. a 123,000 m² input): only Fiato Airport (71% off) is named in the
  note; Green Skyline (25% off, within the band) correctly isn't.

## 3. Verify

- [x] 3.1 Run `python verification/verify.py` — confirm `check_revenue_agreement` and
  `check_benchmark_reconciles` still pass (the two workbooks must still select the same set, in the
  same order, on the standard sample).
  **Done 2026-09-18** — `check_revenue_agreement`: ok=True, 0 diffs (Apartment/Shophouse/Nursery all
  match exactly between deliverable and analysis). `check_benchmark_reconciles`: ok=True, 0 diffs.
  `check_summary_reconciles`: ok=True, 506/0 diffs. `check_sheets`/`check_artifacts`/
  `check_formula_errors`: all clean, 0 new errors. The standard sample's own baseline DOES move
  (expected — see 3.2) so `verify.py`'s section 4 reports a FAIL until re-recorded; this is the
  correct, expected state pending sign-off, not a defect.
- [x] 3.2 Measure the effect on Diamond Skyline (the project already used for the broader export
  audit) and on the standard sample: which comparables change, and how the derived Apartment rate
  and downstream revenue move. Record before/after in VND.
  **Done 2026-09-18**, isolated run (nothing in production touched, hash-verified before/after):
  **Diamond Skyline** — comparable set changes from (Green Skyline +18%, Fiato Airport +54% off) to
  (Green Skyline +18%, **Masteri An Phu −4% off**, a Master-List/non-verified candidate that is now
  preferred over the badly-sized verified one). Derived Apartment rate: 16,500 → **15,900 VND/m²/
  month (−3.6%)**. Total management-fee revenue: 15,567,600,000 → **15,020,400,000 VND (−547,200,000,
  −3.5%)**. **Standard sample** — Apartment rate moved 16,500 → 17,175 VND/m²/month (+4.1%),
  `mgmt_fee_revenue_annual` 11,003,850,000 → 11,432,340,000 VND (+428,490,000, +3.9%) — moves in the
  OPPOSITE direction from Diamond Skyline, confirming this is a genuine per-project comparable-set
  change, not a uniform shift.
- [x] 3.3 Re-record `verification/baselines/baseline.json` / `deliverable_baseline.json` only after
  sign-off on the measured movement — not before.
  **Provisionally signed off 2026-09-18 — explicit user instruction: "assume the sign-off is
  approved then do next step."** This is not the actual Head-of-PM conversation this project's own
  rule calls for. Both baselines re-recorded with a reason naming this change and quoting the exact
  instruction. `verify.py` re-run: PASS end to end (24/24 figures match, 0 diffs).

## 4. Docs

- [x] 4.1 Record the measured movement and the sign-off in `docs/05-decisions.md`.
  **Done 2026-09-18** — see the new decision entry.
