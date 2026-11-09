## ADDED Requirements

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
