## ADDED Requirements

### Requirement: Existing-project common-area utilities are not ramped

In "Existing project" mode, common-area electricity (`EEE.C`) and common-area water (`EEW.C`) SHALL NOT be distributed
by the fill-up curve, and electricity SHALL NOT carry the occupancy floor. The actual spend they start from already
reflects the building's current occupancy (capability `existing-project-utilities`). Every other occupancy-scaled line
SHALL keep its present behaviour. In "New prospect" mode nothing changes.

Data files read: none beyond those of `existing-project-utilities`. No recorded baseline figure moves; the standard
sample is a new prospect.

#### Scenario: An existing project's electricity is not floored or ramped

- **WHEN** an Existing-project sample with utility actuals is run
- **THEN** `EEE.C` and `EEW.C` SHALL hold the same amount in every month in which no tariff row changes
- **AND** the remarks on those two lines SHALL NOT describe the fill-up curve or the electricity floor

#### Scenario: Other ramped lines keep the curve

- **WHEN** the same Existing-project sample is run
- **THEN** the management-fee revenue lines SHALL be distributed exactly as they would be without this requirement
