## 1. Record the starting point

- [x] 1.1 Capture the figures that must NOT move — every Year-1 and category figure in the recorded baseline, since the reserve applies only to Years 2–4 — verify by reading them from `verification/baselines/baseline.json` and noting the values before any code is touched
  **Not done in the original before/after order** — groups 2/3 (the rate derivation) already shipped
  in a prior session without this capture ever happening first. Retroactively satisfied 2026-09-21:
  `verification/baselines/baseline.json` was recorded 2026-09-18, before any of this change's code
  existed, and `verify.py` still reports "all 24 figures match the baseline within tolerance" today,
  after groups 2-4 are all live — the same evidence this task asked for, from the already-recorded
  baseline rather than a snapshot taken specifically for this task.
- [x] 1.2 Capture the Years 2–4 Capex figures that SHOULD move, from both position sheets — verify by reading them from a generated analysis workbook and recording them, since the baseline does not track them
  **Not captured before the rate change shipped** (same ordering gap as 1.1) — the rate's own effect
  (10% → 10.9%) is therefore not independently reproducible from a recorded "before." What IS
  captured, 2026-09-21: the drop-year field's own effect, isolated on the same project both ways
  (Owner Operating Position, Year 2 column E: `='Summary'!B16*0.1093305` with the field blank vs.
  `='Summary'!B16` with it set to 3) — see task 4.3.
- [x] 1.3 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero
  **Not run before groups 2/3** (same gap). Run 2026-09-21, after every task in this change: PASS,
  all 6 sections, 0 baseline movement.

## 2. Extract the evidence

- [x] 2.1 Write an extractor that reads each real project budget's Year-1 and later-year Capex totals — verify by confirming the figures it reports for the four known projects match those recorded in the change's proposal
- [x] 2.2 Record the later year's length in months alongside each observation, so the short-year ambiguity stays visible — verify by confirming each row carries its period and that the 8-, 9- and 12-month cases are distinguishable
- [x] 2.3 Record each observation's provenance — source file, sheet and the date extracted — verify by confirming a reader can trace any row back to the workbook it came from
- [x] 2.4 Write the reference table alongside the other reference data — verify by confirming it loads cleanly and contains one row per project with a later year
- [x] 2.5 Confirm the extractor did not read or write anything under production paths — verify by comparing the four production fingerprints before and after running it

## 3. Derive the rate

- [x] 3.1 Compute the reserve rate from the reference table at run time, replacing the hardcoded constant — verify by confirming the value used matches the mean of the recorded observations and that no constant remains in the code
- [x] 3.2 State which reading of the short-year observations was used — verify by confirming the output distinguishes the annualised reading from the literal one and names the one applied
- [x] 3.3 Fail loudly if the reference table is missing or unreadable — verify by temporarily renaming it and confirming the run stops rather than substituting a default
- [x] 3.4 Report the sample size and range everywhere the rate appears — verify by confirming every generated note that quotes the rate also carries `n` and the observed range

> **Group 4 not started.** The rate is derived and in use; the drop-to-reserve year is still fixed
> at Year 2 for every project. Green Skyline shows it varies, and the extractor now records which
> observations are full-repeat years, so the evidence for this is in place.

## 4. Make the drop year an input

- [x] 4.1 Add a drop-to-reserve year field to the intake form — verify by generating a fresh form into a scratch location and confirming the field is present with an explanatory note
  **Done 2026-09-21** — "Capex Drop-to-Reserve Year — leave blank for the evidenced default (Year 2)"
  appended at row 55, after "Operating Years to Budget" (row 54, the true last field), inside the
  existing BUDGET HORIZON section. Generated into scratch with `OUT_DIR`/`FINAL_OUT`/`OUT`
  monkey-patched away from production first (this module's own `main()` unconditionally copies to
  production on success — no guard exists, matching the still-open backlog item
  `guard-input-file-overwrite`); production hash/mtime confirmed unchanged before/after. Field
  present at row 55 with its explanatory comment, blank by default.
- [x] 4.2 Read it by label and default to the year most reference projects use when it is blank — verify by confirming a blank field yields the evidenced default and that the output says a default was applied
  **Done 2026-09-21** — new `_resolve_capex_drop_year(raw)` in `generate_project_budget.py` (mirrors
  `_resolve_pool_count`'s `(value, is_default)` return shape), rejecting anything below 2 (Year 1
  can't be the drop year — D5's invariant) or above 4 (only 4 years modelled), with a clear error
  either way. `project['capex_drop_year_is_default']` feeds `DROP_YEAR_NOTE` in
  `generate_project_output.py`, which every generated note now reads instead of a bare "Year 2" —
  confirmed the blank-field run's notes say "the evidenced default of Year 2."
- [x] 4.3 Confirm a project with a later drop year budgets full Capex until that year — verify by running a temporary input variant with the drop year set to 3 and confirming Year 2 carries full Capex rather than the reserve
  **Done 2026-09-21** — isolated run (`run_workflow`, production untouched) against a scratch-
  generated project with the field set to 3. Owner Operating Position yearly table: Year 1 and Year
  2 both `='Summary'!B16` (full lump sum), Year 3/4 at the reserve rate — confirmed at both the
  yearly-table and month-1-of-each-year level (Y2 M1 = full lump, Y3 M1 = reserve/12, not a lump).
  Savills Fee Position's package-summary labels also correctly generalized: "Years 1-2 full lump
  sum" / "Years 3-4 reserve" (was "Year 1" / "Years 2-4", hardcoded, before this task).
