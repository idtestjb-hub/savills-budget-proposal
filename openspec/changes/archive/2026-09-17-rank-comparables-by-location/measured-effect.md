## Measured effect — Wayne Tower (Thủ Thiêm, EXAMPLE) and the standard verification sample

Measured 2026-09-16, on the current code, via `verification/run_workflow.py`'s protected harness
(which snapshots `reports/Project_Budget_Input.xlsx` and other production files before and after
every run and raises if any of them move — used deliberately for this measurement, after an earlier,
unrelated testing mistake this same day bypassed that harness and overwrote a different live file;
see `rank-comparables-by-location/tasks.md` task 2.3 for the full account). No production file moved
during any run in this document.

**Refreshed same day, after task 2.4** (real coordinates as the intra-tier distance tie-break —
see `design.md`'s Decisions section). This refresh folds together two things that both moved since
this document was first written: task 1.3's coordinate-coverage jump (63/85 → 79/85 candidates with
a district or city) and task 2.4's new mechanism that actually reads those coordinates. Every figure
below is re-measured on the current code, not carried over from the first version of this document.

**Refreshed again same day, after task 2.5** (your 1km trust radius + ±20% rate-swing cap — design.md's
"Amendment (task 2.5)" note). The end-to-end test that measured this also caught and fixed a real bug:
three per-product pricing loops were independently recomputing an uncapped Apartment rate for the
Apartment product specifically, silently overwriting the cap on the deliverable's `0. Info`!I8 and
`2. Budget-Management Fund`!RM.AP cells while the internal analysis workbook correctly showed the
clamped figure — see `tasks.md` 2.5 for the full account. Fixed before any of the numbers below were
recorded.

### What moved on Wayne Tower and the standard sample, as they exist today: nothing

Neither Wayne Tower's real intake nor the standard synthetic sample has ever had a District, City/
Province, Latitude, or Longitude value — none of those fields existed before this change. `read_input()`
correctly resolves all four to `None` on Wayne Tower's real file, confirmed directly (not assumed).
With no location supplied at all, `nearest_comparables()`'s own tiering AND its intra-tier distance
tie-break both degenerate to exactly today's NFA-only sort (proven in `tasks.md` 2.1 and 2.4 as
byte-for-byte regression checks, not just argued from the code).

Measured directly on Wayne Tower:

| Figure | Before this change | After this change |
|---|---|---|
| `0. Info!I8` Apartment rate | 15,900 VND/m² | 15,900 VND/m² (unchanged) |
| `Comparison!A2` matching-basis text | "...ranked by closest Total NFA (whole-building)..." | Identical text — the dynamic label falls back to the exact pre-change wording when no location is supplied |

**This change has zero effect on any real project until someone fills in its District/City field.**
That is the honest current state, not a caveat buried under a more exciting number — no existing
project's figures move today.

### Illustrative effect, using real comparable-pool data (not Wayne Tower's own — Wayne Tower has no
district on file to demonstrate with)

To show the Head of PM what the mechanism actually does once a project supplies its real location,
this uses a real comparable already in `master_comparables.py` as a stand-in query (querying at
its own NFA, excluding itself) — clearly a demonstration, not a claim about any specific client
project:

| | Comparables selected | Derived Apartment rate |
|---|---|---|
| Querying at Q2 Thao Dien's NFA (33,691.4 m²), **no district supplied** | Dragon Hill 2, Fiato Airport — F Zone MF Pre/Y1/Y2 (neither has a district on file) | **13,500 VND/m²** |
| Same NFA, **`district='Thủ Đức'` supplied**, no coordinates | Hoang Anh Riverview, Masteri An Phu (both real Thủ Đức comparables; ranked by NFA delta within the tier) | **11,950 VND/m²** |
| Same NFA and district, **+ real coordinates on both the project and the pool** | Masteri An Phu, The Sun Avenue (ranked by real km distance within the same tier — Hoang Anh Riverview has no coordinates on file, so it drops out of the distance-preferred ordering) | **13,900 VND/m²** |
| | | **Swing, district-only → district+coordinates: +1,950 VND/m² (+16.3%)** |

