# building-insurance-premium Specification

## Purpose
Prices `ESI2`, the building insurance whose premium is quoted in US dollars, from a premium and an exchange rate the PM
can edit, instead of leaving the line at 0 for want of a rate.

Data files read: the input workbook's optional ESI2 premium (USD per year) and USD exchange rate. Data files written:
none besides the output workbooks. Recorded baselines move: total expense and surplus, by the premium in VND including
VAT.

## Requirements

### Requirement: `ESI2` is a USD premium at an editable exchange rate

`ESI2` SHALL be the annual premium in USD times the exchange rate times 1.10 (insurance VAT of 10%), spread evenly over
the budget's twelve months. When the premium is blank it SHALL default to 1,000 USD (the costing logic file's example
for a 1,000,000 USD liability limit), and the remark SHALL say the default was used. When the exchange rate is blank it
SHALL default to 26,190 VND/USD, the Vietcombank selling rate on 05/10/2026.

#### Scenario: Both inputs blank

- **WHEN** the premium and the exchange rate are blank
- **THEN** `ESI2` SHALL total 1,000 × 26,190 × 1.10 = 28,809,000 VND for the year

#### Scenario: PM enters a quote

- **WHEN** the PM enters a premium of 1,500 USD and a rate of 26,300
- **THEN** `ESI2` SHALL total 1,500 × 26,300 × 1.10 VND for the year

### Requirement: The `ESI2` remark states its basis

The remark SHALL state the liability limit when the default premium is used, the premium in USD, the exchange rate and
its date, and that VAT of 10% is included.

#### Scenario: Default remark

- **WHEN** `ESI2` uses the default premium
- **THEN** its remark SHALL name 1,000 USD, the 1,000,000 USD limit, 26,190 VND/USD on 05/10/2026, and VAT of 10%
