## ADDED Requirements

### Requirement: A line priced from real Savills budgets says how

The remark on a line priced from the real-budget range SHALL say, in Vietnamese:
- the median in đ/m²/tháng, excluding VAT, at 2027 prices;
- the P25–P75 range;
- the number of Savills projects it comes from;
- the fee-paying NFA and the 12 months it is multiplied by;
- the VAT added.

It SHALL name no project. For `ESC1` and `ESC2` it SHALL also say that the figure stands in for the number of
events × the price per event, until the PM enters them. The remark SHALL pass the internal-wording scan, and its
units SHALL be Vietnamese.

Data files read: none beyond those of `real-budget-ranges`. Recorded baseline figures: see that capability.

#### Scenario: Pest control

- **WHEN** `ESS12` is priced from a range of 30 projects with median 120 đ/m²/tháng on 36,679 m²
- **THEN** its remark SHALL state the median 120 đ/m²/tháng, the P25–P75 range, "30 dự án do Savills quản lý", the
  36,679 m² and the 12 months, and the VAT 10% added for 2027

#### Scenario: Events

- **WHEN** `ESC1` is priced from the range
- **THEN** its remark SHALL also say that the figure stands in until the number of events and the price per event
  are entered