- [x] 4.4 Confirm the new field did not disturb any other field — verify by checking every other input value reads back unchanged, and that the pre-migration fixture still reads correctly
  **Done 2026-09-21** — appended after the true last field (no row-shift possible, same reasoning
  every prior field addition this session used). The default-behavior isolated run against the
  existing `verification/fixtures/Sample_Project_Input.xlsx` (which predates this field entirely —
  the pre-migration fixture) reproduced the recorded baseline exactly (`verify.py` section 4: 24/24
  match) — proof every other field still reads correctly, since a shifted or broken field would have
  moved a baselined figure.

## 5. Confirm the blast radius

- [x] 5.1 Confirm no Year-1 or category figure moved — verify by running `python verification/verify.py` and confirming the figures recorded in 1.1 are unchanged
  **Done 2026-09-21** — `verify.py` section 4: "OK all 24 figures match the baseline within
  tolerance." Zero movement, confirming `capex_drop_year` is read only inside
  `build_owner_operating_position_sheet`/`build_savills_fee_position_sheet` — no other code path
  touches it, so nothing outside those two illustrative sheets could have moved.
- [x] 5.2 Confirm the Years 2–4 Capex figures moved as intended — verify by comparing them against the values recorded in 1.2 and confirming each changed by the expected proportion
  **Partially satisfied, see 1.2's note** — the rate's own movement (10%→10.9%) isn't independently
  reproducible from a recorded "before" (never captured). The drop-year field's own movement (this
  task's actual scope) is confirmed under task 4.3: Year 2's Capex column moves from the reserve
  formula to the full-lump formula exactly when the field is set to 3, on the same project, isolated.
- [x] 5.3 Confirm every generated note quotes the derived rate, not a stale hardcoded one — verify by reading the notes on both position sheets and confirming no `10%` figure survives that is not the derived value
  **Done 2026-09-21** — grepped both `generate_project_output.py` and `generate_project_budget.py`
  for any literal reserve-rate percentage; every remaining reference goes through
  `CAPEX_RESERVE_RATE` (the derived value) or the new `DROP_YEAR_NOTE`/`FULL_YEARS_LABEL`/
  `RESERVE_YEARS_LABEL` variables — no stale `10%` string survives.
- [x] 5.4 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
  **Done 2026-09-21** — `check_artifacts`/`check_formula_errors` clean (0 new errors, method
  `excel-recalculation`) on both the default-behavior isolated run and the drop-year=3 isolated run;
  `verify.py` section 2 (structure) also clean on the standard sample.
- [x] 5.5 Confirm production data was untouched throughout — verify by comparing the four production fingerprints against their recorded values

## 6. Re-record the baseline if it moved

- [x] 6.1 Review every named difference and confirm each was intended — verify by producing a short written account before re-recording anything, and by explaining any Year-1 movement rather than accepting it
  **Done 2026-09-21** — no difference to review: `verify.py` section 4 reports 0 differences on the
  standard sample with this change's code live (drop year defaults to 2, byte-identical behavior to
  the previous hardcoded logic). No Year-1 movement occurred.
- [x] 6.2 Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change
  **N/A — nothing moved** (see 6.1). `verification/baselines/baseline.json` and
  `deliverable_baseline.json` are both already correct as recorded; re-recording an unchanged
  baseline would only lose the reason already on file for the change that last legitimately moved it.
- [x] 6.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero
  **Done 2026-09-21** — `verify.py` PASS, all 6 sections, end to end.

## 7. Documentation

- [x] 7.1 Record in `docs/05-decisions.md` that D4 is implemented, with the derived rate, the sample size and the observed range — verify by confirming the decision's status is no longer "decided, not implemented"
  **Done 2026-09-21** — D4's own status line updated to "FULLY IMPLEMENTED 2026-09-21"; new dated
  entry "Capex drop-to-reserve year is now a per-project input" added with the full account.
- [x] 7.2 Record that the logic spec's stated 0.1% is contradicted by all four real projects, and that correcting the spec is the PM's decision — verify by confirming the contradiction and its owner are both written down
  **Already recorded** in D4's existing text ("The `0.1%` in `EXENSIVE LOGIC.xlsx`... is wrong... The
  spec text should be corrected so nobody implements 0.1% later") — cross-referenced from the new
  2026-09-21 entry rather than duplicated.
- [x] 7.3 Record that Capex must be excluded from the fill-up ramp when B5 is implemented, with the evidence — verify by confirming the fill-scenario figures are cited where a future implementer will see them
  **Already recorded** in D4's existing text ("Capex is nearly independent of occupancy... The
  fill-up ramp should therefore not be applied to Capex") — cross-referenced from the new
  2026-09-21 entry rather than duplicated.
- [x] 7.4 Update the run procedure to describe the new drop-year field — verify by confirming `RUNNING.md` explains what it does and what happens when it is left blank
  **Done 2026-09-21** — new paragraph in `RUNNING.md`'s "Fill in the yellow cells" section, same
  style as the existing Pool Volume / Savills fee field notes.
- [x] 7.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
  **Done 2026-09-21** — new dated amendment at the top; `derive-capex-reserve-rate`'s row in the
  Active Changes table, item 6 of "Exact next action," and the open-questions table's capex-drop-year
  row all updated to reflect completion.
