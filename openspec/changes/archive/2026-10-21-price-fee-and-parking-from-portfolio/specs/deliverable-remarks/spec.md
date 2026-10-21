## ADDED Requirements

### Requirement: A revenue unit rate taken from the portfolio states its range without naming a project

Where `RM.AP`, `RP1` or `RP2` is priced from a portfolio range, the line's remark on `2. Budget-Management Fund`
SHALL say, in Vietnamese, that the unit rate is the median of the real figures of N Savills-managed projects,
SHALL quote the median and the P25–P75 band in the rate's own unit (VND per m² per month for `RM.AP`, VND per
vehicle per month for `RP1`/`RP2`), SHALL state the VAT basis of the quoted figures and, for `RM.AP`, the price
year, and SHALL name no project (decision D3). The `1. Summary` narratives and helper sheet B5 SHALL quote the
same applied unit rates. The former wording "theo đề xuất giữ xe của một dự án tham chiếu" SHALL appear only when
the range could not be formed and the former constant is used.

Where the unit rate is one the PM entered, the remark SHALL say so and SHALL name no portfolio statistic, in the
wording already used for an entered management-fee rate.

Data files read: none beyond the pricing itself. No data file is written. No baseline figure moves on account of
the wording.

#### Scenario: `RM.AP` priced from the range

- **WHEN** the Apartment rate is the range median
- **THEN** the `RM.AP` remark SHALL contain the number of projects, the median and the P25–P75 band in
  đ/m²/tháng, the words "chưa VAT" for the quoted figures and the applied rate after VAT, and the price year 2027
- **AND** verification's client-wording scan SHALL find no project name in it

#### Scenario: `RP2` priced from the range

- **WHEN** the car price is the master-list median
- **THEN** the `RP2` remark SHALL read, in Vietnamese, that the price is the median monthly car parking price of
  N Savills-managed projects, with the band, "đã gồm VAT", × the number of bays
- **AND** the `RPa` narrative on `1. Summary` SHALL quote the same price

#### Scenario: `RP1` priced from an entered price

- **WHEN** the PM enters a motorbike price
- **THEN** the `RP1` remark SHALL say the price is the one the PM entered and SHALL contain no "trung vị"

#### Scenario: Verification covers the new remarks

- **WHEN** verification runs on the standard sample
- **THEN** its remark assertions SHALL include the `RM.AP`, `RP1` and `RP2` range wording
