> **STATUS 2026-09-11**: Tasks 1–4, 5.1, 5.3 and now 6 (below) are done and verified. The composer
> is **enabled** (`ENABLE_SUMMARY_REMARK_COMPOSER = True`), reworked to Vietnamese-only wording
> matched to the worked sample's real usage (`docs/12-sample-remark-rescan.md`). `verify.py` PASS
> after the rework — `verify_run_2026-09-11_vietnamese_rework.txt` in this folder. Only **task 5.2**
> (Head-of-PM wording sign-off) is open — the Wayne Tower spot-check output sent to the user is now
> the reworked wording, ready for that review.

## 1. Extend the catalogue

- [x] 1.1 Transcribe the 55 line-level `AI GUIDELINE` instructions from
  `docs/AI Guideline - 2027 Resi Budget Form (IT team).xlsx` column W into
  `data/master_list_verified/Costing_Method_Catalogue.csv` — populate `remark_components` (`;`-list,
  same format as the 61 existing) for each instructed code that lacks it; mark benchmark-priced
  codes as such. Verify: `python -c "import csv; …"` shows every `W`-instructed code now has a
  `remark_components` value; `check_catalogue_drift.py` still passes on the original 67 rows.
  DONE via `extend_catalogue_remarks.py` (kept in this change folder) — 44 new rows added for the
  instructed codes with no entry (all real fund/sinking codes → no drift); the 67 originals keep
  their 13 columns byte-identical. Instruction text from `scratchpad/guideline_remarks.txt`.
- [x] 1.2 Add the 19 `1. Summary` composition recipes as new catalogue rows (`SUM.<code>` or a
  `section = summary-narrative` discriminator — pick one, note it), each with the ordered parts in
  `remark_components`, the per-part input source in `method_detail`, and any fixed sentence verbatim
  in a new `fixed_sentence` column. Verify the file still parses as CSV after the `#` header block.
  DONE — used **two new columns** `summary_recipe` + `fixed_sentence` on the code that owns each
  `1. Summary` PART-1 row (rather than synthetic `SUM.*` rows, which would fail `check_catalogue_drift`).
  Security/Cleaning/Other-service/Accreditation ride on `ESS1`/`ESS4`/`ESS16`/`ESA6`; Insurance on
  `ESI1`. 19 recipes recorded. File parses (111 rows, 15 columns, consistent).
- [x] 1.3 Add the VAT rule to the catalogue — one row (or promoted header) holding the Vietnamese
  and English VAT-treatment sentence and `inputs = 2. Budget-Management Fund!F7`. Verify it reads
  back cleanly. DONE — promoted to a `#` header block (a real `VAT.RULE` row would fail the drift
  check). Holds `vat_switch_cell`, `vat_sentence_vi`, `vat_sentence_en`, and the KHOÁN=excl rule.
  `check_remark_content` parses it back from the header.

## 2. The VAT-sentence helper

