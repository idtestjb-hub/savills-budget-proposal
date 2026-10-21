## ADDED Requirements

### Requirement: Verification confirms the real-budget ranges

`verify.py` SHALL check, on the standard sample and on an Existing-project sample:
- every code priced from the range has the same figure on the `Real-Budget Ranges` sheet and on
  `2. Budget-Management Fund`;
- each range used holds at least 10 projects;
- the project's own entry is left out, on a fixture whose project is in the data file;
- the data file carries none of a list of names supplied as a fixture.

A broken deliverable, with one priced line typed 1,000 VND off, SHALL fail the tie check. The fixtures SHALL contain
no real project name or figure.

Data files read: the generated workbooks, `Ref_RealBudgetValues.csv`, and the verification fixtures. Recorded
baseline figures move once, with the user's approval (design D7).

#### Scenario: A priced line typed off

- **WHEN** the deliverable's `ESS12` differs from the sheet by 1,000 VND
- **THEN** the check SHALL fail and name `ESS12` and both figures

#### Scenario: The project itself is in the data file

- **WHEN** the fixture project matches an entry in the data file
- **THEN** the check SHALL confirm that entry is not among the values used
