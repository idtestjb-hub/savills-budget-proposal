## ADDED Requirements

### Requirement: The sinking fund is read as a third fund

Budget Review SHALL read the approved budget's sinking-fund sheets as well as the management and common-area funds.
It SHALL read, by code:
- the new-year figure from the budget sheet;
- the prior approved, actual and expected figures from the budget sheet and its report sheet, under the same period
  rules as the other funds.

A sinking-fund sheet has no total rows to tie to. The reader SHALL therefore:
- sum the leaf lines;
- mark the fund "không có dòng tổng để đối soát";
- not treat it as tied.

A file without a sinking-fund sheet, or with an empty one, SHALL review the other funds as today. Its Review SHALL
say "file không có quỹ bảo trì".

#### Scenario: Approved file with an empty sheet 3 but prior figures on 3.1

- **WHEN** the approved file's sheet 3 has no figures for its own year
- **AND** its 3.1 has prior approved figures
- **THEN** the Review SHALL use the 3.1 prior approved figures as the carry-forward base
- **AND** the Review SHALL state which year they belong to

#### Scenario: The other funds do not move

- **WHEN** a Review that ran before this change runs again
- **THEN** its management-fund and common-area-fund figures SHALL be unchanged
