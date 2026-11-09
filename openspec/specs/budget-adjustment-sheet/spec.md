# budget-adjustment-sheet Specification

## Purpose
How sheet `4. Điều chỉnh` of a deliverable adjusts a budget code before hand-over: the adjustment types (Số lượng,
Đơn giá, Số lượng + Đơn giá, Trượt giá) and their effect on the detail rows, and how a deliverable built with an older
sheet is upgraded when the Budget web saves into it.

## Requirements

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

### Requirement: The frequency of a budget code is set on its total row

Each total row of sheet `4. Điều chỉnh` SHALL carry input cells for the code's new frequency (one of the six of the
form, blank = keep the original), its first month (T1 to T12), its number of times (Optional) and 12 month cells (a
tick for an Optional month, an amount in VND for a Schedule month), next to the original frequency the row already
keeps. The rules of capability `line-frequency` SHALL apply to these cells. When the new frequency is blank the
code's figures SHALL be those it has without this requirement.

The code's new annual amount SHALL be:
- for a new frequency other than Schedule: the amount its adjustment type gives (the sum of the detail rows' new
  amounts, or the inflated total) × the new number of times ÷ the original number of times, where Monthly counts 12
  times and a Schedule original counts 12;
- for Schedule: the sum of the 12 month amounts typed; the adjustment type SHALL then have no effect and the web and
  Excel SHALL say so on the row.

The code's fund row SHALL then be written as capability `line-frequency` describes for the new frequency, with the
per-time price = the new annual amount ÷ the new number of times, so `1. Summary`, the contingency and
`2.2 Common area Fund` follow without any row being inserted.

#### Scenario: Monthly changed to Quarterly
- **WHEN** a code is Monthly at 3,500,000 VND a month (42,000,000 VND/year), the PM leaves the adjustment type blank
  and sets the new frequency Quarterly with first month T3
- **THEN** the code's new amount SHALL be 14,000,000 VND, its difference −28,000,000 VND
- **AND** its fund row SHALL read Quarterly, 3,500,000 VND per time, in T3, T6, T9 and T12

#### Scenario: Frequency and price changed together
- **WHEN** the same code takes "Đơn giá" with a new unit price 10% higher and the new frequency Quarterly
- **THEN** its new amount SHALL be 42,000,000 × 1.10 × 4 ÷ 12 = 15,400,000 VND

#### Scenario: Schedule typed by month
- **WHEN** the PM sets Schedule and types 10,000,000 VND in T4 and 30,000,000 VND in T12, the other months 0
- **THEN** the code's new amount SHALL be 40,000,000 VND and the fund row's H:S SHALL hold those 12 amounts

#### Scenario: Nothing set
- **WHEN** the new frequency is blank on every code
- **THEN** every figure of the workbook SHALL equal that of the same workbook without the new cells

### Requirement: Every written line is listed whatever its frequency

Sheet `4. Điều chỉnh` SHALL list every line written with a figure on either fund sheet, whatever its frequency in
column C, including a line the template already set to Quarterly, Half a Year, Yearly or Optional. Such a line's
original number of times, per-time price and months of payment SHALL be read from its fund row.

#### Scenario: A template half-yearly line
- **WHEN** RO2a is written as Half a Year at 5,000,000 VND per time
- **THEN** sheet 4 SHALL list RO2a with original frequency Half a Year, 2 times and an original amount of
  10,000,000 VND, and the PM SHALL be able to adjust it

### Requirement: An older adjustment sheet gains the frequency cells when the web saves into it

When the web saves into a deliverable whose sheet `4. Điều chỉnh` was built before the frequency cells existed, it
SHALL add them (new frequency blank) before writing the edits, and the figures of every code the PM did not touch
SHALL be identical before and after the save.

#### Scenario: Saving a frequency into an earlier run
- **WHEN** the PM sets Quarterly on one code of a run made before this change and saves
- **THEN** the saved file SHALL carry the frequency cells on every total row, that code SHALL follow Quarterly after
  Excel recalculates, and every other code SHALL keep its figures
