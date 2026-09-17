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

- [ ] 3.1 Read `B2.6`'s real QĐ 67 unit prices (collection/transport/treatment) from the guideline
  source document. Verify the three components sum to a stated total the guideline itself shows, if
  one is given.
- [ ] 3.2 Locate `B2.6`'s target row/code on `2. Budget-Management Fund` by scanning column Y for a
  waste-collection code (not a bare row number) — if none exists, stop and report back rather than
  invent one. Verify with `assert_row_code`-style guard, same pattern as every other leaf write in
  this pipeline.
- [ ] 3.3 Compute and write `apartment_units × 2.63 kg/unit/day × 365 × (sum of the 3 QĐ 67 unit
  prices)` to that row for projects with apartment units; leave at 0 otherwise. Verify (COM) the
  written `G`/`AK` values match the formula's own arithmetic.
- [ ] 3.4 Write `B2.6`'s remark stating the weight assumption and citing QĐ 67. Verify (openpyxl)
  the remark text contains both the weight figure and "QĐ 67" (or "67/...", whatever citation form
  the guideline itself uses).

## 4. Verification

- [ ] 4.1 Extend `verification/checks.py`'s remark-content check (or add a sibling check) for:
  every priced `0. Info` product has a remark; every canonical-matched `A2`/`A3` position carries
  its canonical description; `B2.6` has a remark whenever it has a figure. Verify it runs as part
  of `verify.py` and fails correctly when a required remark is missing (inject a gap and confirm).
- [ ] 4.2 Record `B2.6`'s new figure in `verification/baselines/deliverable_baseline.json` as a
  fresh addition (not a correction) — **only after task 5.2 sign-off**. Verify `verify.py` PASS on
  the following run.

## 5. Measure, spot-check, sign-off (B2.6 only — tracks 1/2 are display-only, no figure moves)

- [ ] 5.1 Generate the deliverable for Wayne Tower and record `B2.6`'s VND amount and the year-one
  surplus impact. Write the figure into the change's `measured-effect.md`.
- [ ] 5.2 Present the new `B2.6` figure to the Head of PM; capture the sign-off in the change notes
  and `docs/05-decisions.md` before archiving.

## 6. Docs

- [ ] 6.1 Update `docs/12-sample-remark-rescan.md` to mark the `0. Info`, `A2`/`A3`, and `B2.6` gaps
  resolved, with a pointer to this change. Verify the doc no longer lists them as open gaps.
- [ ] 6.2 Update `docs/05-decisions.md` (new decision entry for `B2.6`'s pricing basis) and
  `docs/project-status.md`. Verify both mention the change with the date and, for `B2.6`, the
  signed-off figure.
