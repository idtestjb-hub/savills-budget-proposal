## Context

See `proposal.md` — Why. Found while implementing `write-computed-opex-categories-to-deliverable`.

- `BM11`/`BN11` are the allocation weights. Empty in the template. Headers at row 10 read
  "Doang thu tháng" and "Doanh thu vãng lai" — monthly parking revenue against casual/visitor.
- 351 rows divide by `SUM($BM$11:$BN$11)`.
- 350 are dormant because `BK` routes through `BH10 = '0. Info'!D12` (parking area m²), which the
  pipeline never fills, so `BK = 0` and the `IF` short-circuits.
- `ERM` (row 485) is the sole exception — `BK` reads `$F485` directly. It is the one row that fires
  today, which is exactly why the defect was found by writing a single cost line.
- The pipeline already writes `RP1`/`RP2` (motorbike and car monthly parking revenue). It writes
  none of `RP5`–`RP7`, the daily/visitor codes.

## Goals / Non-Goals

**Goals**

- The denominator is never zero, so no row can produce `#DIV/0!`.
- A zero denominator stops the run rather than reaching a client.
- Whatever split is used is evidenced or explicitly zero — never a guessed ratio.
- `ERM` becomes usable so the deferred Repairs & Maintenance write can land.

**Non-Goals**

- Filling `'0. Info'!D12`. This change makes that input safe to add; adding it belongs with `RM.PA`.
- Editing Savills' template file.
- Any cost code, rate or method.

## Decisions

### D1 — Populate the weights from what the pipeline already computes, and only that

The monthly half is `RP1 + RP2`, which the pipeline derives from slot counts × citywide monthly
fees and already writes into the deliverable. No new derivation.

The casual half has no source. `RP5`–`RP7` are unfilled and no reference table carries a
daily/visitor parking figure.

*The rule this change follows:* recover a basis from the reference budgets if one exists; otherwise
write the monthly half and **zero** for casual. A 100/0 split is arithmetically defined and honestly
labelled — the allocation then attributes everything to monthly parking, which is what the pipeline
actually models. A fabricated 70/30 would look more plausible and be indefensible.

*Why this is acceptable:* `BM`/`BN` are an allocation *view* over costs, not the cost figures. Every
`G` column figure — the actual budget — is unaffected by how the split falls. Getting the emphasis
wrong misstates a secondary presentation; getting it invented would put a made-up ratio into a client
workbook.

### D2 — Fail on a zero denominator rather than trusting the write

Populating the cells fixes today. A guard is what stops it recurring: if the template gains another
such column, or a future edit clears these cells, the pipeline must stop rather than emit a
deliverable whose error cells depend on which rows that run happened to write.

*Why this matters more than the fix:* the defect was invisible for months and surfaced only because
one unusual row got written. A check turns "invisible until someone trips it" into "impossible to
ship". That is the same reasoning as `assert_row_code()` in the sibling change.

### D3 — Restore the deferred Repairs & Maintenance write, and prove it by the harness

Once `ERM` no longer errors, restore `opex_repairs` → row 485 with the remark that change already
wrote, and confirm via full Excel recalculation that no error cell is introduced.

*Verification that actually proves it:* generate with a non-zero parking area in `'0. Info'!D12` as
a **temporary** variant. That is the state that lights up all 350 dormant rows, so it is the only
run that demonstrates the fix rather than the accident. It must not touch the real input file.

### D4 — Record that the template is the thing that is wrong

The pipeline works around a defect in a file it does not own. That is the correct immediate move —
the deliverable must be right today — but it means every future template copy carries the same
landmine.

Whether Savills should fix the template, or the pipeline should keep populating it, is the PM's
call. The change records the defect precisely enough that someone can act on it: the cells, the
formula, the row count, and the input that triggers it.

## Risks / Trade-offs

- **A 100/0 split may misrepresent the allocation** → accepted where no basis exists, stated on the
  output. It affects a presentation column, not a cost. Revisit if a casual-parking basis appears.
