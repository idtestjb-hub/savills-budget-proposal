## 1. Confirm the seed is the only source, before touching it

- [x] 1.1 Confirm `EXAMPLE_DEMAND` (`build_project_input_form.py`) is the sole place a fresh intake
      form's Staffing Demand headcount is seeded for these 8 roles — no template default or other
      code path competes with it. Verify by grepping the template and any other form-writing code for
      these role names, and by generating a fresh form and confirming each affected row's cell value
      traces back to this list.
      Done. Grepped all 8 role names across `source_code/`: 6 files match, but only
      `build_project_input_form.py`'s own `EXAMPLE_DEMAND` seeds a sheet — `generate_project_budget.py`/
      `generate_project_output.py`/`derive_position_staffing_ratios.py` only READ these names (ratio
      lookup tables, Vietnamese labels, source-data keyword matching), none seed a fresh form.
      `build_roster_input_form.py` has an identically-named `EXAMPLE_DEMAND` with the same bug pattern,
      but it is superseded, legacy code — `build_project_input_form.py`'s own docstring states it
      "Replaces the earlier split (build_roster_input_form.py + generate_roster.py..."; `run.py` never
      imports it, confirmed by grep. Out of scope, not touched. Generated a fresh form via the safe
      redirect technique (live file confirmed unchanged) and read back all 13 rows directly — every one
      currently shows `StaffPerDay = 1`, confirming the bug and that `EXAMPLE_DEMAND` is the live source.

## 2. Reseed the 13 affected rows

- [x] 2.1 Change `StaffPerDay` from `1` to `0` for: Reception, Property Manager, Chief Engineer,
      Building Executive, Customer Service (1 row each), Technician (3 shift rows), Shift Leader (3
      shift rows), Amenities Attendant (2 shift rows) — 13 rows total. Verify: generate a fresh intake
      form and confirm each of the 13 cells now holds `0`, matching the Assistant Property Manager /
      Accountant / Cashier rows' existing shape.
      Done. All 13 rows edited in `EXAMPLE_DEMAND`, generated a fresh form via the safe redirect
      technique (live file confirmed unchanged) and read back every row directly — all 13 now hold `0`,
      and the 3 pre-existing precedent roles (Assistant Property Manager/Accountant/Cashier) confirmed
      still at their original `0`, untouched by this edit.

## 3. Verification

- [x] 3.1 Generate a fresh intake form, then run it through `generate_project_budget.py` with a real
      Total NFA. For each of the 8 roles, confirm the resulting Staffing Demand headcount matches
      `_portfolio_headcount()`'s own computed value for that NFA (not the old flat `1`), and that each
      row's remark states the portfolio median, sample size, and the "peer buildings, not a Savills
      standard" disclosure — the same shape the 3-role batch already produces today.
      Done, end-to-end via `run_workflow()`'s protected harness (production files confirmed
      unchanged), not just the isolated function. Precomputed all 13 rows' expected values directly
      from `_portfolio_headcount()` at Total NFA=50,000 m², then generated a fresh reseeded form
      through the real pipeline at the same NFA — every one of the 13 rows matched the precomputed
      value exactly (Reception=2, Customer Service=4, PM/Chief Engineer/Building Exec=1 each,
      Technician all 3 shifts=2, Shift Leader 1/1/0, Amenities Attendant 2/1). Remark text on the
      analysis workbook's 'Staffing Estimate' sheet confirmed to state the median, sample size, and
      the required "not a Savills standard or statutory minimum" disclosure verbatim.
- [x] 3.2 Confirm a role split across shift rows (Technician, Shift Leader) still divides its total
      correctly across those rows post-fix — same `divmod` behavior as the 3-role batch, now exercised
      by 2 more roles for the first time. Verify by checking each shift row sums back to the role's
      whole-building total.
      Done: Technician's 3 shift rows (2+2+2=6) and Shift Leader's 3 shift rows (1+1+0=2) both
      confirmed against the same run's remark text, which independently states each role's
      whole-building total ("= 2 for the building, split across 3 shift rows" for Shift Leader) —
      the per-row values sum back to that stated total exactly.
