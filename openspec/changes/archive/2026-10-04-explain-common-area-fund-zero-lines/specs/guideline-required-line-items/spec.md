## ADDED Requirements

### Requirement: A zero line on the common-area fund sheet states its own reason

`2.2 Common area Fund` takes a share of each matching `2. Budget-Management Fund` line, so a line
left at 0 VND there is also 0 VND on `2.2`. For every Required code on `2.2 Common area Fund` whose
`2. Budget-Management Fund` counterpart was left at 0 VND with a stated reason in the same run, the
pipeline SHALL write that same reason, in Vietnamese, into the `2.2` line's own Remarks cell
(column T), stating that the line is an allocation from `2. Budget-Management Fund`. Where a code's
reason sits on a designated catch-all line on `2. Budget-Management Fund` (EMA1–EMA4 on EMA15),
`2.2`'s matching catch-all line SHALL carry the matching remark. The pipeline SHALL NOT overwrite
text the template already ships in that cell (a cell holding only whitespace counts as empty).

#### Scenario: A line left at zero on both sheets

- **WHEN** a Required code is left at 0 VND on `2. Budget-Management Fund` with a stated reason
- **THEN** the same code's line on `2.2 Common area Fund` SHALL carry that reason in Vietnamese,
  marked as an allocation from `2. Budget-Management Fund`

#### Scenario: A contingency line of the common-area fund itself

- **WHEN** a section-contingency line on `2.2 Common area Fund` (EM#, ES#, EE#) is the sheet's own
  line rather than an allocation, is 0 VND, and the same code is left at 0 VND on
  `2. Budget-Management Fund` with a stated reason
- **THEN** the `2.2` line SHALL carry that reason in Vietnamese, without the allocation wording

#### Scenario: A line that is priced on the operating fund sheet

- **WHEN** a Required code that is normally left at zero is priced in this run (for example EMH1,
  once the PM enters Savills' management-fee terms)
- **THEN** neither `2. Budget-Management Fund` nor `2.2 Common area Fund` SHALL carry a zero reason
  for that code

## MODIFIED Requirements

### Requirement: Verification confirms every Required code is filled

Verification SHALL open the generated deliverable, and fail when a code the recorded reference
classifies as Required carries a zero figure with no stated reason, on either fund sheet:
`2. Budget-Management Fund` or `2.2 Common area Fund`, across each sheet's whole used range. This
check SHALL run on every verification run.

#### Scenario: An unexplained zero on a Required code fails the run

- **WHEN** verification runs and a Required code is zero with no stated reason for this project
- **THEN** verification SHALL fail and name the code

#### Scenario: An unexplained zero on the common-area fund sheet fails the run

- **WHEN** verification runs and a Required code on `2.2 Common area Fund` is zero with no stated
  reason on its own line (or, for EMA1–EMA4, on that sheet's EMA15 line)
- **THEN** verification SHALL fail and name the sheet and the code
