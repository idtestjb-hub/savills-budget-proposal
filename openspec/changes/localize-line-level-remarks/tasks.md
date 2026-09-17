## 1. Shared energy wording (EEW/EEE/EED)

- [x] 1.1 Extract the Vietnamese `EEW`/`EEE`/`EED` sentence currently inlined in `_recipe_narrative()`
      into a standalone `_energy_narrative_vi(key, project)` helper; verify `1. Summary`'s `EEW`/`EEE`/
      `EED` narratives are byte-identical before/after the refactor on a sample-project run.
      Done: `_energy_narrative_vi(category, project, yr)` extracted as a module-level function
      (takes the already-resolved `yr` rather than `wb`, since `_opex_remark`'s scope has no `wb`
      closure to read a workbook object from). Verified byte-identical `1. Summary` EEW/EEE/EED text
      on the standard sample run.
- [x] 1.2 Point `_opex_remark()`'s `EEW`/`EEE`/`EED` branch at `_energy_narrative_vi()` instead of its
      English text; verify `2. Budget-Management Fund!T230/T240/T251` (or current row numbers) now
      read the same Vietnamese sentence as the corresponding `1. Summary` cell.
      Done: `_opex_remark`'s `tariff` branch now calls `_energy_narrative_vi()`, appends a Vietnamese
      tariff-date sentence and a Vietnamese n=1/provenance caveat (replacing the English one — the
      raw `usage_provenance`/`tariff_provenance` strings cite internal sheet names, e.g. "D2. Nước
      Công Cộng sheet", so dropped from client-facing text per the same principle §5 applies to
      flagged-zero remarks). Verified `EEW.C`/`EEE.C`/`EED.C` line-level remarks now open with the
      identical Vietnamese sentence as the matching `1. Summary` row.

## 2. Revenue narratives (RM.AP, RM.SH, RM.0A, RP1, RP2, RO2a)

