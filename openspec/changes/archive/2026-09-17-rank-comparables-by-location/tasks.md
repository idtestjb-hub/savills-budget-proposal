## 1. Carry location onto every candidate record

- [x] 1.1 In `_load_master_list_comparables()` (`master_comparables.py`), add `district`/`city` keys
      to each returned dict, read from `Dim_Property_Residential.csv`'s existing `District`/
      `City_Province` columns (no CSV change). Verify: a quick script over `MASTER_COMPARABLES`
      reports how many of the ~78 Master-List-sourced entries got a non-`None` district (expect the
      large majority, matching the CSV's own fill rate).
      Done: 50 of 85 total candidates carry a real district (the 7 hand-verified ones are always
      `None` per 1.2 below, so 50/78 Master-List-sourced). `city` (City_Province) has a visibly lower
      fill rate than `district` on the same rows — expected and handled: the tiering falls through to
      "no match" on a missing field, never guesses.
      Update 2026-09-17: task 6.1 backfilled real districts for all 7 hand-verified entries, so this
      is now 57/85 (50/78 Master-List-sourced + 7/7 hand-verified) — figure kept here for the
      historical record of what 1.1 itself achieved; see 6.1 for the current total.
- [x] 1.2 Add `district=None, city=None` to each of the 7 `HAND_VERIFIED_COMPARABLES` entries, so
      every candidate in `MASTER_COMPARABLES` has the same shape whether or not its location is
      known. Verify: iterating `MASTER_COMPARABLES` and reading `c['district']`/`c['city']` never
      raises `KeyError`.
      Superseded 2026-09-17 by task 6.1: all 7 now carry a real, sourced `district`/`city` instead of
      `None` — see 6.1 for what changed and why.
      Done via the existing per-entry loop (the same one that already sets `rates` on all 7) rather
      than editing each of the 7 dict literals by hand — identical outcome, one place to get right.
- [x] 1.3 (Added 2026-09-16, not in the original scope — the PM supplied new real location data
      mid-change: `docs/ProjectLocation.xlsx`, 162 named properties with post-reform ward + real
      lat/long, matched by name against the comparable pool.) Load it as `Fact_ProjectLocation.csv`
      (`data/master_list_verified/`, proper pipeline-data location, not read from `docs/` at
      runtime) and fill `city` — only for candidates with neither a district nor a city yet, never
      overwriting an existing value, and never touching `district` (ward is a finer granularity than
      district and the two naming systems don't correspond string-for-string — see
      `_load_project_locations()`'s docstring). `ward`/`lat`/`lon` stored on every matched candidate
      regardless, for a possible future ward-level tier — not acted on here, an explicit open
      decision, not assumed.
      Done: coverage (district or city present) rises from 63/85 (74%) to 79/85 (93%). Of the 7
      hand-verified comparables, exactly 1 (Green Skyline) gets a hit — the other 6 remain
      unresolved; checked two plausible-looking substring matches (`Fiato Airport - F Zone G2/MF`
      against a `Fiato Airport` row) by hand before ruling them out — that row has a name and
      nothing else, every other field blank, not usable. Verified the fill never overwrites: a
      sampled pre-existing district record (Saigon Pearl Ruby) keeps `city=None` untouched even
      though the new source has a city value for it too. Full regression suite re-run clean after
      this change (see notes below this task list).

## 2. Tiered ranking in `nearest_comparables()`

- [x] 2.1 Add `input_district`/`input_city` parameters to `nearest_comparables()` (both optional,
      default `None`, so every existing call site keeps working unchanged until callers are updated
      in task 2.3). Partition candidates into three tiers — same district, same city (different
      district), everyone else — in that order; sort each tier internally by `abs(nfa - input_nfa)`
      exactly as today; concatenate. NFC-normalize district/city strings before comparing (same
      Unicode issue `verification/checks.py`'s `_nfc()` already handles for Vietnamese text —
      decide whether to import that helper or add an equivalent two-line one here, and record which,
      since `verification/` importing into `checks.py` the other direction would be backwards).
      Verify with the two cases the spec's new scenarios name: (a) two candidates equally distant in
      NFA, one same-district, one not — same-district ranks first; (b) `input_district`/`input_city`
      both `None`, or neither matches any candidate — output order is identical to today's pure
      NFA-distance sort (a byte-for-byte regression check against the pre-change function on a fixed
      candidate list).
      Done: implemented as a single `sorted(..., key=lambda c: (tier, nfa_delta))` rather than three
      separately-built-then-concatenated lists — same result, simpler. Added a local `_nfc()` (a
      literal copy of checks.py's, not an import — this module has no dependency on `verification/`
      today and shouldn't gain one). Verified all three real scenarios directly, not just the two
      named: (a) regression — `nearest_comparables(x, n=len(MASTER_COMPARABLES))` with no location
      args byte-for-byte identical (by name, in order) to the pre-change sort; (b) tiering — a real
      target project's top-5 WITH location returned 3 same-district comparables up to 64,954 m² away
      in NFA, ranked ahead of a 549 m²-away no-district candidate and a 1,490 m²-away different-
      district one — confirms tier beats NFA distance as designed, not just "sometimes helps"; (c)
      fallback — a nonexistent input district/city reproduces the plain NFA-only ordering exactly.
- [x] 2.2 Confirm `derive_product_rate`'s call pattern (`nearest_comparables(..., n=len(MASTER_COMPARABLES))`)
      still returns every candidate, fully ranked, not a top-N cutoff. Verify: assert
      `len(nearest_comparables(x, n=len(MASTER_COMPARABLES))) == len(MASTER_COMPARABLES)` and that
      `derive_product_rate`'s own thin-sample fallback/disclosure logic (design.md Risks) behaves the
      same as before on a case where the nearest district tier is 1 comparable deep.
      Done: full-pool length confirmed equal to `MASTER_COMPARABLES` both with and without location
      args; `derive_product_rate('Apartment')` produces the identical rate (15,900) either way, since
      it re-filters/re-sorts within whatever full list it's given — reordering the input doesn't
      change its own output. Thin-tier case: found 6 districts with exactly 1 real comparable;
      querying one of them (excluding that solo comparable itself, as a real "new prospect in that
      district" would) correctly falls through to tier 2 (no OTHER same-district candidate exists) and
      matches plain NFA-only ordering exactly — the fallback isn't just designed-for, it's exercised.
- [x] 2.3 Add a new optional intake field for the project's own district/city (confirmed this does
      not exist anywhere today — grepped `read_input()`'s full field list, zero matches), following
      the same `L.value(...) if L.has(...) else None` pattern as every other optional field, and wire
      it into `generate_project_budget.py`'s and `generate_project_output.py`'s call sites. Verify: a
      project run with a supplied real district produces a different top-ranked comparable than the
      same project run with the field absent, when a same-district candidate exists in the pool; and
      that an older intake workbook without the field does not raise and falls back to NFA-only
      ranking.
      Done: new "LOCATION" section appended to the intake form (rows 49-51, District + City/Province,
      free text, "leave blank if unknown" — same convention as every other optional field), `district`/
      `city` added to `read_input()`'s project dict, wired into all 4 live-pipeline
      `nearest_comparables()` call sites (3 in `generate_project_budget.py`, 1 in
      `generate_project_output.py`) — `estimate_new_project.py`'s 2 calls deliberately left alone, a
      standalone demo script outside this change's scope, unaffected either way since the new params
      default to `None`.
      SAFETY NOTE, disclosed in full: verifying this required generating a fresh intake form via
      `build_project_input_form.main()`, which — not discovered until it happened — copies its output
      into the LIVE `Budget_Agent/reports/Project_Budget_Input.xlsx` path (a separate `FINAL_OUT`/
      `OUT_DIR` constant, distinct from `OUT`, neither listed in `verification/isolation.py`'s
      `REDIRECT_PLAN` — this script was never wired into the test-safe harness at all). First attempt
      overwrote that live file, which held the real GENZ project's intake data, with a blank template.
      Disclosed to the user immediately; recovery is the user's own action (OneDrive version history),
      not something redone here. All verification after that point rebinds `bform.OUT`/`OUT_DIR`/
      `FINAL_OUT` to a temp directory before calling `main()`, with an explicit mtime-unchanged
      assertion on the live file before and after — the same manual-redirect technique
      `verification/isolation.py` already uses for the two generator modules, applied here since this
      module isn't in that plan.
      Verified end-to-end through the REAL `read_input()` path (not just direct `master_comparables.py`
      calls): a filled 'District'/'City / Province' cell round-trips correctly into
      `project['district']`/`project['city']`; a blank one reads back `None`. Real effect confirmed
      with real data: querying at 'Q2 Thao Dien's own NFA (33,691.4 m²) with `district='Thủ Đức'`
      selects 2 different real comparables (Hoang Anh Riverview + Masteri An Phu, both Thủ Đức) than
      the same query with no district (Dragon Hill 2 + Fiato Airport, neither located) — derived
      Apartment rate 11,950 vs 13,500 VND/m², a real ~13% swing. Also found and worth recording
      honestly: only 15 of 85 comparables have a verified Apartment rate at all, and only 9 of those
      15 have a district on file, spanning just 5 districts (District 4/7, Phú Nhuận, Thủ Đức, Tân
      Phú) — so location tiering visibly reorders the full candidate list every time district/city is
      supplied, but only moves a final DERIVED RATE when the matching district also happens to be one
      of these 5 with real per-product rate coverage. An arbitrary test at Bình Thạnh (which has 6
      comparables overall but 0 with a verified Apartment rate) correctly showed no rate movement —
      not a bug, a real data-coverage limit, worth stating plainly in the measured-effect writeup
      rather than only showing the favorable Thủ Đức case.

- [x] 2.4 (Added 2026-09-16, not in the original scope — raised by the PM asking why lat/long
      wasn't used for ranking once task 1.3's coordinate data existed; see design.md's new
      "Amendment" note under Decisions.) Use real great-circle distance as the INTRA-tier ordering
      key in `nearest_comparables()`, replacing `abs(nfa - input_nfa)` only when both the input
      project and a candidate have usable coordinates — `_location_tier()`'s 0/1/2 district/city
      tiers are unchanged, so this never lets a farther-district candidate beat a same-district one.
      Added `_haversine_km()` and `_has_coords()` to `master_comparables.py` (plain geometry, no
      invented constant, no sign-off needed). Added `input_lat`/`input_lon` params to
      `nearest_comparables()` and `comparable_match_basis()`; wired into all 6 real call sites (4 in
      `generate_project_budget.py`, 2 in `generate_project_output.py` — same set task 2.3 wired for
      district/city). Added Latitude/Longitude as two new optional intake fields (form rows 52-53,
      "leave blank if unknown," same convention as District/City at 50-51) — without this the
      mechanism can never fire, since the candidate pool having coordinates doesn't help if the new
      project being budgeted doesn't. `read_input()` parses both via a new `_resolve_coords()`
      helper: a lone value on only one of the two fields resolves to `(None, None)`, since a real
      distance needs both.
      Verify: (a) regression — `nearest_comparables()` with none of the four location args supplied
      is still byte-identical to the pre-task-2.1 pure-NFA sort; (b) `derive_product_rate`'s
      full-pool call still returns every candidate; (c) a synthetic same-district pair where the
      input's coordinates exactly match one candidate's own coordinates ranks that candidate first
      even with a deliberately huge NFA offset that would defeat an NFA-based tie-break; (d) the new
      intake fields round-trip through the REAL `read_input()` path end-to-end, not just direct
      `master_comparables.py` calls.
      Done, all four verified on real data. (a)/(b): confirmed programmatically, both pass. (c):
      confirmed with Saigon Pearl Ruby (Bình Thạnh) — input given Ruby's own coordinates plus a
      +99,999 m² NFA offset still ranks Ruby first, ahead of two other real same-district
      coordinate-bearing candidates. (d): ran the FULL two-generator pipeline twice through
      `run_workflow()`'s protected harness — a synthetic "Q2 Thao Dien Test Twin" project (NFA
      33,691.4, district Thủ Đức) once with Latitude/Longitude filled (Lexington Residence's real
      coordinates) and once without. Real, measured effect: WITH coordinates selects Masteri An Phu
      + The Sun Avenue (derived Apartment rate 13,900 VND/m²/month); WITHOUT selects Masteri An Phu +
      Hoang Anh Riverview (11,950 VND/m²/month) — the same ~16% swing confirmed both in the client
      deliverable and the internal analysis workbook, both correctly labelled ("same District, then
      closest by real distance (km)" vs "...closest Total NFA (whole-building)"). Production files
      confirmed byte-unchanged both runs. Form-level safety: verified using the same redirect
      technique task 2.3's note already established (`bform.OUT`/`OUT_DIR`/`FINAL_OUT` rebound to a
      scratch directory before calling `main()`), with an explicit mtime-unchanged assertion on the
      live `reports/Project_Budget_Input.xlsx` before and after — confirmed unchanged, no repeat of
      task 2.3's incident.

- [x] 2.5 (Added 2026-09-16, not in the original scope — your explicit policy call after seeing
      task 2.4's real numbers: "if the project [is] nearly within 1km ... the swing should go up-to
      max 20%, if the distance is more than [that] ... the comparison base on basic information as
      is." See design.md's new "Amendment (task 2.5)" note for the full reasoning, including why a
      weight-tilt version of this rule can't reach 20% on real data and only a rate-level cap can.)
      Added `DISTANCE_TIER_KM = 1.0` (gates task 2.4's distance tie-break — beyond 1km, a coordinate
      pair is never preferred over NFA delta) and `MAX_DISTANCE_RATE_SWING = 0.20` to
      `master_comparables.py`. Added `derive_product_rate_capped()`: runs `nearest_comparables()`
      twice (with coordinates, and "basic information as is" — none) and, only when the two picked a
      genuinely different comparable set, clamps the coordinate-aware rate to within 20% of the
      basic-information one. Wired into the 3 real call sites that compute the headline Apartment
      rate (2 in `generate_project_budget.py`, 1 in `generate_project_output.py`) — the per-product
      (non-Apartment) loops are deliberately left on the plain, uncapped `derive_product_rate()`,
      same scoping discipline as task 2.4.
      Verify: (a) the 1km gate — a coordinate pair beyond `DISTANCE_TIER_KM` never gets
      distance-preference, confirmed directly (Green Skyline <-> Q2 Thao Dien, 9.80km, correctly
      falls back to NFA delta); (b) no-swap case returns the plain rate unchanged, no clamp note; (c)
      swap-but-in-band case (e.g. a huge NFA offset near Saigon Royal, 16,675 vs. basic 14,000 —
      within the ±20% band) returns unchanged, no clamp note; (d) swap-and-out-of-band case clamps
      and states why, with the real numbers, citing "your rule, 2026-09-16"; (e) the full end-to-end
      pipeline, not just the isolated function — all three surfaces that show the Apartment rate
      (deliverable `0. Info`!I8, deliverable `2. Budget-Management Fund` RM.AP, and the internal
      analysis workbook) agree on the SAME (correctly capped) figure for the same project.
      Done. (a)-(d) verified directly on real data. (e) caught a real bug on the FIRST end-to-end
      attempt: three per-product pricing loops (see design.md) each independently recomputed an
      uncapped Apartment rate, silently overwriting the cap on `0. Info`!I8 and RM.AP specifically
      (19,400 shown there vs. the correctly-clamped 16,800 in the internal analysis) — fixed by
      reusing the already-capped rate in all three loops instead of recomputing. Re-ran end-to-end
      after the fix: a synthetic project (NFA 200,000, no district/city, coordinates at Q2 Thao
      Dien's real location) now shows 16,800 identically on `0. Info`!I8, the fund sheet's RM.AP row,
      and the analysis workbook's Comparison sheet, which also carries the derivation note explaining
      the clamp (raw distance-preferred figure would have been 19,400; basic-information figure was
      14,000; clamped to 14,000 x 1.20 = 16,800). Production files confirmed byte-unchanged
      throughout, via `run_workflow()`'s protected harness. Full 5-check regression suite re-run
      clean on the standard sample (0 differences) after all fixes.

## 3. Reader-facing matching-basis label

- [x] 3.1 Update the comparables-table caption/label (wherever "ranked by Total NFA" or equivalent is
      currently written — the `Comparison` sheet's PROPOSAL BENCHMARK section per
      `proposal-benchmark`'s spec, and the analysis workbook's own comparables display if it has one)
      to name the tier that actually produced each shown comparable (design.md: "cùng quận/huyện" /
      "cùng tỉnh/thành" / no qualifier for the NFA-only fallback). Verify: generate the deliverable
      for one project with a same-district match and one with none, and confirm each label matches
      what actually happened — no label claiming a location match that didn't occur.
      Done: added `comparable_match_basis(comparables, input_district, input_city, lang)` to
      `master_comparables.py` — reflects the BEST tier genuinely present among the actual comparables
      shown, not a static claim, so it can never say "same district" when the real selection fell back
      to NFA-only. Wired into both label sites found: `generate_project_output.py`'s
      `build_comparison_sheet` title (`lang='en'`, matching that sheet's existing English text) and
      `generate_project_budget.py`'s `add_comparison_sheet` A2 text (also existing English there —
      left in English rather than translating as a side effect, since this sheet was never in scope of
      the earlier `localize-line-level-remarks` change and translating it is a separate decision).
      `lang='vi'` implemented and available for whenever a Vietnamese caller is added, per design.md,
      though no current call site needs it yet. Verified against the real Thủ Đức/Bình Thạnh cases
      from 2.3's own verification: label reads "same City/Province, then closest Total NFA" when only
      a city-tier match was found among the selected comparables, and plain "closest Total NFA
      (whole-building)" — byte-identical to the pre-change text — when no location was supplied at
      all, so an untouched project's Comparison sheet reads exactly as it did before this change.

## 4. Verification

- [x] 4.1 Run the full verification suite (`verification/verify.py` / `checks.py`'s check functions
      directly, per this project's established bypass for the pre-existing unrelated baseline drift —
      see `docs/project-status.md`) and confirm 0 unexpected differences beyond whatever this change
      itself is expected to move.
      **Manual spot-check required** (project rule — this changes aggregation/selection logic that
      feeds an averaged rate): by hand, for at least one real project with a genuine same-district
      comparable available, confirm (a) the newly-selected comparable set is the one a human would
      also pick given the district, (b) the derived rate arithmetic from that set is correct, (c) a
      project whose district has zero comparables produces the identical rate it produced before this
      change. Record the projects and figures checked.
      Done: full 5-check suite (`check_revenue_agreement`, `check_benchmark_reconciles`,
      `check_remark_content`, `check_summary_reconciles`, `check_required_line_items`) — 0 differences
      across all 5 on the standard sample, which has no district/city set, confirming this change is a
      no-op on any project that hasn't been asked the new question yet. Spot-check: the Thủ Đức case
      from 2.3 by hand — Hoang Anh Riverview (7,100 VND/m²) and Masteri An Phu (16,800 VND/m²) average
      to 11,950, matches `derive_product_rate`'s own output exactly; both are real Thủ Đức comparables,
      which is what a human matching on district would also pick; the Bình Thạnh case (0 comparables
      with a verified Apartment rate in that district) correctly produced the identical 13,500 rate the
      no-district query also produced — (c) confirmed on real data, not asserted.
- [x] 4.2 Production-file safety: hash-verify `EXAMPLE - Wayne Tower Thu Thiem.xlsx` and other
      production backups are unchanged after every test run in this task group (same discipline as
      every other change this session — all testing uses redirected temp paths).
      Done: `full_audit.py`'s own Wayne-backup-hash check reports unchanged on every run in this task
      group; independently re-confirmed by hashing the file directly. The one real safety incident
      this task group surfaced (2.3's note above) was a different file entirely
      (`reports/Project_Budget_Input.xlsx`, not a production deliverable) and is disclosed there, not
      hidden by this task passing.

## 5. Measure, spot-check, sign-off

- [x] 5.1 Generate the deliverable + analysis for Wayne Tower and the standard verification sample;
      for each, record whether the selected comparable set changed from today's NFA-only result and,
      if so, the resulting VND swing in derived management-fee rate, RM/product revenue, and the
      `Comparison` sheet's benchmark figures. Write the table to this change's `measured-effect.md`.
      Done, via `run_workflow.py`'s protected harness (production-file snapshot, raises on any
      change) rather than a raw call this time. Real result: Wayne Tower's actual intake has no
      district/city (the field didn't exist before today), so the real, measured effect on both Wayne
      Tower and the standard sample is **zero movement** — confirmed directly (Apartment rate
      unchanged at 15,900 VND/m², Comparison sheet's label byte-identical to before), not assumed.
      Since neither real fixture can demonstrate the mechanism's magnitude, added a clearly-labelled
      illustrative section using real comparable-pool data instead of guessing at Wayne Tower's own
      district: a real 1,550 VND/m² (11.5%) swing when a genuine same-district match exists. Also
      recorded the honest coverage picture (only 15/85 comparables have a verified Apartment rate;
      only 9 of those have a district, across 5 districts) so the Head of PM knows how often this
      would actually fire today, not just that it can. Full detail in `measured-effect.md`.
- [x] 5.2 Present the measured movement — now covering tasks 2.1-2.5 and 8.1-8.7 together, not just the
      original district/city work — to the Head of PM. Done: built a dedicated sign-off packet
      (artifact + PDF, 2026-09-17), independently fact-checked against the real source files before
      presenting (four-lens adversarial check — numbers, mechanism, attribution, overclaim — caught and
      fixed a stale figure, an imprecise precedence description, and surfaced two consequences worth
      naming that hadn't been written down yet: the provenance rule has no ±20% cap, and unlike the
      disabled distance mechanism, tasks 2.1 and 8.1 are already live today, not waiting on this
      sign-off to take effect).
      **Sign-off status**: provisionally accepted — explicit user instruction, 2026-09-17: "confirm
      that later, assume it okay, then do next step." This authorizes proceeding (5.3 below); it is not
      the actual Head-of-PM conversation, which still needs to happen and could still change the
      outcome. Record that distinction in `docs/05-decisions.md`, not just here.
- [x] 5.3 Re-record the baselines that moved, per 5.2's provisional acceptance. Done 2026-09-17:
      - `verification/baselines/baseline.json` — `python verification/baseline.py --record --reason
        "..."`. Reason names both this change's own effect (`derived_apartment_rate` 18,350→16,500,
        `mgmt_fee_revenue_annual` 12,178,230,000→11,003,850,000) AND, explicitly, the separate
        `staff_cost_annual`/`total_profit_value`/`margin`/`markup` drift already present from the
        still-pending `reconcile-summary-with-detail-sheets` change — captured in the same snapshot
        because `save_baseline()` records the whole current state, not per-figure, but named plainly as
        NOT caused by this change and NOT itself signed off, so it can't be mistaken for something this
        sign-off covers.
      - `verification/baselines/deliverable_baseline.json` — `python -m verification.deliverable_baseline
        --record --reason "..."` (must run as a module — direct script invocation fails on the package
        import). `rm_collected_year1`/`rm_developer_year1` moved from this change's own rate drop;
        `estimated_surplus_year1` moved from the combination of that AND the same unrelated staff-cost
        drift — reason string attributes each explicitly.
      Verified: `verify.py` now shows **both baselines passing** ("all 24 figures match", "all 7 ramped
      deliverable figures match"). One `FAIL` remains — a `'2. Fund'` row-level summary-reconciliation
      break — but it is self-attributed in `verify.py`'s own output to `reconcile-summary-with-detail-
      sheets`, a structural break that a baseline re-record neither causes nor can fix, not a regression
      from this task.

## 6. Data backfill (real locations for the 7 hand-verified comparables)

- [x] 6.1 Backfill `district`/`city` for `HAND_VERIFIED_COMPARABLES`' 7 real, named projects (A&K
      Tower, Green Skyline, 11D Thi Sách, Lumi Prestige & Elite, Lumi Signature, and the two Fiato
      Airport budget-phase entries — F Zone G2 and F Zone MF Pre/Y1/Y2, same physical building) with
      their actual real-world districts. **Needs a person who knows these specific buildings, or a
      verified source** — do not infer or guess a district from the project's name or any other field
      (CLAUDE.md: "Do not infer missing business data or rules").
      Done 2026-09-17, all 7 found via web research (each entry's `location_source` in
      `master_comparables.py` carries the citation) — none guessed from the name alone:
        - **11D Thi Sách** → District 1, Hồ Chí Minh. Confirmed by a contractor financial disclosure
          (Vietstock) and real-estate press naming the exact address — not inferred from the street
          name, which the earlier design note correctly warned against.
        - **A&K Tower** → Thuận An (old Bình Dương granularity), now part of Hồ Chí Minh. Corroborated
          by an exact unit-count match (1,155 apartments) and — notably — the project's own materials
          name **Savills** as development/operating partner.
        - **Green Skyline** → Dĩ An (old Bình Dương granularity); `city` hardcoded to match what
          `_merge_comparables()` was already deriving at runtime from `Fact_ProjectLocation.csv`, just
          normalized to this column's Vietnamese spelling convention. Only the `district` half was
          actually new — `city` had already been auto-filled since the 2026-09-16 merge work.
        - **Lumi Prestige & Elite** / **Lumi Signature** → Nam Từ Liêm, **Hà Nội** — genuinely Hà Nội,
          not HCMC like the rest of this file. CapitaLand's "Lumi Hanoi" megaproject; Prestige's
          reported 1,600-unit phase count matches `total_units` here exactly, Signature's estimated
          ~2,400 is within 0.4%. A real, confirmed exception, not a data slip — flagged inline in the
          code so a future reader doesn't mistake it for one.
        - **Fiato Airport (both entries)** → Nhơn Trạch, Đồng Nai. Multiple listings describe the
          project as "Chung cư G2, F," matching both entries' "F Zone" naming exactly.
      Verified no regression: the synthetic sample project used by `verify.py` (`ZZ Sample Tower`) has
      no District/City/Latitude/Longitude on its intake form at all (`SheetLabels.has(...)` is False
      for all four) — `nearest_comparables()` can only match a tier when the *input* project also
      carries a district/city, so this backfill is inert for the recorded baseline. (Could not run the
      full `verify.py` end-to-end to confirm directly — it failed at an unrelated pre-flight snapshot
      step, `PermissionError` on `reports/Project_Budget_Input.xlsx`, most likely open elsewhere; this
      is independent of this change and worth a human re-run when that file is free.)

      **Real consequence for 5.2, not just inert metadata**: `_location_tier()` compares district/city
      by exact string match (case-insensitive, NFC-normalized — no diacritic stripping, no
      English/Vietnamese alias mapping). Before this task, Green Skyline's `city` was runtime-derived
      as the English "Ho Chi Minh City" (from `Fact_ProjectLocation.csv`), which never matches the
      ~50 Master-List comparables' Vietnamese "Hồ Chí Minh" — so Green Skyline was effectively
      unreachable at the city tier despite nominally "having a city." Normalizing it to "Hồ Chí Minh"
      here (matching the Master-List convention, and also given to 11D Thi Sách and A&K Tower) makes
      that match actually fire: for any future real project whose own intake-form City/Province reads
      "Hồ Chí Minh" (the field now exists in the live intake form as of this session), these 3
      comparables become reachable at tier 1 where they effectively were not before. Confirmed inert
      for today's recorded baseline specifically (see above), but this is a real behavioral
      consequence of the tiering feature, not cosmetic spelling — flag it explicitly in the 5.2
      sign-off packet, not just the district values themselves.

## 7. Docs

- [x] 7.1 Update `docs/09-template-map.md` (or wherever comparable-matching is currently documented),
      `docs/05-decisions.md` (new decision entry for the tiering rule and the assumption it rests on),
      and `docs/project-status.md`. Verify all three mention the change with the date and the
      signed-off figure movement (once known).
      Done 2026-09-17: `09-template-map.md`'s `RM.AP … RM.KG` write-map row now footnotes that its
      cited function's internal selection logic changed, pointing to `05-decisions.md`; `05-decisions.md`
      carries a new "Comparable-property ranking now uses location and data provenance" entry with the
      measured swing and the provisional-sign-off status; `project-status.md` updated across every task
      touched this session (6.1, 8.1, 8.5, 8.6, 8.7, 5.2, 5.3). All three name the change, the date, and
      the signed-off (provisionally) figure movement.

## 8. Prioritize hand-verified comparables (your rule, 2026-09-17)

- [x] 8.1 In `nearest_comparables()`'s `sort_key()`, rank a `hand_verified` candidate ahead of a
      non-hand_verified one, WITHIN whichever district/city tier and task 2.4 coordinate-precision
      bucket it already falls into. Mark all 7 `HAND_VERIFIED_COMPARABLES` entries `hand_verified=True`
      (the post-construction loop already touching every entry). Update `comparable_match_basis()` to
      disclose when a shown comparable is hand-verified, matching this project's "stated basis must be
      the real one" house rule.
      **A real bug caught and fixed before measuring, not after**: a first attempt put verified-rank
      ahead of the coordinate-precision bucket, which let two coordinate-less Hà Nội projects (Lumi
      Prestige & Elite, Lumi Signature) outrank Masteri An Phu — a real candidate 0.08km from a test
      query with a real rate — and did so invisibly, since `derive_product_rate_capped()`'s ±20% cap
      only fires when its two branches disagree, and both would have agreed on the wrong pick. Caught
      by testing the exact query that should have been safe (task 2.4's own real-coordinate case), not
      by inspection. Fixed by moving verified-rank to a tie-break *inside* the precision bucket — see
      `design.md`'s "Amendment (task 8.1)" for the full account. Re-verified the fix reproduces the
      pre-existing 19,400 VND/m² figure for that exact query.
      Done 2026-09-17. Verify: the three spot-checks and the full `verify.py` run in
      `measured-effect.md`'s "task 8.1" section.
- [x] 8.2 Measure the real effect end-to-end (not just at the function level) — full `verify.py` run
      against the standard sample, following this change's own established discipline (5.1/2.4/2.5).
      Done: `derived_apartment_rate` 18,350 → 16,500 VND/m²/month (−10.1%), `mgmt_fee_revenue_annual`
      12,178,230,000 → 11,003,850,000 VND (−9.6%, i.e. −1,174,380,000 VND/yr). Confirmed the
      pre-existing, unrelated `staff_cost_annual` drift (379,523,020, from
      `reconcile-summary-with-detail-sheets`) is additive with and separable from this task's own
      effect on `total_profit_value` — not confused with it. Full table in `measured-effect.md`.
      Baseline re-recorded at task 5.3, after 5.2's provisional sign-off — not applied unilaterally
      ahead of it.
- [x] 8.3 Present this task's measured swing — folded into the existing 5.2 Head-of-PM sign-off packet,
      not a separate review. Done: the packet named the swing, the ±20% cap gap, and the residual
      question (should Lumi Prestige & Elite / Lumi Signature count as verified comparables for an HCMC
      project at all) as its own explicit open item — resolved separately at task 8.5, before 5.2's
      packet was even built, so the packet presented it as background, not as still-open.
- [x] 8.4 Added the verified-priority scenarios to `specs/product-revenue-pricing/spec.md` (see that
      file's "An individually-verified comparable is preferred..." and "A precise location match is not
      displaced..." scenarios, added alongside task 8.1). `docs/project-status.md` and the roadmap
      tracker updated across tasks 6.1/8.1/8.5/8.6/8.7 and again at 5.2/5.3 for the sign-off and
      baseline re-record. Folded into 7.1 rather than duplicating, as planned.
- [x] 8.5 Exclude Lumi Prestige & Elite and Lumi Signature from `MASTER_COMPARABLES` (your instruction,
      2026-09-17: "Hà Nội is Hanoi or Ha Noi, not the same with Hồ Chí Minh, they are 2 separated
      city") — resolves 8.1's own flagged residual question. Kept both entries in
      `HAND_VERIFIED_COMPARABLES` itself (real, sourced data — `excluded_from_ranking` field states
      why) but `_merge_comparables()` now drops any entry carrying that field before it reaches
      `MASTER_COMPARABLES`, so neither can be selected for any project regardless of verified-status,
      tier, or NFA-delta. `MASTER_COMPARABLES` count: 85 → 83.
      Verify: confirmed real — before this task, an NFA=200,000 query with real coordinates selected
      exactly these two (see 8.1's own account); re-ran the identical query after this fix, they no
      longer appear anywhere in the ranked output. Did NOT move the standard sample's own baseline
      figures (its NFA was never close enough to either Lumi entry for them to have won there even
      before this fix) — a real, necessary correction for other project sizes, not a no-op change.
- [x] 8.6 Disable task 2.4/2.5's real-coordinate-distance comparison entirely, for now (your
      instruction, 2026-09-17: "i think should disable the distance comparison, just compare by the
      basic information first, we do that later"). New module constant
      `DISTANCE_COMPARISON_ENABLED = False` gates the coordinate branch out of both
      `nearest_comparables()`'s sort key and `comparable_match_basis()`'s reader-facing label (so the
      label never claims distance decided an ordering it didn't) — one switch, nothing about
      `DISTANCE_TIER_KM`/`MAX_DISTANCE_RATE_SWING`/`_haversine_km()`/the cap logic itself changed, and
      flipping it back to `True` resumes task 2.4/2.5 exactly as built and already measured.
      Verify: re-ran the "NFA=200000, coords=Q2 Thao Dien" query — now returns the same result with or
      without coordinates supplied (Green Skyline + Fiato MF Pre/Y1/Y2, both hand-verified, by
      NFA-delta), and `comparable_match_basis()` correctly reports "closest Total NFA" rather than
      "closest by real distance" for it. Full `verify.py` re-run: identical figures to 8.1/8.5's own
      measurement (the standard sample never had coordinates to lose).
- [x] 8.7 Resolve whether ranking should ever fall back to the ~78 Master List projects, or use only
      the 8 verified ones (your question, 2026-09-17: "do the 78 project have the budget or rate or
      price... if they have so Keep prioritize + fallback"). Checked directly, not assumed: all 78
      Master List comparables carry a real management-fee rate — required just to be in the pool at
      all (`_load_master_list_comparables()`'s own load filter) — real values seen from 7,100 to
      22,550+ VND/m²/month. 11 of the 78 carry a real Apartment rate specifically, vs. only 2 left
      among the 8 (Green Skyline, Fiato Airport – F Zone MF Pre/Y1/Y2) after task 8.5. Also confirmed
      `Dim_Property_Residential.csv` has no row for either excluded Lumi entry — its only "Lumi"
      matches are an unrelated real project, Lumiere Riverside – Tháp West/East, genuinely in Thủ Đức,
      HCMC.
      Decision: keep prioritize + fallback (task 8.1's existing design) — no code change. A hard
      restriction to only the 8 would leave every non-Apartment product (Shophouse, Retail, etc.) with
      no derivable rate at all, since none of the remaining 8 carry one for anything but Apartment. For
      Apartment specifically, the fallback is mostly dormant today anyway — the 2 remaining verified
      entries already win almost every real query (no project has a district/city on file yet) — so
      this decision mainly keeps the other products working, not Apartment.
