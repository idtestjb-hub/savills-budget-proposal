## Context

See proposal.md — Why. Facts established during scoping, so implementation does not need to
re-derive them:

- The new guideline file (`docs/AI Guideline - 2027 Resi Budget Form (IT team)  1.xlsx`) needs
  `common_utils_v2.repair_workbook()` before openpyxl can load it — the same OneDrive zip-artifact
  corruption every other guideline copy in `docs/` has needed (see
  [[project_budget_agent_onedrive_corruption]]).
- The Required/Optional/Standard classification lives in **column A** on `2. Budget-Management
  Fund` and `2.2 Common area Fund`, one row per code (leaf and section-header rows both carry a
  classification — only leaf rows, the ones with a `Y`-column code, matter for pricing).
- **Reading Vietnamese text from this file needs NFC normalisation on both sides of any string
  comparison** — `ws.cell(...).value == 'Bắt buộc/Required'` returns `False` even for a cell that
  visibly reads exactly that, because the source file's diacritics are NFD-composed and a Python
  literal typed directly is NFC. Every scan in this change MUST go through
  `unicodedata.normalize('NFC', ...)` on both the cell value and the comparison literal — this bit
  the scoping work once already (0 matches until fixed, 88 after). Match the existing project
  convention (`input_labels.normalise()`, `checks._nfc()`) rather than reinventing it.
- Scoped counts on the new guideline file (NFC-normalised, leaf rows with a `Y`-column code only):
  **86 Required codes on `2. Budget-Management Fund`**, **85 on `2.2 Common area Fund`**. Most
  families already have a pricing method and are already filled (RM.AP, RO2-4, EMH1-4, ESS1/4/16,
  EEW/EEE/EED, EN1-3, and more) — the definitive gap list is task 1's job, not resolved here.
- Confirmed gap: `EMA1`/`EMA2`/`EMA3`/`EMA4`/`EMA7` are Required and currently always zero — folded
  into `EMA15`'s catch-all instead of priced individually. `Costing_Method_Catalogue.csv` already
  records a method for each (`benchmark-or-package` EMA1, `benchmark-by-comparable` EMA2-4,
  `headcount-x-consumption` EMA7) — the method is known, it just was never wired to its own leaf.
- `estimate_opex.py`'s admin-expense ratio is sourced from **A&K Tower alone** (its own docstring:
  "derived from A&K Tower ALONE (n=1)") — A&K's real budget gives one blended admin figure, not
  itemized sub-categories, which is *why* EMA1-4 never got individual treatment: the only source
  ever consulted doesn't have the detail.
- Real evidence a second, itemized source may exist: `reports/Green Skyline - Backtest vs Real
  Budget.xlsx`'s "Line-by-Line" sheet shows the pipeline's EMA output as 0 against Green Skyline's
  real Administrative Expense of 105,625,263 VND. That comparison is at the aggregate `EMA` level
  only (the backtest file doesn't itself show whether Green Skyline's real source data was
  itemized into EMA1-4/7) — task 1 needs to check Green Skyline's own underlying data (if available
  in this repo, e.g. `data/generation_A_star_schema/Fact_OPEX.csv` or a similar extract) for actual
  itemized figures before assuming they exist. If no itemized source is found for a given Required
  code, D2's fallback (blend + disclose) applies instead of inventing detail.

## Goals / Non-Goals

**Goals:**
- A definitive, recorded gap list (Required codes vs what the pipeline currently fills).
- Every Required code with a findable pricing method (existing catalogue entry, or a real itemized
  comparable source) filled on its own leaf row.
- A standing "prefer itemized over blended" principle, applied concretely to EMA and left as a
  recorded pattern for future sourcing work.

**Non-Goals:**
- Re-deriving or second-guessing the guideline's own Required/Optional/Standard classification —
  transcribe it as given.
- Inventing a pricing method for a Required code that has none anywhere (catalogue, comparable
  data, or otherwise) — flag it back to the user instead.
- Re-doing `complete-ai-guideline-remark-coverage`'s three tracks (`0. Info`, `A2`/`A3`, `B2.6`) —
  that change stays separate, currently paused mid-`B2.6`.
- Touching Security/Cleaning/Landscape's outsourced-contract pricing (`outsourced-service-costs`)
  — a related but distinct sourcing concern, not in scope here.

## Decisions

### D1 — Transcribe the Required/Optional/Standard classification into a new reference CSV

`data/master_list_verified/AI_Guideline_Required_Classification.csv` (or extend
`Costing_Method_Catalogue.csv` with a `requirement_level` column — decide at implementation time
based on which is less disruptive to the existing 111-row file). Columns: `code`, `sheet`,
`requirement_level` (`Required`/`Optional`/`Standard`), `row` (source row on the guideline, for
re-verification if the guideline updates again). NFC-normalised at read time, matching the trap
noted in Context.