This is a real, measured swing on real data (not a synthetic or hypothetical rate) — it demonstrates
the mechanism moves a genuine derived rate by a material amount, twice over: once from adding
district/city (task 2.1-2.3), and again from adding real distance as the tie-break once coordinates
exist on both sides (task 2.4). The third row was run end-to-end through the REAL two-generator
pipeline via `run_workflow()` (not a direct `master_comparables.py` call) — a synthetic "Q2 Thao Dien
Test Twin" intake workbook with District='Thủ Đức' and Lexington Residence's real coordinates as a
stand-in for the project's own location, confirmed identical in both the client deliverable and the
internal analysis workbook, each correctly labelled "same District, then closest by real distance
(km)" (vs. "...closest Total NFA (whole-building)" on the no-coordinates run of the same sample).

### Task 2.5's cap, measured end-to-end (not just at the function level)

Ran a synthetic project (NFA 200,000 m², no District/City, Latitude/Longitude set to Q2 Thao Dien's
real coordinates) through the full two-generator pipeline via `run_workflow()`'s protected harness:

| Surface | Figure shown |
|---|---|
| What the within-1km comparables (Q2 Thao Dien 22,000 + Masteri An Phu 16,800) would have averaged to | 19,400 VND/m² |
| What "basic information as is" (no coordinates — the pre-task-2.4 method) would have given | 14,000 VND/m² |
| ±20% band around the basic figure | 11,200 – 16,800 |
| **Actual rate shown, all three surfaces, after the fix below** | **16,800** (hit the ceiling exactly) |

All three places that display the Apartment rate — the deliverable's `0. Info`!I8, its
`2. Budget-Management Fund`!RM.AP row, and the internal analysis workbook's Comparison sheet — agree
on 16,800, and the analysis workbook's Comparison sheet carries the derivation note explaining why
(quoted in `tasks.md` 2.5). Production files confirmed byte-unchanged.

**The bug this test caught, stated plainly**: on the first attempt, `0. Info`!I8 and RM.AP showed the
UNCAPPED 19,400 while the analysis workbook correctly showed 16,800 — the three per-product pricing
loops that fill those two deliverable cells were each independently re-deriving the Apartment rate via
the plain, uncapped function instead of reusing the value `derive_product_rate_capped()` had already
computed. This is exactly the class of bug `unify-revenue-basis-across-outputs` (finding X-01) was
created to prevent, and it recurred here because the cap lives in a wrapper function that three
*other* call sites don't automatically know to defer to — fixed by special-casing the Apartment
product in all three loops. Recorded here rather than only in `tasks.md` because it is exactly the
kind of cross-surface disagreement a reader of this document would want to know was checked for, not
just assumed away.

### Coverage — how often this would actually fire today, stated plainly

- Of the 85 comparables in the pool, only **15 have a verified Apartment rate at all** (a pre-existing
  limitation of the source data, not something this change touches or worsens).
- Of those 15, only **9 have a District on file**, spanning exactly **5 districts**: District 4,
  District 7, Phú Nhuận, Thủ Đức, Tân Phú.
- Of those same 15, **12 have real coordinates on file** (task 1.3's `Fact_ProjectLocation.csv`
  match) — more than the district figure, because coordinate coverage doesn't depend on the same
  source rows that happened to carry a District string. The 3 with neither a district nor
  coordinates (Lumi Prestige & Elite, Lumi Signature, Fiato Airport — F Zone MF Pre/Y1/Y2) are
  unreachable by either mechanism, unchanged by task 2.4.
- Of those 12, only **3 pairs sit within task 2.5's 1km trust radius** of each other: Q2 Thao Dien /
  Masteri An Phu (0.08km), Dragon Hill 1 / Dragon Hill 2 (0.15km), Saigon Royal / Rivergate Residence
  (0.67km) — 6 of the 12. The other 6 sit 2.1–9.8km from their nearest rate-bearing peer, so task
  2.5's cap never engages for them; ranking there falls back to task 2.1's district/NFA method
  exactly, whether or not coordinates exist. This is a narrow slice by design — your own rule (task
  2.5, "if the distance is more than [1km] then the comparison base on basic information as is")
  deliberately keeps it that way.
