## 1. Transcribe the Required/Optional/Standard reference

- [x] 1.1 Repair the new guideline file with `common_utils_v2.repair_workbook()`, confirm it loads
  (25 sheets, matching the standard form). Verify by listing sheet names.
  **Done 2026-09-14** — repaired copy loads cleanly, 25 sheets, same set as the standard form.
- [x] 1.2 Scan `2. Budget-Management Fund` and `2.2 Common area Fund` column A (NFC-normalised —
  see design.md Context), recording every leaf row's `(code, sheet, requirement_level, row)` into
  `data/master_list_verified/AI_Guideline_Required_Classification.csv` (or a new
  `requirement_level` column on `Costing_Method_Catalogue.csv` — pick whichever is less disruptive,
  note the choice and why). Verify counts match design.md's scoped 86/85 Required, and total row
  counts are sane against the sheets' own leaf-row totals.
  **Done 2026-09-14** — separate CSV chosen over extending the catalogue: `2.2 Common area Fund`
  has its own code namespace (`RA1.A`/`RA2`-style) not covered by `Costing_Method_Catalogue.csv`
  at all, so forcing it in there would mean inventing catalogue rows for codes that catalogue
  never claimed to describe. Counts: `2. Fund` 86 Required/385 Optional/19 Standard (86 exact
  match to design.md's estimate); `2.2 Common area Fund` 83 Required/354 Optional/15 Standard (83
  vs the earlier rough 85 — the difference is the code-presence filter refining an unfiltered
  scan-only estimate from scoping, not a new finding).
