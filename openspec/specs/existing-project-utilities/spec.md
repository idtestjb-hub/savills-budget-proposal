## Purpose
Defines how the tool budgets common-area electricity (`EEE.C`) and common-area water (`EEW.C`) for a project Savills
already manages. It starts from the building's actual spend over the last 12 months, prices that consumption at the
tariff and VAT in force in each month of the budget year, and explains every change from last year's approved budget.

Data files read:
- the input workbook (project mode, Prior-Year Utilities sheet);
- the utility tariff table `Ref_UtilityTariffs.csv` (new).

Data files written: none besides the output workbooks.

No recorded baseline figure moves. New-prospect mode is unchanged, and the standard sample is a new prospect.

## Requirements

### Requirement: New-prospect mode is unchanged

In "New prospect" mode the tool SHALL price `EEE.C` and `EEW.C` exactly as it did before this change, ignoring the
Prior-Year Utilities sheet even if it has been filled in.

#### Scenario: The standard sample after the change

- **WHEN** the standard (New prospect) sample is run before and after this change
- **THEN** every cell of the client deliverable and of the analysis workbook SHALL be identical

#### Scenario: A new prospect with utility actuals typed in

- **WHEN** the mode is "New prospect" and the Prior-Year Utilities sheet holds figures
- **THEN** `EEE.C` and `EEW.C` SHALL be priced as for a new prospect
- **AND** the run's printed summary SHALL say that the utility actuals were not used because the mode is "New prospect"

### Requirement: The baseline is the actual average of the 12 most recent months

In "Existing project" mode the PM SHALL be able to enter, for each of `EEE.C` and `EEW.C` and for each month (MM/YYYY),
the following:
- the amount actually spent, in VND;
- whether that amount includes VAT;
- optionally, the consumption (kWh for electricity, m³ for water).

The window SHALL be the 12 calendar months ending with the latest month that has an amount. The baseline monthly
consumption SHALL be the average over the months in that window that have an amount. Any month older than the window
SHALL be ignored, and the summary SHALL say how many were ignored.

#### Scenario: Twelve months crossing two calendar years

- **WHEN** amounts are entered for 09/2025 to 08/2026
- **THEN** the window SHALL be 09/2025 to 08/2026
- **AND** the baseline SHALL be the average of those 12 months

#### Scenario: Older months are ignored

- **WHEN** amounts are entered for 03/2025 to 08/2026
- **THEN** only 09/2025 to 08/2026 SHALL be used
- **AND** the summary SHALL state that 6 older months were not used

#### Scenario: A month inside or after the budget year is rejected

- **WHEN** an amount is entered for a month in or after the budget year
- **THEN** the run SHALL stop and name the line and the month

### Requirement: Blank, zero, negative and duplicate months are handled explicitly

The tool SHALL treat month entries as follows:
- **Blank amount:** the month SHALL be treated as missing and left out of the average.
- **Zero amount:** the month SHALL count as zero. The zero SHALL be flagged in the run's printed summary and on the
  Utility Bridge.
- **Negative amount:** the run SHALL stop.
- **Duplicate month:** if the same line and month appear twice, the run SHALL stop and name both rows. The tool SHALL
  neither add them nor choose one.

#### Scenario: A month with no bill yet

- **WHEN** the window has 11 months with amounts and one blank month
- **THEN** the baseline SHALL be the average of the 11 months
- **AND** the remark and the Utility Bridge SHALL say that 11 months were used

#### Scenario: A zero month is counted and flagged

- **WHEN** one month in the window holds 0 VND
- **THEN** that month SHALL count as zero in the average
- **AND** the summary and the Utility Bridge SHALL flag the month as zero

#### Scenario: The same month typed twice

- **WHEN** the line `EEE.C` has two rows for 05/2026
- **THEN** the run SHALL stop and name both rows

### Requirement: Fewer than 3 months fall back to the approved amount

With 3 to 11 months in the window, the baseline SHALL be the average of those months, applied to 12 months, and the
remark and the Utility Bridge SHALL flag that the year is incomplete. With fewer than 3 months, the tool SHALL take as
baseline the approved prior-year amount of that line (VND per year, with its VAT basis), repriced only for the tariff
and VAT change between the prior year and the budget year. If that amount is also missing, the run SHALL stop and name
the missing fields.

