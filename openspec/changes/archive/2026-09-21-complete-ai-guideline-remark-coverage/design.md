## Context

`docs/12-sample-remark-rescan.md` (2026-09-11) is the authoritative extraction of which sheets
carry an `AI GUIDELINE` column and what their real worked examples say. `apply-guideline-remark-model`
(archived 2026-09-14) implemented `1. Summary` and most of `2. Budget-Management Fund`'s line-level
remarks; `0. Info`, `A2`/`A3`'s canonical descriptions, and `B2.6` were explicitly left as documented
gaps because each needs data or logic the pipeline didn't have at the time:

- `0. Info` needs a per-project drawing/legal citation — no intake field exists for it.
- `A2`/`A3`'s canonical descriptions were believed to need a ~30-position reference library and a
  roster-name-matching lookup — **this turned out to be based on a stale comparison; see D2**. The
  live deliverable template already carries every description as its own default content.
- `B2.6` isn't priced at all — there is no Python code computing a waste-collection cost anywhere
  in `generate_project_budget.py` today.

## Goals / Non-Goals

**Goals:**
- Close all three documented gaps: `0. Info`, `A2`/`A3`, `B2.6`.
- Keep the two display-only tracks (`0. Info`, `A2`/`A3`) and the one figure-moving track (`B2.6`)
  cleanly separable, so a PM can approve the first two without needing to review a new cost line.

**Non-Goals:**
- Re-doing anything `apply-guideline-remark-model` already shipped (`1. Summary` narratives,
  `2. Fund` line-level catalogue remarks).
- Re-pricing anything other than `B2.6` — no other line's figure changes.
- A generic "any sheet with an AI GUIDELINE column automatically gets a remark" framework. Three
  sheets, three specific implementations; a future sheet gets its own change.

## Decisions

### D1 — `0. Info`: one new intake field, blank by default

