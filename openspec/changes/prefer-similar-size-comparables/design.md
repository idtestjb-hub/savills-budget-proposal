## Context

`nearest_comparables()` (`master_comparables.py`) ranks the comparable pool by
`(location_tier, coordinate-precision-bucket, verified_rank, |NFA delta|)`. Checking a real project
("New AZ", Total NFA 123,000 m²) found its two selected comparables 25% and 71% off in size. Root
cause: most intake forms carry no District/City, which collapses location tier to a constant (tier
2) for every candidate — the function's own docstring already documents this as "where almost every
real project sits today." With tier neutralized, `verified_rank` becomes the real primary
differentiator, and only 2 of the 8 hand-verified comparables (Green Skyline, Fiato Airport) carry a
real Apartment rate — so any project without a district/city gets these two almost by default,
however far off in size, since NFA-delta is the LAST tiebreak and never overrides verified-status.

## Goals / Non-Goals

**Goals:**
- Prefer similarly-sized comparables over badly-sized ones, within the same location tier.
- Never leave a project with zero comparables — always fall back to nearest-available.
- Disclose plainly when the band isn't met, rather than silently using a poor match.

**Non-Goals:**
- Re-enabling or redesigning the distance mechanism (`DISTANCE_COMPARISON_ENABLED`) — untouched.
- Rebalancing the size-similarity band's exact percentage against real absorption/rate data — no
  such data exists for this question; the value is a named, tunable constant, flagged as a judgment
  call for PM review, not derived from any source.
- Building a smooth size-weighted score (e.g. "closer within the band scores higher than farther
  within the band") — that's what NFA-delta, the existing last tiebreak, already does; size-tier is
  a coarse preference, not a replacement for it.

## Decisions

### D1 — Insert size-tier BEFORE verified-status, not after

The whole point of this change is that verified-status currently wins even against a large size
gap. Putting size-tier after verified-status (as a second-order refinement within the same
verified-status bucket) would leave today's behavior completely unchanged — it would only ever
reorder two candidates that already share verified-status, which the existing NFA-delta tiebreak
already does. Size-tier has to sit between location-tier and verified-status to have any real
effect, and does: `(location_tier, size_tier, verified_rank, |NFA delta|)`.

**This deliberately, partially reweighs `rank-comparables-by-location`'s 2026-09-17 verified-priority
rule (task 8.1).** That rule was itself carefully scoped ("verified-rank is checked AFTER the
coordinate precision bucket, not before it... precision-of-match takes priority over verification
status") specifically so verified-status could never beat a genuinely closer, more precise match.
This change applies exactly the same principle one level up: a genuinely closer SIZE match now
beats verified-status too, for the same reason — a badly-sized comparable's real detailed budget
workbook doesn't make its rate a better estimate for a project of a very different scale.

### D2 — The band is ±50%, a named constant, not a sourced figure

No Savills guideline, prior decision, or reference dataset in this repo states a size-similarity
threshold (checked: no percentage-based NFA threshold exists anywhere in `master_comparables.py`
today, and the only existing swing cap, `MAX_DISTANCE_RATE_SWING = 0.20`, governs the unrelated,
currently-disabled distance mechanism). ±50% is chosen as a generous "same order of magnitude" band
— wide enough that it doesn't collapse into "always outside the band" given the small comparable
pool (13 candidates system-wide carry a real Apartment rate), but tight enough to matter as a real
preference. This is flagged explicitly, here and in the code comment, as a judgment call for PM
review — not presented as guideline-derived the way the location-tier and verified-status rules
were.

### D3 — Fallback, never rejection

If no candidate in a project's location tier clears the size band, ranking falls back to nearest-by-
NFA exactly as it does today — this change adds a preference, not a filter. A project with a genuinely
thin comparable pool (most of them, in practice) still gets a usable rate; it just also gets an
honest note that the nearest available comparable is a size outlier, instead of no note at all.

### D4 — Disclosure lives in `comparable_match_basis()`, not a new function

That function already composes the one-line "ranked by X" phrase written onto both workbooks'
Comparison-style sheets, and already handles the same kind of conditional disclosure (location tier,
verified-status). Extending it keeps one function as the single source of truth for what a reader is
told about how comparables were chosen, rather than duplicating logic at each of its two call sites.
It needs a new parameter, the input project's own Total NFA, to compute the per-comparable delta —
both call sites already have `project['total_nfa']` / `project.get('total_nfa')` in scope.

## Risks / Trade-offs

- **[Partially reverses a recently-signed-off rule]** → D1's reasoning applies the SAME principle
  ("a closer match beats verified-status") the 2026-09-17 rule itself was built on, one dimension
  earlier in the sort. Not a reversal of the rule's intent, an extension of it — but it does change
  which comparable some already-generated projects would get on their next run, and that movement
  needs measuring and sign-off like any other change.
- **[The ±50% band is a guess]** → named as one explicitly, both in code and in this doc, so a PM can
  retune `SIZE_SIMILARITY_BAND` without needing to re-derive the whole mechanism.
- **[A project could still get a badly-sized comparable]** → by design, whenever the whole tier's
  pool is thin — the disclosure note exists exactly for this case, not to make it impossible.