- [x] 2.1 Add `_vat_sentence(wb, year)` to `generate_project_budget.py` — reads
  `2. Budget-Management Fund!F7`, returns `""` for the exclusive-of-VAT option (`KHOÁN`), else the
  bilingual sentence (from the catalogue's recorded wording) with `year` substituted. Verify with a
  crafted `F7` = each of the three values. DONE — `_catalogue_vat_rule()` parses the wording + cell
  from the catalogue `#` header; `_vat_sentence()` normalises the switch (blank/unrecognised →
  inclusive). Unit-tested against all 5 switch values.
- [x] 2.2 Call `_vat_sentence` from `_write_remark()` and `_opex_remark()` — append only if the
  sentence is not already a substring of the remark. Verify (COM) that on an incl-VAT run every
  pipeline-written `T` remark ends with the sentence, and on a `KHOÁN` run none does.
  DONE — applied at the single choke point `_write_remark()` via `_append_vat()` (substring-guarded,
  placed at the very end of the final concatenated text). `_opex_remark()`'s output flows through
  `_write_remark()`, so it is covered there rather than appending mid-string — noted in a comment at
  `_opex_remark`. `build_budget()` sets the module global `_ACTIVE_VAT_SENTENCE` once from
  `_vat_sentence(wb, year)` after loading the workbook. COM verification is task 4.x.

## 3. Compose the `1. Summary` narratives

- [x] 3.1 Build the `written` map as the pipeline fills lines — `{code: (row, value, item_name)}` —
  in `fill_management_fund_sheet` / `fill_common_area_fund_sheet` / the RM block. Verify it contains
  every code the pipeline wrote a non-zero figure to for one real project.
  DONE via `_collect_written(wb)` — reads back what the fills wrote from the two fund sheets' C /
  F / H:S / Y / Z cells (all literals openpyxl can see), rather than threading a map through ~15
  writers. `{code: {row, value, sheet, name_vi, name_en}}`. Verified on the ZZ Sample fixture:
  22 codes (RM.AP/RM.SH/RM.KG, RM.0A, RP1/RP2, EMH2, EMA15, ESS1/ESS4/ESS16, ESM2/3/4/5/8,
  EN1–4, EEW.C/EEE.C/EED.C, RA1.A/RA2).
- [x] 3.2 Add the recipe-wording dict to `generate_project_budget.py` — a bilingual
  fill-in-the-blanks template per recipe-driven code (`RM`, `RPa`, `EMH`, `ESC`, security, cleaning,
  `ESI`, `EN`, `EEW`, `EEE`, `EED`), placeholders filled from `0. Info` / `estimate_opex` /
  `fill_curve` / the roster. A clause with no data for the project is omitted cleanly. Verify each
  template renders for the Wayne Tower inputs. DONE — `_recipe_narrative(key, wb, project, demand,
  year, written)` with templates for `RM`, `RPa`, `RI`, `EMH`, `ESS1`(security), `ESS4`(cleaning),
  `EN`, `EEW`, `EEE`, `EED`. `ESC` / `ESI` are recipe-listed but the pipeline writes nothing under
  them, so no runtime template — they stay recorded in the catalogue. Security/cleaning role
  breakdown from the roster (shift-time suffixes collapsed; supervisor split from the priced post
  count to stay consistent with the `T` remark). Budget year taken from
  `2. Budget-Management Fund!AL5` (not the roster calendar year). Rendered on the ZZ Sample fixture.
- [x] 3.3 Add `_compose_summary_narratives(wb, project, year, written)` — for every non-zero PART-1
  `1. Summary` row: recipe-driven rows use 3.2; roll-up rows (`RO`, `EMA`, `EMB`, `ESM`,
  `ESA`+`ESL`, `ER`, other-service) emit `"Dự ước bao gồm: <names> / Estimate includes: <names>"`
  over the `written` children under that section + any catalogue `fixed_sentence`; append
  `_vat_sentence`. Write plain bilingual text to column K, overwriting the template pull/blank.
  Verify (COM) K is populated for every non-zero PART-1 total and reads correctly.
  DONE — signature is `_compose_summary_narratives(wb, project, demand, year, written)` (needs
  `demand` for the security/cleaning role breakdown). `_SUMMARY_PART1` maps each PART-1 row → kind /
  recipe code / fund-code prefixes. VAT sentence appended once via `_append_vat`. On the fixture it
  fills K14, K15, K19, K22, K23, K29, K30, K33, K36, K38, K39, K40 — all bilingual, all reconcile
  with the sibling `T` remarks; K16/K17 (advertising/rentals legal text) left as the template ships
  them. COM re-verification is task 4.
- [x] 3.4 Call `_compose_summary_narratives` in `build_budget()` after the fills and **before**
  `_normalise_all_remark_columns()`. Verify `python run.py` completes and the K rows are sized.
  DONE — placed after `_fix_fake_formula_strings(wb)`, before `_normalise_all_remark_columns(wb)`;
  the sweep's line cap raised 12 → 30 for the taller composed K cells. `build_budget` completes;
  production untouched. Full `run.py` / `verify.py` is task 4.3.

## 4. Verification

- [x] 4.1 Add `check_remark_content(paths)` to `verification/checks.py` (COM, one workbook open):
  every non-zero PART-1 `1. Summary` total has a K narrative; each recipe part / fixed sentence from
  the catalogue appears in it; each `written` child's item name appears in its aggregate total's
  narrative; on an incl-VAT run the VAT sentence appears in every non-empty K cell and a sample of
  written `T` cells; K carries a Vietnamese and an English marker. Return `(ok, rows, differences,
  notes)`. DONE — **openpyxl, not COM** (design D5 revised, rationale there: every cell inspected is
  a literal the pipeline wrote; "non-zero PART-1" = the `_collect_written` funded-leaf set, which is
  the composer's own contract; a broken VLOOKUP that zeroes a funded row is a figure fault owned by
  `check_summary_reconciles`). Recipe "parts" enforced via `_REMARK_RECIPE_ANCHORS` token table
  (presence, not phrasing). Negative-tested: blanked K22 → fail; child name removed from K33 → fail;
  `KHOÁN` run → no VAT sentence anywhere, still passes.
- [x] 4.2 Wire `check_remark_content` into `verify.py` as section 5e, after 5d; on failure print the
  offending total + missing part and exit non-zero. Verify `python verification/verify.py` runs it.
  DONE — wired as **§5d** (the next free section — no §5d exists yet; the sibling
  `reconcile-summary-with-detail-sheets` also plans a §5d, whichever lands second renumbers). Prints
  each offending total + reason, returns 1 on failure.
- [x] 4.3 Confirm no figure moved: run `verify.py` and confirm all 24 analysis + 7 deliverable
  baseline figures are unchanged (remarks are text, not baselined). DONE — `python
  verification/verify.py` → **PASS** (full Excel recalculation). All 24 analysis baselines match;
  all 7 ramped deliverable baselines match; revenue-agreement and PROPOSAL BENCHMARK still
  reconcile; production artefacts byte-identical; no new Excel errors. §5d `check_remark_content`
  ran and passed 21 assertions across 13 composed narratives + sampled T remarks.

## 5. Review & docs

- [x] 5.1 **Manual spot-check** (project rule — output presentation changed): generate the
  deliverable for one real project; read every composed `1. Summary` narrative; confirm for that
  project each states the right chargeable area, fee rate, consumption, and child-line list, carries
  the correct legal/tariff citation, and reads correctly in Vietnamese and English. Record the
  checks and the project used. DONE — project: **Wayne Tower** (`reports/Project_Budget_Input.xlsx`,
  Total NFA 79,650 m², budget year 2027, VAT model THU HỘ CHI HỘ). Generated in an isolated workdir
  (production byte-identical). All 13 composed narratives (K14/15/19/22/23/29/30/31/33/36/38/39/40)
  read: K14 area/rate per product = value ÷ (12 × NFA) reconciles (RM.AP 3,875,625,000 ÷ (12 ×
  75,000) = 4,306); K15 parking bays match RP1/RP2; K22 payroll = EMH2; K29 security 29 posts /
  ₫2.22bn matches the T145 remark; K33/K36 child lists match the funded ESM*/EN* leaves; K38/K39/K40
  consumption + tariff + citation + fill-up basis all present; every incl-VAT K ends with the VAT
  sentence for year 2027; every narrative carries a Vietnamese and an English passage. Residual
  cosmetic items are template-inherited item names ("cảnh quang", "Enviromental") — not composer
  faults. `check_remark_content` PASS on the Wayne deliverable.
- [x] 5.2 Head of PM reviews the Vietnamese wording of the recipe templates against the spot-check
  output; capture sign-off in the change notes. **SIGNED OFF 2026-09-14.** Wording reviewed against
  the Wayne Tower spot-check output (sent 2026-09-11, re-shown 2026-09-14) across two rounds — the
  bilingual draft and the reworked Vietnamese-only, sample-matched version (task 6). User approved
  proceeding to archive after the second round. The recipe templates live in one function
  (`_recipe_narrative` in `generate_project_budget.py`); `check_remark_content` enforces *presence
  of parts*, not phrasing, so any future wording revision needs no code review — edit the function
  and re-run `verify.py`.
- [x] 5.3 Update `docs/11-guideline-remark-model.md` (mark the summary-K gap closed),
  `docs/05-decisions.md` (new entry), `docs/08-guideline-change-family.md` (the "remark-content
  check" cross-cutting item — mark done), and `docs/project-status.md`. Verify each names the change
  with the date. DONE — all four updated, each names `apply-guideline-remark-model` / 2026-09-10;
  `docs/08` and `docs/11` also corrected the `0. Info!F7` → `2. Budget-Management Fund!F7` reference.

## 6. Rework wording from the worked sample (added 2026-09-11, done 2026-09-11)

Findings: `docs/12-sample-remark-rescan.md`, full extraction `remark_rescan_report.txt` (this
folder). Direction from the user: Vietnamese only (drop English); fill every blank in the AI
Guideline's own note text with this project's real data, in the guideline's own phrasing — not the
larger `A2`/`A3` canonical position-description library (deferred, not requested).

- [x] 6.1 Decide, per the findings in `docs/12`, which wording/format changes to adopt. DONE:
  Vietnamese only (both the composed narratives and the VAT sentence — line-level `T` remarks' own
  English business-logic prose is untouched, only its VAT-sentence tail changes language); bulleted
  `- item` aggregate lists (not comma-joined); the terser sample-validated VAT sentence; `RM`/`RPa`/
  `EMH`/`EN`/security/cleaning rewritten to follow the guideline's own numbered/bulleted note
  structure with blanks filled from project data; a small enumerable Vietnamese label map for the
  roster's ~5 canonical Security/Cleaning position names (not the full ~20-entry A2/A3 library —
  out of scope this round); RM gains the sample's 4th point (handover-rate/bad-debt caveat, no
  fabricated number). Catalogue's `vat_sentence_vi` updated to match.
