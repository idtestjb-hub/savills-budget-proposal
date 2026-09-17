## Context

See `proposal.md` for motivation. Design-relevant facts established by inspection:

- `generate_project_budget.py` fills exactly two fund sheets by literal name — `2. Budget-Management
  Fund` and `2.2 Common area Fund` — via `MGMT_FUND_ROWS` / `COMMON_AREA_FUND_ROWS`, which are
  `{name: row}` maps keyed to fixed row numbers, guarded by `_assert_leaf_rows()` against the code in
  column Y. Column positions are module constants (`_CODE_COL = 25`, remark column 20). The whole fill
  path assumes one sheet per fund, one year.
- `input/template/` holds only single-year forms (`2027 Resi Budget Form (IT team).xlsx` and the
  `202608 -` Resi/Commercial forms). **There is no blank multi-phase form in this repository.** The
  multi-phase example we have — `docs/Ngân sách mẫu … năm 1 + năm 2 có giai đoạn tiền khai trương` —
  is a delivered *project* workbook, not a blank template.
- That sample's fund sheets are one column wider than our template (it carries an extra prior-year
  benchmark column before Unit Price), shifting code to Z, remark to U, months to I:T. Its row codes
  nonetheless match ours closely: of 497 codes on our generated sheet and 494 on its year-1 sheet, 493
  are common. So the two forms share a row vocabulary but not a column layout.
- The fill-up curve already lives in one shared module (`fill_curve.py`) read by both generators, and
  the deliverable already has the two fill-up sheets the curve is written onto.
- `_compose_summary_narratives()` writes `1. Summary` column K; `check_summary_reconciles` and
  `check_remark_content` read fixed columns on `1. Summary` and on the fund sheets.
- `verification/run_workflow.py` already fails a run in which only one of the two generators completes,
  on the grounds that the two workbooks would then describe different projects.

## Goals / Non-Goals

**Goals**
- A phase model explicit enough that "one operating year, no pre-opening" is just its degenerate case,
  so the single-year path can be proven unchanged rather than argued to be unchanged.
- Per-phase sheets whose cross-sheet formulas resolve within their own phase.
- Escalation that is stated and disclosed, never assumed.

**Non-Goals**
- The stabilised-occupancy scenario variants the sample also carries (25% / 50% / 75% / 100% sheets).
  Those are a different axis — alternative assumptions about the same period, not additional periods —
  and are out of scope here.
- Adopting the sample's own column layout. We stay on the IT-team template's columns; the row-code
  vocabulary is what the two forms share, and the column shift is precisely what we are not taking on.
- Sinking-fund multi-year modelling. The sinking-fund sheets are stubs today and stay stubs.

## Decisions

### D1 — Per-phase sheets are derived programmatically from the template's own fund sheets, not shipped as a wider template

Three ways to obtain a year-2 fund sheet were considered:

- **(a) Derive it in code** from the template's existing fund sheet, once per additional phase, then
  rewrite its cross-sheet references to point at its own phase's sheets. **Chosen.**
- **(b) Obtain a blank multi-phase form** from whoever owns the standard form at Savills. Strictly
  better if such a form exists, because its cross-sheet wiring would be authored by the form's owners
  rather than rewritten by us. We do not know whether one exists — task 1.1 finds out, and if it does,
  this decision is revisited before any code is written.
- **(c) Strip the delivered sample workbook back to a blank multi-phase template** and adopt that.
  Rejected: it is a different column layout (see Context), so adopting it means re-pointing every
  column constant and re-verifying every row map in the pipeline — a template migration of the same
  size as `rebase-output-onto-25-sheet-form`, bundled into an unrelated change.

(a) wins on the constraint that matters most: it keeps `MGMT_FUND_ROWS`, the column constants, and
`_assert_leaf_rows()` valid exactly as they are, so the pricing logic does not move at all. The risk it
carries — silently wrong cross-sheet references on a copied sheet — is bounded and directly testable
(D4).

### D2 — A phase list, with today's behaviour as the one-element case

The horizon becomes an ordered list of phases, each carrying: kind (`pre-opening` / `operating`), a
label, a month count, its index within its kind, and its escalation exponent (`0` for the first
operating year). `build_budget()` loops over that list where it today fills once.

A project that states nothing yields `[Phase(operating, 12 months, index 1, exponent 0)]` — one
iteration of the same code that runs today, writing the same sheet under the same name. This is why
the single-year-unchanged requirement is testable rather than aspirational: it is the same code path,
not a preserved parallel one.

### D3 — Year 1 keeps its sheet name; later phases are suffixed

The spec requires a single-year project's sheet names to be unchanged, so the year-1 fund sheet stays
`2. Budget-Management Fund` and additional phases take a suffixed name identifying the phase. This
deliberately does **not** match the sample's own `2a.` / `2b.` / `0.Budget-Pre` convention, which would
require renaming year 1 and so breaking the unchanged-output guarantee. Whether to move to Savills'
naming wholesale is a form-owner decision recorded in Open Questions, not settled here.

### D4 — Cross-sheet references are rewritten by name, and verified by recalculation

When a phase's sheet is derived, every formula on it that names another sheet the phase also owns (its
paired common-area-fund sheet, its own staff-cost sheet where one exists) is rewritten to name that
phase's copy; references to genuinely shared sheets (`0. Info`, the fill-up sheets, the rate sheets)
are left pointing at the shared sheet. Correctness is established by the check this project already
trusts for template work: a full Excel COM recalculation of the generated workbook with **zero cells
resolving to a spreadsheet error**, plus the existing row-code assertion re-run per phase sheet.

