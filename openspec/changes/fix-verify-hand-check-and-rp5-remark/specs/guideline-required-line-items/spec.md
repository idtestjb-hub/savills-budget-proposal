## ADDED Requirements

### Requirement: A Required line whose remark the form ships as a placeholder states its own reason

The standard form ships the placeholder remark "demo" on the RP5 line of `2.2 Common area Fund`
(daily motorbike and bicycle visitor parking, revenue). RP5 is a Required code, the pipeline has no
visitor-volume input to price it, and it stays at 0 VND. The pipeline SHALL replace that placeholder
with its own Vietnamese reason, in the form used for other lines left at zero ("Để ở mức 0: …"), saying
that daily visitor parking revenue needs an assumption about visitor numbers and that no input
supplies one. The reason SHALL carry the VAT-treatment sentence on a run that is inclusive of VAT, as
every other remark on that sheet does. The pipeline SHALL write it only when the cell is empty or
holds exactly the text "demo"; any other text already in the cell SHALL be left alone.

#### Scenario: The placeholder is replaced by a reason

- **WHEN** the deliverable is generated and the RP5 remark cell on `2.2 Common area Fund` holds the
  form's text "demo"
- **THEN** the cell SHALL hold a Vietnamese reason for the zero, and no longer the word "demo"
- **AND** the figure on the RP5 line SHALL be unchanged (0 VND)

#### Scenario: Text a person has already written is kept

- **WHEN** the RP5 remark cell holds any text other than "demo"
- **THEN** the pipeline SHALL leave it as it is

## MODIFIED Requirements

### Requirement: Verification confirms every Required code is filled

Verification SHALL open the generated deliverable, and fail when a code the recorded reference
classifies as Required carries a zero figure with no stated reason, on either fund sheet:
`2. Budget-Management Fund` or `2.2 Common area Fund`, across each sheet's whole used range. This
check SHALL run on every verification run. A placeholder remark that ships with the standard form
and explains nothing (the exact text "demo" on the RP5 line of `2.2 Common area Fund`) SHALL NOT
count as a stated reason. It is matched by sheet, code and exact text, never by the word alone.

#### Scenario: An unexplained zero on a Required code fails the run

- **WHEN** verification runs and a Required code is zero with no stated reason for this project
- **THEN** verification SHALL fail and name the code

#### Scenario: An unexplained zero on the common-area fund sheet fails the run

- **WHEN** verification runs and a Required code on `2.2 Common area Fund` is zero with no stated
  reason on its own line (or, for EMA1–EMA4, on that sheet's EMA15 line)
- **THEN** verification SHALL fail and name the sheet and the code

#### Scenario: A form placeholder is not a reason

- **WHEN** verification runs and the RP5 line of `2.2 Common area Fund` is zero and its remark is
  exactly the form's placeholder text "demo"
- **THEN** verification SHALL fail and name the sheet and the code