- [x] 6.2 Apply the decided wording changes to `_recipe_narrative` / `_rollup_narrative` in
  `generate_project_budget.py`. DONE — `_bi()` removed (was the VN+EN wrapper); `_vi_list()` added
  (bullet format); `_PRODUCT_VI_LABEL` and `_SECURITY_CLEANING_ROLE_VI` added; every recipe branch
  and `_rollup_narrative` rewritten Vietnamese-only; `_append_vat` gives the VAT sentence its own
  line on a multi-line remark.
- [x] 6.3 Re-run `verify.py` (confirm 24+7 baselines still unchanged — this stays display-only) and
  `check_remark_content` on the ZZ Sample fixture and a real project. DONE — `verify.py` PASS
  (`verify_run_2026-09-11_vietnamese_rework.txt`, this folder); `check_remark_content` PASS (21
  assertions) on both the ZZ Sample fixture and Wayne Tower.
- [x] 6.4 Set `ENABLE_SUMMARY_REMARK_COMPOSER = True`; re-verify. DONE.
- [x] 6.5 Re-do the manual spot-check (5.1) and Head-of-PM wording review (5.2) against the reworded
  output; then `/opsx:archive`. Spot-check DONE — Wayne Tower, all 13 narratives read correctly in
  Vietnamese, figures reconcile, sent to the user. **5.2 (Head-of-PM sign-off) still open — human
  task; archive waits on it.**

