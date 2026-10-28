# budget-adjustment-sheet Specification

## Purpose
How sheet `4. Điều chỉnh` of a deliverable adjusts a budget code before hand-over: the adjustment types (Số lượng,
Đơn giá, Số lượng + Đơn giá, Trượt giá) and their effect on the detail rows, and how a deliverable built with an older
sheet is upgraded when the Budget web saves into it.

## Requirements

### Requirement: Adjustment types of a budget code

Each budget code on sheet `4. Điều chỉnh` SHALL take at most one adjustment type, chosen on its total row: blank
(original figure), "Số lượng", "Đơn giá", "Số lượng + Đơn giá" or "Trượt giá". On each detail row the new amount SHALL
be: "Số lượng" new quantity × original unit price; "Đơn giá" original quantity × new unit price; "Số lượng + Đơn giá"
new quantity × new unit price; "Trượt giá" original amount × (1 + the total row's %); blank, the original amount. A
detail row whose quantity is locked (a lumped row) SHALL keep its original quantity under every type. A code without
detail rows SHALL accept only blank or "Trượt giá". New quantity and new unit price SHALL NOT be negative; the % SHALL
be greater than −100%. The Excel formula of column M, the dropdown of column D, the web's preview and the web's
validation SHALL apply the same rule.

#### Scenario: Both quantity and price change
- **WHEN** a security code has a detail row of 4 posts at 20,000,000 and the PM picks "Số lượng + Đơn giá", new
  quantity 5 and new unit price 22,000,000
- **THEN** the row's new amount SHALL be 110,000,000 in the web preview and in column M after Excel recalculates
- **AND** the fund sheet's month cells of that code SHALL follow through the existing new / original ratio

#### Scenario: A lumped row under the combined type
- **WHEN** a code's only detail row is a lumped row (quantity locked) and the PM picks "Số lượng + Đơn giá" with a new
  unit price 10% higher
- **THEN** the new amount SHALL be the original quantity × the new unit price

#### Scenario: A code without detail rows
- **WHEN** the PM sends "Số lượng + Đơn giá" for a code without detail rows
- **THEN** the web SHALL refuse it with "chỉ điều chỉnh được bằng trượt giá" and write nothing

### Requirement: An older adjustment sheet is upgraded when the web saves into it

When the web writes an adjustment into a deliverable whose sheet `4. Điều chỉnh` was built before the combined type
existed, it SHALL rewrite every detail row's column M formula and the column D dropdown to the current form before
saving, so that "Số lượng + Đơn giá" works on that file. Under blank, "Số lượng", "Đơn giá" and "Trượt giá" the
figures SHALL be identical before and after the upgrade.

#### Scenario: Saving into a deliverable of an earlier release
- **WHEN** the PM picks "Số lượng + Đơn giá" on a run made before this change and saves
- **THEN** the saved file's detail formulas SHALL include the combined type and its figures SHALL follow it after
  Excel recalculates
- **AND** every other code's figures SHALL equal those of the file before the save
