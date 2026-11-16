# sinking-fund Specification

## Purpose
Fills the standard form's sinking-fund sheets (`3. Budget-Sinking Fund`, `3.1 Report-Sinking Fund`) for a new
project and for a budget review, from real Savills budgets and the project's own approved figures, so `1. Summary`
shows a real sinking fund.

## Requirements

### Requirement: A new project's sinking fund is priced from the real-budget median

For a new project, every sinking-fund code that has a reference value from at least 10 projects SHALL be written on
`3. Budget-Sinking Fund`:
- **Value:** the median of the reference values, in VND excluding VAT at 2027 prices.
- **Driver for the lift codes** (ERLM1–ERLM4, ESA1): the value is per lift per month, multiplied by the project's
  total lift count, service lifts included. It comes from the Project Info input "Total Elevators (incl. service)" /
  "Tổng số thang máy (gồm thang dịch vụ)", the same count as the master list's (user, 12/11). The site page pre-fills
  it from the master list's total, with no division by towers.
- **Driver for every other code:** the value is per m² of fee-paying NFA per month, multiplied by the project's NFA.
- **Amount:** written as a monthly amount for 12 months, so that sheet 3's own Total Price and allocation formulas give
  the year.
- **Remark** (Vietnamese): the basis, the number of reference projects and the middle range (p25–p75) per unit.

The reference pool SHALL be every project in the sinking-fund reference, with no similarity filter. A code with fewer
than 10 reference projects for its driver SHALL be treated as a line left for the PM.

#### Scenario: A priced per-m² code

- **WHEN** a new project with fee-paying NFA 50,000 m² is generated
- **AND** ERE2 has reference values from 30 projects with median V VND/m²/month
- **THEN** ERE2 on sheet 3 SHALL total V × 50,000 × 12 VND for the year
- **AND** the remark SHALL name the basis, "30 dự án" and the p25–p75 range

#### Scenario: Lift codes without a lift count

- **WHEN** the input form's "Total Elevators (incl. service)" is blank or 0
- **THEN** ERLM1, ERLM2 and ESA1 SHALL be left for the PM with the reason "chưa có số thang máy"

### Requirement: Sinking-fund lines without a price are left for the PM

A sinking-fund line SHALL be left blank, shaded and remarked "PM điền: <lý do>", exactly as sheet 2 lines left for the
PM, when either of these holds:
- the code has fewer than 10 reference projects for its driver;
- the driver the code needs is missing.

Each such line SHALL get a "Nhập số" row on `4. Điều chỉnh` with the `SF|` prefix. It SHALL also be listed with the
other PM lines in the analysis and the run log.

#### Scenario: A rare code

- **WHEN** ERF3.2 (tennis court spare parts) has 4 reference projects
- **THEN** ERF3.2 SHALL be blank on sheet 3, remarked "PM điền: dưới 10 dự án tham chiếu"
- **AND** `4. Điều chỉnh` SHALL carry a "Nhập số" row for `SF|ERF3.2`

### Requirement: A new project's warranty months cost only the lines a warranty does not cover

The input form SHALL have "Số tháng bảo hành còn lại tính từ tháng đầu ngân sách", default 24. For each budget month
inside the warranty, the only sinking-fund lines that cost money SHALL be:
- every maintenance-contract code (item "maintenance contract" / "Hợp đồng bảo trì");
- the safety inspections ESA1–ESA21;
- periodic cleaning and suction ERCS1–ERCS5;
- outsourced sewage-plant operation ERS1;
- bank fees EMB1;
- irrigation and plumbing and sanitary, ERPS4 and ERPS5.

Every other code (spare parts, repair, renovation, construction, "Others") SHALL be 0 for those months. Its remark
SHALL be "trong thời gian bảo hành (<n> tháng)". When the whole budget year is inside the warranty, those lines SHALL
be 0 for the year with that remark. They are not PM lines.

#### Scenario: Year fully inside the warranty

- **WHEN** a new project's budget year starts at handover and the warranty is 24 months
- **THEN** ERE2 (electric spare parts) SHALL be 0 with remark "trong thời gian bảo hành (24 tháng)"
- **AND** ERE1 (electric maintenance contract) SHALL carry its median amount