- **The pipeline writes into a column it does not otherwise own** → `BM11`/`BN11` are inputs a PM
  might expect to control. If a project has real weights, the pipeline should not overwrite them —
  the change should write only where the cells are empty, and say when it did.
- **The fix is invisible until parking area is entered** → the temporary-variant run in D3 is what
  makes it demonstrable now rather than a claim.
- **Restoring the R&M write raises the deliverable's expense total by 28,135,740** → same framing as
  its own change: correcting an omission, not adding a cost.

## Migration Plan

Generated output only. Rollback is removing the two writes and the guard, and re-deferring the
`opex_repairs` write site — the state this change starts from.

## Open Questions

- Whether any reference budget carries a monthly-versus-casual parking revenue split. Answerable by
  reading them; decides D1's outcome.
- Whether Savills should correct the template. PM's call — see D4.
- Whether `BM11`/`BN11` should be exposed as intake-form inputs, so a project with real weights can
  supply them instead of receiving the pipeline's.

## Amendment (2026-09-17): a second, structurally different zero-denominator defect

Testing D3's own triggered state (task 4.1) proved the BM11/BN11 fix resolved the row that originally
motivated this change (ERM, row 485) — but 14 of 42 error rows survived, through a mechanism this
design did not anticipate. Investigated rather than assumed away, on your explicit instruction to
expand this change's scope to cover it.

### D5 — Populate the per-row area-basis reference too, not just the shared weight

351+ rows on this sheet don't only read `BM11`/`BN11` (the shared monthly/casual weight) — every one
of them ALSO has its own `BG<row>`/`BH<row>` cells, which `BJ<row>`/`BK<row>` divide by
(`SUM($BG<row>:$BH<row>)`). Confirmed by direct inspection: **350 of 356 rows already carry
`=$BG$10`/`=$BH$10`** — a plain reference to the row-10 header cells (`BG10='0. Info'!$D$8` Apartment
NFA, `BH10='0. Info'!D12` parking area), the exact same "per-row cell references a shared header"
shape `BM<row>`/`BN<row>` already use for `BM11`/`BN11`. **6 rows are missing it**: EMH1, EMH2, EMH3
(Savills management-fee-family codes), VAT, CIT1a, CIT1b (tax codes) — and ERM (row 485) itself.

ERM does not error from this specific cause — proposal.md already established its `BK` reads `$F485`
directly, bypassing BG/BH entirely, which is *why* it was the one row already failing before this
change (a different, first defect). But it was still missing the same reference every one of its 355
siblings carries, and populating it is the same fix for the same reason: restoring what the template's
own established pattern says should be there, not chasing only the symptom visible today.

*Why populate rather than leave alone*: identical reasoning to D1 — these are template cells the
pipeline does not otherwise own, but leaving them blank is not neutral; it is the second half of the
same landmine D2 exists to prevent. `=$BG$10`/`=$BH$10` are the template's own established formula for
this slot, not an invented substitute — writing them restores consistency, it does not decide anything
new.

*Detection, and why it took two attempts*: dynamic (scan the sheet for the actual signal, not a
hardcoded row list), same reasoning as D2. The first attempt matched rows whose `BM`/`BN` formula
references `$BM$11` — correct for 5 of 6 rows and for ERM, but VAT's own `BM498`/`BN498` are
`SUBTOTAL()` rollups of child rows, not the direct formula, so that signal alone missed it even though
VAT's own `BJ498`/`BK498` have the exact same `SUM($BG498:$BH498)` defect as the other 5. Caught only
by re-testing the actual triggering state after the first fix and finding one real cell still erroring,
not by reasoning about the template's shape in the abstract. Final detection combines both real
signals — `BM`/`BN` references `$BM$11`/`$BN$11`, OR `BJ`/`BK` itself divides by `SUM($BG` — either one
qualifies a row.

### Risk added, same shape as before

- **[Risk] A row could exist that neither signal detects** → *Mitigation*: same class of guard as D2,
  extended to this pattern — the pipeline fails rather than ship a workbook where any row matching
  either signal still has both cells blank. Verified this guard actually fires (tasks 3.1-3.3's
  equivalent for this second pattern) before relying on it.
