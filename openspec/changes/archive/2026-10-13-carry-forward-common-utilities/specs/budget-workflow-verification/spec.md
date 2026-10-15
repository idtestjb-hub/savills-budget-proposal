## ADDED Requirements

### Requirement: Verification exercises Existing-project utilities

`verify.py` SHALL run invented Existing-project samples that carry utility actuals and check the following:
- `EEE.C` and `EEW.C` on the client deliverable equal the Utility Bridge's budget-year figures;
- the twelve months of each line sum to its annual figure;
- the New-prospect standard sample has no Utility Bridge, and its figures equal the recorded baselines.

Unit tests SHALL cover the cases that stop a run: a missing reason, a duplicated month, a month in the budget year,
a missing tariff row, and too few months without an approved amount. The samples SHALL use invented figures only.

Data files read: the invented samples under `verification/fixtures/`, the tariff table. No recorded baseline figure
moves.

#### Scenario: The bridge does not tie

- **WHEN** the Utility Bridge's budget-year figure for `EEW.C` differs from `EEW.C`'s annual total on the deliverable by
  more than 1 VND
- **THEN** verification SHALL fail and name the line and both figures

#### Scenario: A New-prospect run shows a Utility Bridge

- **WHEN** the standard sample's analysis workbook contains a Utility Bridge sheet
- **THEN** verification SHALL fail