- The 7 hand-verified comparables (the most individually-checked ones — A&K Tower, Green Skyline,
  etc.) have **zero** location data of any kind — district, city, OR coordinates — except Green
  Skyline, which task 1.3 gave a city (not a district, and not coordinates). They cannot participate
  in district tiering until `tasks.md` 6.1 (backfill) lands, which needs a person who knows these
  specific real buildings, not a guess — task 2.4 does not change this gap either way.

Practical implication for the Head of PM: today, this feature only visibly moves a derived rate for a
new project whose own district happens to be one of those 5 AND whose nearest same-district
comparable(s) happen to have a verified Apartment rate. Outside that intersection, the ranking order
still changes (a same-district comparable is shown first even without a rate), but the FINAL derived
rate does not move — the fallback machinery (`derive_product_rate`'s own thin-sample handling,
unchanged by this work) takes over exactly as it does today. Task 2.4's distance tie-break only
refines the ordering FURTHER WITHIN that same intersection — it cannot fire on a project outside it,
and it cannot fire at all unless the new project's OWN intake also supplies Latitude/Longitude (a
new, separate optional field — see `tasks.md` 2.4), not just District/City.

### Refreshed 2026-09-17, after task 8.1: hand-verified projects prioritized when both are in range

Direct instruction from you, 2026-09-17, after the district backfill (task 6.1) made it visible that
only 8 of the 85 comparables (`HAND_VERIFIED_COMPARABLES`) have a real detailed budget workbook behind
them — the other ~78 are `Dim_Property_Residential.csv`'s auto-scraped Master List. Your rule:
"prioritize the 8 verified projects when both are in range."

