## Context

Sheet `4. Điều chỉnh` (docs/32 §3, `budget_adjustment.py`) has one total row per code with the type dropdown (D) and
the inflation % (L), and detail rows with original quantity G, unit price H, amount I, new quantity J, new unit price K;
M is `IF($D="Số lượng",J*H,IF($D="Đơn giá",G*K,IF($D="Trượt giá",I*(1+$L),I)))`. J of a lumped row is `=G` and locked.
The web (`webapp/adjust.py`, `index.html`) reads the sheet, previews with the same rule, and writes only D, L, J, K.

## Goals / Non-Goals

- Goal: one more type with both J and K live, in Excel and on the web, also on deliverables of earlier releases.
- Non-goal: combining inflation with quantity or price; changing any existing type; any figure of the pipeline.

## Decisions

1. **Name "Số lượng + Đơn giá"** (user's choice). Constant `TYPE_QTY_PRICE` in `budget_adjustment.py`; order in the
   dropdown: Số lượng, Đơn giá, Số lượng + Đơn giá, Trượt giá.
2. **Formula J × K.** J of a lumped row is `=G`, so the same formula gives G × K without a special case. In the web
   preview the locked quantity is the original one, as for "Số lượng".
3. **Upgrade on save, not on read** (user's choice). `apply_edits` rewrites M of every detail row with
   `detail_formula(parent_row, row)` and replaces the sheet's list validation with the current type list. The
   formula depends only on row numbers, which `_scan` finds again, so the rewrite is idempotent and gives the same
   figure for the old types. Reading a run never changes its file.
4. **Inflation % locked** under the combined type, as under Số lượng and Đơn giá.

## Risks / Trade-offs

- [A PM edited the M formula by hand in Excel] → the sheet is protected and M is locked, so a hand edit means the
  protection was removed; the upgrade overwrites it. Accepted: the web already treats M as template-owned.
- [An older file opened in Excel without going through the web] → the dropdown there lacks the new type; picking it
  needs a save through the web once. Accepted (user's choice).

## Migration Plan

Budget-web release through [Hub] after tests and verify.py PASS. Rollback = previous release; a file saved with the
combined type under the new release keeps its upgraded formulas and still opens correctly in Excel.
