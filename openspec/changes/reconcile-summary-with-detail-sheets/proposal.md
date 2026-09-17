## Why

A full reconciliation sweep of the client deliverable (`docs/09-template-map.md` §9) found the grand
total sheet (`1. Summary`) does not tie to the detail sheets it aggregates: it is **643,780,247 VND
too high** on the year-one surplus (revenue overstated 5,000,000 by a template `RO2a` defect;
staff understated 638,780,247 because `EMH2` uses a Python shortcut while the deliverable's own
`A1. Staff cost` payroll sheet — which nothing reads — says a larger number). The deliverable also
ships **254 `#DIV/0!` / `#REF!` cells** on helper sheets the pipeline writes to but no formula
reads. A budget whose own pages disagree cannot be defended to a client.

## What Changes

- **`RO2a` "Bank Interest on Savills account"** (`2. Budget-Management Fund` row 37) — the pipeline
  now **zeroes it** (clears `F37` and the stray payment-month date). It is a template placeholder
  with no basis; bank interest becomes a line a PM enters. `G` and `AK` then tie at 0, and the
  `RO2a` `G ≠ AK` split (the only such row in the sheet) is gone.
- **`EMH2` "Staff cost for Savills"** (row 83) is **driven from the deliverable's own
  `A1. Staff cost 08.2026 (VN)` sheet** — Savills' payroll calculator (13th-month, PIT, insurance
  caps, Trade Union 2%, +10% admin markup) — instead of the Python `Σ (bare roster cost × 1.215)`.
  Any roster position with no predefined row-group on `A1` (today: Reception, which otherwise only
  appears on `B1. Lịch Lễ tân`, a duty roster with no payroll math) gets a **real row of its own** on
  `A1` — one per headcount unit, using `A1`'s own exact formula chain, not a Python-computed number
  folded into another sheet's formula. `EMH2` then sums `A1`'s own total plus those row(s), so every
  figure it uses is a live, auditable Excel calculation. The internal analysis workbook's staff
  figure moves onto the same basis so the two workbooks still agree.
- **Orphaned helper-sheet writes removed / made clean.** The pipeline currently writes rates and
  counts to `A2 / A3 / A4 / B2 / B3 (Consumable) / B3 (Garbage) / B4 / B5` — sheets **no formula
  anywhere reads** (ESS1/4/16, advertising and the rest are computed in Python and written straight
  to the budget). `A2 / A3 / A4` also ship with **204 `#DIV/0!` cells** because their real input
  cells are never filled. The pipeline stops writing to a sheet nothing consumes, and ensures the
  deliverable carries no error cell the pipeline could have resolved.
- **`verify.py` gains a reconciliation check** — it opens the deliverable, and fails if `1. Summary`
  disagrees with `2. Budget-Management Fund` on any code's year total, if any fund leaf row has
  `G ≠ AK`, if `EMH` does not equal the `A1` payroll total, or if the deliverable ships an
  unresolved error cell above a recorded ceiling.
- **Two one-line notes** are added to the deliverable (no figure change): `1. Summary` states its
  chargeable-area figure is the 4-product `0. Info` subset (the Nursery is priced on the budget
  sheet, not shown there); and it notes that common-area advertising revenue is on
  `2.2 Common area Fund`, a separate fund.

**Figure movement** (measured on the Wayne Tower example; PM sign-off required before archive):
year-one estimated surplus **−643,780,247 VND** (`RO2a` −5,000,000, `EMH2`/staff −638,780,247).
The staff swing is larger than first estimated for two reasons: the deliverable's roster includes a
Reception group with no predefined `A1` row-group — priced on the same full-payroll basis as
everything else, it is ~8.7% of the 23-head in-house roster, not the "one or two positions, <0.5%"
first assumed (see design.md Risks) — and, once Reception was given a real row on `A1` (rather than
a Python-computed top-up folded into `EMH2`'s formula), its real formula chain also picks up `A1`'s
smaller extras (team building, 1.3% training, annual checkup, accident insurance, uniform) that the
Python approximation had omitted — a further +5,755,257 VND.

## Capabilities

### New Capabilities

- `deliverable-total-integrity`: the client deliverable's grand total (`1. Summary`) SHALL tie to
  the detail sheets it aggregates — every code's year total, the two total columns (`G` / `AK`) of
  the budget sheet, and the staff figure against the deliverable's own payroll sheet — and
  verification SHALL enforce it.

### Modified Capabilities

- `standard-budget-template`: the "carried without adding broken references" requirement is
  broadened — **no** sheet in the deliverable (not only new scaffolding) may ship with an error cell
  the pipeline could have resolved, and the pipeline SHALL NOT write values into a sheet that no
  formula consumes.

## Impact

- **Affected code**:
  - `generate_project_budget.py` — the `RO2a` zero-out (new, small), `fill_management_fund_sheet`'s
    `staff_remainder`/`EMH2` write (now an `A1` formula reference + unmatched-position top-up),
    `fill_staff_cost_sheet` (may need to fill more `A1` rows / read its total), and removal of the
    `A2‑A5 / B2‑B5` rate/count writes plus their error cells.
  - `generate_project_output.py` — the analysis workbook's staff basis, to stay aligned with the new
    `EMH2`.
  - `verification/checks.py` + `verify.py` — the new reconciliation check (section 5d), following
    `check_revenue_agreement` / `check_benchmark_reconciles`.
- **Affected data**: none. Reads only what the two generators already read. **Generation A
  (deliverable-writing) only; no Generation B table and no Fact/Dim join key changes** — the Copilot
  Studio package's live data is unaffected.
- **Baselines**: `verification/baselines/deliverable_baseline.json` moves (`estimated_surplus_year1`,
  and staff-derived figures) — re-record with a stated reason after PM sign-off. The 24-figure
  analysis baseline (`baseline.json`) moves for the staff figures on the same sign-off.
- **Risk**: Medium — a deliberate, measured client-facing figure movement (−644M surplus). Low
  technical risk: the reconciliation is now enforced by `verify.py` on every run.