#### Scenario: Warranty ends mid-year

- **WHEN** the warranty months end after month 6 of the budget year
- **THEN** ERE2 SHALL cost only months 7–12 of its yearly median
- **AND** the remark SHALL say the first 6 months are inside the warranty

#### Scenario: PM sets no warranty

- **WHEN** "Số tháng bảo hành" is 0
- **THEN** every priced code SHALL carry its full median amount

### Requirement: A review carries the prior approved sinking fund forward per code

For a budget review, the new year of each sinking-fund code SHALL be built from a base figure for that code, in this
order:
1. the approved budget's own sinking-fund budget (the approved year), read from each line's Total Price;
2. when that sheet is empty, the approved figure on its 3.1 report sheet, with the year it belongs to named in the
   remark.

The base SHALL be taken out of VAT with that file's own factor and brought to the budget year with CPI. It SHALL then
be written in the deliverable's VAT basis, as sheet 2 is. A code with no base SHALL fall back to the new-project
median rule. A code with neither SHALL be left for the PM.

The prior approved figures SHALL be written into `3.1 Report-Sinking Fund`, so that sheet 3's own lookups show them
beside the new year.

#### Scenario: Code with a prior figure

- **WHEN** the approved budget has ERLM1 approved at A VND for the year
- **AND** the CPI step to the budget year is c
- **THEN** ERLM1 on sheet 3 SHALL total A × c (excluding VAT) for the year
- **AND** the remark SHALL say "theo số duyệt năm trước × CPI"

#### Scenario: Approved code the tool cannot price

- **WHEN** the approved budget has ERF7.3 approved above 0
- **AND** ERF7.3 has no prior figure and fewer than 10 reference projects
- **THEN** `4. Điều chỉnh` SHALL carry a "Nhập số" row for `SF|ERF7.3`

#### Scenario: Base older than the year before (user, 2026-11-12)

- **WHEN** the approved file's sheet 3 is empty and its 3.1 approved column belongs to a year earlier than N−1
- **THEN** that figure SHALL still be the base, brought to the budget year with CPI from its own year
- **AND** the year SHALL be named in the remark and in the Review's source column

#### Scenario: Code with no base and fewer than 10 projects in a review (user, 2026-11-12)

- **WHEN** a review finds no base for a code and fewer than 10 reference projects
- **THEN** the line SHALL be left for the PM with its "Nhập số" row, as for a new project; no warranty applies in a review

#### Scenario: Existing form without a review (user, 2026-11-12)

- **WHEN** an Existing-project form carries no 'Sinking Fund Prior' sheet
- **THEN** each code SHALL be priced like a review with no base: the median for all twelve months, no warranty months

### Requirement: Each code is priced in one fund only

The tool SHALL NOT price the same code on both `2. Budget-Management Fund` and `3. Budget-Sinking Fund`. Until the
Head of PM decides where each repair and maintenance code belongs (question B8), any code that sheet 2 carries with
an amount, or leaves for the PM, SHALL stay on sheet 2. Today that is ERM and ERCS1. On sheet 3 such a code SHALL be
0, remarked:
- "đang tính ở quỹ quản lý" when sheet 2 prices it;
- "để PM điền ở quỹ quản lý" when sheet 2 leaves it for the PM.

#### Scenario: ERM

- **WHEN** a budget is generated
- **THEN** ERM SHALL carry an amount on sheet 2 only, and be 0 on sheet 3

### Requirement: The sinking-fund sheets are visible when they hold figures

`3. Budget-Sinking Fund` and `3.1 Report-Sinking Fund` SHALL be made visible when sheet 3 holds any non-zero line or
3.1 holds any prior figure. Otherwise they SHALL stay hidden as in the template. `1. Summary` rows 66–70 SHALL read
the sheet 3 total through the template's own formulas.

#### Scenario: New project

- **WHEN** a new project is generated with at least one priced sinking-fund code
- **THEN** sheets 3 and 3.1 SHALL be visible
- **AND** `1. Summary` row 69 SHALL equal sheet 3's expense total
