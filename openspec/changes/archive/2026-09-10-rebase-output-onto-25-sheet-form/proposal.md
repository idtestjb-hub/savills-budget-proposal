## Why

Decision D6 (`docs/05-decisions.md`, 2026-09-09) made the 25-sheet **AI Guideline 2027 Resi Budget
Form (IT team)** the standard output template. The pipeline still builds the client deliverable on
the older `202608 - 2027 Resi Budget Form.xlsx` (21 sheets — 19 Savills sheets plus the two staff
sheets a PM pasted in on 2026-08-28). Three sheets the 25-sheet form carries and the deliverable
lacks — the resident fill-up schedule, the parking fill-up schedule, and the QĐ 67/2025 household-
waste tariff table — are exactly the scaffolding the next two changes in the family need
(`docs/08-guideline-change-family.md`, changes B and D). This change adds them, and moves no budget
figure.

## What Changes

- **A blank standard template is produced and committed to `input/template/`.** Built from the
  AI Guideline form's Savills sheets with its `AI GUIDELINE` instruction columns cleared (design D1
  — the full sheet diff, task 1.1, showed `3. Budget-Sinking Fund` / `3.1` / `1. Summary` differ
  materially from `202608` and must travel as one matched set, so a graft from `202608` is not
  viable). No staff-sheet graft: the guideline form's native `A1. Staff cost 08.2026 (VN)` /
  `A1.1 Allowance` are the same calculator as `202608`'s `1. Staff cost` / `1.1 Allowance`, so
  `STAFF_COST_SHEET` is re-pointed at `A1.` (design D1) and the fill runs unchanged. The example
  curve values on the three new sheets are cleared where identifiable.
- **The pipeline points at the new template.** `generate_project_budget.py`'s `TEMPLATE_PATH`
  changes. The only other code change: the `0. Info` write block, because the new form's fee table
  has `Shophouse` where `202608` had `Shopping Mall` at row 11 (design D1a). `0. Info` is a display
  sheet — nothing in the pipeline reads it — so **no budget figure moves.** Every code written to
  `2. Budget-Management Fund` / `2.2 Common area Fund` sits at the same row as before.
- **The deliverable gains `Tỷ lệ lấp đầy cư dân`, `Tiến độ lấp đầy bãi xe` and `B2.6 Rác sinh hoạt
  (QD67)` as blank scaffolding**, plus the standard form's updated `1. Summary` / sinking-fund
  sheets. Changes B and D fill the new sheets later.
- **`Master Info ( tính Staff cost)` is NOT carried into the deliverable template.** Its ~1,577
  formulas link to an external workbook (`[3]…`) and already carry `#REF!`; including it would put
  formula errors into a client file and fail the verification harness. Benchmark comparables belong
  with the per-product management-fee change (C), not here. This is a deliberate narrowing of D6's
  "…and the Master Info benchmark comparables", recorded in `design.md`.
- **The 19-sheet `202608` form stays in `input/template/` as backup**, marked superseded — not
  deleted.
- `fill_staff_cost_sheet` now writes the standard form's own `A1. Staff cost 08.2026 (VN)` (it is
  the same payroll calculator the pipeline already used). The deliverable carries one staff sheet,
  not two — this closes, rather than defers, the A1/A1.1 reconciliation.

**No figure the pipeline writes moves, and none of the 24 verification baseline figures move.** The
client deliverable's *total* shifts by ~28,000,000 VND (−0.28% of expense) because the superseded
`202608` form shipped two unsourced example values — `ESC12` (14M) and `ESM25` (14M/yr) — that
Savills' current standard form leaves blank (design D1b; change D fills them with a real basis).
No BREAKING change to any output value the pipeline computes.

## Capabilities

### New Capabilities

- `standard-budget-template`: the client deliverable is built on Savills' current standard budget
  template and carries its full sheet set, including the fill-up and waste-tariff sheets that later
  changes populate; switching the template preserves every figure the pipeline already writes and
  introduces no spreadsheet formula errors.

### Modified Capabilities

- `budget-workflow-verification`: the recorded sheet-count baseline changes (the deliverable grows
  from 22 sheets to 25 — 24 Savills sheets and `Comparison`), and the harness gains a check that the
  deliverable carries every sheet name the standard template defines.
  The existing "zero formula errors after recalculation" and "no corruption artifacts" requirements
  are unchanged in intent but must pass against the new template.

## Impact

**Affected code**

- `generate_project_budget.py` — `TEMPLATE_PATH` constant; the `0. Info` write block (row 11
  `Shopping Mall` → `Shophouse`, design D1a) and its stale comment; the sheet-count assertion, if
  any. No change to `MGMT_FUND_ROWS`, `PRODUCT_REVENUE_ROWS`, `COMMON_AREA_FUND_ROWS`, the fund /
  common-area / staff-cost fill functions, or any figure they write.
- `generate_project_output.py` — untouched; it builds the 5-sheet internal analysis and explicitly
  does not use the template.
- `verification/` — the recorded baseline (sheet count, and the headline-figure baseline if a
  recalculation shifts only rounding) is re-recorded with a stated reason; a new assertion that the
  deliverable carries every standard-template sheet name.

**New files**

- `input/template/2027 Resi Budget Form (IT team).xlsx` — the blank standard template, committed.
- A one-time builder script that produces it from the AI Guideline form (+ `202608` for the two
  staff sheets), kept with the change (same pattern as `adopt-guideline-as-costing-method-spec`'s
  `build_catalogue.py`).

**Data scope** — reads and writes no Generation A or Generation B table; changes no Fact/Dim join
key. The Copilot Studio package's live data is unaffected. Money and headcount figures in the
generated workbook are unchanged in value and keep their existing currency (VND) and unit labels.

**Depends on** — decision D6; the archived change `adopt-guideline-as-costing-method-spec` (the
catalogue and `docs/08` change family). Unblocks change B (occupancy ramp) and change D (blank
lines / waste).
