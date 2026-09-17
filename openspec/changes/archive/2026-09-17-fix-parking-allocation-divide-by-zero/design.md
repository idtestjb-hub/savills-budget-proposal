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

## Amendment (2026-09-17, part 2): ERM's `AK` column reads a different row than its `G` column

Reopened after this change's own task 5.3 measurement (`G485` = 28,135,740) was later shown to have
proved only half the row. `reconcile-summary-with-detail-sheets`'s `check_summary_reconciles` — a
check this change never ran, since it predates that change's own verification section — caught the
other half: `1. Summary` reads column `AK`, not `G` (design.md of that change, Context), and `AK485`
is 0 on every run this change has ever produced.

### D6 — Under investigation; first hypothesis (mirror the write into row 486) tried and disproven

`AK485` is not a normal leaf formula. Every other one of the 27 rows `MGMT_FUND_ROWS` targets has
`AK<row> = SUM(AQ<row>:BB<row>)`, deriving from its own row. Row 485 alone has
`AK485 = SUBTOTAL(9,AK486)` — it reads row 486 (`Y486 = 'ERM1'`), a separate leaf with its own normal
`AK486 = SUM(AQ486:BB486)` formula, which the pipeline has never written to. Confirmed this is isolated
to ERM: scanned the `AK` formula of all 27 `MGMT_FUND_ROWS` targets directly against the generated
deliverable; row 485 is the only one whose `AK` doesn't derive from itself.

**First hypothesis, tried and empirically disproven**: that this is deliberate template structure —
`G263` (`=SUBTOTAL(9,G264:G485)`) stops at row 485, `AK263` (`=SUBTOTAL(9,AK264:AK486)`) reaches one
row further to 486, read as "485 holds the annual total for `G`, 486 holds the same cost's monthly
detail for `AK`." Implemented as a mirrored write (same monthly amount into row 486's `C`/`F`/`H:S`,
row 485 unchanged) and verified via full Excel recalculation on the triggered state: `G263`/`AK263` did
reconcile (28,135,740 both sides), **but `G79`/`AK79`** — the broader "(E)" rollup, range 80:494,
which already spans both 485 and 486 — **went from a 28,135,740 deficit on `AK` to an exact
28,135,740 excess on `G`**. `F486`/`C486` mechanically drive both `G486` and `AK486` identically
(same underlying formulas as every other row), so populating row 486 makes it a second genuine
non-SUBTOTAL leaf that `G79` counts alongside `G485` — `AK79` only looked fine because `AK485`,
itself a `SUBTOTAL`, is auto-skipped by `AK79`'s own nested-SUBTOTAL-ignore, an asymmetry `G79` has
no equivalent of. There is no variant of "populate row 486" that satisfies both `G263`'s narrower
range and `G79`'s wider one. Reverted.

**Second reading, implemented**: `G79` covering both rows with nothing compensating for 486, combined
with `F486` shipping blank in Savills' own template, is more consistent with `AK485 =
SUBTOTAL(9,AK486)` being a template defect (an Excel row-insert artifact carrying a stale reference)
than a deliberate two-column design — no different in kind from the D2/D5 defects this same change
already fixed elsewhere on this sheet. Confirmed directly: row 486's own `AK`/`AQ:BB` formulas are
fully intact, and — once `486`→`485` is substituted — byte-for-byte identical to row 484's own
formulas with `484`→`485` substituted. Row 486 was never a data row; it is an unused leaf that still
carries the template's normal formula shape, which is what makes the row-insert-artifact reading solid
rather than speculative.

Fix implemented as a formula repair, not a data write: `generate_project_budget.py` scans every fund
leaf row for an `AK` formula matching exactly `=SUBTOTAL(9,<ref>)` (a leaf row's `G` is never itself a
`SUBTOTAL`, so this can't misfire on a genuine section header), and where found, copies the referenced
row's own intact `AK`/`AQ:BB` formula text with the row number substituted — restoring row 485 to the
same self-referencing shape all 26 sibling rows already have. Dynamic detection, not hardcoded to row
485, matching every other guard added by this change. Verified via full Excel recalculation on a fresh
run: `G485=AK485=28,135,740`, `G263=AK263=28,135,740`, `G79=AK79=9,533,984,013.92` (previously off by
exactly 28,135,740 in one direction or the other under each attempt), `G486=AK486=0` (row 486 stays
correctly untouched). `check_summary_reconciles` run directly against a fresh output: `ok=True`, 506
rows checked, 0 differences. `verify.py` section 5 now reports exactly one expected movement —
`estimated_surplus_year1` drops by 28,135,740 VND, i.e. the surplus correctly falls once the R&M cost
is counted on the `AK`/cash-flow basis `1. Summary` actually reads — gated on sign-off before
re-recording (tasks.md 9.6), same as every other figure movement this session.

### Risk

- **[Risk] Another mapped row could develop this same defect if the template changes** →
  *Mitigation*: no guard added — the scan in this amendment is a point-in-time check, not a running
  assertion, and `assert_row_code` only checks the code in column Y, which is insufficient (row 485's
  own code is genuinely `ERM`; the defect is in its `AK` formula, which `assert_row_code` does not
  read). Left as a documented gap rather than over-built for a shape observed exactly once.