Add "Area basis / drawing reference" (free text) and "confirmed as of year" to `Project Info`,
appended after every existing field — the same append-only pattern the "months prepaid on
handover" field used (`apply-guideline-remark-model`), chosen specifically because this sheet has
a history of a row-shift bug from mid-sheet insertions. `read_input()` reads it guarded by
`SheetLabels.has(...)` so existing intake workbooks (Wayne Tower's included) keep reading cleanly
as blank.

- **Why free text, not a structured citation**: the guideline's own examples are prose ("per TKTC
  construction drawings, updated per Investor figures 2026") — a PM transcribes whatever their
  actual drawing reference is, not a value this pipeline can derive.
- **Why blank-safe rather than required**: most real intake workbooks in this project's history
  arrive without this level of drawing detail. A required field would either block generation or
  invite a placeholder value — worse than an honest "PM-supplied" caveat.

### D2 — `A2`/`A3`: REVISED after implementation — the template already carries every description;
verify it, don't write it

**Original plan** (superseded): transcribe the guideline's canonical Security/Cleaning positions
into a CSV, then match each roster demand position against it and write the matched description as
a line-level remark. Built the transcription (`data/master_list_verified/
AI_Guideline_Canonical_Positions.csv`, 27 rows: 17 Security + 10 Cleaning, sourced by reading
`docs/AI Guideline - 2027 Resi Budget Form (IT team) __repaired.xlsx` directly, not approximated).

**What implementation found**: `generate_project_budget.TEMPLATE_PATH` — the actual standard-form
template this pipeline generates every deliverable from — **already ships the full duty
description for all 27 canonical positions**, verbatim, at every row, in `A2!I` and `A3!L`.
Checked exhaustively: every one of the 27 rows the guideline defines has `note_present=True` on
the live template, matching the transcribed CSV. There is no missing remark to fill in.

**Why the original plan was wrong**: `docs/12-sample-remark-rescan.md`'s finding — "the roster's
own position names don't map to canonical names, needs a lookup table" — compared the guideline
against a *different, older worked-example workbook* (`docs/Ngân sách mẫu...`), not
`TEMPLATE_PATH`. Accurate for that older sample; not a description of what the live pipeline's
deliverable actually contains today.

**Revised approach**: no name-matching, no remark-writing. Keep the transcribed CSV as a
verification reference (task 2.1 stands), and add a check confirming every one of its 27 positions
still carries its description on the generated deliverable — this is the thing actually worth
guarding: a future Savills template revision silently dropping the text, not a gap in today's
pipeline. `docs/12` gets a correction note so this stale comparison doesn't mislead someone else.

- **Why keep the CSV even though nothing writes from it**: it is now the recorded, independently
  re-derivable contract for "what the template's A2/A3 SHOULD contain" — exactly the role
  `Costing_Method_Catalogue.csv` and `checks.py`'s hardcoded sheet-set constants already play
  elsewhere in this project. Without it, a template regression would look like "some cells are
  blank," not "these named 27 positions lost their required text."

### D3 — `B2.6`: price from unit count, the guideline's weight assumption, and QĐ 67 —
REVISED after reading the real source sheet

**Corrected from the original plan** (which guessed `×365` before the source was actually read):
the guideline's own `B2.6 Rác sinh hoạt (QD67)` sheet gives real, specific numbers, not just the
"2.63 kg/unit/day" headline docs/12 quoted:

- Unit prices (VND/kg, QĐ 67/2025/QĐ-UBND): collection 485.97, transport 180.07, treatment 420.45
  — sum 1,086.49/kg.
- Apartment: 2.63 kg/unit/day, confirmed by both the note text and the formula instruction.
- **Time basis is MONTHLY (`× 30 days`), not annual** — the guideline's own instruction reads
  "units × 2.63 × 30 ngày" verbatim. This matches how every other `2. Budget-Management Fund` leaf
  is priced (a `Monthly` frequency row), so `B2.6` follows that same shape rather than the annual
  basis first assumed.
- **The sheet also has a Shophouse section** (rows 12-18) the original design missed — it is
  internally inconsistent: the note text states "khoảng 3.41kg" per shophouse/day, while the
  formula instruction next to it says "2.63 × 1.5 × 30 ngày" (= 3.945 kg/day). **PM decision**: use
  the formula-instruction basis (3.945 kg/unit/day), not the note text (3.41) — the note is treated
  as the guideline's own inconsistency, disclosed in the remark, not followed. No Officetel/Office
  section exists on this sheet at all — those stay unpriced, same as before.

`waste_monthly = Σ over {Apartment, Shophouse} of (product_units × weight_kg_per_unit_per_day ×
30 × 1,086.49)`, written to whatever `2. Budget-Management Fund` row/code the template reserves
for it (find by scanning column Y for a "waste"/"rác" code the same way every other leaf row in
this pipeline is targeted — `assert_row_code`-guarded, not a bare row number; the guideline sheet's
own title, "B2.6b", hints there may be more than one waste-costing variant on the template — verify
which code is actually present before writing) — if no such row-group exists on the current
template, this task needs to stop and report back rather than guess a location, since inventing a
row would risk colliding with an existing formula.

### D4 — Verification stays independent of baselines for the two display-only tracks

The `0. Info` and `A2`/`A3` checks join the existing remark-content check (no baseline dependency,
per `deliverable-remarks`'s existing "Remarks are not a baselined figure" requirement). `B2.6`'s
new figure DOES need a baseline entry (it is a real number now, where before it was always zero) —
recorded fresh alongside the existing baseline-recording step, not folded into the remark check.

## Risks / Trade-offs

- **[`B2.6`'s real unit prices aren't sourced yet]** → read them from the actual guideline
  worksheet during implementation (not this design doc); if QĐ 67's own published rates are needed
  instead of what the guideline file states, flag the discrepancy rather than silently picking one.
- **[`A2`/`A3` template regresses silently]** → superseded the original "wrong match" risk (D2:
  no matching happens at all now). The real risk is a future Savills template edit dropping a
  canonical description without anyone noticing; the verification check in D2 is the mitigation.
- **[`B2.6` is a brand-new client-facing cost]** → measured on Wayne Tower and shown to the Head of
  PM before archive (spec requirement), same gate pattern as `reconcile-summary-with-detail-sheets`.
- **[The new `0. Info` field sits unused on every existing intake workbook]** → blank-safe by
  design (D1); no existing workbook needs updating for this change to be non-breaking.

## Migration Plan

1. Land `0. Info` and `A2`/`A3` (display-only); run `verify.py` — expect it to pass immediately,
   no baseline movement.
2. Land `B2.6`'s costing; run `verify.py` — expect it to FAIL on the new (previously-zero) figure,
   same as any other baseline-moving change in this project.
3. Measure `B2.6` on Wayne Tower; present the VND amount to the Head of PM.
4. Re-record the baseline with the reason; `verify.py` passes.
5. Rollback = revert the code; `0. Info`/`A2`/`A3` revert cleanly (no data dependency elsewhere);
   `B2.6`'s baseline reverts with the code.

## Open Questions

- The exact QĐ 67 collection/transport/treatment unit prices — read from the guideline source
  document at implementation time; not a decision this design needs to make now, and won't change
  the spec or task breakdown, only the constant's value.
