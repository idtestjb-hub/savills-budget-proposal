## Why

`master_comparables.py`'s `nearest_comparables()` — the single function both the client deliverable
and the internal analysis workbook call to pick which real projects a management-fee rate is derived
from — ranks the comparable pool purely by `abs(nfa - input_nfa)`. It never reads the `District`/
`City_Province` columns that already sit in the same rows of `Dim_Property_Residential.csv`/
`Dim_Property_Commercial.csv` as the fee columns it does use (verified this session: an empty grep
for `District`/`City_Province`/`location` anywhere in `master_comparables.py`). A management fee is a
strongly local-market figure — labor cost, competitive density, and building-class expectations all
vary by district — so ranking on size alone can select a same-size comparable from a materially
different market ahead of a nearer, more relevant one of slightly different size.

## What Changes

- `nearest_comparables()` gains location as a real ranking input alongside Total NFA — not a
  replacement for it; there usually are not enough same-district comparables to rank on location
  alone. The exact blend (tiering vs. weighting) is a design decision, deliberately not made in this
  proposal — see design.md.
- A project whose own district (or city) has zero comparables SHALL fall back to today's NFA-only
  ranking, not fail or produce an empty comparable set. This must be explicit in the spec, not an edge
  case discovered later.
- Because both generators and the `Comparison` sheet's benchmark already call through this one shared
  function, no separate per-consumer change is needed — but the two existing specs that describe
  today's ranking as NFA-only need their wording corrected to match the new rule.
- **BREAKING** for any project whose currently-selected comparable set changes once location is
  factored in: a different comparable set means a different derived rate, which moves that project's
  RM/product revenue and its `Comparison` sheet benchmark figures. A project whose location-ranked
  outcome is unchanged from today's NFA-only outcome (e.g. it already had its nearest-by-NFA
  comparable in the same district) is unaffected.

## Capabilities

### New Capabilities
(none — this modifies the ranking method an existing shared function already performs; no new
externally-observable capability is introduced)

### Modified Capabilities
- `product-revenue-pricing`: the "two workbooks report the same revenue" requirement currently states
  comparables are "ranked on the same size measure — the project's total building net floor area" and
  that any comparables table shown to a reader is "ordered by distance from this project's Total NFA."
  Both statements need to describe the new location-then-size (or blended) ranking instead, while
  preserving the requirement's actual invariant — both workbooks still select the same set, in the
  same order, for the same input.
- `proposal-benchmark`: the "client deliverable benchmarks the finished proposal" requirement states
  the comparables used are "the nearest real projects by total building net floor area." That
  description needs to match the new ranking method; the requirement's own invariant — the benchmark
  uses the exact same set, in the same order, that the rate-derivation already selected, and never
  selects a different set — is unaffected, since both still resolve through the one shared function.

## Impact

- `Budget_Agent/source_code/master_comparables.py`: the ranking logic inside `nearest_comparables()`
  (or its loader, `_load_master_list_comparables`, if location needs to be carried into the candidate
  records first — it currently is not).
- **Confirmed, not assumed**: the INPUT project's own district/city is not read anywhere today either
  — grepped `generate_project_budget.py`'s full intake field list (`read_input()`, lines 554-591) for
  `District`/`city`/`Location`, zero matches. This change therefore also needs a new optional intake
  field for the project's own district/city, the same shape as `wire-real-elevator-count-into-ad-
  revenue`'s new field (`L.value(...) if L.has(...) else None`, backward-compatible with older intake
  workbooks) — not only the comparable-pool side. A project whose own district/city is not supplied
  falls back to today's NFA-only ranking (already required by the "project's own district has no
  comparable" scenario in the modified spec, which covers this case identically to a genuinely absent
  comparable match).
- Reads two new columns (`District`, `City_Province`) from `Dim_Property_Residential.csv`/
  `Dim_Property_Commercial.csv` that already exist today. No column is added, removed, or modified in
  those files; no Fact/Dim join key changes, so the Copilot Studio package's live data is unaffected.
- No expected code change in `generate_project_budget.py` (client deliverable) or
  `generate_project_output.py` (analysis workbook) or the `Comparison` sheet's benchmark section — all
  three already consume `nearest_comparables()`'s output rather than re-deriving it; confirming this is
  actually true (not assumed) is a verification task, not a design decision.
- Figure-moving for any project whose selected comparable set changes — needs the same measure-then-
  Head-of-PM-sign-off gate as every other figure-moving change in this project (see
  `fill-guideline-required-line-items`, `activate-common-area-fund-cost-share`,
  `reconcile-summary-with-detail-sheets` for the established pattern: implement → measure the swing on
  Wayne Tower and the standard sample → present to Head of PM → re-record the relevant baseline(s) →
  archive).

Not in scope: elevator count, basement count, reception staffing — separate proposals from the same
investigation session, independent in scope and risk (the same reasoning this project already used to
keep `localize-line-level-remarks` and `add-multiyear-preopening-budget-phases` as separate changes
despite coming from the same source scan).