- [x] 1.3 Scan any other sheet that carries the same column-A classification (check `0. Info`,
  `A1. Staff cost`, `A2`/`A3`, at minimum) and extend the reference if any do. Verify by listing
  which sheets were checked and which carried the classification.
  **Done 2026-09-14** — checked `0. Info`, `A1. Staff cost`, `A2`, `A3`, plus `A4` (not explicitly
  listed in the task, checked anyway since it's the same position-library shape as A2/A3).
  `A1. Staff cost` carries NONE (0 cells, any column, exhaustively checked). `A2`/`A3`/`A4` carry
  it in column A (same as the fund sheets) — 17/10/3 classified rows respectively, matching the
  canonical-position counts `complete-ai-guideline-remark-coverage` already found. `0. Info`
  carries it too, but in **column M**, not column A (the only sheet with a different
  classification column) — classified by product/line name (`Apartment`, `Shophouse`, parking
  sub-lines), not a `Y`-column-style code. Reference extended to cover all 6 sheets: 982
  classified+coded rows total, 191 of them Required (86 Fund + 83 Common-area + 8 A2 + 7 A3 + 1 A4
  + 6 Info). Script kept at `scratchpad/extract_required_classification.py`.

## 2. Gap analysis

- [x] 2.1 Cross-reference every Required code from task 1 against what
  `generate_project_budget.py` actually writes — `MGMT_FUND_ROWS`, `Costing_Method_Catalogue.csv`
  write-coverage, and any catch-all folding (`EMA15`, `ERM`, etc.). Exclude bare section-header
  codes (SUBTOTAL rows, not leaves). Verify by producing a written list,
  `docs/14-required-line-item-gaps.md`, of every Required leaf code and its current fill status
  (filled directly / filled via catch-all / genuinely zero).
  **Done 2026-09-14** — 119 leaf codes across the two fund sheets. Found, mid-analysis, that most of
  `2.2 Common area Fund`'s share of the gap (60+ codes) was not a missing pricing method at all —
  a template-native pass-through formula chain was dormant because column C was blank. That fix is
  tracked and gated separately (change `activate-common-area-fund-cost-share`, pending PM/finance
  sign-off) and excluded from this change's own figures. See docs/14 for the full breakdown.
- [x] 2.2 For each gapped code, check whether `Costing_Method_Catalogue.csv` already records a
  pricing method (EMA1/2/3/4/7 confirmed already; check the rest). Verify the gap list from 2.1 is
  annotated with "has a method" / "no method found" for each entry.
  **Done 2026-09-14** — see docs/14's "Priced" / "Stated-reason zeros" / "Flagged, not priced"
  tables. `ESS9` and its waste-collection siblings have a real method (QĐ 67/2025) but pricing them
  is owned by the sibling change `complete-ai-guideline-remark-coverage` (B2.6 track) —
  cross-referenced, not duplicated.
- [x] 2.3 **Pause point**: if the gap list is materially larger than the confirmed EMA1-4/7
  example, report back before pricing anything — do not silently expand scope further on your own
  judgment.
  **Done 2026-09-14** — reported (91 zero codes, far larger than EMA1-4/7). User direction: "price
  everything with an existing catalogue method" — accept some may end up priced when a stricter
  per-project applicability filter would have kept them zero, rely on the manual spot-check (task
  6.2) to catch mistakes, rather than doing the full applicability investigation first.

## 3. Price the confirmed EMA gap

- [x] 3.1 Wire `EMA7`'s `headcount × consumption` calculation to `2. Budget-Management Fund!EMA7`'s
  own leaf row. Verify (COM): `EMA7`'s `G`/`AK` are non-zero and match the same calculation the
  OPEX sheet shows.
  **Done 2026-09-14, with a correction**: the "already computed for the analysis workbook's OPEX
  sheet" premise in this change's own proposal/design was checked and found FALSE — no such
  calculation exists anywhere in the codebase (`estimate_opex.py`/`generate_project_output.py`
  grepped clean for "drinking"/"BQL headcount"/the guideline's own 19L/60,000 figures). Wrote it
  new instead, directly from the catalogue's own stated method (BQL headcount x 1 L/person/day,
  19L bottle @ 60,000 VND incl. VAT — no invention, the guideline states the exact formula). BQL
  headcount = every in-house roster position except Security/Cleaning/Landscape, same exclusion
  `fill_staff_cost_sheet`/EMH2 already use. Verified (COM): Wayne Tower EMA7 G = 26,510,532
  (23 BQL headcount), remark states the full arithmetic and source.
- [x] 3.2 Investigate whether an itemized comparable source exists for `EMA1`-`EMA4`. Verify by
  stating clearly which outcome was found before proceeding to 3.3.
  **Done 2026-09-14** — checked `data/generation_A_star_schema/Fact_OPEX.csv`: only one project
  (A&K Tower) has an Administrative Expense row, and it's a single blended figure — no Green
  Skyline row, no itemized EMA1-4 breakdown for any project in this repo. **No itemized source
  found.**
- [x] 3.3a N/A — no itemized source found, so this branch does not apply.
  **Confirmed 2026-09-21** — re-checked against 3.2's own finding before archiving; still no
  itemized source anywhere in this repo. Marked complete as "confirmed not applicable," matching
  3.3b (the branch that did apply) rather than left open.
- [x] 3.3b **No itemized source found**: `EMA1`-`EMA4` stay folded into `EMA15`. Verified
  (openpyxl) `EMA15`'s existing remark already discloses the blend by name and sample size ("A&K
  Tower's real per-m² NFA ratio... n=1... This is the section's general line, not a breakdown...")
  — pre-existing text from change `write-computed-opex-categories-to-deliverable`, no change
  needed to satisfy this requirement.

## 4. Price any further confirmed gap

- [x] 4.1 For each additional gapped Required code from task 2 that has a known, real, sourced
  pricing method, wire it to its own leaf row. Verify per-code (COM): each newly-priced code's
  `G`/`AK` is non-zero and matches its stated method's arithmetic.
  **Done 2026-09-14** for the codes with a real, findable, non-fabricated method:
  - `EMH4` (PCCC training/allowance) — wired as a live formula reference to `'A5. Trợ cấp
    PCCC'!H8`, a real template sheet with its own already-computed total (ND 105/2025 basis).
    Verified (COM): Wayne Tower G = 10,567,717.
  - `ESC12` (environmental incident-response plan) and `ESM25` (wastewater cross-check) — the
    guideline states these figures directly (not a benchmark estimate); hardcoded as real cited
    reference costs, same pattern already used for `ESM2`/`ESM3`/`ESM5`/`ESM8`. Verified (COM):
    Wayne Tower G = 14,000,004 each (the 4 VND is the same monthly-rounding artifact every other
    flat-reference cost in this file already carries).
  - `EMH1` and `ESI1` — genuinely no basis to price (no contract terms; no captured asset value).
    Left at zero, but now carry a stated-reason remark (previously had none at all, which was
    itself a spec gap independent of pricing). See task 4.2.
- [x] 4.2 For each gapped Required code with NO known pricing method anywhere, do not invent one —
  record it as an open item in `docs/14-required-line-item-gaps.md` and report it back rather than
  guessing. Verify the doc clearly separates "priced this change" from "flagged, not priced."
  **Done 2026-09-14** — `docs/14-required-line-item-gaps.md`'s "Flagged, not priced" table: `RP3`,
  `RP5`, `EMH3`, `EMB1`, `EMB4`, `EMO2` (legitimately zero, conditional on `EMO1`), `EMO6`, `EM#`,
  `ESC1`, `ESC2`, `ESC4`, `ESC5`, `ESS9/10/12/17/18/19/23` (cross-referenced to the sibling
  change's waste-collection track), `ESI2`, `ESM6/7/9/10/12/13`, `ESR`, `ES#`, `EE#`, `ERCS1` — 33
  codes, each with the specific reason no real figure was written.

## 5. Verification

- [x] 5.1 Add `check_required_line_items(paths)` to `verification/checks.py`, reading the task 1
  reference, checking every Required code's realized figure is non-zero or carries a stated-reason
  remark. Verify it runs standalone against a generated deliverable and correctly flags an injected
  gap (same negative-test pattern `complete-ai-guideline-remark-coverage` used).
  **Done 2026-09-14** — enforces on `2. Budget-Management Fund` only (`2.2 Common area Fund` is
  scanned and reported as notes, never failed — its own completeness is entirely gated on the
  separate change `activate-common-area-fund-cost-share`; failing this run on a sheet this change
  doesn't own would conflate two changes' completion criteria). Standalone positive test: 0/119
  differences on Wayne Tower (81 pass on the enforced sheet, 5 not-found noted, 33 pending on `2.2`
  noted). Negative test: blanked `RP3`'s remark on a copy, check correctly failed and named it.
- [x] 5.2 Wire the check into `verify.py` as a new section (5f). Verify `python
  verification/verify.py` runs it.
  **Done 2026-09-14** — caught a real syntax bug (an apostrophe inside a single-quoted string)
  during the import-check pass, fixed before it ran. `verify.py`'s own section 4 (baseline) FAILs
  first on pre-existing, unrelated drift (see measured-effect.md), so section 5f is not reached in
  a live `verify.py` run today — verified directly via the standalone script instead (5.1's own
  positive/negative tests). Will run as part of the normal flow once that unrelated baseline issue
  clears.
- [x] 5.3 Record the moved figures' baseline **only after task 6.2 sign-off** —
  `deliverable_baseline.json` (and `baseline.json` if the analysis workbook's own figure moved
  too). Verify `verify.py` PASSes on the following run.
  **Done 2026-09-21** — recorded jointly with `complete-ai-guideline-remark-coverage`'s `ESS9` (one
  combined re-record, standard sample, reason naming both changes). Only `deliverable_baseline.json`
  — the analysis workbook is untouched by this change (confirmed in `measured-effect.md`).
  `verify.py` re-run: **PASS end to end**.
- [x] 5.4 (added, not in the original plan) — full line-by-line, sheet-by-sheet audit at the
  user's explicit request, run directly against `checks.py` (bypassing `verify.py`'s early exit on
  the unrelated baseline drift) on both the standard verification sample and Wayne Tower.
  **Done 2026-09-14** — found and fixed one real regression from this change's own work:
  `check_summary_reconciles`'s assertion (d) compared `'1. Summary'!H22` (the whole EMH section)
  against only `EMH2`'s own derivation (`A1 payroll + top-up`), which was correct only while every
  other EMH code was zero. Adding `EMH4` broke that assumption — H22 correctly grew to include it,
  but the check's `expected` didn't, so it started failing on a change that was actually correct.
  Root-caused (not just silenced): the check now adds every other EMH-family leaf's own `G` to the
  expected total, so it stays correct if `EMH1`/`EMH3` are ever priced too. Negative-tested (broke
  `EMH4`'s frequency on a copy — the check correctly caught 5 real differences, including the fixed
  assertion). **After the fix, every check passes cleanly with 0 differences** on both the
  standard sample (`check_revenue_agreement`, `check_benchmark_reconciles`, `check_remark_content`
  52/51 assertions, `check_summary_reconciles` 506 rows, `check_required_line_items` 81 rows,
  `check_sheets`, `check_artifacts`) and Wayne Tower (`check_summary_reconciles` 506 rows,
  `check_required_line_items` 81 rows, `check_remark_content` 52 rows). `check_formula_errors`:
  zero new Excel errors introduced on either project (53/2355 all pre-existing/inherited).
  Independently verified `'2.2 Common area Fund'`'s own internal arithmetic directly (not covered
  by `check_summary_reconciles`, which only reads `2. Fund`): 291 coded rows, every `G` matches its
  own `AK`, every `SUBTOTAL` roll-up matches the sum of its own leaf range — 0 mismatches, confirms
  that sheet is internally self-consistent even though its cross-fund accounting treatment is
  still pending separate sign-off. The standard sample's own `check_deliverable_figures` baseline
  diff (666,797,405 VND) decomposes cleanly into the two already-known pending changes — 65,078,257
  is this change's own four new codes (confirmed identical on both projects), the remainder is the
  separately-paused `reconcile-summary-with-detail-sheets` EMH2/Reception rework manifesting at its
  own (project-specific) size on this fixture. Nothing unexplained.

