## ADDED Requirements

### Requirement: Sinking-fund codes are adjusted with the SF prefix

`4. Điều chỉnh` SHALL accept sinking-fund rows keyed `SF|<code>`, beside the existing fund prefixes. The rows SHALL be:
- a "Nhập số" row for every sinking-fund line left for the PM;
- a "Nhập số" row for every code a review finds approved above 0 where the tool gives 0.

A PM entry on such a row SHALL replace the sheet 3 amount for that code on the next run. The web adjust table SHALL
list them under a "Quỹ bảo trì" group.

#### Scenario: PM types a figure

- **WHEN** the PM enters 120,000,000 VND for the year on `SF|ERF3.2`
- **THEN** the next run SHALL write ERF3.2 on sheet 3 as 10,000,000 VND per month
- **AND** the remark SHALL say "PM nhập"
