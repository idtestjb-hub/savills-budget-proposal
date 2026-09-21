## Why

Checking a real project ("New AZ", Total NFA 123,000 m²) found its two selected comparables are
92,100.09 m² (Green Skyline, −25%) and 35,836.27 m² (Fiato Airport, −71%) — a much larger size gap
than expected. Tracing `nearest_comparables()`'s sort key (`master_comparables.py`) explains why:
today's ordering is `(location_tier, coordinate-precision, verified_rank, |NFA delta|)` — Total NFA
closeness is the LAST tiebreak, after location tier and hand-verified status. Most real intake
forms carry no District/City at all (per the function's own docstring: "tier 2 ... is where almost
every real project sits today"), which collapses location tier to a no-op and makes hand-verified
status the PRIMARY differentiator. With only 2 of the 8 hand-verified comparables (Green Skyline,
Fiato Airport) carrying a real Apartment rate, any project without a district/city ends up with
these two selected almost by default, however far off in size they are — there is no floor or
preference anywhere in the ranking for size similarity itself.

This is not hypothetical for New AZ alone: the same mechanism produced Diamond Skyline's own
comparable set (Green Skyline: NFA delta 13,800, ~17.6%; Fiato Airport: NFA delta 42,464, ~54.2%)
on the very same 2 candidates, for the same structural reason.

## What Changes

- **A size-similarity band becomes a real preference in the ranking**, inserted between location
  tier and verified-status: `(location_tier, size_tier, verified_rank, |NFA delta|)`. Within the
  same location tier, a candidate whose Total NFA sits within `SIZE_SIMILARITY_BAND` (proposed:
  ±50%, a judgment call — not sourced from any Savills guideline, flagged for PM review and tuning)
  of the input project's own Total NFA is preferred over one that doesn't, even if the one outside
  the band is hand-verified. This partially reweighs `rank-comparables-by-location`'s 2026-09-17
  verified-priority rule (task 8.1) — a deliberate, disclosed tradeoff, not an accident.
- **Never rejects down to zero comparables.** If no candidate in the location tier clears the size
  band, ranking falls back to whichever is nearest by NFA anyway — exactly today's behavior — so no
  project loses its comparable set over this.
- **Honest disclosure when the band isn't met.** `comparable_match_basis()` (the phrase written
  onto the Comparison sheet and reader-facing remarks) states when a selected comparable's NFA
  differs from the project's own by more than the band, in both languages — matching this
  pipeline's established pattern (the fill-up curve, EMA15's blended catch-all, the "hand-verified"
  label itself) of using the best available data but never silently implying a closer match than
  what was actually found.
- **Does not touch the currently-disabled distance mechanism** (`DISTANCE_COMPARISON_ENABLED`,
  `MAX_DISTANCE_RATE_SWING`) at all — size-tier sits alongside it in the sort key exactly where
  coordinate-precision already does, so re-enabling distance comparison later composes with this
  unchanged.

## Capabilities

### Modified Capabilities

- `product-revenue-pricing`: the comparable-ranking requirement gains a size-similarity preference,
  ordered between location tier and verified-status, with a disclosed judgment-call threshold and a
  reader-facing note when the band isn't met.
