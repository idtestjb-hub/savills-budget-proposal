## 1. Record the starting point

- [x] 1.1 Capture the figures that must NOT move — verify by reading them from `verification/baselines/baseline.json` and recording them before any code is touched
      Done. Recorded from `verification/baselines/baseline.json` (2026-09-08T19:10:20+07:00): all 24
      tracked figures, notably `opex_repairs_annual: 28,135,740 VND` (the analysis-side figure this
      change is meant to restore on the deliverable side, per `write-computed-opex-categories-to-
      deliverable`'s deferred task 2.4) and every other figure, which per proposal.md's Impact section
      must NOT move as a result of this change (allocation columns are a view over costs, not costs
      themselves).
- [x] 1.2 Capture how many rows would error once the trigger input is present — verify by generating
      with a temporary non-zero parking area and recording the count and a sample of the error cells,
      so the fix has something to be measured against
      Done, on a scratch copy only (never the real input file — see 4.3). Generated the standard
      sample deliverable via `run_workflow()`, confirmed `'0. Info'!D12` (parking area) is blank
      (`None`) today, then set it to 5,000 m² on a throwaway copy and scanned via
      `checks._scan_errors_via_excel()` (real Excel recalculation, not cached values). Result: **109
      `#DIV/0!` cells across 42 distinct rows** on `'2. Budget-Management Fund'`, spanning columns
      BJ/BK/BM/BN (not just BM/BN as proposal.md's formula excerpt named — BJ/BK carry their own
      denominator, `SUM($BG:$BH)`, which the same D12 trigger also empties for these specific rows;
      recorded as part of this change's actual blast radius, not assumed narrower than it is). Rows:
      79-85, 94, 101, 109, 132-133, 143-144, 160, 192, 194-197, 200, 210, 222-228, 230, 238, 240,
      250-251, 495-511 range. Separately noted: 3 unrelated `#REF!` cells on other sheets
      ('B1. Lịch Lễ tân', 'B3. Vật tư vệ sinh - Consumable') — these are part of the template's
      already-known, already-accepted 53-error baseline (`verify.py`'s own "53 inherited from the
      blank template" line), present regardless of this change, not newly triggered by D12.
- [x] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero
      Done: exit code 0. `verify.py` reports the same pre-existing, separately-tracked
      `staff_cost_annual`/`total_profit_value`/`margin`/`markup` baseline drift already documented in
      `docs/project-status.md` (from the paused `reconcile-summary-with-detail-sheets` change) —
      unrelated to parking allocation, unchanged by anything done this session.

## 2. Establish the split before writing it

- [x] 2.1 Establish whether any reference budget records a monthly-versus-casual parking revenue split — verify by reading them and recording plainly whether a basis exists, since the answer decides what is written
      Done. No raw reference-budget source files are present in this repo clone (`input/budget_planning/`
      doesn't exist here — same gap noted elsewhere this session). Checked the closest available
      evidence instead: `Costing_Method_Catalogue.csv`'s own entries for RP5/RP6 (the visitor/casual
      codes) state `method: visitor-parking-estimate`, `inputs: visitor volume assumption; daily rate`
      — the catalogue itself documents that this code requires an ASSUMPTION, not measured data, and
      `exensive_logic: not-covered` confirms the Savills AI Guideline's own worked example doesn't
      cover it either. No basis exists anywhere accessible. Confirms design.md's D1 fallback branch
      (write the monthly half, zero for casual) is the one that actually applies — established by
      checking, not assumed by default.
- [x] 2.2 Use the pipeline's own monthly parking revenue for the monthly half — verify by confirming the value written equals the parking revenue the deliverable already reports, and is not separately re-derived
      Done. `BM11` = `moto_full_monthly + car_full_monthly`, the exact same variables RP1/RP2's own
      write-site uses — no re-derivation. Verified on the standard sample: RP1's own remark states
      176,000,000 (100%-fill monthly), RP2's states 418,000,000; BM11 = 594,000,000 = their sum
      exactly.
- [x] 2.3 Write zero for the casual half if no basis was found, rather than a plausible ratio — verify by confirming no split was chosen that cannot be traced to evidence, and that the choice is stated on the output
      Done. `BN11 = 0`, per task 2.1's finding (no basis exists). Stated in `BM11`'s own cell comment
      (openpyxl `Comment`, matching this codebase's established per-cell disclosure convention):
      "Casual/visitor weight (BN11) is 0: no real basis exists for that split... 100% of the
      allocation therefore goes to monthly parking, not a guessed ratio."
- [x] 2.4 Do not overwrite weights a project already carries — verify by pre-filling the cells with different values, running, and confirming the pipeline leaves them and says it did
      Done. Built a scratch copy of the real template with `BM11=111`/`BN11=222` pre-filled (real
      template file confirmed untouched throughout, both via `run_workflow()`'s own snapshot and a
      direct mtime check), redirected `TEMPLATE_PATH` to it, ran the full pipeline — both cells came
      through unchanged at 111/222, and no comment was added (correctly recognized as already-filled,
      not blank).

## 3. Make a zero denominator impossible to ship

- [x] 3.1 Fail the run when the allocation denominator would be zero — verify by temporarily clearing the weights and confirming the run stops and names the affected cells
      Done. Built a scratch template copy with `BM11=0`/`BN11=0` pre-set (real template confirmed
      untouched), redirected `TEMPLATE_PATH`, ran the pipeline — raised `ValueError` naming the exact
      cells: `"'2. Budget-Management Fund'!BM11:BN11 (parking allocation weights) sum to zero..."`.
- [x] 3.2 Confirm no deliverable is produced when that check fails — verify by confirming the output directory holds no client workbook after a failed run
      Done: the failed run's workdir was completely empty (`[]`) — no partial or broken output leaked
      through.
- [x] 3.3 Confirm the check does not depend on which cost rows were written — verify by running with a cost line added and removed and confirming the check behaves identically both times
      Done: re-ran the same zeroed-weights template against a second sample with a materially
      different cost-row composition (different Total NFA, product mix, pool settings) — failed
      identically, naming the same cells. Structurally guaranteed by placement too: the check runs
      immediately after RP1/RP2 are written, before nearly every other cost line in the function, and
      reads only the two fixed weight cells — nothing about its own logic references any other row.

## 4. Prove the fix on the state that actually triggers it

- [x] 4.1 Generate with a temporary non-zero parking area and confirm no error cells appear — verify by full Excel recalculation and comparing against the count recorded in 1.2
      Done, after a genuine scope expansion (your explicit instruction, mid-task). The BM11/BN11 fix
      alone resolved 28 of 42 error rows on the first triggered-state test, including row 485 (ERM) —
      the original motivating case — but 14 rows still erred through a DIFFERENT mechanism: 6 rows
      (EMH1/EMH2/EMH3/VAT/CIT1a/CIT1b) have blank `BG<row>`/`BH<row>` cells that their own BJ/BK
      formulas divide `SUM()` over, independent of BM11/BN11. Confirmed by direct inspection that 350
      of 356 sibling rows already carry `=$BG$10`/`=$BH$10` — the template's own established pattern,
      just missing from these 6 (one of which, row 485, doesn't itself error from this cause — its BK
      reads a different cell directly per proposal.md — but was still missing the same reference every
      sibling carries). First fix attempt (detect via BM referencing `$BM$11`) caught 5 of 6 but missed
      VAT (row 498, whose BM/BN are SUBTOTAL() rollups, not the direct formula) — caught only by
      re-testing the actual triggering state, not by reasoning about the template in the abstract.
      Final detection combines two real signals (BM/BN references the shared weight, OR BJ/BK itself
      divides by SUM($BG)) — dynamic, not a hardcoded row list. Final scan: **0 `#DIV/0!` cells**
      (down from 109), only the 3 pre-existing, unrelated `#REF!` cells remain (part of the template's
      already-accepted 53-error baseline).
- [x] 4.2 Confirm the allocation columns resolve to numbers — verify by reading a sample of the previously-dormant rows and confirming each holds a value rather than an error
      Done: all 7 rows needing the BG/BH reference (82, 83, 84, 485, 498, 502, 503) confirmed holding
      `=$BG$10`/`=$BH$10` post-fix, each resolving to a real number under full Excel recalculation, not
      an error.
- [x] 4.3 Confirm the temporary variant touched no real input file — verify by comparing the production fingerprints before and after
      Done on every run in this task group: `run_workflow()`'s own snapshot confirmed unchanged, and
      the real `TEMPLATE_PATH` file's mtime was independently re-checked unchanged both before and
      after every redirected-template test.
- [x] 4.4 Confirm no cost figure changed as a result of the allocation weights — verify by comparing every cost line against its pre-change value, since the allocation is a view over costs and not a cost
      Done: `verify.py`'s FIGURES section (24 headline figures) matched pre-change values on every run
      in this task group where the trigger wasn't active; the BM/BN/BG/BH columns are an allocation
      view computed downstream of already-written `G`-column cost figures, never feeding back into
      them, confirmed by the formulas' own shape (`IF(BK>0, BK*BM11/SUM(...), 0)` reads a cost, never
      writes one).

## 5. Restore the deferred Repairs & Maintenance write

- [x] 5.1 Restore the write site deferred by `write-computed-opex-categories-to-deliverable`, with the remark it already carried — verify by confirming the figure appears and equals the analysis workbook's
      Done. `write-computed-opex-categories-to-deliverable` never actually landed this write (its own
      design.md D6: "computed on every run and discarded" — no prior code to copy verbatim), so the
      remark was composed now, mirroring `opex_admin`'s exact pattern: `_opex_remark(...)` (the
      existing A&K ratio-per-m² narrative, Vietnamese) + `_CATCH_ALL_NOTE` (the existing
      whole-section-not-itemized disclosure) + a new sentence carrying that change's own D2 finding —
      materials only, excludes maintenance contracts (Điều 150 Luật Nhà ở 2023, separate sinking
      fund), and explicitly does NOT include clearance/suction services (ERCS) even though those
      dominate real ER spend — so a reader cannot mistake this figure for the clearance budget.
      Added `'Repairs & Maintenance (materials only)'` to `_OPEX_CATEGORY_VI` (was missing, would
      have fallen back to raw English inside an otherwise-Vietnamese sentence). Also corrected two
      stale comments in the same function that still described both opex_admin and opex_repairs as
      "deliberately left blank" — both are now written; left uncorrected they contradicted the code
      directly beneath them.
- [x] 5.2 Confirm writing it introduces no error cells — verify by full Excel recalculation, both with and without a parking area present
      Done, using the project's own established method (`check_formula_errors()`, which diffs
      against `_baseline_error_locations()` — the blank template's own error set — rather than
      expecting an absolute zero). Standard state (no parking area): 0 NEW errors, 5 inherited from
      the 2,355-cell blank-template baseline, method=excel-recalculation (full, not degraded).
      Parking-triggered state (D12=5000 set post-hoc on a copy of the generated deliverable, same
      approach as tasks 1.2/4.1 — parking area is not a pipeline input field, so there is no input
      form path to drive it): also 0 NEW errors, 3 inherited.
      **False alarm, corrected**: a first-draft test script compared against a hardcoded "expect 0
      total errors" instead of the real baseline, and flagged `BK507`/`BK511` as newly introduced.
      Investigated rather than assumed: those two cells belong to a self-contained "break-even
      management-fee price" analysis block (rows 507-511, Vietnamese-labelled, e.g. "Gía dịch vụ
      quản lý cân bằng"), confirmed by a whole-workbook reference scan to be read by nothing else in
      either workbook. `BK507 = -BK505/BK10` where `BK10 = BH10 = '0. Info'!D12` — the same parking-
      area cell, referenced directly rather than through `SUM($BG:$BH)` — so it errors whenever
      parking area is blank, independent of opex_repairs or anything else in this change. Checked
      directly against `_baseline_error_locations()`: both cells (and their BJ-column siblings) are
      already inside the blank template's own 2,355-cell error set — a pre-existing template
      artifact this project's own verify.py has correctly classified as inherited all along, not a
      regression this write introduced. `BJ507`/`BJ511` (the Apartment-side siblings) never error,
      since `BJ10` = Apartment NFA is always populated.
- [x] 5.3 Confirm every category the estimator computes now agrees across both workbooks — verify by comparing them category by category and confirming the count with a figure is identical in both
      Done for the two categories this change is responsible for. Same run, full recalculation:
      opex_admin — deliverable G109 57,166,716 = analysis workbook (same run) 57,166,716 = recorded
      baseline 57,166,716. opex_repairs — deliverable G485 28,135,740 = analysis workbook (same run)
      28,135,740 = recorded baseline 28,135,740.
      The other four `estimate_opex()` categories are outside this change's scope and were already
      correct by earlier, unrelated design — checked to be sure rather than assumed: Diesel and Pool
      Salt agree deliverable-to-analysis exactly (both flat, non-ramped). Electricity and Water do
      **not** match 1:1, by design, not defect: the deliverable applies the year-1 occupancy fill-up
      ramp (change `cost-energy-from-consumption-and-tariff` / the fill-up-ramp work), so its total is
      the ramped year-1 figure, while the analysis workbook's OPEX sheet reports the flat full-
      occupancy annual figure. An early draft of this check wrongly flagged both as "MISSING" on the
      analysis side — a script bug (Electricity/Water/Diesel each appear twice on the OPEX sheet, once
      at their data row and once in a footnote row comparing against Parking Building's real figures;
      the footnote row's blank column C silently overwrote the real value in a naive dict build) had
      nothing to do with the pipeline itself.
- [x] 5.4 Confirm the section total and the expense total rose by exactly the restored figure — verify by recalculating and reconciling the difference
      Done. ER section subtotal (`G263`, `=SUBTOTAL(9,G264:G485)`) measured 0 -> 28,135,740 — ER had
      no other populated leaf, so the section total equals the restored figure exactly.
      TOTAL EXPENSE corroborated rather than re-measured from scratch: `write-computed-opex-
      categories-to-deliverable`'s own tasks.md (2.4) already recorded, from when this exact write was
      live before being reverted for the `#DIV/0!` defect this change fixes, that with both opex_admin
      and opex_repairs present TOTAL EXPENSE rose by exactly 85,302,456 = 57,166,716 + 28,135,740. Since
      opex_admin's +57,166,716 was already delivered and unmoved throughout this change, the isolated
      contribution of restoring opex_repairs is exactly +28,135,740 by subtraction — matching this
      session's own fresh ER-subtotal measurement exactly. Two independent measurements agree.

## 6. Confirm the blast radius

- [x] 6.1 Confirm the analysis workbook did not move — verify by comparing it cell by cell against a pre-change run
      Done via `python verification/verify.py`'s BASELINE section, which compares every one of
      baseline.json's 24 tracked figures — including every OPEX category, all sourced from the
      analysis workbook — against their recorded values. Exactly 4 differ: `staff_cost_annual`,
      `total_profit_value`, `margin`, `markup`, all moved by the same underlying amount
      (379,523,020 VND). No OPEX figure, revenue figure, or anything else this change could plausibly
      touch moved.
      **Attribution corrected before recording** (caught by a second advisor pass, not assumed):
      first drafted this as `activate-dormant-staffing-ratios`'s drift, since that change also moves
      `staff_cost_annual`. Checked the arithmetic and the actual figures rather than pattern-matching
      "staff cost moved, I touched staff cost this session": 3,543,782,105 (baseline) + 379,523,020 =
      3,923,305,125 (today's figure) — exact — but `activate-dormant-staffing-ratios`'s own
      `measured-effect.md` (written earlier this session) already states plainly that its swing is
      +986,062,578, measured on a synthetic Wayne-Tower-scale test, and separately confirms "0
      differences on the frozen fixture" `verify.py` actually reads — the standard sample predates
      that change and still holds its old seed values, untouched by it. The two numbers don't match
      because they're not the same drift. This is instead the pre-existing drift task 1.3 already
      recorded before this change started, and which `docs/project-status.md`'s own 2026-09-14 note
      already names by this exact figure and attributes to `reconcile-summary-with-detail-sheets` —
      unrelated to parking allocation, OPEX, or anything touched this session.
- [x] 6.2 Confirm the structural checks pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
      Done, same `verify.py` run: sheets present on all 3 workbooks (25/14/5, none missing), no
      corruption artifacts, no Excel errors introduced (5 inherited from the 2,355-cell blank-template
      baseline, method=excel-recalculation — the full method, not degraded).
- [x] 6.3 Confirm production data was untouched throughout — verify by comparing the production fingerprints against their recorded values
      Done: `verify.py` — "OK all production artefacts byte-identical." Consistent with every
      individual run's own snapshot check throughout this task group.

## 7. Re-record the baseline if it moved

- [x] 7.1 Review every named difference and confirm each was intended — verify by producing a short written account before re-recording anything
      Done — see 6.1. The 4 named differences (staff_cost_annual, total_profit_value, margin,
      markup) are a pre-existing, already-documented drift from `reconcile-summary-with-detail-
      sheets` (scaffolded 2026-09-10, flagged in `docs/project-status.md` since 2026-09-14) — not
      caused by this change, and not by `activate-dormant-staffing-ratios` either (see 6.1's
      correction). Nothing this change is responsible for (opex_repairs_annual, opex_admin_annual, or
      any other tracked figure) differs from its recorded baseline value.
- [x] 7.2 Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change
      NOT REQUIRED — no tracked figure moved because of this change (same reasoning as the sibling
      change's own 6.2: "the baseline reads both OPEX figures from the ANALYSIS sheet, which this
      change did not touch"). `opex_repairs_annual` was already 28,135,740 in the baseline before this
      change started — this change closes the DELIVERABLE side to match a figure the ANALYSIS side
      already carried, so the baseline's own value was already correct and needs no update.
      Re-recording now would incorrectly fold `reconcile-summary-with-detail-sheets`'s still-pending
      drift (see 6.1/7.1) under this change's name — that change owns its own re-record, gated on its
      own Head-of-PM sign-off, not this one. (An earlier draft of this note misattributed the same
      drift to `activate-dormant-staffing-ratios` — corrected, see 6.1.)
- [~] 7.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero
      BLOCKED, not by this change. `verify.py` currently exits 1 solely on the 4 figures named in
      6.1/7.1 — a drift that predates this entire session (flagged in `docs/project-status.md` since
      2026-09-14, attributed there to `reconcile-summary-with-detail-sheets`, gated on that change's
      own Head-of-PM sign-off, tasks 6.2/6.3). Task 1.3 already recorded this exact condition as
      pre-existing before any code in this change was touched — `verify.py` has not exited 0 on the
      standard sample at any point in this task group's own before/after window, so this was never
      "this change broke it," only "this change cannot fix a different, already-known, already-gated
      block on its way to a clean run." This change's own portion of verify.py — structure,
      corruption, formula errors, all 24 figures it could plausibly move — is clean (sections
      6.1-6.3). Recording this as a known, attributed cross-change block rather than forcing a false
      "done": resolving it is `reconcile-summary-with-detail-sheets`'s own task, gated on its own
      sign-off, not something this change's scope reaches.

## 8. Documentation

- [x] 8.1 Record the template defect precisely enough to act on — verify by confirming `docs/05-decisions.md` names the cells, the formula, the row count and the input that triggers it
      Done. `docs/05-decisions.md`'s existing "Repairs & Maintenance is still not written, and why"
      subsection already named `ERM`/row 485, the `BM485=$BK485*$BM$11/SUM($BM$11:$BN$11)` formula,
      the 351-row count, and `'0. Info'!D12` as the trigger — retitled to reflect the fixed state and
      kept as the defect record. New section "Parking-allocation divide-by-zero fixed; Repairs &
      Maintenance now closes the gap (2026-09-17)" adds the D5 amendment's own cells/formula/count
      (`BG`/`BH`, `=$BG$10`/`=$BH$10`, 6 rows + ERM) and the newly-found `BK507`/`BK511` block.
- [x] 8.2 Record that correcting the template is Savills' decision and the pipeline is working around it — verify by confirming the choice and its owner are both written down
      Done, same subsection: "It is still Savills' template that is wrong... whether to correct the
      template itself, or keep relying on the pipeline to paper over it, remains the PM's call."
- [x] 8.3 Record what split was written and on what basis, including if it was zero — verify by confirming a reader can tell whether the allocation is evidenced or a stated placeholder
      Done, new section: `BM11` = `RP1`+`RP2` (not re-derived); `BN11` = 0, stated as "no reference
      budget or catalogue entry carries a monthly-versus-casual parking split... so the split is 100%
      monthly rather than an invented ratio," plus the already-carries-real-weights exception.
- [x] 8.4 Record that the cross-workbook OPEX gap is now closed, with the final figure — verify by confirming the decision record no longer describes Repairs & Maintenance as deferred
      Done: new section states "85,302,456 → 0" and all six `estimate_opex()` categories agreeing
      (or intentionally differing, with the reason). Old subsection no longer says "is still not
      written" — retitled "was blocked... fixed 2026-09-17."
- [x] 8.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
      Done. Added a 2026-09-17 top section covering all 4 changes touched this session; updated the
      §1 active-changes table (this change 0/29 -> 28/29, i.e. every task done except 7.3 which is
      explicitly `[~]` partial/blocked on a different, pre-existing change — plus the 3 other changes
      which weren't in the table at all); rewrote §4 "Exact next action" to lead with the pending
      sign-offs and the BK507/511 finding; added new rows to §5's PM-questions table. Count verified
      directly (`grep -c` on tasks.md: 29 total, 28 `[x]`, 1 `[~]`) rather than trusted from an
      earlier estimate or the CLI's own summary, which reported a different total.
- [x] 8.6 Decide whether this change needs a Head-of-PM sign-off task, resolving the open question 8.5 flagged — verify by checking direct precedent rather than guessing
      Decided: **no**, on your explicit instruction to decide. Checked directly rather than by
      intuition: grepped all 4 changes this session plus this change's own predecessor,
      `write-computed-opex-categories-to-deliverable`, for "sign-off" anywhere in their planning
      artifacts. The 3 changes that DO gate on sign-off (`activate-dormant-staffing-ratios`,
      `rank-comparables-by-location`, `wire-real-elevator-count-into-ad-revenue`) each introduce a
      **new method, rule, or reactivated calculation** that changes what number gets computed in the
      first place — a rate-cap formula, a distance tie-break, a ratio-derived headcount. This change,
      like its predecessor, does neither: `estimate_opex()` already computed 28,135,740 the same way
      since 2026-09-09, and the analysis workbook already counted it in Cost Priority and profit since
      then — nothing about WHAT the figure is or HOW it's computed changes, only that a template
      defect no longer hides it from the client-facing workbook. `write-computed-opex-categories-to-
      deliverable` moved a **larger** figure via the identical mechanism (Administrative Expense,
      57,166,716) and has zero sign-off mentions anywhere in its own tasks/proposal/design — sitting
      complete, undisputed, awaiting archival. Treating this change differently from the one it
      directly completes, for the same class of figure movement, would be the inconsistent choice.
      Transparency is still served without a formal gate: `docs/05-decisions.md`'s 2026-09-17 section
      states the figure and its "correction, not a new cost" framing plainly, matching how the
      original 2026-09-09 entry framed Administrative Expense before it shipped the same way.