**A design flaw was caught and fixed before any number below was recorded, not after.** The first
implementation put `hand_verified` status ahead of task 2.4's coordinate-precision bucket in the sort
key. Tested directly (not just reasoned about): querying at NFA 200,000 with Q2 Thao Dien's own real
coordinates returned **Lumi Signature + Lumi Prestige & Elite — two Hà Nội projects with no
coordinates on file at all** — beating Masteri An Phu, which sits 0.08km away and carries a real rate.
Because `derive_product_rate_capped()`'s "basic information as is" branch would have agreed with the
coordinate-aware branch (neither depends on distance once verified-status decides it), the ±20% swing
cap never engages for a case like this — it only fires when the two branches *disagree*. Fixed by
scoping `hand_verified` to a tie-break WITHIN whichever precision bucket a candidate already occupies
(has a real within-1km coordinate match, or doesn't), never letting it jump a candidate out of a worse
bucket. Re-tested the same query after the fix: correctly returns Q2 Thao Dien + Masteri An Phu again,
19,400 VND/m² — exactly the figure already recorded above under "Task 2.5's cap, measured end-to-end".
Real coordinates still beat verified-but-distant status; verified-but-equally-imprecise status still
beats non-verified.

**Spot-checks after the fix** (same Q2 Thao Dien queries as the illustrative table above):

| Query | Comparables selected | Rate |
|---|---|---|
| No district, no coordinates (tier 2 — today's typical real case) | Fiato Airport – F Zone MF Pre/Y1/Y2, Green Skyline (both hand-verified; **Dragon Hill 2 displaced**) | 16,500 VND/m² (was 13,500 — **+22.2%**) |
| `district='Thủ Đức'`, no coordinates (tier 0 — no verified project is in this district) | Hoang Anh Riverview, Masteri An Phu (unchanged) | 11,950 VND/m² (**no change** — nothing to prioritize) |
| No district, real coordinates near Q2 Thao Dien | Q2 Thao Dien itself excluded correctly; Masteri An Phu wins by real distance (unchanged) | 19,400 VND/m² (**no change** — real precision still wins) |

The middle row matters as much as the first: it's the direct evidence that this rule is genuinely
conditional ("when both are in range"), not a blanket preference — Thủ Đức has real comparables but
none of them are among the 8, so nothing moved.

**Real, end-to-end measured effect — the standard verification sample**, via `verify.py` (full
two-generator pipeline, not a direct function call):

| Figure | Baseline (before task 8.1) | Current | Moved |
|---|---|---|---|
| `derived_apartment_rate` | 18,350 VND/m²/month | 16,500 VND/m²/month | **−1,850 (−10.1%)** |
| `mgmt_fee_revenue_monthly` | 1,014,852,500 VND | 916,987,500 VND | **−97,865,000** |
| `mgmt_fee_revenue_annual` | 12,178,230,000 VND | 11,003,850,000 VND | **−1,174,380,000 (−9.6%)** |

This is a real, material, **downward** swing on the standard sample — not the direction either of the
Q2 Thao Dien illustrations above happened to move, a reminder that the sign depends entirely on which
2 of the 4 rate-bearing hand-verified comparables (Green Skyline 15,000, Fiato MF Pre/Y1/Y2 18,000,
Lumi Signature 17,000, Lumi Prestige & Elite 21,000 — VND/m²) are closest in NFA to whatever project is
being queried, not on any general "verified projects cost more/less" pattern.

`verify.py` also reports `staff_cost_annual`/`total_profit_value`/`margin`/`markup` as differing.
`staff_cost_annual`'s own delta (379,523,020) is byte-identical to the pre-existing, separately-tracked
`reconcile-summary-with-detail-sheets` drift (unrelated to this task — re-confirmed present before this
task too). `total_profit_value`'s delta (1,553,903,020) is exactly that pre-existing 379,523,020 plus
this task's own 1,174,380,000 revenue drop — the two effects are additive and independently traceable,
not confused with each other.

**A residual question this task's own fix doesn't resolve, worth naming rather than deciding here**:
Lumi Prestige & Elite and Lumi Signature (task 6.1 found these are genuinely in Hà Nội, not HCMC) are
now reachable via verified-priority at tier 2 for ANY project with no district/city on file — which is
most real projects today. The fix above stops them from displacing a real *nearby* candidate when
coordinates exist, but does nothing at tier 2, where geography isn't discriminating in either
direction anyway. Whether a Hà Nội project should count as a "verified comparable" for an HCMC
project's rate at all is a real question for the Head of PM, not something this task's own scope
(precedence and mechanism) should quietly settle either way.

**Baseline not re-recorded.** Per this change's own established practice (5.2 → 5.3), the swing above
is presented, not applied — `verify.py` is expected to keep failing on these 3 figures (plus the
pre-existing 4) until sign-off says otherwise.

### Refreshed again 2026-09-17, after tasks 8.5 and 8.6: same sample figures, two real fixes underneath

Task 8.5 (your instruction: Hà Nội and Hồ Chí Minh "are 2 separated city") excludes Lumi Prestige &
Elite and Lumi Signature from `MASTER_COMPARABLES` entirely. Task 8.6 (your instruction: disable
distance comparison for now) sets `DISTANCE_COMPARISON_ENABLED = False`, so `nearest_comparables()`
never consults coordinates at all until it's turned back on.

Re-ran the full `verify.py` suite after both: **identical figures to the task 8.1 table above** —
`derived_apartment_rate` still 16,500 (−10.1%), `mgmt_fee_revenue_annual` still 11,003,850,000
(−9.6%). This is expected, not a sign either fix was a no-op: the standard sample's own NFA was never
close enough to either Lumi entry to have selected them (they only won in the NFA=200,000 illustration
above, a different query), and the sample project has never had coordinates on its intake form (the
same fact that made task 6.1's district backfill inert on this baseline too) — so it never exercised
the distance mechanism regardless of whether task 8.6 disabled it.

Both fixes were independently confirmed effective on the queries that DO exercise them, not just
assumed safe because the sample didn't move:
- 8.5: re-ran the NFA=200,000 + real-coordinates query that previously selected the two Hà Nội
  projects (see the task 8.1 section above) — neither appears in the ranked output after this fix.
- 8.6: re-ran the same query with and without coordinates supplied — now returns the identical result
  either way (Green Skyline + Fiato Airport – F Zone MF Pre/Y1/Y2, by NFA-delta), and
  `comparable_match_basis()` correctly reports "closest Total NFA" rather than "closest by real
  distance."

Net effect on what the Head of PM is being asked to sign off: still exactly the two figures in the
table above, now produced by a mechanism with the Hà Nội gap closed and the distance tie-break turned
off pending a later decision — not a new or different swing.

### Manual spot-check (task 4.1 — project rule for changed aggregation/selection logic)

By hand: Hoang Anh Riverview's real Apartment rate is 7,100 VND/m², Masteri An Phu's is 16,800 VND/m²;
average = (7,100 + 16,800) / 2 = 11,950 — matches `derive_product_rate`'s own output exactly. Both are
real Thủ Đức properties, the same two a human filtering the source CSV by district would also pick.
Separately confirmed the Bình Thạnh case (6 real comparables in that district, 0 with a verified
Apartment rate) produces the identical 13,500 VND/m² the no-district query also produces — the
"district has no usable comparable" fallback was exercised on real data, not just asserted to work.

**Task 2.4's own spot-check**: Masteri An Phu's real Apartment rate is 16,800 VND/m², The Sun
Avenue's is 11,000 VND/m²; average = (16,800 + 11,000) / 2 = 13,900 — matches exactly. Confirmed by
hand that The Sun Avenue genuinely has coordinates on file and Hoang Anh Riverview genuinely does
not, which is why distance-ranking swaps one for the other rather than just reordering the same pair
— not a coincidence of the test data. Also confirmed the tie-break's precedence directly: querying
with the input coordinates set to exactly Saigon Pearl Ruby's own real coordinates, plus a
deliberately huge (+99,999 m²) NFA offset that would defeat any NFA-based ordering, still ranks
Saigon Pearl Ruby first — proving distance, not NFA, is genuinely driving the order within the tier,
not just breaking rare exact ties.

### What did NOT move

- Every other figure on Wayne Tower's deliverable and analysis workbook — this change touches only
  `nearest_comparables()`'s ordering and the two comparables-table labels; no other function's output
  changes.
- `verify.py`'s pre-existing, separately-tracked `staff_cost_annual`/`total_profit_value`/`margin`/
  `markup` baseline drift (from the paused `reconcile-summary-with-detail-sheets` change): re-confirmed
  present, unaffected, and unrelated after task 2.4 too — none of the 4 drifted figures are staffing-
  adjacent to comparable-matching or location, and this change's 6 edited call sites never touch
  roster/staffing code.
- The standard synthetic sample's full 5-check regression suite, re-run after task 2.4: 0 differences
  (`check_revenue_agreement`, `check_benchmark_reconciles`, `check_remark_content`,
  `check_summary_reconciles`, `check_required_line_items`), confirming this change (both the original
  tiering and the task 2.4 distance amendment) is a no-op on the standard sample.
- `derive_product_rate`'s full-pool contract (`len(nearest_comparables(..., n=len(MASTER_COMPARABLES))) == len(MASTER_COMPARABLES)`),
  re-confirmed after task 2.4 with coordinates supplied as well as without.

---

## Note added 2026-10-18 (change apply-head-of-pm-decisions-2026-10, group 4)

The figures above predate the size-band preference (2026-09-18) and the comparable VAT basis. The real-distance
comparison (`DISTANCE_COMPARISON_ENABLED`) is on again, and its ±20% cap now covers every product's rate and the blended
fallback, not only the Apartment rate. The standard sample has no coordinates, so it is unaffected by the distance step;
its Apartment rate moves 17,175 → 18,892 through the VAT-basis conversion alone. Current measurements:
`openspec/changes/apply-head-of-pm-decisions-2026-10/design.md`, "Measured", group 4.
