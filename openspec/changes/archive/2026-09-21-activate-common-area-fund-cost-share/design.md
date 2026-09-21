## Context

Found while working change `fill-guideline-required-line-items` (its own gap analysis, task 2.1):
`2.2 Common area Fund` was showing 60+ Required-code "gaps" that turned out not to be missing
pricing methods at all. Diagnosed via COM on a generated Wayne Tower deliverable:

- `F{row}` on every `EMH*`/`EMA*`/`EMB*`/`EMO*`/`ESC*`/`ESS*`/`ESI*`/`ESM*`/`ESR`/`EN*`/
  `EEW.*`/`EEE.*`/`EED.*`/`EEG.*`/`ER*` leaf row already carries a template-native formula:
  `=XLOOKUP(Y{row}, '2. Budget-Management Fund'!$Y$79:$Y$494, '2. Budget-Management Fund'!$AL$79:
  $AL$494) * $F$8` — a real, non-zero value once `2. Fund`'s own matching code is priced.
- `F8` (this sheet's own cell) = `$AH$13 / (SUBTOTAL(9, '2. Budget-Management Fund'!$AL$13:$AL$76)
  + $AH$13)` — a revenue-proportional ratio (common-area revenue over total revenue), ~0.4456% on
  the Wayne Tower example.
- `G{row} = IF($C{row}="Schedule", SUM(H{row}:S{row}), F{row}*E{row})`, and
  `E{row} = IF(OR(C="Schedule", C="Monthly"), 12, IF(C="Yearly", 1, ...))` — E only returns a
  non-zero multiplier when C holds a recognized frequency string.
- The template ships C **blank** on 213 of these rows. Only 9 (`EMB3`, `ESC12`, `ESS1`, `ESS4`,
  `ESS38`, `ESI1`, `ESI2`, `ESM25`, `EEE.P`) ship with `C='Monthly'` already set — which is exactly
  why `ESS1`/`ESS4` were the only two expense codes showing as "filled" on this sheet before this
  change, alongside the two revenue rows (`RA1.A`/`RA2`) the pipeline writes directly.
- Confirmed via COM on Wayne Tower: activating C on the already-priced codes (`EMH2`, `EMA15`,
  `ESS16`, `ESM2/3/4/5/8`, `EN1/2/3`, `EEW.C`/`EEE.C`/`EED.C`) makes `2.2`'s G column resolve to
  exactly `F8 × the matching 2.Fund G value` for every one of them (ratio checked to 6 decimal
  places, identical across all 15 spot-checked rows). A still-zero code on `2. Fund` (`EMA1`)
  correctly stays zero on `2.2` too — proportional share of zero, not a bug.

This directly contradicts a prior comment in the same file (see proposal.md Why) asserting no real
allocation split exists. It does — it was just dormant. Whether it is the *correct* one is the
open question this change exists to answer.

## Goals / Non-Goals

**Goals:**
- Record the mechanism precisely (done — see the updated comment in `generate_project_budget.py`
  above `COMMON_AREA_FUND_ROWS`, and this design doc).
- Measure the isolated year-one effect of activation alone.
- Get an explicit PM/finance answer on the two open questions (allocation basis correctness;
  RI1 double-count risk) before archiving.

**Non-Goals:**
- Pricing any new code on `2. Fund` itself — that is `fill-guideline-required-line-items`'s job;
  this change only concerns whether `2.2`'s own pass-through rows are switched on.
- Redesigning `F8`'s own formula or the revenue-share methodology — if it's wrong, the fix is a PM/
  finance-directed replacement, not something this pipeline invents on its own.

## Decisions

### D1 — Keep the activation implemented, gate archival on sign-off

Per user direction (2026-09-14): the fix stays live in code (it is a real template mechanism, not
invented), but is tracked as its own change so its accounting question doesn't block
`fill-guideline-required-line-items`'s own, unambiguous pricing work. `verify.py`'s baseline for
this sheet's totals is NOT re-recorded until sign-off lands — a deliberate, expected FAIL state
matching this project's own established pattern for every figure-moving change pending sign-off
(see `reconcile-summary-with-detail-sheets`).

### D2 — Measure this change's effect in isolation

Because `fill-guideline-required-line-items` prices new `2. Fund` codes in the same period, and
those prices cascade automatically into `2.2` once C is activated, a naive before/after diff on
`2.2`'s total would conflate both changes' effects. Measure this change's isolated effect by
generating twice on the same project and code state: once with `_activate_common_area_passthrough_
rows` stubbed out (C stays blank), once with it active — both against the SAME priced `2. Fund`
state — and diff only those two runs.

## Risks / Trade-offs

- **[Wrong allocation basis]** → explicit sign-off gate; reverting is a one-function change if
  rejected (the function has no side effects outside the C column of these specific rows).
- **[RI1 double-count]** → named explicitly as one of the two sign-off questions; not assumed
  either way.
- **[Conflated with fill-guideline-required-line-items' own measured figure]** → D2's isolated
  measurement approach; each change reports and is signed off on only its own effect.

## Migration Plan

1. Record the mechanism (done).
2. Measure the isolated effect (D2) on Wayne Tower.
3. Present both sign-off questions to PM/finance.
4. If confirmed: record the baseline, `verify.py` passes, archive.
5. If rejected: revert or replace the ratio per the confirmed correct basis, then archive.
6. Rollback = revert `_activate_common_area_passthrough_rows`'s call site (one line) or the
   function itself; no other code depends on it.

## Open Questions

- Is revenue-share the correct basis to allocate common-area costs between the two funds, or
  should it be area-share, unit-count, or something else entirely? — PM/finance to confirm.
- **Does populating these rows double-count against `RI1`'s own recovery mechanism? — traced
  precisely (2026-09-14, measured-effect.md), not yet resolved.** Correction to this doc's earlier
  text: `RI1`'s source is `'2.2 Common area Fund'!AH40` (a cross-sheet reference), not
  `'2. Fund!AH40'` as first assumed from the catalogue's (stale) note — and `AH40` moves in exact
  lockstep with this activation's own newly-populated expense rows. Isolated measurement: turning
  the activation on moves `RI1` by the SAME 40,096,270 VND as `2.2`'s own expense-row total, and
  `1. Summary!H54`'s surplus goes UP by that same amount, with `2.2`'s own worsened position never
  appearing in `H54` anywhere. Two readings, genuinely undecided: (1) a legitimate previously-
  understated recovery, now correctly shown; (2) a one-sided recognition that inflates the reported
  surplus — see measured-effect.md's full writeup. This is the central question sign-off must
  answer, more concretely stated than when this doc was first written.
