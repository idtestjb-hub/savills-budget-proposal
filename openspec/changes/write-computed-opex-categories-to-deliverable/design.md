## Context

See `proposal.md` — Why. Established by reading the template, the code, and two real project
budgets.

- `estimate_opex()` returns five ratio categories plus Pool Salt. `generate_project_budget.py`'s
  `MGMT_FUND_ROWS` carries write sites for Electricity, Water and Diesel only. There is no
  `opex_admin` or `opex_repairs` key, so those two are computed on every run and discarded.
- `generate_project_output.py` writes all six to its OPEX sheet and feeds them into Cost Priority,
  so the analysis already treats both as real costs. Administrative Expense is even classified
  Must-Have there, meaning it is inside the profit figure the analysis reports.
- The deliverable's `EMA` (row 94) and `ER` (row 263) are `=SUBTOTAL(9,G95:G113)` and
  `=SUBTOTAL(9,G264:G485)`.
- The `ER` section is organised by building system — electric, generator, transformer, BMS, lifts,
  escalators, travelator, chillers, AHU, pumps, fire systems, façade, and more — each with
  `maintenance contract` / `spare parts` / `renovation` / `Others`. There is no all-systems row.
- **What real projects actually spend under `ER` is not spare parts.** 11D Thi Sách: 39,800,000, all
  of it `ERCS` clearance and suction. Green Skyline: 41,800,000 of 49,720,000 the same way. Only
  3,960,000 of either project's `ER` is a spare-parts line.

## Goals / Non-Goals

**Goals**

- Every category `estimate_opex()` computes appears in both workbooks with the same figure.
- Neither figure displaces a formula the template owns.
- The remark on each row states the basis, the sample size, and what the figure excludes.

**Non-Goals**

- Changing how either figure is derived. Both stay n=1 A&K ratios.
- Any other blank cost code found by the gap analysis.
- Decomposing either aggregate into the template's line items.
- `EMH1`, which stays blank per D1.

## Decisions

### D1 — Write to a catch-all leaf, never to the section roll-up

`EMA` → **`EMA15` "Others"** (row 109). `ER` → **`ERM` "Miscellaneous"** (row 485).

*Why not the roll-up row:* both hold a live `SUBTOTAL` formula. Writing a value there replaces the
template's own arithmetic with a constant, so the section stops summing its own line items. Any
figure a user later types into a leaf would then be silently ignored in the total. That is a worse
failure than the blank it replaces, because the sheet would still look right.

*Why these two leaves:* each sits inside its section's subtotal range (`109` within `95:113`, `485`
within `264:485`), each is empty in the template, and each keeps its own
`=IF($C…="Schedule",SUM(H…:S…),F…*E…)` formula — so the figure rolls up with no formula touched
anywhere. Both are the template's own general-purpose lines, which is what an undecomposed
aggregate is.

*Alternative considered:* spread each figure across the specific leaves the real projects use
(`EMA1`–`EMA7`, `ERCS1`–`ERCS4`). Rejected — the pipeline holds one blended ratio per category and
no allocation data. Splitting it would fabricate a breakdown, which is the failure mode this
project is recovering from.

### D2 — State the `ER` semantic mismatch on the row rather than resolve it

`Repairs & Maintenance (materials only)` is spare parts and materials, deliberately excluding
maintenance contracts — those are funded from the separate sinking fund under Housing Law 2023
Article 150, which is why the extractor excludes them. But the `ER` section as real projects use it
is dominated by clearance and suction *services*.

So the figure is narrower than the section it now sits in. The remark says so explicitly: what the
figure covers, that it is n=1, and that it does **not** include maintenance contracts or the
clearance work (`ERCS`) that both reference projects budget separately.

*Why not rename or re-map it:* the alternative is to place it under `ERCS`, which would label a
materials figure as clearance work — a mislabel, not a fix. Costing `ERCS` properly needs tank,
drainage and septic quotes that no reference table holds. That is a separate change; this one
records the gap where a reader will see it.

### D3 — Expect the movement before running

