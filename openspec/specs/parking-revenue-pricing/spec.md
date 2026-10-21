# parking-revenue-pricing Specification

## Purpose
Decides the monthly parking price per vehicle behind the deliverable's `RP1` (motorbike) and `RP2` (car) lines
from what Savills-managed projects actually charge, instead of two constants copied from one reference project,
and lets the PM enter the project's own price.

## Requirements

### Requirement: The monthly parking price comes from the portfolio's list prices

For each vehicle type (car, motorbike) the tool SHALL read the monthly parking price of every project in the
master list's residential table whose free-text parking-fee cell states one, and SHALL form a range from them:
- the price read is the first monthly price quoted for the first vehicle of that type, in VND per vehicle per
  month, as quoted (the master list quotes prices including VAT; no CPI step is applied);
- a cell that is blank, 0, says there is no paid parking, or holds no readable price SHALL NOT be part of the
  range; it SHALL be listed on the internal analysis with its reason;
- the project being budgeted SHALL be left out when its name matches a master-list row;
- values below P25 − 1.5 × (P75 − P25) or above P75 + 1.5 × (P75 − P25) SHALL be left out, decided once;
- the range SHALL be used only when at least 10 projects remain.

The applied price SHALL be the median of the remaining values. P25, the median, P75 and the number of projects
SHALL be available to the remarks and to the internal analysis.

Data files read: `Budget_Agent/data/master_list_verified/Dim_Property_Residential.csv` (the two parking-fee text
columns, never read before). No data file is written. Recorded baseline figures move on the standard sample
(parking revenue and the totals it feeds); verify runs with the baseline gates open until group 10 re-records them.

#### Scenario: A project with car and motorbike bays

- **WHEN** a new project enters 300 car bays and 1,000 motorbike bays and no parking price
- **THEN** `RP2` at 100% fill SHALL be the car median × 300 and `RP1` the motorbike median × 1,000, in VND per
  month, before the fill-up curve
- **AND** both workbooks and helper sheet B5 SHALL quote the same two prices

#### Scenario: A price text that lists tiers

- **WHEN** a master-list cell reads "Xe thứ 1: 1,200,000 VNĐ / Xe thứ 2 trở đi: 1,500,000 VNĐ"
- **THEN** the price read for that project SHALL be 1,200,000

#### Scenario: A cell that says there is no paid parking

- **WHEN** a master-list cell reads "CĐT đã bán ô đậu xe nên không có phí" or "Không có" or "N/A" or 0
- **THEN** that project SHALL NOT be in the range, and the internal analysis SHALL list it with the reason

#### Scenario: Fewer than 10 prices

- **WHEN** fewer than 10 projects remain for a vehicle type
- **THEN** the tool SHALL price that vehicle type exactly as before this change (110,000 VND for a motorbike,
  1,100,000 VND for a car) and the remark SHALL say the portfolio range could not be formed

### Requirement: An entered parking price wins over the range

`Project Info` SHALL offer two optional fields, "Car Parking Price (VND/vehicle/month)" and "Motorbike Parking
Price (VND/vehicle/month)". Where a price is entered for a vehicle type, both workbooks and helper sheet B5 SHALL
use it as the applied price for that type, unchanged. Blank or 0 means "not entered". The recorded monthly
parking revenue of a project at stable operation SHALL still rank ahead of both the entered price and the range.
A negative number or text SHALL stop the run and name the field.

#### Scenario: A car price is entered

- **WHEN** the PM enters 1,500,000 in the car field and leaves the motorbike field blank
- **THEN** `RP2` SHALL be priced at 1,500,000 VND per bay per month and `RP1` at the motorbike median
- **AND** the `RP2` remark SHALL say the price is the one the PM entered and SHALL name no portfolio statistic

#### Scenario: Recorded revenue and an entered price

- **WHEN** a project at stable operation has a recorded car parking revenue and an entered car price
- **THEN** `RP2` SHALL be the recorded revenue × 12, exactly as before this change

#### Scenario: An invalid price

- **WHEN** the motorbike price field holds text or a negative number
- **THEN** the run SHALL stop before writing any workbook and SHALL name the field

### Requirement: The internal analysis shows the parking price range

The internal analysis SHALL show, for each vehicle type: the number of master-list rows read, the number with a
price, the median, P25 and P75, the applied price and its source (entered, range or former constant), and one
row per master-list project with the text read, the price parsed or the reason it was not used, and whether it
was left out as an outlier or as the project itself. The internal analysis may name the projects; the client
deliverable SHALL NOT.

#### Scenario: The analysis lists every row

- **WHEN** the analysis workbook is generated
- **THEN** its parking block SHALL have one row per residential master-list project, and the count of rows with
  a price SHALL equal the number the remark quotes plus the rows left out as outliers or as the project itself
