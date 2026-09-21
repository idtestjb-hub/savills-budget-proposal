## 1. Record the mechanism

- [x] 1.1 Write `_activate_common_area_passthrough_rows` in `generate_project_budget.py`, called
  from `fill_common_area_fund_sheet`. Verify (COM): on a generated Wayne Tower deliverable, every
  already-priced `2. Fund` code's matching `2.2 Common area Fund` row now equals `F8 × the 2.Fund
  G value` to 6 decimal places; a still-zero `2. Fund` code stays zero on `2.2` too; the two
  revenue rows in `COMMON_AREA_FUND_ROWS` and the 9 rows the template itself pre-set C on are
  untouched.
  **Done 2026-09-14** — verified via COM: `EMH2`, `EMA15`, `ESS16`, `ESM2/3/4/5/8`, `EN1/2/3`,
  `EEW.C`/`EEE.C`/`EED.C` all resolved to ratio 0.004456 (= F8) against their `2. Fund` G value;
  `EMA1` (zero on `2. Fund`) stayed zero on `2.2`. Production backup hash unchanged, `production
  touched: no` on every run.
- [x] 1.2 Update the prior comment in `generate_project_budget.py` (above `COMMON_AREA_FUND_ROWS`)
  that asserted no allocation split exists — record what was actually found, without deleting the
  original reasoning. Verify by reading the comment back.
  **Done 2026-09-14.**
- [x] 1.3 Scaffold this change's own proposal/specs/design so the finding and its sign-off gate are
  on the record independent of `fill-guideline-required-line-items`. Verify all four artifacts
  exist.
  **Done 2026-09-14.**

## 2. Measure in isolation

- [x] 2.1 Generate Wayne Tower twice against the same priced `2. Fund` state — once with
  `_activate_common_area_passthrough_rows` stubbed to a no-op, once live — and diff only `2.2
  Common area Fund`'s own totals and anything downstream that reads from it (`2.2.1 Report-Common
  area Fund`, `1. Summary` if applicable). Record the isolated year-one movement in
  `measured-effect.md`. Do this AFTER `fill-guideline-required-line-items`'s own `2. Fund` pricing
  work lands, so the "live" run reflects the real, final `2. Fund` state this activation will ship
  against.
  **Done 2026-09-14, with a significant finding**: isolated effect is **+40,096,270 VND to the
  reported year-1 surplus** (surplus goes UP, not down — counter-intuitive for an expense-adding
  change). Traced the exact mechanism: `RI1` on `2. Fund` (booked as revenue) reads directly from
  `'2.2 Common area Fund'!AH40`, which moves in lockstep with this activation's own newly-populated
  expense rows — and `2.2`'s own worsened position never appears in `'1. Summary'!H54` anywhere.
  This directly sharpens design.md's own open question (see there) rather than resolving it — two
  internally-consistent readings exist (legitimate previously-hidden recovery vs. one-sided
  recognition that inflates the surplus), and this session cannot decide between them. Full
  writeup: `measured-effect.md`.

## 3. Sign-off

- [x] 3.1 Present both open questions (design.md) plus the measured isolated movement to PM/
  finance. Capture the answer in this change's own notes and `docs/05-decisions.md`.
  **Done 2026-09-21.** Before presenting, traced the RI1/AH40 mechanism further than design.md had:
  RI1's own template label reads *"Collect operating expenses already paid for common area fund /
  Thu kinh phí vận hành đã chi hộ quỹ khai thác khu vực chung"* — a "chi hộ" (paid-on-behalf-of)
  reimbursement, template-native, not a pipeline invention. Searched the entire operating-fund
  sheet for every cross-reference to `2.2 Common area Fund`: exactly one, RI1's own `F78`. No
  offsetting expense exists anywhere on that sheet for whatever the fund advances. Presented both
  questions plus this sharper finding. **RI1 double-count question: "Confirm as correct — ship
  it."** **Allocation basis (revenue-share) question: "Not sure / no strong opinion"** — left as is,
  flagged as an open item per design.md's own Non-Goals (redesigning `F8` is out of this change's
  scope regardless). See `docs/05-decisions.md`'s new entry.
- [x] 3.2 If confirmed: record `2.2 Common area Fund`'s (and any downstream sheet's) baseline in
  `deliverable_baseline.json` / `baseline.json` as applicable. Verify `verify.py` passes.
  **Done 2026-09-21** — only `deliverable_baseline.json` (`2.2 Common area Fund` doesn't exist on
  the analysis workbook, confirmed by grep — `baseline.json` untouched). `verify.py` re-run: **PASS
  end to end**, all 6 sections.
  **Found and fixed in passing**: `check_required_line_items`'s own explanatory note for `2.2`'s 32
  still-zero Required codes said this sheet's completeness was "gated... pending PM/finance
  sign-off" — stale now that sign-off landed. Checked directly (not assumed): every one of the 32 is
  a proportional share of a code that is ALSO zero, with a stated reason, on `2. Budget-Management
  Fund` — correct, not a gap. What's actually missing is that `2.2` never gets its own copy of that
  disclosure text (`_FLAGGED_NO_METHOD` only writes to the first sheet). Comment and printed note
  corrected to say this; the underlying enforcement scope is unchanged (writing ~32 matching remarks
  onto `2.2` is real, separate work, not absorbed into this fix — flagged as a follow-up).
- [x] 3.3 If rejected or a different basis is confirmed: implement the correction (replace `$F$8`
  usage, or revert `_activate_common_area_passthrough_rows`'s call site) before proceeding to
  archive.
  **N/A** — confirmed as correct (3.1), not rejected. Nothing to revert or replace.

## 4. Docs

- [x] 4.1 Update `docs/09-template-map.md`'s `2.2 Common area Fund` row description and
  `docs/project-status.md` once sign-off lands, either direction.
  **Done 2026-09-21** — `docs/09-template-map.md`'s "Other branches" section extended with the
  activation mechanism, the RI1/"chi hộ" finding, and a pointer to `docs/05-decisions.md`'s new
  entry. `docs/project-status.md`: new dated amendment at the top, plus a "RESOLVED" pointer on the
  original 2026-09-14 narrative block.
