## ADDED Requirements

### Requirement: Project mode and the Prior-Year Roster are read by label

The generators SHALL read the project mode, the minimum-wage region, the prior budget year, the Prior-Year Roster
block, the Holiday and Night Duty block, the Staff Lines block (approved prior-year amounts, overrides and their
reasons) and the optional actual-headcount block by their labels, like every other field, so that moving a section does not break the read. A missing required label SHALL
fail loudly and name the label. A workbook made before this change, which has none of these labels, SHALL still be
read and treated as "New prospect".

Data files read: the input workbook only.

#### Scenario: A renamed label

- **WHEN** the label of the Prior-Year Roster block is renamed
- **THEN** the run stops and names the label it could not find

#### Scenario: An old workbook

- **WHEN** a workbook without the new labels is read
- **THEN** it is read as before and treated as "New prospect"