- [x] 3.3 Confirm a genuine PM override still wins: type a real headcount onto one of the 13 rows
      after generating the form, regenerate/re-run, and confirm the typed number is used and the
      remark says "PM override," not a ratio-derived figure.
      Done: typed 5 onto Reception, ran end-to-end — result staff=5, remark reads "PM override — 5
      typed over this row's ratio suggestion on the Staffing Demand sheet, and used as typed."
- [x] 3.4 Confirm typing (or leaving) `0` on one of the 13 rows still lets the ratio apply — it does
      NOT zero the role out (per design.md's documented "delete the row to force zero" convention,
      unchanged by this fix). Verify the row still shows a ratio-derived, non-zero headcount.
      Done: explicitly set Property Manager to 0 (simulating a PM clearing the cell back to zero, not
      just the untouched seed), ran end-to-end — result staff=1 (the ratio's own computed value, NOT
      forced to 0), remark correctly shows the full portfolio-ratio derivation, not an override note.
      Confirms zero is indistinguishable from "not yet touched," exactly as design.md documents.
- [x] 3.5 Confirm the `EMH2`/`check_summary_reconciles` interaction survives this change. Reception is
      one of the 8 activated roles, and it is also the specific role `reconcile-summary-with-detail-
      sheets`' `EMH2` top-up formula names by hand (reads `A1. Staff cost` row 96 + a Reception top-up
      — see that change's design.md). `docs/project-status.md` already records `check_summary_
      reconciles`' EMH assertion breaking once before (during `fill-guideline-required-line-items`,
      when `EMH4` was added and the check's own `expected` value didn't follow) — the same shape of
      gap could recur here, now sourced from 8 roles' headcount instead of 1 new code. Verify: the
      `EMH2` top-up formula and `check_summary_reconciles`' EMH assertion both still hold after the
      reseed, on both Wayne Tower and the standard sample.
      Done. Ran the full 5-check suite against my own reseeded sample (Total NFA=50,000, Reception's
      headcount genuinely moved 1->2 via the ratio, not the frozen standard fixture — see 3.6's note on
      why the standard fixture alone can't exercise this). `check_summary_reconciles` reports OK — the
      EMH2 top-up formula and its assertion both hold with a real, ratio-changed Reception headcount
      flowing through. Wayne Tower's OWN real file is unaffected (its Staffing Demand cells are already
      non-zero/already-generated — see 4.1), so nothing to separately check there; confirmed via 3.6's
      Wayne-scale illustrative run instead.
- [x] 3.6 Run the full verification suite and confirm 0 unexpected differences beyond what this change
      itself is expected to move.
      **Manual spot-check required** (project rule — aggregation logic changed on client-facing
      figures): by hand, for Wayne Tower, confirm the new headcount for at least 2 of the 8 roles
      against `Fact_StaffingRatio_ByPosition.csv`'s own median and Wayne Tower's real NFA. Record the
      figures checked.
      Done, with one important caveat surfaced and one unrelated finding disclosed:
      - CAVEAT: `verification/fixtures/Sample_Project_Input.xlsx` (the standard regression fixture) has
        its OWN frozen 'Staffing Demand' sheet, still holding the pre-fix `1`s — it predates this
        change and is not regenerated by `EXAMPLE_DEMAND` on each run. Running the standard suite
        against it proves BACKWARD COMPATIBILITY (an already-generated project stays unaffected,
        exactly as design.md's Risk section requires), not that the new ratio fires — those are two
        different, both-necessary claims, and conflating them would have been a real verification gap.
        Used my own freshly-reseeded sample (task 3.1's) for the checks that need the ratio to actually
        fire (3.5 above), and the frozen fixture only to confirm no-regression.
      - UNRELATED FINDING: running the full 5-check suite against my reseeded sample surfaced that
        `check_required_line_items` fails on ESM4/ESM5 (pool chemicals/testing) being blank with no
        stated reason when a project has no pool — a real, pre-existing bug in
        `generate_project_budget.py`'s `if project.get('has_pool')` blocks (lines ~2078/2097), which
        skip writing ANY remark when false, unlike every other conditional Required code on that sheet.
        Confirmed by code inspection this is entirely unrelated to the 8 staffing roles this change
        touches — never previously surfaced because the standard fixture likely has a pool, and this
        session never ran the full check suite against a custom "no pool" sample before now. Flagged as
        a separate follow-up task (not fixed here — out of this change's scope) rather than absorbed
        silently or left undisclosed.
      All 4 checks THIS change is actually responsible for (`check_revenue_agreement`,
      `check_benchmark_reconciles`, `check_remark_content`, `check_summary_reconciles`) pass on the
      reseeded sample; the standard-fixture run (all 5 checks) is clean. Manual spot-check, Wayne
      Tower's real NFA (79,650 m²), by hand against `Fact_StaffingRatio_ByPosition.csv`'s raw figures:
      Property Manager — median 0.0161/1,000m² x 79.65 = 1.28 -> round -> 1 (matches computed). Reception
      — median 0.0332/1,000m² x 79.65 = 2.64 -> round -> 3 (matches computed). Both confirmed against
      the raw CSV, not just the function's own self-consistency.
- [x] 3.7 Production-file safety: hash-verify `EXAMPLE - Wayne Tower Thu Thiem.xlsx` and other
      production backups are unchanged after every test run in this task group.
      Done: `run_workflow()`'s snapshot confirmed the 4 tracked production files unchanged on every run
      in this task group. Wayne Tower's own hash independently re-confirmed identical to every earlier
      check this session (`4b6c1ae7a145970a0516a5a08e53e22a00ecfc2c195deef3a746fcc5a7e908de`).

## 4. Measure, spot-check, sign-off

- [x] 4.1 Generate the deliverable + analysis for Wayne Tower and the standard sample; for each,
      record the before/after headcount for all 8 affected roles and the resulting VND swing in staff
      cost and year-one surplus, broken out per role and totaled. Write the table to this change's
      `measured-effect.md`. Explicitly flag any role whose ratio-derived headcount is LOWER than the
      old flat seed, per design.md's Risk note — do not fold a downward move into a net total without
      calling it out.
      Done. Wayne Tower's own real file: zero movement, confirmed directly (its Staffing Demand cells
      are already generated/non-zero). Since it can't demonstrate magnitude, built an illustrative
      before/after at Wayne Tower's own real scale (Total NFA 79,650 m²) and ran BOTH through real
      Excel-COM recalculation (not cached/estimated values): Annual Staff Cost 4,293,950,777 ->
      5,280,013,355 VND (+986,062,578/year, +23.0%), Total Profit Value 5,927,173,356 ->
      4,941,110,778 VND (same swing, opposite sign — correct by construction), Margin 39.00% ->
      32.51%. This is the largest single swing of the three changes implemented this session. Also
      tested a smaller scale (NFA=50,000) and found + explicitly flagged the downward case design.md's
      Risk anticipated: Shift Leader's Night-shift row computes to 0 there (whole-building total 2,
      split 3 ways), lower than the old flat seed of 1 — stated plainly in `measured-effect.md`, not
      folded into the net total. Full detail, including the per-role headcount table, in
      `measured-effect.md`.
- [ ] 4.2 Present the measured movement, per role, to the Head of PM — including the reminder that
      these are portfolio medians describing peer-building behavior, not a Savills standard or a
      statutory minimum. Capture the sign-off in the change notes and `docs/05-decisions.md` before
      archiving.
- [ ] 4.3 Only after 4.2 sign-off: re-record whichever baseline(s) moved
      (`verification/baselines/baseline.json` and/or `deliverable_baseline.json`), with a `--reason`
      naming this change. Verify `verify.py` PASS on the following run.

## 5. Docs

- [ ] 5.1 Update `docs/05-decisions.md` (new decision entry) and `docs/project-status.md`. Verify both
      mention the change with the date and the signed-off figure movement.