```
EMA section (Administrative Expense)   0 -> 57,166,716
ER  section (Repairs & Maintenance)    0 -> 28,135,740
                                            ----------
deliverable Management Fund total          +85,302,456
```

The analysis workbook must **not** move — it already carried both. If any analysis figure moves,
something was wired wrong and the run should stop rather than be re-baselined.

### D6 — Repairs & Maintenance is deferred, not forced (added during implementation)

`ERM` remains the correct placement. It is not written, because writing it introduces two
`#DIV/0!` cells and the harness's "no Excel errors introduced" check is not something to relax to
make a change land.

*What was actually found:* `ERM` (row 485) is the **only leaf of 178** in the `ER` section whose
`BK` column reads `$F485` directly. Every sibling — and every row this pipeline already writes —
uses `=$AL…/SUM($BG…:$BH…)*$BH…`, which evaluates to 0 while parking area is empty and so never
reaches the division. `ERM` skips that guard, so `BM485 = $BK485*$BM$11/SUM($BM$11:$BN$11)` fires
the moment the row holds a value, and `BM11:BN11` is empty in the template.

*Why this is bigger than this change:* **351 rows** carry that division. They are dormant only
because `'0. Info'!D12` — parking area in m² — is also empty, which is the same missing input that
already keeps `RM.PA` blank. Enter a parking area and the whole sheet lights up. That is
`fix-parking-allocation-divide-by-zero`.

*Alternatives rejected:*

- **Write it as `Schedule` frequency.** `BK485` would resolve through `VALUE(AK485)` to 0 and the
  error would vanish — but `Schedule` means a Year-1 lump in month 1, and this is a monthly
  run-rate cost. Silencing an error by misstating the cost's shape is worse than the blank.
- **Leave the frequency cell blank.** `E485` then falls through to 0 and `G485 = F485*0`, zeroing
  the figure itself.
- **A different `ER` leaf.** There is no other section-level catch-all; the ~40 `Others` rows are
  each scoped to one building system, so any of them would mislabel the figure.
- **Fill `BM11`/`BN11` here.** It would fix all 351 rows, which is precisely why it deserves its own
  change rather than riding along inside this one — and the two cells mean monthly versus casual
  parking revenue, a split that would have to be established rather than guessed.

*Consequence, stated plainly:* the cross-workbook gap closes from 85,302,456 to 28,135,740 — 67%,
not 100%. The remaining 28,135,740 is a known, named, single-line disagreement rather than an
unexplained one.

## Risks / Trade-offs

- **Both figures are n=1 A&K ratios** → unchanged by this work, but they now reach the client
  deliverable, where a thin number is more consequential than in an internal analysis. Stated in the
  remark on each row. Widening the basis is `R-D02`.
- **A catch-all row is less informative than itemised lines** → accepted. A PM reviewing the budget
  sees one Administrative Expense figure rather than nineteen. The remark carries the basis, and the
  alternative is an invented breakdown.
- **`ERM Miscellaneous` may read as "everything else under repairs"** → mitigated by the remark, not
  eliminated. A reader who ignores remarks could over-read it.
- **The deliverable's bottom line falls by 85,302,456** → that is the point; it was overstating
  profit by omitting two real costs. Worth flagging to the PM as a visible change in every future
  budget, not just a technical correction.
- **Row 109 is a hardcoded position** → same trade-off `align-methods-with-logic-spec`
  D2 accepted for the Service sheet. They are template-fixed, and a shift would show up as a figure
  landing under the wrong label rather than silently. The change should assert the code at each row
  before writing, so a moved template fails loudly.

## Migration Plan

No data migration. Generated output only. Rollback is removing the two `MGMT_FUND_ROWS` entries and
their write sites, then re-recording the baseline with a reason.

## Open Questions

- Whether the PM wants Administrative Expense itemised across `EMA1`–`EMA19` in future. That needs
  per-line reference data the pipeline does not have; the catch-all is correct until it does.
- Whether `ERCS` clearance and suction should be costed at all — both reference projects budget it
  and the pipeline has no rate for it. Out of scope here; belongs with the wider gap analysis.