- **Why a separate reference, not inferred at runtime from the guideline file directly**: the
  pipeline should never need the guideline `.xlsx` itself at generation time (same reason
  `Costing_Method_Catalogue.csv` exists instead of re-reading the guideline every run) — a
  transcribed CSV is the recorded, independently-versioned contract.

### D2 — Gap analysis: cross-reference Required codes against actual pipeline output

Task 1's own deliverable: for every Required code in the D1 reference, check whether
`generate_project_budget.py` writes to its own leaf row (directly, via `MGMT_FUND_ROWS`, or via any
other mechanism) versus only ever reaching it through a catch-all fold. Produce a written list
(e.g. `docs/14-required-line-item-gaps.md`, following this project's own `docs/09`-style
convention) rather than only a mental model — this is the artifact task 2+ implements against.

- Known false-positives to exclude while building this list: bare section-header codes (`RO`,
  `EMH`, `EMA`, etc. — `SUBTOTAL()` formulas, not leaves; same distinction
  `reconcile-summary-with-detail-sheets` D5 already made for its own reconciliation check) and any
  code explicitly conditional on project features the current project lacks (pool, garden).

### D3 — EMA1-4/7: price from the itemized source where one exists, else disclose the blend

For `EMA7` (Drinking water): wire the existing `headcount-x-consumption` calculation (already
computed for the analysis workbook's OPEX sheet) to also write `EMA7`'s own leaf row on the
deliverable — no new pricing logic, just a second write target.

For `EMA1`-`EMA4`: task 1 must first determine whether an itemized comparable source actually
exists (Green Skyline's own data, re-checked properly — not assumed from the backtest's aggregate
number alone). Two outcomes:
- **If found**: price EMA1-4 from that itemized source, write each to its own leaf, and update
  `estimate_opex.py`'s admin-expense sourcing note to record which source backs which code.
- **If not found**: EMA1-4 stay folded into `EMA15`'s catch-all as today, but `EMA15`'s remark
  SHALL explicitly disclose "sourced from a single blended comparable (A&K Tower); no itemized
  breakdown available" — satisfying the "stated reason" branch of the verification requirement
  rather than leaving the gap unexplained. This is NOT re-opening `EMA1-4` as still-zero-but-hidden
  — the disclosure requirement still applies, it is just carried on `EMA15` instead of on each
  individual code, since no individual figures exist to write.

- **Why not force an itemized breakdown from a single blended number**: splitting one real figure
  into four invented sub-figures (e.g. by an assumed ratio) would look precise while being no more
  informed than the blend — worse, since it hides its own approximation behind decimal-looking
  numbers. Disclosure is the honest fallback design.md's own principle (throughout this project)
  consistently prefers over a fabricated split.

### D4 — Verification: completeness check against the D1 reference

New `check_required_line_items(paths)` in `verification/checks.py`, mirroring the shape of
`check_summary_reconciles`/`check_remark_content` (COM or openpyxl as appropriate — likely
openpyxl, since this only reads literal written values, not formulas needing recalculation). Reads
D1's reference, checks each Required code's `G`/`AK` (or the deliverable's realized figure) is
non-zero OR carries a stated-reason remark. Wired into `verify.py` as a new section.

## Risks / Trade-offs

- **[The real gap list is larger than the confirmed EMA1-4/7 example]** → task 1 produces the
  definitive list before any pricing work starts; if it is much larger than expected, stop and
  report back rather than silently expanding scope further.
- **[No itemized second source actually exists for EMA1-4]** → D3's disclosure fallback; the
  Green Skyline backtest's aggregate number is evidence a real gap exists, not proof an itemized
  breakdown is available to fix it precisely.
- **[Figure movement is larger than any single change so far this session]** → explicit measure +
  Head-of-PM sign-off gate (proposal.md Impact), same pattern as `reconcile-summary-with-detail-
  sheets`; do not archive without it.
- **[Confusion with the still-open `complete-ai-guideline-remark-coverage` change]** → kept
  strictly separate per the user's own direction; no shared code changes, no shared tasks.

## Migration Plan

1. Build the D1 reference CSV; verify NFC-normalised counts match what was scoped here (86/85).
2. Build the D2 gap list; report it before pricing anything (a natural pause point for user
   confirmation if the list is much larger than the EMA example already found).
3. Implement D3 for the confirmed EMA gap; re-run for any further gap D2 surfaced with a known
   method.
4. Add D4's verification check; expect `verify.py` to FAIL on the moved figures (baseline not yet
   re-recorded), same migration shape as every other figure-moving change here.
5. Measure on Wayne Tower (and Green Skyline if its real comparable data supports checking against
   it directly); present to the Head of PM.
6. Re-record baselines with the reason; `verify.py` passes; archive.
7. Rollback = revert the code; baselines revert with it.

## Open Questions

- Whether `EMA1`-`EMA4` end up itemized or stay a disclosed blend depends on task 1's finding
  (D3) — genuinely unknown until that investigation runs, and does not change the spec (both
  outcomes are compliant with the "or a stated reason" requirement) or the task breakdown's shape.
