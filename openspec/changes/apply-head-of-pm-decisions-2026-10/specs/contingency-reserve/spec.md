## Purpose

Prices the contingency lines the standard form provides for management, services and energy (`EM#`, `ES#`, `EE#`), on
both fund sheets and in the internal analysis, as a stated percentage of the lines they cover.

Data files read: the input workbook's optional contingency rate. Data files written: none besides the output workbooks.
Recorded baselines move: total expense, surplus, profit, margin and markup.

## ADDED Requirements

### Requirement: Each contingency line is a rate times its group's covered lines

On `2. Budget-Management Fund`, `EM#`, `ES#` and `EE#` SHALL each be written, for every month, as a live formula. The
formula is the contingency rate times that month's sum of the group's leaf lines. Each leaf SHALL count once, even where
it sits inside a sub-group total. The contingency line SHALL NOT be part of its own base. These lines are excluded:
- the management group's base SHALL exclude `EMH1`, Savills' own fee;
- the energy group's base SHALL exclude `EEW.A` and `EEE.A`, the collect-on-behalf lines, so a collect-on-behalf pair
  still has no effect on the surplus.

The rate SHALL come from the input form, default 2%. Repairs (`ER`) and capital expenditure (`EN`) carry no
contingency. A rate of 0 SHALL leave the three lines at 0 with a stated reason.

#### Scenario: Default rate

- **WHEN** the contingency rate is blank
- **THEN** `ES#` in each month SHALL equal 2% of that month's sum of the `ES` leaf lines

#### Scenario: Savills' fee is outside the base

- **WHEN** `EMH1` carries a fee
- **THEN** `EM#` SHALL NOT change with it

#### Scenario: A collect-on-behalf pair

- **WHEN** a collect-on-behalf water and electricity pair is entered
- **THEN** `EE#` SHALL NOT change, and the surplus SHALL equal the surplus without the pair

#### Scenario: Sub-group totals and the line itself

- **WHEN** `EE#` is computed for a month in which `EEW` and `EEE` each have a sub-group total
- **THEN** each energy leaf SHALL count once in the base
- **AND** no contingency cell SHALL depend on itself, and verification SHALL fail if one does

### Requirement: The common-area fund carries the same contingency

`2.2 Common area Fund` SHALL carry its own `EM#`, `ES#` and `EE#` on the same rule, over its own leaf lines, with the same
exclusions.

#### Scenario: Common-area fund contingency

- **WHEN** the deliverable is generated
- **THEN** `2.2 Common area Fund!ES#` SHALL equal the contingency rate times the sum of that sheet's `ES` leaf lines

### Requirement: The contingency reaches the summary and the analysis

`1. Summary` SHALL include the contingency lines in the section totals that hold them, and its narrative SHALL name
them. The internal analysis SHALL show the same contingency amount, so that the two workbooks' expense totals agree.

#### Scenario: Summary ties

- **WHEN** the contingency is non-zero
- **THEN** `1. Summary`'s section totals SHALL still equal their detail sheets, and verification SHALL confirm it

#### Scenario: Analysis agrees

- **WHEN** both workbooks are generated
- **THEN** the analysis's contingency SHALL equal the sum of the deliverable's three contingency lines over the year
