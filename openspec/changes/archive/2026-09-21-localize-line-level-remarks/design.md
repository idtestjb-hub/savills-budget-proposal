## Context

See `proposal.md` for motivation and the full 50-code inventory. Grounding facts:

- Every line-level remark passes through `_write_remark(ws, row, remark)` (generate_project_budget.py
  ~line 468), which appends the VAT sentence via `_append_vat()`/`_vat_sentence()`. That plumbing is
  language-agnostic and unchanged by this proposal.
- The remark **text itself** is produced at each fill call site — `_opex_remark()` (the OPEX/energy
  block), the inline strings passed to `_write_even_monthly_row()`/`_write_ramped_row()`/
  `_write_year1_lump_row()` throughout `fill_management_fund_sheet()`, and the `_FLAGGED_NO_METHOD`
  dict's per-code `reason` strings. There is no single choke point — 50 separate call sites each carry
  their own English string.
- A Vietnamese wording pattern for this exact content already exists and is proven correct for three
  of these codes: `_recipe_narrative()` (generate_project_budget.py ~line 691) composes Vietnamese text
  for `EEW`/`EEE`/`EED` at the `1. Summary` level, from the same `estimate_opex()` output `_opex_remark`
  already reads (`qty`, `unit`, `tariff`, `tunit`, `as_of`). Today the two functions independently
  produce different-language text from the same numbers.
- `_recipe_narrative()` runs after `written` (the `{code: (row, value, name)}` map) is built, i.e.
  after `fill_management_fund_sheet()` has already called `_opex_remark()` and written the line-level
  cell. `_opex_remark()` itself needs only `project` and `estimate_opex()`'s output — it does not need
  `written` — so there is no ordering obstacle to sharing wording between the two call sites.
- `check_remark_content` (verification/checks.py, from `apply-guideline-remark-model`) already has a
  Vietnamese-content assertion for `1. Summary` narratives (a diacritic-presence check); the same
  primitive extends to line-level cells.

## Goals / Non-Goals

**Goals**
- Every line-level remark the pipeline writes reads in Vietnamese, matching the real deliverable's
  convention and the already-Vietnamese `1. Summary` narratives.
- Where a Vietnamese line-level narrative and a Vietnamese summary-level narrative describe the same
  single figure (the `EEW`/`EEE`/`EED` case, and any other 1:1 code), they SHALL be produced from one
  shared wording function — not hand-kept in sync as two copies.
- `Costing_Method_Catalogue.csv` and other internal filenames never appear in client-facing cell text.

**Non-Goals**
- No figure, zero/non-zero status, or pricing-method change for any code — wording only.
- No change to the VAT-sentence mechanism (`_write_remark`/`_append_vat`/`_vat_sentence`) — already
  Vietnamese, already shared, untouched.
- No change to `1. Summary`'s existing composed narratives beyond what naturally follows from sharing
  a wording function with a line-level counterpart (the visible summary text should not change for
  `EEW`/`EEE`/`EED`, since the shared function's output IS today's summary wording).
- Multi-year / pre-opening narrative variants — a separate proposal
  (`add-multiyear-preopening-budget-phases`).

## Decisions

### D1 — One Vietnamese wording function per code family, called from both the line-level fill and the summary composer where both exist

For `EEW`/`EEE`/`EED`: extract the Vietnamese sentence currently inlined inside `_recipe_narrative()`
into a standalone helper, e.g. `_energy_narrative_vi(key, project) -> str`, taking only what
`estimate_opex()` already provides. `_opex_remark()` calls it directly (replacing its English branch);
`_recipe_narrative()` calls the same helper instead of its inline copy. One wording, two call sites,
no drift possible.

For every other code in the 50-item inventory, there is no existing summary-level Vietnamese version
to reuse (most PART-1 totals are roll-ups, not 1:1 with a single line), so this is new authoring: a
Vietnamese template per code, following the same fill-in-the-blanks pattern as `_recipe_narrative()`
D2's recipe shapes (the AI Guideline's own worked wording where the guideline names one; a plain
factual Vietnamese description of the computation otherwise).

### D2 — Flagged-zero remarks: state the reason, drop the file citation

The `_FLAGGED_NO_METHOD` dict's `reason` strings and the other ad hoc zero-with-reason remarks
(`RP3`, `EMH1`, `EMB1`, etc.) are rewritten in Vietnamese with the same meaning, minus any reference to
`Costing_Method_Catalogue.csv` or other internal file/module names. Where the code comment above each
`_FLAGGED_NO_METHOD` entry already documents the internal reasoning for engineers, that comment is
left in English and in place — only the string written into the workbook cell changes. This keeps the
engineering audit trail intact while keeping the client-facing cell professional.

### D3 — `check_remark_content` gains a line-level sweep

Extend the existing Vietnamese-content assertion (already used for `1. Summary`) to also run over
every non-blank `T` cell on `2. Budget-Management Fund` and `2.2 Common area Fund`, and add a second
assertion that no such cell's text contains `.csv`, `.py`, or a small denylist of internal filenames
seen in the current codebase (`Costing_Method_Catalogue`, `generate_project_budget`,
`estimate_opex`). Both assertions are structural (presence of Vietnamese characters / absence of a
filename substring), not phrasing checks — matching the existing check's own "presence of parts, not
exact wording" philosophy.

## Risks / Trade-offs

- **[Vietnamese wording is wrong, unnatural, or uses incorrect financial/legal terminology across 50
  codes]** → same mitigation as the original narrative work: a Head-of-PM read-aloud review against a
  real project's generated output (tasks §4) before this is considered done; wording lives in one
  place per code, easy to revise without touching figures.
- **[Authoring 50 Vietnamese templates is a much larger content task than the original 3-code
  estimate]** → tasks.md batches them by section (revenue, EMH/EMA/EMB, ESC/ESS/ESI/ESM, EN, EEW/EEE/
  EED, contingency/rollup rows) so review can happen incrementally rather than as one 50-item review.
- **[A future code added to `_FLAGGED_NO_METHOD` reintroduces an English or file-citing remark]** →
  `check_remark_content`'s new assertions run on every verification run, not just at ship time, so a
  regression is caught immediately rather than discovered on the next real audit.
- **[Sharing `_energy_narrative_vi` between line-level and summary-level changes today's summary
  wording for EEW/EEE/EED]** → it shouldn't: the extraction moves existing text verbatim into a
  function, it does not rewrite it. Verified by the check in tasks.md that the summary-level narrative
  is byte-identical before/after the refactor.

## Migration Plan

Additive/rewording, display-only. Deploy = ship the code; the next `run.py` writes Vietnamese line-level
remarks. No baseline re-record (verify.py's figure-comparing checks are untouched; only
`check_remark_content` gains scope). Rollback = revert the code; `check_remark_content`'s two new
assertions are removed with it. Manual spot-check (tasks §4): generate for one real project, read every
line-level remark aloud in Vietnamese, confirm none names an internal file and each states the right
figure/reason for that project.
