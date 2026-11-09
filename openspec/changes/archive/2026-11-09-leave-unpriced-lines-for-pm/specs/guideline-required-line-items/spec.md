## MODIFIED Requirements

### Requirement: Every Required code carries a non-zero figure on the deliverable

For every code the recorded reference classifies as Required, the generated deliverable SHALL
carry a non-zero figure for that code, UNLESS the project genuinely has no basis for that cost
(for example, a pool-related Required code on a project with no pool), OR the tool has no pricing
method or lacks this project's input for it, in which case the line SHALL be left for the PM to fill
(capability `pm-filled-lines`) rather than stated as 0.

#### Scenario: A Required code with an available pricing method is filled

- **WHEN** the deliverable is generated and a Required code has a pricing method recorded in the
  costing catalogue
- **THEN** that code's own leaf row SHALL carry the resulting figure — not folded into an
  unrelated catch-all row instead of its own line

#### Scenario: A Required code genuinely does not apply to this project

- **WHEN** a Required code's basis does not exist for this specific project (e.g. no pool, no
  garden)
- **THEN** that code MAY be zero, and the reason SHALL be stated rather than silently left blank

#### Scenario: A Required code the tool cannot price

- **WHEN** a Required code has no pricing method, or its method needs an input this project lacks
- **THEN** its figure cells SHALL be left blank and shaded for the PM, with the remark "PM điền: <reason>"

### Requirement: A zero line on the common-area fund sheet states its own reason

`2.2 Common area Fund` takes a share of each matching `2. Budget-Management Fund` line, so a line
left at 0 VND there is also 0 VND on `2.2`. For every Required code on `2.2 Common area Fund` whose
`2. Budget-Management Fund` counterpart was left at 0 VND with a stated reason in the same run, the
pipeline SHALL write that same reason, in Vietnamese, into the `2.2` line's own Remarks cell
(column T), stating that the line is an allocation from `2. Budget-Management Fund`, and SHALL lead
it with "PM điền" when the `2. Budget-Management Fund` line is left for the PM and with "Để ở mức 0"
when it is a zero line. Where a code's reason sits on a designated catch-all line on
`2. Budget-Management Fund` (EMA1–EMA4 on EMA15), `2.2`'s matching catch-all line SHALL carry the
matching remark. The pipeline SHALL NOT overwrite text the template already ships in that cell (a
cell holding only whitespace counts as empty).

#### Scenario: A line left at zero on both sheets

- **WHEN** a Required code is left at 0 VND on `2. Budget-Management Fund` with a stated reason of kind C
- **THEN** the same code's line on `2.2 Common area Fund` SHALL carry that reason in Vietnamese,
  led by "Để ở mức 0" and marked as an allocation from `2. Budget-Management Fund`

#### Scenario: A line left for the PM on both sheets

- **WHEN** a Required code is left for the PM on `2. Budget-Management Fund`
- **THEN** the same code's line on `2.2 Common area Fund` SHALL carry its reason led by "PM điền",
  marked as an allocation from `2. Budget-Management Fund`, and no "Để ở mức 0" wording

#### Scenario: A contingency line of the common-area fund itself

- **WHEN** a section-contingency line on `2.2 Common area Fund` (EM#, ES#, EE#) is the sheet's own
  line rather than an allocation, is 0 VND, and the same code is left at 0 VND on
  `2. Budget-Management Fund` with a stated reason
- **THEN** the `2.2` line SHALL carry that reason in Vietnamese, without the allocation wording

#### Scenario: A line that is priced on the operating fund sheet

- **WHEN** a Required code that is normally left at zero is priced in this run (for example EMH1,
  once the PM enters Savills' management-fee terms)
- **THEN** neither `2. Budget-Management Fund` nor `2.2 Common area Fund` SHALL carry a zero reason
  or a "PM điền" remark for that code
