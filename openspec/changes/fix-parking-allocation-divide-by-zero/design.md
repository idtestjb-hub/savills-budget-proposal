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
