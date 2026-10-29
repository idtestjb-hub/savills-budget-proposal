## MODIFIED Requirements

### Requirement: Diesel is priced from the dated listed price

Diesel SHALL be priced from the listed Region 1 price of "DO 0,05S-II" in force at 00:00 on the 1st of each budget
month (an adjustment at 15:00 on the 1st counts from the next month; one at 00:00 on the 1st counts for that month). The
table SHALL hold one such row per month from January 2024, each with its Petrolimex announcement, and the latest listed
price, 29,710 VND/l from 01/10/2026, for later months. Each listed price carries the VAT of its `listed_vat_pct` row:
10% to 30/06/2025, 8% from 01/07/2025, none from 27/03/2026 (fuel outside output VAT, Nghị quyết 19/2026/QH16 and its
extensions to 31/12/2026). Each month's price SHALL be listed / (1 + listed VAT) × (1 + diesel's VAT rate of that month),
where diesel's rate is its own `vat`/`diesel` row when one is in force (10% while the general cut excluded refined
petroleum, 0% from 27/03/2026 to 31/12/2026) and the general rate otherwise. The remark SHALL name the fuel grade as the
price source states it and the listing date. A month before the table's first row SHALL stop the run naming the month.

#### Scenario: A 2027 month

- **WHEN** diesel is priced for a 2027 month
- **THEN** the price SHALL be 29,710 × 1.10 VND/l, about 32,681

#### Scenario: A month without VAT on fuel

- **WHEN** diesel is priced for April 2026
- **THEN** the price SHALL be the listed 35,440 VND/l with no VAT added

#### Scenario: A month when the general VAT cut excluded fuel

- **WHEN** diesel is priced for January 2025
- **THEN** the price SHALL be the listed price with its 10% VAT, not re-priced at the general 8%
