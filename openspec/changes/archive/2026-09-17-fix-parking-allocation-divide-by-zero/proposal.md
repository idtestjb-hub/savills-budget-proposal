## Why

The 2027 Resi template allocates every cost line across two parking revenue streams:

```
BM<row> = =IF(BK<row>>0, $BK<row>*$BM$11/SUM($BM$11:$BN$11), 0)
BN<row> = =IF(BK<row>>0, $BK<row>*$BN$11/SUM($BM$11:$BN$11), 0)
```

`BM11` and `BN11` are the split weights — "Doanh thu tháng" (monthly parking revenue) against
"Doanh thu vãng lai" (casual/visitor parking revenue). **They are empty in Savills' template**, so
`SUM($BM$11:$BN$11)` is zero and the division is undefined.

**351 rows carry that formula.** They produce `#DIV/0!` the moment their `BK` is greater than zero.

Today almost all of them are dormant, and only by accident: `BK` is
`=$AL<row>/SUM($BG<row>:$BH<row>)*$BH<row>`, and `BH10` reads `'0. Info'!D12` — **parking area in
m²**, which this pipeline never fills. So `BK` evaluates to 0, the `IF` short-circuits, and the
division never runs.

Two things follow, and the second is the serious one:

1. **`ERM` (row 485) already fails.** It is the only leaf of 178 in the `ER` section whose `BK`
   reads `$F485` directly rather than through the parking-area split. It ignores the guard, so
   writing any value there fires the division immediately. This is what stopped
   `write-computed-opex-categories-to-deliverable` from writing Repairs & Maintenance
   (28,135,740 VND/year) and is why that figure still appears in the analysis workbook and not in
   the client's.

2. **The moment anyone enters a parking area in m², the whole sheet lights up.** `BK` goes positive
   on all 350 remaining rows and every one of them produces `#DIV/0!`. The pipeline is one input
   away from generating a client deliverable full of error cells, and nothing in the pipeline warns
   about it — the harness only catches it today because the one always-live row was written to.

Parking area in m² is the same missing input that already keeps `RM.PA` (management fee on parking
area) deliberately blank. It is a real gap that will be filled eventually, and filling it currently
breaks the deliverable.

## What Changes

**The two allocation weights are populated**, so the denominator is never zero and the 351 rows
resolve instead of erroring.

**Amendment (2026-09-17, scope expanded on request after testing the fix on the actual triggering
state):** a second, structurally different zero-denominator defect surfaced — 6 rows (EMH1, EMH2,
EMH3, VAT, CIT1a, CIT1b, and ERM itself) are also missing their own per-row `BG<row>`/`BH<row>`
reference to the same header cells, which 350 of their 356 sibling rows already carry. Populated the
same way, with the same "restore the template's own established pattern, never invent a value" and
"fail loudly rather than ship a landmine" reasoning — see design.md's Amendment (D5) for the full
account, including why it took two detection attempts to catch all 6 rows.

The pipeline already computes both halves of that split. `RP1` and `RP2` — monthly motorbike and car
parking revenue — are written into the deliverable today from slot counts × citywide monthly fees.
That is the "Doanh thu tháng" half by construction.

**The casual/visitor half is established, not assumed.** `RP5`–`RP7` are the template's daily and
visitor parking codes and the pipeline fills none of them, so it holds no casual-parking figure. The
change must determine what the second weight should be from the reference budgets rather than
inventing a ratio. **If no basis is recoverable, the change writes the monthly half and a zero
casual half rather than a guessed split** — a 100/0 allocation that is wrong in emphasis is still
arithmetically defined, whereas a fabricated 70/30 is a number nobody can defend.

**A zero denominator is caught before it reaches a client.** Whatever weights are written, the
pipeline must fail rather than emit a deliverable whose allocation columns are undefined. That check
is what stops this recurring the next time a template column changes.

**Then Repairs & Maintenance is written.** With `ERM` usable, the deferred half of
`write-computed-opex-categories-to-deliverable` lands and the cross-workbook gap closes from
28,135,740 to zero.

**This is a defect in Savills' template, and that is recorded.** The template ships with an empty
denominator behind 351 live formulas. Whether the right long-term fix is to correct the template or
to keep populating it from the pipeline is **the PM's decision**, not this change's — the pipeline
cannot edit a file it does not own. The change makes the generated workbook correct and writes the
finding down.

Deliberately **not** in scope:

- **Filling `'0. Info'!D12`** (parking area in m²). It is a genuinely missing project input and
  belongs with `RM.PA`, not here. This change makes that input *safe to add*; it does not add it.
- Any other cost code, rate or method.
- Correcting the template file itself.

## Capabilities

### New Capabilities

<!-- None. This is the existing requirement that generated workbooks are structurally sound,
     extended to a defect the pipeline can trigger rather than one it introduces directly. -->

### Modified Capabilities

- `budget-workflow-verification`: the requirement that generated workbooks are structurally sound is
  extended — where the source template contains a formula that is undefined until an input the
  pipeline controls is populated, the pipeline SHALL populate it or fail, rather than emit a
  workbook whose errors depend on which rows happened to be written.

## Impact

**Code**

- `generate_project_budget.py` — writes the two allocation weights, and refuses to produce a
  deliverable while the denominator is zero.
- Once unblocked, the `opex_repairs` write site deferred by
  `write-computed-opex-categories-to-deliverable` is restored.

**Data**

- None. No reference table is read differently and no Fact/Dim join key changes, so the Copilot
  Studio package's live Generation B data is unaffected. Whether a casual-parking basis can be
  recovered is a read-only question against budgets already held.

**Figures**

- The allocation columns (`BM`/`BN`) resolve to numbers instead of `#DIV/0!`. These are an
  allocation view, not the cost figures themselves, so **no cost line changes value**.
- Repairs & Maintenance **+28,135,740** on the deliverable once restored, closing the remaining
  cross-workbook gap.
- The deliverable's expense total therefore rises by that amount. Same framing as before: a
  correction of an omission, not a new cost.

**Not affected**

- No dependency changes. No production data changes. No template file changes.
