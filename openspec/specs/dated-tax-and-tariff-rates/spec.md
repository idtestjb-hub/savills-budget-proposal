# dated-tax-and-tariff-rates Specification

## Purpose
Keeps one dated source for the VAT rates and the utility and fuel tariffs the budget uses, and adds VAT by month to the
lines the tool prices excluding VAT, so that a tariff or tax change moves every budget that depends on it, in both
project modes, from one place.

Data files read: `Ref_UtilityTariffs.csv`, which gains the diesel price, the business and administrative water rows and
the VAT rates (or a dated VAT table beside it, as the design decides). `Fact_OPEX.csv`'s water and diesel prices are no
longer read; its usage figures still are. Data files written: none besides the output workbooks. Recorded baselines move
for electricity, water, diesel, `ESS9`, `ESC12`, `ESM25`, total expense and surplus.

## Requirements

### Requirement: One dated source holds every tariff and VAT rate

Every utility tariff, fuel price and VAT rate the budget uses SHALL come from one dated source in which each row states
its first day in force, its last day in force where one is set, and its legal or published basis. New-prospect and
Existing-project budgets SHALL both read it, and no second copy of the same price SHALL be read anywhere else.

#### Scenario: A tariff row changes

- **WHEN** a tariff row in the dated source is changed
- **THEN** both a new-prospect and an Existing-project budget that use that tariff SHALL move by it
- **AND** no other file SHALL hold a price that overrides it

### Requirement: The VAT rate is the one in force in each budget month

The general VAT rate SHALL be 8% for a month up to 31/12/2026 and 10% from 01/01/2027 (Nghị quyết 204/2025/QH15 and
Nghị định 174/2025/NĐ-CP). Insurance SHALL be at 10% in every month, because it is excluded from the reduction.

#### Scenario: A 2027 month

- **WHEN** a budget month falls in 2027
- **THEN** the general VAT rate for that month SHALL be 10%

#### Scenario: A 2026 month

- **WHEN** a budget month falls in 2026
- **THEN** the general VAT rate for that month SHALL be 8%, and insurance SHALL still be 10%

### Requirement: Lines priced excluding VAT add each month's VAT

`ESC12`, `ESM25`, `ESS9` and a new prospect's `EEE.C` SHALL be written as the amount excluding VAT times (1 + that
month's VAT rate). A
line spread evenly over the year (`ESC12` once a year, `ESM25` quarterly) SHALL stay spread evenly, with VAT applied to
each month's share. The line's remark SHALL state the VAT rate applied and the months it applies to, and SHALL NOT say
the figure excludes VAT.

#### Scenario: Electricity in a 2027 budget

- **WHEN** `EEE.C` is priced at 2,226 VND/kWh excluding VAT for a January–December 2027 budget
- **THEN** each month SHALL equal that month's excl.-VAT amount times 1.10
- **AND** its remark SHALL state that VAT of 10% is included

#### Scenario: No contradictory VAT wording

- **WHEN** any of the four lines is written
- **THEN** its remark SHALL NOT contain "(chưa gồm VAT)"

### Requirement: A line already priced including VAT gets no second VAT

VAT by month SHALL be added only to amounts the tool prices excluding VAT. These amounts are already gross and SHALL be
written as they are:
- Existing mode's electricity and water: an actual average, or the approved amount repriced from the dated source;
- the collect-on-behalf pairs;
- an amount the PM entered including VAT.

#### Scenario: Existing-project electricity

- **WHEN** an Existing-project `EEE.C` is taken from the actual average of last year's bills
- **THEN** no VAT factor SHALL be applied to it

#### Scenario: Collect-on-behalf pair

- **WHEN** a collect-on-behalf electricity pair is entered
- **THEN** its revenue and expense lines SHALL equal the entered amounts, with no VAT added

### Requirement: Water is priced by the building's customer group

The input form SHALL offer the building's water customer group: business or administrative. For a new prospect the
default SHALL be business. In Existing-project mode the default SHALL stay the one `existing-project-utilities` sets
(household top tier, approved 2026-10-11), and the two groups SHALL be available as choices. The price per
m³ SHALL be the group's base price plus 5% VAT, plus a 30% drainage charge on the base, plus that month's VAT on the
drainage charge. Business base: 21,300 VND/m³ (29,266 all-in in 2026, 29,394 from 2027). Administrative base: 13,000
VND/m³ (17,862 in 2026, 17,940 from 2027). The remark SHALL name the group and say when it is the default.

#### Scenario: Blank customer group

- **WHEN** the customer group is blank on a new prospect
- **THEN** water SHALL be priced at the business rate
- **AND** the remark SHALL say the business rate is the default

#### Scenario: Blank customer group in Existing mode

- **WHEN** the customer group is blank on an Existing project
- **THEN** water SHALL keep the household top-tier default

#### Scenario: Administrative building

- **WHEN** the PM selects administrative for a 2027 budget
- **THEN** water SHALL be priced at 17,940 VND/m³

### Requirement: Diesel is priced from the dated listed price

Diesel SHALL be priced from the listed Region 1 price of 29,710 VND/l in force from 01/10/2026, which includes 8% VAT.
Each month's price SHALL be 29,710 / 1.08 × (1 + that month's VAT rate). The remark SHALL name the fuel grade as the
price source states it and the listing date.

#### Scenario: A 2027 month

- **WHEN** diesel is priced for a 2027 month
- **THEN** the price SHALL be 29,710 / 1.08 × 1.10 VND/l, about 30,260

### Requirement: A new prospect's utility usage is unchanged by a price change

A new prospect's water and diesel usage per m² SHALL stay as recorded. A price change SHALL move the cost in proportion
and SHALL NOT be absorbed by re-deriving the usage.

#### Scenario: The water price rises

- **WHEN** the water price changes from 19,786 to 29,394 VND/m³
- **THEN** the new-prospect water cost SHALL rise by the same ratio

### Requirement: The analysis applies the same prices and VAT by month

The internal analysis SHALL price electricity, water and diesel from the same dated source and SHALL apply each budget
month's VAT rate, so that its energy lines differ from the deliverable's only by the occupancy basis it already
discloses, not by price or tax.

#### Scenario: Electricity in a 2027 budget

- **WHEN** the analysis prices electricity for a January–December 2027 budget
- **THEN** its annual electricity cost SHALL equal its monthly amount excluding VAT times 12 times 1.10
