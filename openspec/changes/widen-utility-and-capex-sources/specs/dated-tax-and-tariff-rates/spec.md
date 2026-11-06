## ADDED Requirements

### Requirement: A new prospect's electricity is priced from the dated tariff

A new prospect's electricity SHALL be priced month by month from the dated EVN tariff in force on the 1st of each
budget month, in the administrative category below 6 kV (the common-area rate) unless the input names another
category, plus each month's VAT. The price inside a reference budget SHALL no longer be read for electricity.

#### Scenario: A 2027 budget

- **WHEN** a new prospect's electricity is priced for January 2027 and the tariff in force is 2,226 VND/kWh
- **THEN** the price SHALL be 2,226 × 1.10 VND/kWh

#### Scenario: A tariff change mid-year

- **WHEN** a new EVN rate takes effect on 10 May of the budget year
- **THEN** May SHALL keep the old rate and June onwards SHALL use the new one

## MODIFIED Requirements

### Requirement: A new prospect's utility usage is unchanged by a price change

A new prospect's electricity, water and diesel usage per m² SHALL stay as set by the usage benchmark. A price change
SHALL move the cost in proportion and SHALL NOT be absorbed by re-deriving the usage.

#### Scenario: The water price rises

- **WHEN** the water price changes from 19,786 to 29,394 VND/m³
- **THEN** the new-prospect water cost SHALL rise by the same ratio

#### Scenario: The electricity price rises

- **WHEN** the EVN rate changes from 2,226 to 2,350 VND/kWh
- **THEN** the new-prospect electricity cost SHALL rise by the same ratio