## 7. Case model + one intake field (added 2026-09-11, done 2026-09-11)

Findings: `docs/13-remark-case-model.md` — every `Nếu...thì...` conditional in the guideline (21),
classified into modeled-and-built / needs-a-new-field / needs-new-pricing-logic /
needs-new-roster-logic. User approved building only the one case that's a pure remark-only addition.

- [x] 7.1 Add "Months of Management Fee Prepaid on Handover" to `Project Info`
  (`build_project_input_form.py`) — appended after every existing field (no row shift risk), blank
  default, comment explaining it changes no figure (`RM.0A` is computed from the fill-up curve,
  independent of this field). Verified the real `reports/Project_Budget_Input.xlsx` (Wayne Tower)
  is untouched by generating into a redirected scratch path and diffing its hash before/after.
- [x] 7.2 Read it in `generate_project_budget.py`'s `read_input()` as
  `project['handover_prepaid_months']`, guarded by `SheetLabels.has(...)` so a pre-existing workbook
  without the field (confirmed: the real Wayne Tower intake) still reads cleanly as `None`.
- [x] 7.3 Wire it into the `RM` recipe (`_recipe_narrative`) — entered → states the real month count,
  matching the guideline's own sentence and the sample's demonstrated fill (*"Ước tính theo thông
  tin CĐT cung cấp thu trước `<N>` tháng PQL cư dân khi bàn giao nhà..."*); blank → the existing
  qualitative description, unchanged. Verified both branches render correctly (ZZ Sample fixture:
  blank; a crafted 6-months value: filled) and production stays untouched either way.
- [x] 7.4 Catalogue: extended `RM`'s `summary_recipe` to name the new field and its intake location.
- [x] 7.5 Re-run `check_remark_content` (PASS, unaffected — the RM anchors don't depend on this
  field) and `verification/verify.py` (PASS — 24+7 baselines unchanged; confirms the addition moved
  no figure). Report: `verify_out3` result folded into the change notes.
- [x] 7.6 Update `docs/13-remark-case-model.md` (move the resolved case from Group B to Group A;
  correct the remaining Group B entries — on closer look five of the original six need Group C/D
  work first, not just a field, since the line they'd describe isn't priced or the position doesn't
  exist in the roster yet), `docs/project-status.md`, and memory.
