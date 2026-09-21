## Measured effect — Wayne Tower — Thủ Thiêm (EXAMPLE), isolated

Measured 2026-09-14 by generating Wayne Tower twice against the SAME final `2. Fund` pricing state
(after `fill-guideline-required-line-items` landed): once with `_activate_common_area_passthrough_
rows` live (current code), once with it monkeypatched to a no-op for that one run only. Production
file hash-verified unchanged throughout; both runs used redirected temp paths.

| | Activation OFF | Activation ON | Delta |
|---|---|---|---|
| `'1. Summary'!H54` (estimated year-1 surplus) | 6,920,688,544 | 6,960,784,814 | **+40,096,270** |
| `'2.2 Common area Fund'` sum of leaf `G` (its own expense rows) | 93,840,634 | 133,936,904 | +40,096,270 |
| `'2. Fund'!RI1` (row 78 — "collect operating expenses already paid for common-area fund") | 11,295,178 | 51,391,448 | +40,096,270 |

**The surplus goes UP, not down, when the activation is turned on** — counter-intuitive for a
change that only adds expense rows. Traced the exact mechanism rather than reporting the number
without explaining it:

## The mechanism

`RI1`'s own `F` column (the cell that becomes its `G` value under `Monthly` frequency) is:

```
F78 = '2.2 Common area Fund'!AH40
```

Not `'2. Budget-Management Fund'!AH40` as `Costing_Method_Catalogue.csv`'s RI1 row states — that
catalogue entry is stale/wrong; the real formula is a cross-sheet reference INTO `2.2`, and `AH40`
moves in exact lockstep with `2.2`'s own newly-activated expense-row total (both deltas are
40,096,270 to the VND). So `RI1` — money `2. Fund` books as REVENUE, "recovered from the common-
area fund" — is driven directly by the very expense rows this activation switches on.

`'1. Summary'!H54 = H46 = H13 - H20`, where `H13` includes `RI1` and `H20` is `2. Fund`'s own total
cost. **`2.2 Common area Fund`'s own bottom line never appears in `H54` at all** — nothing in this
formula chain nets the common-area fund's own newly-recognized cost against anything.

## Two readings — genuinely undecided, not something this session can settle

1. **Legitimate previously-hidden recovery.** If `2. Fund`'s own `EMH2`/`EMA15`/etc. figures are
   meant to be the WHOLE building's real cost (management fund pays it all up front), and `RI1` is
   the real, contractual reimbursement the common-area fund owes back for its share — then before
   this activation, that reimbursement was silently understated (stuck near zero because `2.2`'s
   own expense recognition was dormant), and the surplus WAS wrong — too low. This activation would
   be a genuine fix, not a double-count.
2. **One-sided recognition.** If `2.2 Common area Fund`'s own position (its own report, e.g.
   `2.2.1 Report-Common area Fund`) is meant to be read TOGETHER with `1. Summary`'s H54 as a
   combined two-fund picture — then this activation books the SAME 40,096,270 VND swing as revenue
   on one side (`RI1`, inside H54) without ever subtracting it from anything H54 or a combined view
   accounts for, and `2.2`'s own worsened position (a real cost now recognized there) has nowhere
   it flows back to in this picture. That would be a real double-count in the direction that makes
   the deliverable look BETTER than reality — the worst direction for a client-facing budget.

Both readings are internally consistent with what was traced; nothing found this session decides
between them. This is squarely the kind of real estate fund-accounting judgment call the sign-off
gate (design.md's two open questions) exists for — reported precisely rather than guessed either
way.

## What this means for sign-off

The measured isolated effect is **+40,096,270 VND to the reported year-1 surplus** on Wayne Tower
(a distinct, separate effect from `fill-guideline-required-line-items`' own **-65,078,257 VND**,
per that change's own `measured-effect.md` — the two are measured and reported independently, per
spec). Whoever reviews this for sign-off should be told plainly: the direction of this movement
(surplus UP) is the reason for extra scrutiny, not just the size — reading 2 above, if correct,
means shipping this as-is would overstate the client-facing surplus.
