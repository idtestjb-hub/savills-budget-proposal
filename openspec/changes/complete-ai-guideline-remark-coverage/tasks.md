## 1. `0. Info` per-product remark

- [x] 1.1 Add "Area basis / drawing reference" (free text) and "confirmed as of year" fields to
  `build_project_input_form.py`'s Project Info sheet, appended after every existing field (no
  row-shift risk). Verify by generating a form and confirming every existing field still reads at
  its previous cell.
  **Done 2026-09-14** — added at rows 42/43 (section header row 41). Caught and fixed a real bug
  before it shipped: the section header text and the field label both normalised to the same
  `input_labels.py` lookup key (`normalise()` cuts at the first `(`/`—`, and "AREA BASIS / DRAWING
  REFERENCE (...)" vs "Area basis / drawing reference — ..." collided) — raised `AmbiguousLabel`.
  Reworded the header to "PRODUCT AREA CITATION (...)". Also added "Number of Pools" (row 45, not
  in the original task list — added on direct user request while testing this task) with the same
  no-collision check. Verified via a redirected-to-temp-path form generation (the production
  `reports/Project_Budget_Input.xlsx` was accidentally overwritten by an earlier un-redirected test
  run during this task — user reviewed it and explicitly said not to restore it; every test since
  uses a temp `OUT`/`FINAL_OUT`).
- [x] 1.2 Read the new field(s) in `read_input()`, guarded by `SheetLabels.has(...)` so an existing
  intake workbook without the field still reads cleanly as blank. Verify against Wayne Tower's real
  input file (untouched, read-only) — confirm it reads as blank without error.
  **Done 2026-09-14** — `area_basis`, `area_basis_year`, `pool_count` all read guarded. Verified
  against `reports/Project_Budget_Input_PRE_ROLES_2026-09-09.xlsx` (older layout, all three read as
  `None`) and against `reports/EXAMPLE - Wayne Tower Thu Thiem.xlsx` (real Wayne Tower data,
  read-only, hash-verified untouched before/after) — both read cleanly.
- [x] 1.3 In `build_budget()`, write each priced `0. Info` product row's remark: the entered basis +
  year when present, else "area is PM-supplied" with no invented citation. Verify (openpyxl):
  every row in `_INFO_FEE_ROWS` with a non-blank area has a non-blank remark.
  **Done 2026-09-14** — written to `0. Info!G8:G11` inside the existing `_INFO_FEE_ROWS` loop, using
  `_PRODUCT_VI_LABEL` for the per-product name. Verified both branches: blank `area_basis` (Wayne
  Tower backup, read-only) gives the PM-supplied fallback on every priced row; a filled `area_basis`
  ("thuyết minh TKTC", year 2026) composes "Diện tích căn hộ theo thuyết minh TKTC. Cập nhật theo
  thông số Chủ Đầu Tư cung cấp năm 2026." — matching the guideline's own worked-example pattern.

## 2. `A2`/`A3` canonical position descriptions

- [x] 2.1 Transcribe the AI Guideline file's own A2 (Security, ~20) and A3 (Cleaning, ~10)
  canonical positions — name, VI+EN duty description, applicability condition — into
  `data/master_list_verified/AI_Guideline_Canonical_Positions.csv`, read directly from
  `docs/AI Guideline - 2027 Resi Budget Form (IT team).xlsx`, not approximated from docs/12's two
  quoted examples. Verify row count matches what the guideline sheet actually lists (~20 + ~10).
  **Done 2026-09-14** — read from the `__repaired` copy (the OneDrive-corruption-safe one), columns
  D(name)/I(note)/V(guide) on A2, D(name)/L(note)/Y(guide) on A3. 27 rows total: 17 Security + 10
  Cleaning (A1 appears twice on Security — day-shift "Đội trưởng" and night-shift "Ca trưởng" Team
  Leader variants, both genuinely code A1 in the source). VI/EN split on `\n` for descriptions
  (verified via raw JSON dump, not the terminal's newline-collapsed display) and ` / ` for names;
  3 names had a `/` inside the Vietnamese phrase itself ("ra/ vào" = "in/out") that broke a naive
  first-`/` split — fixed with an explicit (sheet, row) override after checking the raw cell values,
  not a string-match override (which silently failed once on an ellipsis/whitespace mismatch).
  Script kept at `scratchpad/extract_canonical_positions.py` for re-running if the guideline updates.
- [x] 2.2 **REVISED after 2.1's own verification step revealed the real state** — originally:
  "add a confidence-gated name-matching helper... write the matched canonical description as the
  line-level remark." Superseded: checking `generate_project_budget.TEMPLATE_PATH`'s `A2`/`A3`
  sheets directly (not the CSV, the actual live deliverable template) found every one of the 27
  canonical positions already carries its duty description as the template's own shipped content —
  `note_present=True` on all 27 rows, exhaustively checked, none missing. There is nothing to match
  or write. Design.md D2, the `deliverable-remarks` spec delta, and `docs/12` corrected to record
  this instead of the original (stale-comparison-based) plan — see task 2.3 below for what replaced
  the matching/writing work.
- [x] 2.3 (replaces the original "write matched description" task) Add a verification check
  confirming every canonical position in `AI_Guideline_Canonical_Positions.csv` still carries a
  non-blank duty description on the generated deliverable's `A2`/`A3` — guards against a future
  Savills template revision silently dropping the text, which is the real risk now that nothing in
  this pipeline writes it. Verify: inject a blank into one row on a scratch copy and confirm the
  check fails and names that row; confirm it passes clean on an unmodified Wayne Tower generation.
  **Done 2026-09-14** — added to `check_remark_content` (not a separate function — one coherent
  "remark content" check, matching the spec's single requirement covering both `0. Info` and
  `A2`/`A3`). Reads `AI_Guideline_Canonical_Positions.csv` by `row` + `category`, checks
  `A2!col I <row>` / `A3!col L <row>` directly. Clean pass on Wayne Tower (51 assertions, 0
  differences: 24 from the existing checks + 4 `0. Info` products + 27 canonical positions,
  including 2 Security `A1` rows since the code repeats). Negative test: cleared `A2!I10` on a
  scratch copy (openpyxl gotcha caught along the way — `ws.cell(row, col, value=None)` does NOT
  clear a cell, it's indistinguishable from "value not given"; the correct clear is
  `ws.cell(row, col).value = None`) — check correctly failed, naming exactly that row.

## 3. `B2.6` waste-collection costing

- [x] 3.1 Read `B2.6`'s real QĐ 67 unit prices (collection/transport/treatment) from the guideline
  source document. Verify the three components sum to a stated total the guideline itself shows, if
  one is given.
  **Done 2026-09-21** — read directly from `docs/AI Guideline - 2027 Resi Budget Form (IT team)
  __repaired.xlsx`, sheet `B2.6 Rác sinh hoạt (QD67)`: collection 485.97, transport 180.07,
  treatment 420.45 VND/kg (QĐ 67/2025/QĐ-UBND) — sum 1,086.49 VND/kg, matching design.md D3.
  Confirmed the same three prices are also present on the live `TEMPLATE_PATH` form (not just the
  docs/ source copy). Apartment 2.63 kg/unit/day (note and formula instruction agree). Shophouse:
  the sheet's own note text (~3.41kg) and formula instruction (2.63×1.5=3.945kg) disagree — used
  the formula-instruction basis per design.md D3's PM decision, disclosed in the written remark.
- [x] 3.2 Locate `B2.6`'s target row/code on `2. Budget-Management Fund` by scanning column Y for a
  waste-collection code (not a bare row number) — if none exists, stop and report back rather than
  invent one. Verify with `assert_row_code`-style guard, same pattern as every other leaf write in
  this pipeline.
  **Done 2026-09-21** — column Y alone gives no clue (codes are short, unlabelled), so searched
  every sheet/column of the real template for "rác"/"waste"/"CTRSH". Found row 153 = `ESS9`
  ("Normal garbage collection / Thu gom rác sinh hoạt"), with column T carrying the guideline's own
  note naming Quyết định 67/2025 directly at that row. Also found the code already had a
  `_FLAGGED_NO_METHOD` placeholder explicitly cross-referencing this change — confirming ESS9 as
  the intended target independently. Added `waste_collection: 153` to `MGMT_FUND_ROWS` /
  `MGMT_FUND_EXPECTED_CODE`, which gives it the standard `_assert_leaf_rows` guard automatically
  (same mechanism every other leaf write uses, no new guard code needed).
  **Found and fixed in passing**: the existing `_FLAGGED_NO_METHOD` dict also claimed ESS10, ESS12,
  ESS17, ESS18, ESS19, ESS23 were all "the same QĐ 67/2025 tariff family as ESS9." Checked each
  row's real column-Z label: true only for ESS10 (hazardous garbage, a different waste stream) and
  ESS19 (garbage bags, a real waste-adjacent consumable) — ESS12 is Pest control, ESS17 is Planting
  cost, ESS18 is Toiletries, ESS23 is outsourced Pool staff, all unrelated to waste. Corrected all
  six reasons (EN + VI) so the generated deliverable stops citing a wrong, misleading reason on
  four real cost lines.
- [x] 3.3 Compute and write `apartment_units × 2.63 kg/unit/day × 365 × (sum of the 3 QĐ 67 unit
  prices)` to that row for projects with apartment units; leave at 0 otherwise. Verify (COM) the
  written `G`/`AK` values match the formula's own arithmetic.
  **Done 2026-09-21, on a MONTHLY basis, not the ×365 this task text assumed** — the guideline's own
  instruction is explicit ("units × 2.63 × 30 ngày"), matching design.md D3's correction and every
  other Monthly-frequency row in this sheet; annual = monthly×12 passed into the existing
  `write_even_monthly()` helper (same pattern as `drinking_water`/`env_incident_plan`). Also sums
  Shophouse (units × 3.945 kg/unit/day × 30 × 1,086.49) when the project has shophouse units — the
  task text only named Apartment, but the guideline's own B2.6 sheet prices both product types.
  Verified via isolated run (`verification/run_workflow.py`) against the real Diamond Skyline input
  (Wayne Tower's own example file no longer exists in this repo — see task 5.1's note): full Excel
  recalculation confirms G153/AK153 = 624,928,404 VND/year, matching 600 apartment units × 2.63 ×
  30 × 1,086.49 + 5 shophouse units × 3.945 × 30 × 1,086.49 by hand. `check_formula_errors` reports
  0 new errors.
- [x] 3.4 Write `B2.6`'s remark stating the weight assumption and citing QĐ 67. Verify (openpyxl)
  the remark text contains both the weight figure and "QĐ 67" (or "67/...", whatever citation form
  the guideline itself uses).
  **Done 2026-09-21** — remark states both weights (Apartment 2.63 kg/unit/day, Shophouse 3.945),
  all three QĐ 67 unit prices, cites "Quyết định 67/2025/QĐ-UBND", and discloses the note-vs-formula
  discrepancy on the Shophouse weight. Confirmed present via the isolated run's output file.

## 4. Verification

- [x] 4.1 Extend `verification/checks.py`'s remark-content check (or add a sibling check) for:
  every priced `0. Info` product has a remark; every canonical-matched `A2`/`A3` position carries
  its canonical description; `B2.6` has a remark whenever it has a figure. Verify it runs as part
  of `verify.py` and fails correctly when a required remark is missing (inject a gap and confirm).
  **Done 2026-09-21** — the `0. Info` and `A2`/`A3` checks already existed (tasks 1.3/2.3); added
  the `B2.6`/ESS9 one now: checks column F (a literal the pipeline writes directly — NOT column G,
  which is a formula unevaluated under this function's own `data_only=False` load, an early attempt
  caught this the hard way when a negative test silently passed) is non-zero implies column T is
  non-blank. Negative-tested: cleared T153 on a scratch copy, check correctly failed naming exactly
  that row; clean pass confirmed on the unmodified generation.
  **Found and fixed in passing, in the same spirit as the 2026-09-14 EMH2/EMH4 precedent**:
  `check_summary_reconciles`'s own `_SUMMARY_RECONCILE_ROWS` table matched Summary row 31 to fund
  code `ESS16` alone — but that row's real Excel formula is `AK144(ESS section) - H29(ESS1) -
  H30(ESS4)`, i.e. everything in the ESS section except Security and Cleaning. The narrow matcher
  only ever produced the right total by coincidence, because every other ESS code (including ESS9)
  was zero until now. Pricing ESS9 surfaced a real, reproducible `check_summary_reconciles` FAIL
  (888,928,404 vs 264,000,000 — exactly the new ESS9 figure). Fixed by extending
  `_fund_code_match()` with an exclusion syntax (`!X`/`!=X`) and correcting the matcher to `('ESS',
  '!=ESS1', '!=ESS4')`. Re-verified: `check_summary_reconciles` now passes clean (0 differences,
  including the previously-failing row).
- [x] 4.2 Record `B2.6`'s new figure in `verification/baselines/deliverable_baseline.json` as a
  fresh addition (not a correction) — **only after task 5.2 sign-off**. Verify `verify.py` PASS on
  the following run.
  **Done 2026-09-21** — recorded jointly with `fill-guideline-required-line-items`' own newly-signed
  figures (one combined re-record, standard sample), reason naming both changes. Also added `ESS9`
  to `verification/method_coverage.py`'s `METHOD_VERDICTS` (a registry this change's own work
  predates) — `verify.py` section 6 failed once on "written with no recorded verdict: ['ESS9']"
  before this. `verify.py` now **PASSes end to end**, all 6 sections, including the new
  `ESS9`-remark-presence check and the `check_summary_reconciles` H31 fix.

## 5. Measure, spot-check, sign-off (B2.6 only — tracks 1/2 are display-only, no figure moves)

- [x] 5.1 Generate the deliverable for Wayne Tower and record `B2.6`'s VND amount and the year-one
  surplus impact. Write the figure into the change's `measured-effect.md`.
  **Done 2026-09-21, on Diamond Skyline, not Wayne Tower** — Wayne Tower's own example workbook no
  longer exists anywhere in this repo (checked `Budget_Agent/reports/` directly; only the current
  live project, Diamond Skyline, is present). Measured instead on Diamond Skyline's real, live
  input (isolated run, production untouched, hash-verified before/after): **ESS9 = 624,928,404
  VND/year** (52,077,367 VND/month; 600 apartment units + 5 shophouse units). Year-1 surplus moves
  by the same amount, since this is a pure new-cost addition with nothing else depending on it —
  confirmed via `check_summary_reconciles`'s own H46/H54 derivation, both consistent before and
  after the H31 fix above. See `measured-effect.md` for the full write-up.
- [x] 5.2 Present the new `B2.6` figure to the Head of PM; capture the sign-off in the change notes
  and `docs/05-decisions.md` before archiving.
  **Provisionally signed off 2026-09-21** — explicit instruction: "assume it's approved, commit
  it." Not the actual Head-of-PM conversation this change's own design calls for. See
  `docs/05-decisions.md`'s new entry.

## 6. Docs

- [x] 6.1 Update `docs/12-sample-remark-rescan.md` to mark the `0. Info`, `A2`/`A3`, and `B2.6` gaps
  resolved, with a pointer to this change. Verify the doc no longer lists them as open gaps.
  **Done 2026-09-21** — `0. Info` and `B2.6` sections each got a "Resolved" correction note (`A2`/
  `A3` already had one from 2026-09-14).
- [x] 6.2 Update `docs/05-decisions.md` (new decision entry for `B2.6`'s pricing basis) and
  `docs/project-status.md`. Verify both mention the change with the date and, for `B2.6`, the
  signed-off figure.
  **Done 2026-09-21** — new `docs/05-decisions.md` entry (shared with `fill-guideline-required-
  line-items`, both signed off on the same instruction). `docs/project-status.md` updated in the
  same pass as the other two changes' sign-offs.