## 6. Measure, spot-check, sign-off

- [x] 6.1 Generate the deliverable for Wayne Tower. Record the year-one surplus movement, split by
  newly-priced code. Write the table into the change's `measured-effect.md`.
  **Done 2026-09-14** — surplus 7,025,863,071 -> 6,960,784,814 VND (**DOWN 65,078,257**, i.e. the
  surplus falls by that amount once these previously-undisclosed costs are shown; an earlier draft
  of this note had the "before" figure computed with the wrong sign — corrected during review, see
  `measured-effect.md`). Full per-code breakdown in `measured-effect.md`. Green Skyline not measured — its own real budget doesn't carry
  itemized `EMA7`/`EMH4`/`ESC12`/`ESM25` figures to compare against directly, and the four new
  lines are guideline-cited/template-formula sourced, not comparable-derived, so a Green Skyline
  comparison wouldn't add independent evidence here the way it did for the original EMA backtest.
- [x] 6.2 **Manual spot-check** (project rule — new pricing logic): by hand confirm each
  newly-priced code's figure against its stated source and method. Record the checks and the
  project(s) used.
  **Done 2026-09-14** — all four confirmed by hand against their stated source (arithmetic
  reproduced to within the codebase's own standard monthly-rounding artifact). See
  `measured-effect.md`'s own "Manual spot-check" section.
- [x] 6.3 Present the measured movement to the Head of PM; capture the sign-off in the change notes
  and `docs/05-decisions.md` before archiving.
  **Provisionally signed off 2026-09-21** — explicit instruction: "assume it's approved, commit
  it." Not the actual Head-of-PM conversation this change's own design calls for. See
  `docs/05-decisions.md`'s new entry (shared with `complete-ai-guideline-remark-coverage`).

## 7. Docs

- [x] 7.1 Update `docs/09-template-map.md`'s EMA note (currently: "EMA15 — catch-all for the whole
  EMA section") to reflect the new per-code reality. Update `docs/05-decisions.md` and
  `docs/project-status.md`.
  **Done 2026-09-14** for `docs/project-status.md` (new dated section at the top, see there) and
  `docs/14-required-line-item-gaps.md` (the full gap analysis, this change's own primary doc
  artifact). **`docs/09-template-map.md`'s EMA note and `docs/05-decisions.md`'s formal decision
  entry completed 2026-09-21**, now that 6.3's provisional sign-off has landed — the template-map
  table gained rows for `EMH4`/`EMA7`/`ESC12`/`ESM25` (plus `ESS9` from the sibling change) and a
  note that `EMA15`'s catch-all now excludes `EMA7`. `docs/project-status.md` updated again in the
  same pass. Previously held until 6.3's actual sign-off lands — writing "signed off" language before
  a human had signed off would have misrepresented the state; both had been drafted and ready to add
  the moment sign-off was
  recorded.
