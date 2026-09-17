## Why

Decision D8 (`docs/05-decisions.md`) and the method catalogue require a new-project budget to show
revenue and load-driven costs **ramping month by month** with a fill-up curve. The pipeline still
writes every line as a flat 1/12 split at 100% occupancy. For a building that opens the year
half-empty this overstates year-1 collected management fee and parking revenue by roughly 3×, and
overstates year-1 utilities by roughly 2×. It also leaves `RM.0A` — the developer's management-fee
top-up on unsold units, ~2.9bn VND on one real comparable — blank, because that line only has a
value once the ramp exists.

Change A put the two fill-up sheets (`Tỷ lệ lấp đầy cư dân`, `Tiến độ lấp đầy bãi xe`) into the
deliverable as blank scaffolding. This change fills them and drives the occupancy-scaled budget
lines from them.

## What Changes

- **One monthly fill-up curve, shared by both generators.** The internal analysis already uses a
  fixed curve (0% at month 0 → 50% by end of year 1, linear — `_MONTH_ANCHORS` in
  `generate_project_output.py`). It moves to a shared module so the client deliverable and the
  analysis ramp identically. Making the curve a per-project intake field is a later follow-up.
- **The two fill-up sheets are populated** with the resident and parking curves; the guideline's
  own formulas on those sheets do the per-month arithmetic where practical.
- **Occupancy-scaled budget lines are written month by month** into `2. Budget-Management Fund`
  columns H:S (frequency `Schedule`, so `G = SUM(H:S)`), each with a remark pointing to the fill-up
  sheet:
  - `RM.AP`..`RM.KG` — fee area × rate × resident fill %(month)
  - **`RM.0A` (new line)** — Σ(units × rate) × (1 − resident fill %(month)); the mirror of `RM`
  - `RPa` / `RP1` / `RP2` — bays × parking fill %(month) × monthly rate (parking fill tracks
    resident fill, ~2× faster where bays < units)
  - `EEW` / `EEW.C` — full annual ÷ 12 × resident fill %(month)
  - `EEE` / `EEE.C` — full annual ÷ 12 × the fill %, floored at 40% of full at 0% occupancy and
    reaching full by ~40% occupancy (the guideline's stated electricity behaviour)
- **`EED` (diesel) stays flat** — driven by generator test/backup hours, not occupancy. **`ESS4`
  cleaning stays as the current fixed vendor contract** — ramping cleaning posts is a staffing
  judgement for its own change. `RP5`/`RP6` visitor parking stay blank (need a volume basis —
  change D).
- **Verification gains a deliverable-figure baseline** for the ramped lines, so an accidental
  future revert to flat writing is caught.

**This moves headline figures materially — intentionally.** Year-1 collected management fee (`RM`)
drops sharply while `RM.0A` rises to offset it, so *total* management-fee revenue is roughly
unchanged; parking revenue and public utilities drop with no offset. The change records the exact
movement on a real project (task group 5) and the PM signs it off.

## Capabilities

### New Capabilities

- `occupancy-ramp`: for a project not yet at stable occupancy, the budget's occupancy-scaled
  revenue and load-driven cost lines vary month by month with a single fill-up curve shared by the
  client deliverable and the internal analysis; the developer's management-fee top-up on unsold
  units (`RM.0A`) is written as the curve's mirror; the fill-up sheets carry the curve; a line not
  linked to occupancy (diesel, fixed service contracts) stays flat.

### Modified Capabilities

- `budget-workflow-verification`: gains a recorded baseline for the client deliverable's ramped
  budget lines (the existing 24 figures are all analysis-workbook figures). A ramped line reverting
  to a flat 100% write, or the curve changing, SHALL fail verification with the line named.

## Impact

**Affected code**

- `generate_project_budget.py` — `fill_management_fund_sheet()`: occupancy-scaled codes routed
  through a new month-by-month writer instead of `_write_even_monthly_row`; `RM.0A` added to the
  written set; the two fill-up sheets populated. No change to `MGMT_FUND_ROWS` / row positions.
- **New shared module** for the fill-up curve (imported by both generators).
- `generate_project_output.py` — imports the curve from the shared module instead of defining
  `_MONTH_ANCHORS` locally; its numbers are unchanged (same curve).
- `verification/` — new deliverable-figure baseline + its check; the 24 analysis baselines are
  re-verified unchanged; the config's "manual spot-check when aggregation logic changes" rule is
  satisfied by task group 5.

**Relationship to other changes**

- Depends on the archived `rebase-output-onto-25-sheet-form` (the fill-up sheets) and
  `adopt-guideline-as-costing-method-spec` (the catalogue's `occupancy_scaled` flag and methods).
- `cost-energy-from-consumption-and-tariff` (active) changes how `EEE`/`EEW`'s *annual* figure is
  derived. This change ramps whatever annual figure those codes carry, so the two compose: land
  either order.
- Satisfies the `logic-spec-method-alignment` requirement for the `occupancy_scaled` codes without
  a delta — it implements the method the catalogue states for them.

**Data scope** — reads and writes no Generation A or Generation B table; changes no Fact/Dim join
key. All figures stay in VND with units stated. The Copilot Studio package's live data is
unaffected.