A reference that names a sheet the rewriter does not recognise as either phase-owned or shared stops
generation with the sheet, the cell and the formula named. Guessing is the failure mode that would
produce a plausible-looking workbook silently reporting another year's numbers.

### D5 — Escalation is a per-code property in the costing catalogue, not a blanket multiplier

Applying one escalation rate to every cost line would double-count on lines already priced from a
dated, source-cited basis (electricity and water carry their own published tariff and its date;
diesel carries a quoted price as of a stated day). So `Costing_Method_Catalogue.csv` gains a column
saying whether a code escalates year-on-year, defaulting to yes for benchmark/ratio/flat-reference
costs and no for codes whose price basis is itself dated and separately maintained. This follows the
established division in this project: the catalogue holds the rule, the code holds the wording.

Revenue is deliberately asymmetric — the management-fee rate does not escalate on its own. A fee rate
is contractual and, in practice, fixed by the owners' congress for a period; escalating it silently
would inflate the reported surplus in the direction that flatters Savills, which is the direction this
project's conventions treat as requiring an explicit human decision rather than a default.

### D6 — Pre-opening needs its own roster input, and is reported gross

A pre-opening phase is not the operating year scaled down: it has a mobilisation team, not a full
operating roster, and no resident fee revenue. The sample carries a separate pre-opening staff-cost
sheet for exactly this reason. So pre-opening requires a stated mobilisation roster as its own input —
it cannot be derived from the operating demand sheet — and its deficit is reported as its own figure
rather than netted into year 1, because who funds it (in practice the developer) is a commercial
question the budget should expose, not bury.

### D7 — The summary's phase-dependent columns make several fixed column indices variable

Appending a column group per phase moves `1. Summary`'s Remarks column right. `_compose_summary_
narratives()`, `check_summary_reconciles` and `check_remark_content` all address that column by a
fixed index today. They become phase-count-aware, resolving the column from the sheet's own header row
rather than a constant — which is also how they should have addressed it in the first place, and
removes a latent breakage the next template revision would have caused anyway.

## Risks / Trade-offs

- **[A derived sheet's formula silently points at another phase's sheet]** → D4's rewrite-then-verify,
  with an unrecognised reference stopping generation rather than being guessed at. This is the failure
  that would be least visible on inspection and most damaging in front of a client, so it gets the
  hard stop rather than a warning.
- **[The single-year path changes by accident during the refactor]** → staged migration (below) puts
  the phase-model refactor in its own stage whose entire acceptance criterion is a byte-for-byte
  unchanged single-year output against the recorded baseline, before any multi-phase behaviour exists.
- **[This change collides with three in-flight changes]** → `localize-line-level-remarks` rewrites the
  same remark call sites, `activate-common-area-fund-cost-share` changes the common-area sheet this
  change duplicates per phase, and `reconcile-summary-with-detail-sheets` changes the summary
  reconciliation this change makes phase-aware. Sequencing: this change should start after those three
  settle. Starting earlier multiplies each of their review surfaces by the phase count.
- **[Escalation compounds an error across years]** → a wrong year-1 figure becomes a wrong figure in
  every later year, scaled up. Mitigated by the measurement requirement: each phase's revenue, cost and
  surplus recorded separately for a real project, so a year-on-year progression that does not look
  right is visible before sign-off rather than after.
- **[Multi-phase workbooks get large]** → each phase adds two ~500-row, ~90-column sheets. A
  three-year-plus-pre-opening project is roughly four times today's fund-sheet content. Generation time
  and file size should be measured in stage 2 rather than assumed acceptable.

## Migration Plan

Four stages, each independently shippable, ordered so that nothing observable changes until the seam
is proven:

1. **Phase model, no behaviour change.** Introduce the phase list and loop with a single hard-coded
   operating phase. Acceptance: generated output is unchanged against the recorded baseline — same
   sheet names, same figures, same layout. Nothing in the deliverable moves.
2. **N operating years.** Horizon input, per-phase sheet derivation (D1/D4), escalation (D5),
   phase-aware summary (D7). Acceptance: a two-year project generates and recalculates with zero
   formula errors, and its year-1 figures still match the single-year baseline.
3. **Pre-opening phase.** The mobilisation-roster input and the pre-opening sheet (D6). Acceptance: a
   pre-opening phase reports its own total, carries no resident fee revenue, and does not alter any
   operating year's figures.
4. **Measure, sign off, document.** Record each phase's revenue/cost/surplus for a named real project
   against its single-year figures; Head-of-PM sign-off before the capability is used for a client
   deliverable; update the template map and the status docs.

Rollback at any stage: revert that stage's code. Stage 1 is reversible with no figure impact by
construction; stages 2 and 3 are opt-in per project via the horizon input, so reverting them returns
every project to the single-year path rather than leaving projects in a half-migrated state.

## Open Questions

- Whether to adopt Savills' own `2a.` / `2b.` / `0.Budget-Pre` sheet-naming convention wholesale,
  which would rename the year-1 sheet and so require re-agreeing the unchanged-output guarantee. A
  form-owner decision; it changes sheet labels only, not the phase model, the approach or the tasks.
- Whether the stabilised-occupancy scenario variants (25/50/75/100%) become a later capability of their
  own or are dropped. Out of scope here either way; deciding it does not change this change.