#### Scenario: Eight months of actuals

- **WHEN** 8 months have amounts
- **THEN** the budget-year consumption SHALL be the 8-month average times 12
- **AND** the remark SHALL say that the figure rests on 8 months

#### Scenario: Two months and an approved amount

- **WHEN** 2 months have amounts and the approved prior-year amount is 250,000,000 VND per year including VAT
- **THEN** the baseline SHALL be 250,000,000 VND repriced for the tariff and VAT change only
- **AND** the remark SHALL say that the actual data were too few and the approved budget was used

#### Scenario: Nothing to start from

- **WHEN** a line has fewer than 3 months and no approved prior-year amount
- **THEN** the run SHALL stop and name the line, the months field and the approved-amount field

### Requirement: Consumption is taken from the bill or derived from the amount

When a month has a consumption figure, the tool SHALL use it, and SHALL check the unit price it implies against the
tariff of the line's category for that month on the same VAT basis. A difference above 1% SHALL be flagged. When a
month has no consumption figure, the tool SHALL derive it as the amount divided by the unit price for that month on the
amount's VAT basis. That unit price is the PM-entered price when there is one, otherwise the tariff table's.

#### Scenario: Amount only

- **WHEN** a month of `EEE.C` shows 48,081,600 VND including 8% VAT and the category is the default
- **THEN** the derived consumption SHALL be 48,081,600 ÷ (2,226 × 1.08) = 20,000 kWh

#### Scenario: Bill rate differs from the category

- **WHEN** a month shows 20,000 kWh and an amount that implies 3,152 VND/kWh excluding VAT, and the category is the
  default administrative rate of 2,226 VND/kWh
- **THEN** the month SHALL be flagged as priced at a different rate than the chosen category
- **AND** the flag SHALL suggest checking the tariff category

### Requirement: Prices and VAT come from a dated, sourced tariff table

Every unit price and VAT rate the tool uses for these lines SHALL come from a tariff table. Each row of that table
SHALL carry:
- the utility, the tariff category and the component (base price, drainage-and-wastewater charge, VAT);
- the value and its unit;
- the date from which the row is in force;
- the legal basis and the date it was checked.

The budget-year price of each month SHALL be the price in force in that month. The tool SHALL NOT apply any
percentage uplift of its own. A month not covered by the table SHALL stop the run and name the month and the
category.

#### Scenario: VAT changes at the start of the budget year

- **WHEN** the table carries electricity VAT 8% until 2026-12-31 and 10% from 2027-01-01, and the budget year is 2027
- **THEN** every month of 2027 SHALL use 10%
- **AND** the remark SHALL name the VAT rate and its legal basis

#### Scenario: No uplift without a published change

- **WHEN** no tariff row changes between the baseline window and the budget year
- **THEN** the budget-year unit price excluding VAT SHALL equal the baseline unit price excluding VAT

#### Scenario: A row without a legal basis is rejected

- **WHEN** a tariff row has no legal basis or no effective date
- **THEN** loading the table SHALL fail and name the row

### Requirement: Default tariff categories and the PM's own unit price

Unless the PM chooses another category, the tool SHALL use these categories:

| Line | Default category | Unit price excl. VAT | Legal basis |
|---|---|---|---|
| `EEE.C` | Administrative and public-service use, below 6 kV | 2,226 VND/kWh | QĐ 1279/QĐ-BCT; TT 60/2025/TT-BCT Điều 8.2.b |
| `EEW.C` | Ho Chi Minh City household top tier, plus the drainage and wastewater charge (30% of the base price) | 14,400 VND/m³ base | QĐ 25/2019/QĐ-UBND Điều 2 (chung cư in the household group); QĐ 17/2021/QĐ-UBND |

The PM SHALL be able to choose another category from the table: for electricity, 6 kV and above, or business use.
The PM SHALL also be able to enter the unit price shown on the bill, with its source. That price is excluding VAT, and
it SHALL win over the table for the line. VAT still follows the table.

