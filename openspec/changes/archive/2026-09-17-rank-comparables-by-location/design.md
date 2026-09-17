## Context

`master_comparables.py` merges two real sources into one ranking pool (`MASTER_COMPARABLES`):
`HAND_VERIFIED_COMPARABLES` (7 named, individually-checked projects, hardcoded in this file — no
location field on any of them today) and `_load_master_list_comparables()` (~78 more, read from
`Dim_Property_Residential.csv`, which already carries `District`/`City_Province` columns that this
loader does not currently extract). `nearest_comparables(input_nfa, exclude_name=None, n=2)` sorts
the merged pool by `abs(nfa - input_nfa)` and returns the top `n`. Two callers matter for how this
can change safely: `derive_mgmt_rate`/most call sites take a small `n` (top-2) directly; but
`derive_product_rate` calls `nearest_comparables(..., n=len(MASTER_COMPARABLES))` — the FULL pool,
already ranked — and does its own filtering/averaging over that order. Whatever this change does
must still produce one stable, total ordering over the whole pool, not just a top-N cutoff, or
`derive_product_rate` breaks.

See proposal.md for why (location-blind ranking on a fee that's a local-market figure) and the two
modified specs for the externally-observable contract this must satisfy.

## Goals / Non-Goals

**Goals:**
- Make district (then city, as a fallback tier) a real ranking input, without inventing an
  unfounded numeric weight to blend it with NFA distance.
- Preserve `nearest_comparables()`'s existing signature and the "full stable ranking, not just
  top-N" property `derive_product_rate` depends on.
- Fail open, not closed: any missing location data (on the input project or on a candidate) SHALL
  degrade gracefully to today's NFA-only behavior for the affected comparison, never raise or
  return fewer comparables than requested when NFA-only ranking would have returned enough.

**Non-Goals:**
- Not deciding a quantified location/size trade-off (a formula like "1 district = X m² of NFA
  distance") — no data in this repo justifies picking a specific number, and inventing one would
  repeat exactly the mistake this project has corrected elsewhere this session (fill-up curves,
  lifeguard staffing) of asserting a ratio nobody actually measured.
- Not reading `Dim_Property_Commercial.csv` (currently unused by `master_comparables.py` entirely)
  or adding commercial comparables — out of scope, a separate concern.
- Not backfilling the 7 `HAND_VERIFIED_COMPARABLES`' districts with a guess — see Risks.

## Decisions

### Ranking method: strict tiering, not a weighted composite score

Two real options, both raised in the proposal:

1. **Strict tiering (chosen).** Partition the candidate pool into three tiers — same district,
   same city (different district), everyone else — in that preference order. Within each tier,
   sort by today's `abs(nfa - input_nfa)`, exactly as now. Concatenate the tiers into one ranked
   list. No new constant.
2. **Weighted composite score** (`score = nfa_delta + PENALTY * location_mismatch_level`). Rejected:
   `PENALTY` would be an invented number with no basis in this repo's data (we have no measurement
   of how much district vs. size actually moves a real management fee), and a badly-chosen
   `PENALTY` could silently produce worse matches than either pure signal alone. Tiering needs no
   such constant — it only asserts that "same district" and "same district and closer in size" are
   both strictly better than "different district," which the data doesn't need to justify
   numerically, only ordinally.

Tiering does encode one real qualitative judgment, undocumented by data in this repo: that district
match matters *more* than close NFA match for a management fee (a same-district comparable always
outranks a different-district one, however close the latter's NFA). This is a defensible starting
assumption (labor cost and market competition are franchise/district-level; scale economies on
management fee are a second-order effect) but it is an assumption, not a measured fact — flag it for
the Head of PM explicitly when this change's measured effect is presented, the same sign-off gate
every other figure-moving change in this project already goes through.

### Amendment (task 2.4, 2026-09-16): real distance as the intra-tier key, when available

`docs/ProjectLocation.xlsx` (task 1.3) gave the candidate pool real lat/lon for 79/85 candidates —
of the 15 with a verified Apartment rate specifically, 12 have coordinates vs. 9 with a district, so
coordinates reach more of the pool that can actually move a derived rate. Raised the question:
should ranking use real distance instead of district/city tiering?

**Answer: no, distance replaces the intra-tier key only — the tier ordering above is unchanged.**
`_location_tier()` still returns 0/1/2 from district/city exactly as before; "same district beats
different district" is still the one assumption queued for Head-of-PM sign-off at 5.2, untouched by
this amendment. What changes is HOW candidates are ordered *within* a tier: today's `abs(nfa -
input_nfa)` remains the ordering whenever either side lacks usable coordinates, but when the input
project AND a candidate both have real lat/lon, that candidate is ordered by great-circle distance
(haversine — geometry, not a business rule, so it needs no sign-off) instead. Coordinate-bearing
candidates sort ahead of non-coordinate ones within the same tier — preferring the more precise
measure when it exists, the same principle already applied to district-over-city.

Why not a tier of its own, ranked above district: that would change the reviewed assumption itself
(a coordinate match would sometimes beat a same-district match), reopening exactly the ordinal
judgment call this section already resolved once. A tie-break inside the existing tier changes
nothing about that ordering — only what "closest" means once you're already comparing candidates the
tier system already agreed belong together.

**This amendment is dead on arrival without also giving the INPUT project coordinates**: the pool
having coordinates doesn't help if the new prospect being budgeted doesn't. Added Latitude/Longitude
as two new optional intake fields (form rows 52-53, parallel to District/City at 50-51) — "leave
blank if unknown," same convention. Until a real intake fills them in, this amendment is a no-op on
every real project, same honest answer 5.1 already recorded for district/city on Wayne Tower.

### Amendment (task 2.5, 2026-09-16): a 1km trust radius, and a capped rate swing — your rule, not derived

After seeing task 2.4's real numbers (nearby buildings' rates tend to already be similar — Dragon
Hill 1/2, 0.15km apart, have an *identical* rate), you set an explicit policy: within 1km, trust a
real comparable's distance enough to let it move the derived rate — but cap that move at ±20% of
what the pre-coordinate ("basic information as is") method would have given. Beyond 1km, coordinates
are not trusted as "near" at all; ranking reverts to task 2.1's plain district/city + NFA-delta
tiering. **This is recorded here as your decision, not a measured fact** — 1km and 20% come from no
data in this repo, the same disclosure every other policy call in this change has gotten (task 2.1's
"district beats size" ordering included).

Two real, distinct parameters, confirmed with you before building:
- **`DISTANCE_TIER_KM = 1.0`** — gates task 2.4's distance tie-break itself. Beyond this, a
  coordinate pair is never preferred over NFA delta, however close it might seem citywide (the pool
  overall is dense — median nearest-neighbor distance 0.24km — but the operative rate-verified
  subset is sparse: only 3 pairs among the 15 rate-verified comparables sit within 1km of each other).
- **`MAX_DISTANCE_RATE_SWING = 0.20`** — a cap on the OUTPUT rate, not the input weight. Confirmed by
  direct arithmetic on a real pair (Saigon Royal/Rivergate, 0.67km apart) that a weight-tilt version
  of this rule could not reach a 20% swing on this data (nearby real rates are too similar to each
  other) — only a cap on the resulting rate can. `derive_product_rate_capped()` computes the rate
  both ways (with coordinates, and "basic information as is" — no coordinates at all) and, only when
  the two methods actually selected a *different* comparable set, clamps the coordinate-aware rate to
  within `MAX_DISTANCE_RATE_SWING` of the basic one. A swap that lands inside the band anyway (most
  of them, per the real end-to-end test below) needs no clamp and gets none.

**A real bug this amendment caught and fixed, worth recording plainly**: the per-product pricing
loops in both `generate_project_budget.py` (the `PRODUCT_REVENUE_ROWS` loop feeding RM.AP, and the
`0. Info` fee-table loop feeding cell I8) and `generate_project_output.py` (its own per-product loop)
each independently RE-CALLED the plain, uncapped `derive_product_rate()` for the Apartment product
specifically — silently overwriting the correctly-capped `apt_rate`/`derived_rate` with an uncapped
figure on those three cells, so the deliverable's `0. Info`!I8 and RM.AP disagreed with the internal
analysis workbook on the very first end-to-end test (19,400 uncapped vs. 16,800 clamped). Fixed by
special-casing `product == 'Apartment'` in all three loops to reuse the already-capped rate instead
of recomputing. Caught by testing through the real pipeline, not just the isolated function — the
isolated `derive_product_rate_capped()` was correct in every direct test; the bug was only in how its
result got consumed downstream, three call sites removed from where it was computed.

### Amendment (task 8.1, 2026-09-17): hand-verified projects win ties — your rule, scoped inside task 2.4's precision bucket, not ahead of it

After task 6.1 backfilled real districts for the 7 `HAND_VERIFIED_COMPARABLES`, it became visible that
these — plus Parking Building, excluded from ranking — are the *only* 8 properties in the whole
85-candidate pool with a real detailed budget workbook behind them (`Dim_Property_v2_verified.csv`,
`SourceSheet` column). Everything else is `Dim_Property_Residential.csv`'s auto-scraped Master List:
real data, but never individually checked against a source document (docs/10-data-layer-assessment.md).
Your rule, given directly: "prioritize the 8 verified projects when both are in range."

**Where this sits relative to the existing tiers, and why it is NOT a new tier of its own**: same
reasoning task 2.4 already gave for distance — a tier of its own would reopen the district/city
ordering already queued for sign-off at 5.2. So this is a tie-break, checked WITHIN whichever
district/city tier a candidate already lands in.

**Where this sits relative to task 2.4's coordinate precision bucket — this needed a real fix, not just
a decision.** A first implementation put verified-status ahead of the coordinate-precision bucket in
the sort key. Tested directly before presenting anything (see `measured-effect.md`'s task 8.1 section
for the full account): this let two coordinate-less Hà Nội projects outrank Masteri An Phu, a real
candidate 0.08km from the query with a real rate — reversing task 2.4's own stated principle ("prefer
the more precise measure when it exists") instead of refining it, and invisibly, since
`derive_product_rate_capped()`'s ±20% cap only fires when its two branches disagree, and both branches
would have agreed on the wrong pick here. Fixed by scoping `hand_verified` status to a tie-break
*within* task 2.4's existing precision bucket (has a real within-1km coordinate match, or doesn't) —
never a way to jump out of a worse bucket. A real, close, non-verified candidate still always wins over
a distant verified one; verified status only decides ties among candidates the precision bucket already
judged equally precise. Re-verified against the same failing query after the fix: correctly reproduces
the pre-existing 19,400 VND/m² figure.

**What this actually reaches, in practice**: tier 2 ("no location match"), overwhelmingly — because
almost every real project has no District/City on its intake form today (measured-effect.md: zero
effect on Wayne Tower or the standard sample from the district/distance work alone). There, a
hand-verified candidate now displaces a Master-List one purely on provenance, ahead of NFA-delta. This
is real and material: measured on the standard verification sample via the full pipeline (not a direct
function call), `derived_apartment_rate` moved 18,350 → 16,500 VND/m²/month (−10.1%) and
`mgmt_fee_revenue_annual` moved −1,174,380,000 VND (−9.6%). See `measured-effect.md` for the full
figures and for why the swing is a decrease here specifically, not a general direction.

**A residual question, named rather than resolved here**: two of the 8 (Lumi Prestige & Elite, Lumi
Signature — task 6.1) are genuinely in Hà Nội, not HCMC. The precision-bucket fix above stops them from
displacing a real nearby HCMC candidate when coordinates exist, but at tier 2 — where most real
projects sit — geography isn't discriminating either way, so they remain eligible to win purely on
NFA-delta among the 4 rate-bearing hand-verified projects. Whether a Hà Nội comparable should count
toward an HCMC project's rate at all is a Head-of-PM question, not something resolved by this task's
own scope (precedence mechanics, not pool membership). **Resolved at task 8.5, below** — not left open.

### Amendment (task 8.5, 2026-09-17): Lumi Prestige & Elite / Lumi Signature excluded from ranking — your instruction, resolving 8.1's own residual question

Your words: "Hà Nội is Hanoi or Ha Noi, not the same with Hồ Chí Minh, they are 2 separated city."
Direct, unambiguous, and correct — every other property in this 85-candidate pool is HCMC or an
immediately neighboring province (Bình Dương/Dĩ An/Thuận An, Đồng Nai, Bà Rịa-Vũng Tàu); Hà Nội is a
different market roughly 1,700km away with no bearing on an HCMC property-management fee.

**Where the fix lives, and why not just delete the two entries**: `HAND_VERIFIED_COMPARABLES` keeps
both dicts — the NFA/rate/source/location_source data task 6.1 researched is real and may be useful if
this pipeline is ever pointed at an actual Hà Nội project — but each now carries
`excluded_from_ranking` (a reason string), and `_merge_comparables()` drops any entry carrying that
field before building `MASTER_COMPARABLES`. This means `nearest_comparables()` can never select either
one, for any project, regardless of tier, verified-status, or NFA-delta — a pool-membership exclusion,
not a ranking-precedence one, which is the right layer for "this candidate is never a valid comparable
here" as opposed to "this candidate isn't the best available one this time."

**Confirmed this was a real fix, not a precaution against something that couldn't happen**: task 8.1's
own account already showed a concrete case — an NFA=200,000 query with real coordinates selected
exactly these two Hà Nội projects (before task 8.6 below also disabled the coordinate mechanism
separately). Re-ran the identical query after this exclusion: neither appears anywhere in the ranked
output. Did not move the standard sample's own baseline — that project's NFA was never close enough to
either Lumi entry to have won there regardless — so this is a real correction for other project sizes,
confirmed rather than assumed to matter only hypothetically.

### Amendment (task 8.6, 2026-09-17): real-distance comparison disabled — your instruction, revisit later

Your words: "i think should disable the distance comparison, just compare by the basic information
first, we do that later." A deliberate, temporary simplification — not a reversal of task 2.4/2.5's own
reasoning, which stands unchanged and resumes exactly as built the moment this is turned back on.

New module constant `DISTANCE_COMPARISON_ENABLED = False` (default) gates task 2.4/2.5's whole
coordinate-distance mechanism off at its two actual read sites: `nearest_comparables()`'s sort key
(never evaluates the within-`DISTANCE_TIER_KM` branch) and `comparable_match_basis()`'s reader-facing
label (never claims "closest by real distance" for an ordering distance was never consulted for — the
second site matters exactly as much as the first, since a stated basis that overclaims what decided a
ranking is the same class of bug this project's "stated basis must be the real one" house rule already
exists to prevent). `DISTANCE_TIER_KM`, `MAX_DISTANCE_RATE_SWING`, `_haversine_km()`, and
`derive_product_rate_capped()`'s cap-comparison logic are all untouched — with the coordinate branch
disabled, the cap's two comparison runs always agree, so it naturally has nothing to clamp, which is
the correct degrade rather than a separate case needing its own handling.

Re-verified after flipping the flag: the exact query that previously exercised task 2.4's distance
tie-break (NFA=200,000, real coordinates near Q2 Thao Dien) now returns the identical result whether or
not coordinates are supplied, and the label correctly reads "closest Total NFA" rather than "closest by
real distance." Did not move the standard sample's baseline (it never had coordinates to lose).

### Where location lives on a candidate record

Add `district`/`city` fields (default `None`) to every dict `_load_master_list_comparables()`
produces, read from the CSV's existing `District`/`City_Province` columns. Add the same two fields
(currently absent) to each `HAND_VERIFIED_COMPARABLES` entry as `None` — not guessed — so every
candidate has a consistent shape whether or not its location is actually known; a `None` simply
never matches any tier above "everyone else."

### Matching granularity: exact district-string equality, not fuzzy/normalized matching

`District`/`District_Raw` both exist in the source CSV — use the parsed `District` column (already
normalized by `transform_master_list.py`) and compare by exact case-insensitive string equality
after the same NFC Unicode normalization `verification/checks.py`'s `_nfc()` already uses elsewhere
in this codebase for Vietnamese text, rather than inventing a second normalization routine.

### Reader-facing label

The comparables table already states its matching basis (per the existing "labelled and stated"
convention this project uses everywhere — VAT sentences, provenance captions, fallback disclosures).
Update that label to say which tier actually produced each shown comparable (e.g. "cùng quận/huyện"
same-district vs "cùng tỉnh/thành" same-city vs no qualifier for the NFA-only fallback), not a
single static "ranked by Total NFA" string — this follows the `deliverable-remarks` capability's
existing house rule that a stated basis must be the real one, not a stale default.

## Risks / Trade-offs

- **[Risk] The 7 hand-verified comparables have no district on file, so they can never win the
  same-district tier even when one of them genuinely IS in the input project's district** →
  *Mitigation*: backfill their districts as a task in this change (tasks.md) — but this needs a
  person who actually knows these 7 named, real buildings' locations, or a verified source lookup.
  Not guessed or inferred from the project name (CLAUDE.md: "Do not infer missing business data or
  rules"). Until backfilled, those 7 simply keep behaving exactly as they do today (NFA-only), which
  is a safe degrade, not a regression.
- **[Risk] The qualitative judgment "location beats size" is unmeasured** → *Mitigation*: covered
  above — surfaced explicitly at the Head-of-PM sign-off stage as an assumption, not shipped as if
  it were a measured fact.
- **[Risk] A district with exactly one comparable produces a rate "average" of one, thinner than
  today's top-2 NFA-only average** → *Mitigation*: not a new risk this change introduces —
  `derive_mgmt_rate`/`derive_product_rate` already have their own thin-sample fallback and
  disclosure logic for exactly this shape of gap; this change only reorders the input list they
  already handle, so their existing behavior applies unchanged. Confirm this with a task-level test
  rather than assuming it, since it is easy to get the interaction wrong.
- **[Risk] Only `Dim_Property_Residential.csv` is read today (line `MASTER_LIST_CSV` in
  `master_comparables.py`) — `Dim_Property_Commercial.csv`'s `District` field is irrelevant here**
  → *Mitigation*: none needed, out of scope per Non-Goals; noted so it isn't mistaken for an
  oversight.

## Migration Plan

1. Implement the tiering change in `master_comparables.py` (`_load_master_list_comparables`,
   `HAND_VERIFIED_COMPARABLES`, `nearest_comparables`).
2. Verify `derive_product_rate`'s full-pool call pattern still works unchanged (existing regression
   coverage, plus a new case with a thin district tier).
3. Generate the deliverable + analysis for Wayne Tower and the standard sample; record, for each,
   whether the selected comparable set changed and, if so, the resulting swing in derived rate / RM
   revenue / Comparison-sheet benchmark figures, the same measured-effect discipline every other
   figure-moving change here has used.
4. Present the measured effect — and the unmeasured "location beats size" assumption above — to the
   Head of PM.
5. Only after sign-off: re-record whichever baseline(s) moved, following the existing
   `verification/README.md` procedure.

## Open Questions

None — the one real judgment call (tiering vs. a weighted score, and the ordering-precedence
assumption it implies) is resolved above rather than deferred, since leaving it open would have
changed the spec's own scenarios.
