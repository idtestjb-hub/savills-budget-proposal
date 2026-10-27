## Why

On sheet `4. Điều chỉnh` and on the Budget web's adjust table, each budget code takes one adjustment type: Số lượng
(new quantity × original unit price), Đơn giá (original quantity × new unit price) or Trượt giá. A PM who changes
both the number of posts and the contract price of a line (a new security contract with one more post at a new rate,
for example) cannot enter it: one of the two edits is ignored. The user asked on 2026-10-27 for an option with both.

## What Changes

- A fourth adjustment type **"Số lượng + Đơn giá"**: on each detail row, new amount = new quantity × new unit price.
  A lumped row (quantity locked) keeps its original quantity, so only its price moves. A code without detail rows
  cannot take it (inflation only, as for Số lượng and Đơn giá). The inflation % stays locked under this type.
- The deliverable's sheet `4. Điều chỉnh`: dropdown, column M formula of the detail rows and the guide line know the
  new type.
- The Budget web: the type in the dropdown, both input columns open, the preview, the validation and the "cách tính"
  table and guide follow.
- A deliverable made before this change is upgraded when the web saves an adjustment into it: the detail rows' column
  M formulas and the dropdown are rewritten to the new form. Figures under the three existing types do not change.
- No figure of a run without adjustment changes; no baseline moves.

## Capabilities

### New Capabilities
- `budget-adjustment-sheet`: the adjustment types of sheet `4. Điều chỉnh` and of the web adjust table, their
  formulas, and the upgrade of an older sheet. (The sheet's layout so far lived only in docs/32; this capability
  starts its spec with the adjustment types.)

### Modified Capabilities
<!-- none -->

## Impact

- Code: `budget_adjustment.py` (type list, detail formula, guide), `webapp/adjust.py` (types, `new_amount`,
  validation, sheet upgrade in `apply_edits`), `webapp/static/index.html` (dropdown, inputs, preview, guide).
- Tests: `tests/test_budget_adjustment.py`, `tests/test_webapp_adjust.py`.
- Release: budget-web through [Hub]; the pipeline's deliverable also carries the new dropdown.
