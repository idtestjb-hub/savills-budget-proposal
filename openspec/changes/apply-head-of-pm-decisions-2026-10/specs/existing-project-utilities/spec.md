## MODIFIED Requirements

### Requirement: Prices and VAT come from a dated, sourced tariff table

Every unit price and VAT rate the tool uses for these lines SHALL come from a tariff table. Each row of that table
SHALL carry:
- the utility, the tariff category and the component (base price, drainage-and-wastewater charge, VAT);
- the value and its unit;
- the date from which the row is in force;
- the legal basis and the date it was checked.

The VAT on electricity and on the drainage-and-wastewater charge SHALL be the table's general VAT rate (shared with the
other lines the budget prices, see the capability `dated-tax-and-tariff-rates`), not a copy held on the electricity or
water rows. The VAT on clean water SHALL stay its own 5% row.

The budget-year price of each month SHALL be the price in force in that month. The tool SHALL NOT apply any
percentage uplift of its own. A month not covered by the table SHALL stop the run and name the month and the
category.

#### Scenario: VAT changes at the start of the budget year

- **WHEN** the table carries the general VAT rate 8% until 2026-12-31 and 10% from 2027-01-01, and the budget year is
  2027
- **THEN** every month of 2027 SHALL use 10% on electricity and on the drainage-and-wastewater charge
- **AND** the remark SHALL name the VAT rate and its legal basis

#### Scenario: No uplift without a published change

- **WHEN** no tariff row changes between the baseline window and the budget year
- **THEN** the budget-year unit price excluding VAT SHALL equal the baseline unit price excluding VAT

#### Scenario: A row without a legal basis is rejected

- **WHEN** a tariff row has no legal basis or no effective date
- **THEN** loading the table SHALL fail and name the row

#### Scenario: Equal prices, equal Existing figures

- **WHEN** an Existing-project sample is run before and after the general VAT rate replaces the per-utility VAT rows
- **THEN** every `EEE.C` and `EEW.C` figure SHALL be identical, because the general rate equals the old per-utility
  rates in every month

### Requirement: Default tariff categories and the PM's own unit price

Unless the PM chooses another category, the tool SHALL use these categories:

| Line | Default category | Unit price excl. VAT | Legal basis |
|---|---|---|---|
| `EEE.C` | Administrative and public-service use, below 6 kV | 2,226 VND/kWh | QĐ 1279/QĐ-BCT; TT 60/2025/TT-BCT Điều 8.2.b |
| `EEW.C` | Ho Chi Minh City household top tier, plus the drainage and wastewater charge (30% of the base price) | 14,400 VND/m³ base | QĐ 25/2019/QĐ-UBND Điều 2 (chung cư in the household group); QĐ 17/2021/QĐ-UBND |

The PM SHALL be able to choose another category from the table: for electricity, 6 kV and above, or business use; for
water, the business or the administrative customer group (the two groups the capability `dated-tax-and-tariff-rates`
prices, each with the same drainage-and-wastewater charge). Choosing a water group is a choice only: a blank category
SHALL keep the household top tier. The PM SHALL also be able to enter the unit price shown on the bill, with its
source. That price is excluding VAT, and it SHALL win over the table for the line. VAT still follows the table.

The water default SHALL apply only when the project's "City / Province" is Ho Chi Minh City, and so SHALL the business
and administrative water groups, whose table prices are the Ho Chi Minh City ones. When it is another province, or
blank, and the PM has entered no water bill price, the run SHALL stop and name both fields. A category that has no
single price in the table (business electricity, which is billed by time band) SHALL also require the bill price, and
the run SHALL stop without it.

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

#### Scenario: An Existing project chooses the business water group

- **WHEN** an Existing project in Ho Chi Minh City selects the business water group for `EEW.C` and the budget is for
  2027
- **THEN** `EEW.C` SHALL be priced from the business group's table rows (base 21,300 VND/m³)
- **AND** the remark SHALL name the group as the PM's choice

#### Scenario: An Existing project leaves the water group blank

- **WHEN** an Existing project leaves the water category blank
- **THEN** `EEW.C` SHALL stay priced at the household top tier, and every figure SHALL equal the figure before the
  business and administrative groups were added