The water default SHALL apply only when the project's "City / Province" is Ho Chi Minh City. When it is another
province, or blank, and the PM has entered no water bill price, the run SHALL stop and name both fields. A category
that has no single price in the table (business electricity, which is billed by time band) SHALL also require the
bill price, and the run SHALL stop without it.

#### Scenario: A project outside Ho Chi Minh City

- **WHEN** the PM enters a water unit price of 12,000 VND/m³ excluding VAT from the local water company's bill
- **THEN** `EEW.C` SHALL be priced at 12,000 VND/m³ plus VAT
- **AND** the remark SHALL name the PM-entered price and its source, and SHALL NOT cite the Ho Chi Minh City decision

#### Scenario: Outside Ho Chi Minh City without a bill price

- **WHEN** "City / Province" is not Ho Chi Minh City, or is blank, and no water bill price is entered
- **THEN** the run SHALL stop and name the "City / Province" field and the water unit-price field

#### Scenario: Business electricity without a bill price

- **WHEN** the PM chooses the business electricity category and enters no bill price
- **THEN** the run SHALL stop and name the line and the unit-price field

### Requirement: The budget-year figure and its monthly spread

For each line, the budget-year consumption SHALL be the baseline monthly consumption, or the PM's override when one is
given, in every month of the budget year. Each month's amount SHALL be that consumption times that month's unit price.
VAT SHALL be added when the form's VAT switch (`2. Budget-Management Fund`!F7) shows an inclusive model ("KHÔNG KHOÁN"
or "THU HỘ CHI HỘ"), and SHALL NOT be added for "KHOÁN". No fill-up curve and no electricity floor SHALL apply.

#### Scenario: Even months when nothing changes in the year

- **WHEN** no tariff row changes during the budget year
- **THEN** the twelve monthly amounts of the line SHALL be equal
- **AND** they SHALL sum to the line's annual figure

#### Scenario: An exclusive-of-VAT model

- **WHEN** the VAT switch is "KHOÁN"
- **THEN** the line SHALL be consumption × unit price excluding VAT

### Requirement: A PM override of consumption carries a reason

The PM SHALL be able to override the budget-year monthly consumption of a line, for example because a new clubhouse
opens or irrigation is budgeted to a norm. An override SHALL carry a reason code from the approved list, plus a note:

- Mở dịch vụ hoặc tiện ích mới
- Thay đổi giờ vận hành
- Bàn giao hoặc bổ sung khu vực quản lý
- Thay đổi số cư dân vào ở
- Tiết kiệm năng lượng
- Khác (bắt buộc ghi chú)

An override without a reason code, or with "Khác" and no note, SHALL stop the run and fail verification. Changes that
come only from actual consumption, tariff or VAT SHALL carry a reason the tool writes itself.

#### Scenario: Override with a reason

- **WHEN** the PM overrides `EEE.C` to 25,000 kWh per month with "Mở dịch vụ hoặc tiện ích mới" and the note "clubhouse
  mở từ 03/2027"
- **THEN** the line SHALL use 25,000 kWh per month
- **AND** the remark SHALL give the reason and the note

#### Scenario: Override without a reason

- **WHEN** an override has no reason code
- **THEN** the run SHALL stop and name the line

### Requirement: The Utility Bridge ties the prior year to the budget year

The analysis workbook SHALL carry, in Existing-project mode only, an internal sheet "Utility Bridge". It SHALL show, for
`EEE.C` and `EEW.C`, the following in VND per year:
- the approved prior-year amount (when given);
- the actual baseline;
- the consumption effect;
- the tariff effect;
- the VAT effect;
- the PM override effect;
- the budget-year figure.

It SHALL also list the months used and every flag (missing months, zero months, rate differences). The budget-year
figure of each line SHALL equal that line's annual figure on the client deliverable. The sheet SHALL NOT appear on the
client deliverable.

#### Scenario: The bridge ties

- **WHEN** an Existing-project sample is run
- **THEN** the Utility Bridge's budget-year figure for `EEE.C` SHALL equal `EEE.C`'s annual total on
  `2. Budget-Management Fund`, and the same for `EEW.C`

#### Scenario: No bridge for a new prospect

- **WHEN** a New-prospect project is run
- **THEN** the analysis workbook SHALL have no Utility Bridge sheet