- [x] 2.1 Write Vietnamese wording for the 6 revenue-side computed remarks; verify each cell contains
      Vietnamese content and the same figures/percentages as today's English text (run
      `check_remark_content` locally against a sample-project output).
      Done: RM.AP/RM.SH (and every other priced product via the shared loop), RM.0A, RP1, RP2, RO2a
      all verified Vietnamese on the standard sample, figures unchanged. `_anchor_note`/`_parking_note`
      (shared helper text both revenue families call) localized once, not per-caller.
      SCOPE ADDITION, disclosed: the EMH1 fixed-fee/% remarks (`write_even_monthly('mgmt_fee_expense',
      ...)`, ~line 1852/1864) were not in this change's original 50-code inventory — that scan ran
      against a project with no Savills contract entered, so this branch never fired and its English
      text was never observed. Localized anyway, being the same class of client-facing English this
      change exists to remove. Also corrected a stale cell reference while there (Project Info!B34/B35
      → B36/B37, from the 2026-09-15 field-reorder work) — unrelated to localization, but wrong either
      language.
      BUG FOUND, not yet fixed (see task 5.1): tested the fixed-fee branch with real contract data
      (Fixed Monthly Fee = 88,000,000) and the EMH1 cell still shows "Left at zero: no Savills
      management-fee contract terms..." — a SEPARATE, unconditional `_write_remark(ws,
      MGMT_FUND_ROWS['mgmt_fee_expense'], ...)` at ~line 2116 overwrites whatever the fixed-fee/%
      branch wrote, regardless of whether real data exists. The FIGURE (G column) is correct either
      way — only the remark text is wrong, silently, whenever a real contract is entered. Pre-existing,
      not introduced by this change; EMH1's flagged-zero text is already in task 5.1's scope, so the
      conditional-write fix lands there rather than here.

## 3. Management-fee and admin narratives (EMH2, EMA7, EMA15)

- [x] 3.1 Write Vietnamese wording for `EMH2` (payroll pull), `EMA7` (drinking water computation), and
      `EMA15` (A&K Tower per-m² ratio, including the n=1 sample-size caveat); verify each still states
      its data-provenance caveat in Vietnamese.
      Done. Also localized `_opex_remark`'s remaining two branches (`ratio_per_m2`, flat-fallback) and
      `_CATCH_ALL_NOTE`, since EMA15 depends on both — added `_OPEX_CATEGORY_VI` so the category name
      embedded in that shared text (e.g. "Administrative Expense") reads in Vietnamese too. Left the
      `method` branch (Pool Salt/ESM4) English — that one is task 4.1's, not this one's. Verified all
      3 codes + full regression (5 checks, 0 differences, production untouched — this edit touched
      shared infrastructure other codes call, so the full suite mattered here, not just the 3 targets).

## 4. Service-cost narratives (ESC12, ESS1/4/16, ESM2/3/4/5/8/25, EN1-4)

- [x] 4.1 Write Vietnamese wording for the 13 environmental/security/environmental-monitoring/capex
      computed remarks; verify each still states the underlying quantity x rate the English version
      stated.
      Done: ESC12, ESS1/4/16 (+ shared `_CONTRACT_BASIS`), ESM2/3/4/5/8/25 (ESM4 required editing
      `estimate_opex.py`'s `_pool_salt()` too — its `method`/`source` fields flow straight into the
      client remark, so translating only the call site would have left one function as the real
      source of English text with a Vietnamese wrapper around it), EN1-4 (+ `_capex_remark`,
      `_CAPEX_CATEGORY_VI`). Dropped internal file citations (`EXENSIVE LOGIC.xlsx`,
      `Costing_Method_Catalogue.csv`, `Fact_Capex_Rescanned.csv`) from client text throughout,
      consistent with task 5.1's principle — kept as code comments only. Verified all 13 codes
      (pool enabled, so ESM4/ESM5 actually fire) + full regression, 0 differences.

## 5. Flagged-zero remarks

- [x] 5.1 Rewrite the ~26 flagged-zero remark strings (the `_FLAGGED_NO_METHOD` dict's `reason` values
      plus the ad hoc zero-with-reason remarks: `RP3`, `EMH1`, `EMH3`, `EMB1`, `EMB4`, `EMO2`, `EMO6`,
      `EM#`, `ESC1`, `ESC2`, `ESC4`, `ESC5`, `ESI1`, `ESI2`, `ESM6`, `ESM7`, `ESM9`, `ESM10`, `ESM12`,
      `ESM13`, `ESR`, `ES#`, `EE#`, `ERCS1`) in Vietnamese, preserving the reasoning but dropping any
      reference to `Costing_Method_Catalogue.csv` or another internal filename from the cell text;
      keep the existing English code comment above each entry for engineering reference. Verify no
      cell in `2. Budget-Management Fund`/`2.2 Common area Fund` contains `.csv`, `.py`, or the
      strings `Costing_Method_Catalogue`/`generate_project_budget`/`estimate_opex`.
      Done: all 24 `_FLAGGED_NO_METHOD` codes + EMH1 + ESI1, all 26 verified Vietnamese, English
      reasons kept in a parallel `_FLAGGED_NO_METHOD_VI` dict (engineering record vs. client text
      never accidentally swappable). Internal filenames, `docs/14-required-line-item-gaps.md`, and
      the `complete-ai-guideline-remark-coverage` change name all dropped from cell text — kept only
      in code comments.
      BUG FIXED (found while testing task 2.1, fixed here since EMH1 was already in this task's
      scope): EMH1's flagged-zero write was unconditional, silently overwriting the real fixed-fee/%
      remark from task 2.1 whenever a PM entered actual Savills contract terms — the figure was
      always correct, only the remark text was wrong, and only when real data existed. Now guarded
      on the same condition the fixed-fee/% branch already checks. Verified both directions: no fee
      data → Vietnamese "left at zero" text; real fee data (tested Fixed Monthly Fee = 88,000,000)
      → the real Vietnamese fixed-fee remark, no longer overwritten.
      SCOPE GAP FOUND AND CLOSED: proposal.md's own stated scope names both `2. Budget-Management
      Fund` and `2.2 Common area Fund`, but no task in this file ever enumerated a `2.2 Common area
      Fund` code — Groups 1-5 as originally scoped only ever touched the first sheet. A denylist scan
      across both sheets surfaced 3 English remarks on `2.2 Common area Fund`: `RA1.A`/`RA2`
      (elevator/LCD advertising revenue, in `fill_common_area_fund_sheet()`) — localized, using the
      same identifier-vs-display-label split as `_PRODUCT_VI_LABEL` (the underlying `item` string
      that classifies lift-ad vs LCD-ad must stay the English text it pattern-matches on, so the
      Vietnamese label lives in a separate `_AD_ITEM_VI` lookup, not by renaming the field) — and
      `RP5` ("demo"), which is a template-shipped default this pipeline's code never writes to at
      all, so there is nothing to localize without editing the template file itself; left alone,
      consistent with this project's standing "keep the template file" boundary. Full denylist scan
      across both sheets re-run clean after these three; only the already-known, deliberately
      out-of-scope `EMH4` (not in any task in this change) still shows an internal citation.

## 6. Verification

- [x] 6.1 Extend `check_remark_content` (verification/checks.py) with a line-level Vietnamese-content
      assertion (every non-blank `T` cell on both fund sheets) and a no-internal-filename assertion;
      wire both into `verify.py`'s existing §5d/5e section.
      Done, after TWO broken filter designs discarded in the process (both discovered by testing, not
      inferred): (1) "non-blank T + has a code" — flagged 13 rows of genuine, already-Vietnamese
      TEMPLATE-default content (`ESA6/11/12/16` maintenance-fund guidance, `2.2 Common area Fund`'s
      `VAT1/VAT2/CIT1/CIT1a/CIT1b/CIT2` "[Lưu ý nội bộ: ...]" notes, `RP5`="demo") as false positives,
      because this pipeline never writes to those rows at all. (2) An inclusion filter — "T starts
      with '=' (a computed figure) or 'Để ở mức 0:' (the flagged-zero convention)" — looked right
      against source code, but `generate_project_output._fix_fake_formula_strings` (a separate,
      pre-existing, documented safety net) strips a leading `"= "` from any matching cell late in the
      pipeline, so in the actual deliverable almost none of this change's own remarks still start
      with `=`. This filter's positive test silently checked only 31 rows — most of Groups 1-4's real
      work was never exercised — caught by a negative test returning a false OK instead of a failure.
      FINAL DESIGN (an EXCLUSION list, not inclusion — flagged by the advisor tool before landing on
      the broken (2) permanently): scan every non-blank coded `T` cell on both sheets by default;
      skip only a new, explicit `_TEMPLATE_OWNED_T_ROWS` set of the same 11 confirmed-template-owned
      (sheet, code) pairs from failure (1) above, each verified again by its F/G columns (F blank or
      a template-native absolute-reference formula, G always the template's own pass-through formula
      — never a literal value, which is what every pipeline write looks like). This fails LOUD on a
      pipeline regression or a genuine new template note (still scanned, since it isn't in the
      11-row exclusion set) and fails SILENT only on the rare case of the template shipping a new
      untouched default row — the opposite failure direction from both discarded designs, which
      failed silent on the common case (a new remark-writing code added and forgotten here — this
      change alone added dozens). Deliberately NOT built by importing `MGMT_FUND_EXPECTED_CODE`/
      `COMMON_AREA_FUND_EXPECTED_CODE`/`PRODUCT_REVENUE_EXPECTED_CODE`/`_FLAGGED_NO_METHOD` from
      `generate_project_budget.py` (the plan going into this task) — checks.py's own file docstring
      states its expected-value contracts are deliberately hardcoded independently of the thing being
      checked "so the check doesn't agree with the pipeline by construction"; importing the
      generator's own registries as the check's scope would reproduce exactly that failure mode one
      level removed (a code silently dropped from the generator's registry would silently narrow the
      check's scope too). `_INTERNAL_ARTIFACT_DENYLIST` extended with `.md`, `docs/`, and
      `complete-ai-guideline-remark-coverage` — task 5.1's own verification text names
      `docs/14-required-line-item-gaps.md` and that change name as things dropped from cell text,
      which `.csv`/`.py` alone would never catch. The three rules (VAT sentence, Vietnamese content,
      denylist) now run independently per row with no short-circuit, matching the '1. Summary' K-cell
      loop just above it in the same function — a row wrong two ways now reports both reasons, not
      just the first. That restructuring surfaced a pre-existing minor bug in the same function's own
      summary note: `composed`/`t_checked` counted `rows` ENTRIES, which can now exceed the number of
      actual cells checked when one cell fails more than one way; fixed to count unique labels.
      `verify.py` §5d already called `check_remark_content` (wired in by `apply-guideline-remark-
      model`, unchanged here since the function's name/signature/return shape didn't change) — only
      its printed assertion-description text needed updating to name the two new checks. Could not
      exercise this live through `verify.py` end-to-end past §4, because of a PRE-EXISTING, already-
      documented baseline drift from the unrelated, separately-gated `reconcile-summary-with-detail-
      sheets` change (`docs/project-status.md`, 379,523,020 VND `staff_cost_annual`) — verified
      `check_remark_content` directly against `checks.py` instead, the same bypass `docs/project-
      status.md` itself already documents as the sanctioned workaround for this exact obstacle.
- [x] 6.2 Positive-test: run the check against a freshly generated sample-project deliverable and
      confirm it passes (0 differences).
      Done: 0 differences, 61 unique line-level `T` cells checked (up from the broken filter's 31 —
      confirms Groups 1-4's remarks are now actually being exercised, not silently skipped). Full
      5-check regression suite (`check_revenue_agreement`, `check_benchmark_reconciles`,
      `check_remark_content`, `check_summary_reconciles`, `check_required_line_items`) also re-run
      clean, 0 differences across all 5; Wayne Tower production backup hash unchanged.
- [x] 6.3 Negative-test: on a copy, revert one line-level remark to English and confirm the check
      fails and names the code and row; separately, insert a `Costing_Method_Catalogue.csv` reference
      into one remark and confirm the filename assertion fails and names it.
      Done, both rebuilt from the task-6.1 fix. Test 1's original mutation (keep the VAT sentence,
      drop everything else to English) turned out to be unable to isolate the Vietnamese-content
      assertion, because `vat_vi` (`"Chi phí hạng mục này đã bao gồm VAT..."`) is itself Vietnamese —
      keeping it would make the Vietnamese-content check pass regardless of the rest of the cell, so
      it could never be the thing that fails. Rewrote the mutation to English throughout (VAT sentence
      included); the no-short-circuit change from 6.1 means the check now reports BOTH failures on
      that cell as separate entries, and the test asserts specifically on the `'no Vietnamese
      content'` reason string among them (not just "some failure occurred on this row"), the same
      way test 2 already isolates on `'artifact'`. Test 2 (append `Costing_Method_Catalogue.csv` to
      the original, unmutated Vietnamese/VAT-complete text) now genuinely exercises the denylist:
      under the old broken filter it returned a false OK (the row was silently skipped, not passed
      for the right reason); now correctly fails, naming the `.csv` leak on the exact row.

## 7. Manual review and sign-off

- [ ] 7.1 Generate the deliverable for one real project (or the standard synthetic sample, per
      whatever `reconcile-summary-with-detail-sheets`/`apply-guideline-remark-model` used), read every
      line-level remark aloud in Vietnamese, and confirm each states the right figure or reason for
      that project and reads naturally — same review shape as the original narrative work's Wayne
      Tower read-aloud review.
- [ ] 7.2 Confirm with Head of PM (or whoever owns Vietnamese financial/legal terminology review) that
      the wording is correct and professional before this change is archived.
