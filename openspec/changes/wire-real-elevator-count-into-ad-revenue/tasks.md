## 1. Intake field

- [x] 1.1 Add "Passenger Elevators per Tower" to the intake form's Project Info section
      (`build_project_input_form.py`), alongside Tower Count / Gate Count. Verify: a freshly-generated
      intake form has the new labelled cell, blank by default.
      Done: appended as its own "BUILDING DETAILS" section (row 56/57) rather than inserted next to
      Tower Count (row 10) — inserting there would shift every row below it (PRODUCT MIX etc.), the
      exact row-shift risk every other field added this session has avoided by appending instead.
      `read_input()` finds fields by label, not position, so this costs nothing functionally. Verified
      via the safe redirect technique (`bform.OUT`/`OUT_DIR`/`FINAL_OUT` rebound to scratch, mtime on
      the live `reports/Project_Budget_Input.xlsx` confirmed unchanged before/after): a freshly
      generated form has the field at row 57, blank by default.
- [x] 1.2 Add the field to `read_input()`'s project dict (`generate_project_budget.py`) as
      `passenger_elevators_per_tower`, optional per the established pattern (`L.value(...) if
      L.has(...) else None`). Verify: reading an OLDER intake workbook (without this field) does not
      raise, and returns `None` for it.
      Done and verified directly — an older-format workbook (missing the field entirely) reads back
      `None`, no exception.

## 2. Wire the override into both generators

- [x] 2.1 Write one shared helper (e.g. `_ad_frame_qty_and_note(project, tower_count)`) that returns
      the "Ad frame" row's quantity and remark — real-data quantity/wording when
      `passenger_elevators_per_tower` is set, today's unchanged fallback quantity/wording when it is
      not. Verify with both cases directly (unit-level, no full generation needed).
      Done, with one deliberate shape change from the example name/signature above, disclosed here
      rather than silently substituted: implemented as `_real_ad_frame_qty(project, tower_count)` in
      `generate_project_output.py`, returning ONLY the real quantity (or `None`) — not a combined
      quantity+remark tuple. Each of the two call sites already builds its own remark text in its own
      language/format (English `assumption` vs. Vietnamese `_AD_ITEM_VI`, an existing separation of
      concerns this codebase uses elsewhere too) — a helper that also tried to own remark text would
      have needed to speak both languages or reintroduce a translation step. The smaller helper keeps
      that separation intact and shrinks the diff. Verified directly: no field -> `None`; a set field
      (3/tower x 3 towers) -> `9`; an explicit `0` -> `None` (treated as "not entered," consistent
      with how blank/zero is already handled for other optional counts in this pipeline).
- [x] 2.2 Call the helper from `build_additional_revenue_sheet` (`generate_project_output.py`) for the
      "Ad frame" tuple only — the two LCD-screen tuples keep using `ELEVATOR_AD_ITEMS`'s own
      `qty_per_tower`/`assumption` exactly as today. Verify: a project with no elevator count supplied
      produces byte-identical Additional Revenue sheet output to before this change.
      Done: loop now uses `enumerate`, calls `_real_ad_frame_qty` only at `idx == 0`. Verified
      end-to-end (not just unit-level) via `run_workflow()`'s protected harness: with no field set, Qty
      remains 6 (2/tower x 3 towers) with the original unchanged assumption text; the two LCD rows
      (Qty 3 and 1) are identical in both the with- and without-field runs.
- [x] 2.3 Call the same helper from `fill_common_area_fund_sheet`'s RA1.A handling
      (`generate_project_budget.py`), including its Vietnamese remark via the existing `_AD_ITEM_VI`-
      style pattern (real-data sentence in Vietnamese, not just the English one translated ad hoc).
      Verify: a project with no elevator count supplied produces a byte-identical `2.2 Common area
      Fund` RA1.A row to before this change.
      Done: same `enumerate`/`idx == 0` pattern, with a Vietnamese real-data sentence
      ("Số liệu thực tế: dự án này có...") written alongside the existing Vietnamese assumption text,
      not a translation of the English one. Verified end-to-end: RA2 (lift-ad) row's monthly figure
      with no field set is 5,090,910 VND (= 848,485 x 6), byte-identical to the pre-change formula.
