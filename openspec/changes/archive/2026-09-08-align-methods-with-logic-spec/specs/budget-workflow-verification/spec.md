## MODIFIED Requirements

### Requirement: Verification reports its own strength honestly

Verification SHALL report which checking method was actually used. When full Excel recalculation is unavailable and a weaker file-level inspection is used instead, verification MUST state this explicitly rather than presenting a reduced check as a full one.

A check that independently reconciles a figure SHALL fail when it cannot read the input it is
anchored to. It MUST NOT fall back to the artifact under test, and MUST NOT report success against
a substituted or absent value — a check that silently stops proving anything is worse than one that
fails, because it still reads as evidence.

#### Scenario: Full recalculation is available
- **WHEN** Excel recalculation can be performed
- **THEN** the result states that a full recalculation check was performed

#### Scenario: Full recalculation is unavailable
- **WHEN** Excel recalculation cannot be performed
- **THEN** the result states that only a reduced check was performed
- **AND** states that formula errors visible only on recalculation were not detectable in this run

#### Scenario: A hand-check cannot reach its input
- **WHEN** a hand-check's expected value depends on an input it cannot read from the sample fixture
- **THEN** the check reports failure
- **AND** does NOT compute its expectation from the workbook it is checking

#### Scenario: A hand-check's inputs survive a form layout change
- **WHEN** the intake form's row layout changes
- **THEN** the hand-checks read the same input values as before the change
