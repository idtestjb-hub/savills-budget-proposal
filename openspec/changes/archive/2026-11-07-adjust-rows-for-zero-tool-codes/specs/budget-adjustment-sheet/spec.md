## MODIFIED Requirements

### Requirement: Adjustment types of a budget code

Each budget code on sheet `4. Điều chỉnh` SHALL take at most one adjustment type, chosen on its total row: blank
(original figure), "Số lượng", "Đơn giá", "Số lượng + Đơn giá", "Trượt giá" or "Nhập số". On each detail row the new
amount SHALL be: "Số lượng" new quantity × original unit price; "Đơn giá" original quantity × new unit price; "Số
lượng + Đơn giá" new quantity × new unit price; "Trượt giá" original amount × (1 + the total row's %); "Nhập số" the
figure typed in the row's "Đơn giá mới" cell, read as the row's new annual amount in VND; blank, the original
amount. A detail row whose quantity is locked (a lumped row) SHALL keep its original quantity under every type. A
code without detail rows SHALL accept only blank or "Trượt giá". New quantity, new unit price and the "Nhập số"
figure SHALL NOT be negative; the % SHALL be greater than −100%. The Excel formula of column M, the dropdown of
column D, the web's preview and the web's validation SHALL apply the same rule.

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

#### Scenario: A typed amount
- **WHEN** a code with one lumped detail row of original amount 0 gets the type "Nhập số" and the figure 240,000,000
- **THEN** the row's new amount SHALL be 240,000,000, the code's total 240,000,000, and each of the fund row's twelve
  month cells 20,000,000 after Excel recalculates

## ADDED Requirements

### Requirement: A Review adds a row for every approved code the tool left at zero
After the generators of a Review run, every on-form code that carries an approved figure (at least 0.5 VND in
absolute value) and a tool figure of 0 SHALL get a total row on sheet `4. Điều chỉnh` with one lumped detail row
(quantity 1 locked, original unit price 0, original amount 0) and its fund row's month cells linked to that total
row, so the PM can adjust it on the web or in Excel. A code whose row cannot be found on the fund sheet SHALL be
named in the run log and skipped. A new-project run SHALL NOT add such rows. Untouched, a zero row SHALL leave
every month cell at 0, so the deliverable's figures are the generator's.

#### Scenario: Zero rows present
- **WHEN** a Review run's approved budget prices ESS38 at 3,175,200,000 VND and the tool prices it at 0
- **THEN** sheet `4. Điều chỉnh` has a total row ESS38 with "Thành tiền gốc" 0 and one detail row, and the fund
  row's twelve months read 0 after Excel recalculates

#### Scenario: Month link for a zero original
- **WHEN** a fund row linked to a zero row is recalculated after the PM types a "Nhập số" figure
- **THEN** each month cell equals that figure / 12, and `1. Summary` and the contingency lines follow

#### Scenario: New-project run unchanged
- **WHEN** "Tạo ngân sách" runs for a new project
- **THEN** sheet `4. Điều chỉnh` holds the same rows as before this change