- [x] 2.6 (Added 2026-09-16, not in the original scope — user request: "if we have lift then also go
      along with the base[ment] and everything else relevant." See design.md's "Amendment (task 2.6)"
      note.) Checked first whether a basement-count FORMULA could be derived (floor count, parking
      slots) — real `Dim_Property_Residential.csv` data shows basement count tracks parking slots only
      loosely (1-basement buildings range 4-838 car slots) and floor count not at all — too noisy,
      same conclusion as the elevator-count research. So: a second manual field, "Number of
      Basements", added to PROJECT SCALE alongside Passenger Elevators per Tower (form row 18, shifting
      everything below by +1 — `_POOL_AREA` updated from `$B$38` to `$B$39` to match, same
      downstream-reference check as the earlier PROJECT SCALE reorganization). `read_input()` gains
      `basement_count`. New helper `_real_basement_lcd_qty(project)` (`generate_project_output.py`,
      same shape as `_real_ad_frame_qty`) returns the real count or `None`; both generators' loops now
      also check `idx == 2` (the "LCD screen (basement lobby)" tuple) alongside the existing `idx == 0`
      check — `idx == 1` (tower-lobby LCD) untouched under any input.
      Verify: (a) helper unit-tested directly — no field -> `None`; 2 basements -> `2`; explicit `0` ->
      `None` (treated as "not entered", same convention as the elevator field); (b) form layout
      verified via the safe redirect technique, live file confirmed unchanged; (c) full end-to-end
      test with BOTH fields set (3 elevators/tower, 2 basements, 3 towers) through `run_workflow()`'s
      protected harness.
      Done, all three verified on real data. (c): Ad frame Qty=9 (unchanged from task 2.2/2.3's own
      verification), LCD tower-lobby Qty=3 (unchanged fallback), LCD basement-lobby Qty=2 (real data,
      was flat-1 before this task) — deliverable's RA1.A (combined LCD line) = 5,757,575 VND/month =
      (1,212,121 x 3) + (1,060,606 x 2), exact arithmetic match. Production files confirmed
      byte-unchanged. Full 5-check regression suite re-run clean on the standard sample.

## 3. Verification

- [x] 3.1 Confirm both generators agree: given the same project with a real elevator count supplied,
      the deliverable's RA1.A revenue and the analysis workbook's Ad-frame revenue SHALL derive from
      the same quantity. Verify by generating both for one project and comparing.
      Done on real data: a synthetic project (3 towers, 3 passenger elevators/tower) run through
      `run_workflow()`'s protected harness shows Qty=9 on both sides — the analysis workbook's
      Additional Revenue sheet (Ad frame row, Source column stating the real-data derivation) and the
      deliverable's `2.2 Common area Fund` RA2 row (7,636,365 VND/month = 848,485 x 9) — same quantity,
      arithmetic checks out exactly.
- [x] 3.2 Confirm the LCD-screen lines are provably unaffected: generate the same project once with
      and once without the new field set, and diff every other `ELEVATOR_AD_ITEMS` row's quantity and
      remark — SHALL be identical in both runs.
      Done: both LCD rows (Qty 3 tower-lobby, Qty 1 basement-lobby) and their assumption text are
      byte-identical between the with-elevator-count and without-elevator-count runs — confirmed by
      direct comparison of both generated Additional Revenue sheets.
- [x] 3.3 Run the full verification suite and confirm 0 unexpected differences beyond what this change
      itself is expected to move.
      Done: full 5-check suite (`check_revenue_agreement`, `check_benchmark_reconciles`,
      `check_remark_content`, `check_summary_reconciles`, `check_required_line_items`) — 0 differences
      on the standard sample (which has no `passenger_elevators_per_tower` field at all), confirming
      this change is a no-op on any project that hasn't been asked the new question yet.
- [x] 3.4 Production-file safety: hash-verify `EXAMPLE - Wayne Tower Thu Thiem.xlsx` and other
      production backups are unchanged after every test run in this task group.
      Done: `run_workflow()`'s own snapshot confirmed the 4 tracked production files unchanged on
      every run in this task group. `EXAMPLE - Wayne Tower Thu Thiem.xlsx` specifically isn't in that
      tracked list, so hashed and mtime-checked it directly — mtime 2026-09-10 (predates today's
      session entirely), confirming nothing in this task group touched it (no test in this group ever
      referenced its path).

## 4. Measure, spot-check, sign-off

- [x] 4.1 Generate the deliverable + analysis for Wayne Tower and the standard sample: once with the
      field unset (confirm no figure moves) and once with a real supplied passenger-elevator count
      (confirm RA1.A / Additional Revenue move by the expected amount, and confirm whether the swing
      is in fact modest as proposal.md expects — state the actual figure either way). Write both to
      this change's `measured-effect.md`.
      Done, via `run_workflow.py`'s protected harness. Wayne Tower's real intake: zero movement
      confirmed directly (RA2 unchanged at 3,393,940 VND/month, qty 4, remark byte-identical — the
      field doesn't exist on it yet). Since Wayne Tower can't demonstrate the mechanism's magnitude,
      added a synthetic 3-tower illustration (matching the template's own worked example) using real
      per-device rates: qty 6->9, RA2 5,090,910->7,636,365 VND/month (+30.5M VND/year). Confirmed
      modest relative to the other two changes proposed this session, as proposal.md expected — stated
      as a measured comparison, not assumed. Full detail in `measured-effect.md`.
- [ ] 4.2 Present the measured movement to the Head of PM. Capture sign-off in the change notes and
      `docs/05-decisions.md` before archiving.
- [ ] 4.3 Only after 4.2 sign-off: re-record whichever baseline(s) moved, with a `--reason` naming
      this change. Verify `verify.py` PASS on the following run.

## 5. Docs

- [ ] 5.1 Update `docs/05-decisions.md` (new decision entry) and `docs/project-status.md`. Verify both
      mention the change with the date and the signed-off figure movement.
