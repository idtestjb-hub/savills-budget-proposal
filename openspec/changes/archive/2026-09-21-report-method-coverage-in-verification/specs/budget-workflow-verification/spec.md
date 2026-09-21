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

Verification SHALL also report how much of the work was checked at all, not only whether the figures
it does check still reproduce. It SHALL report the share of a real reference budget's cost the
pipeline fills, and the share of what it writes that is computed by a method the costing
specification states. A run that reports only reproducibility SHALL NOT present itself as a
statement about coverage, method or accuracy.

#### Scenario: Coverage is reported against real reference budgets
- **WHEN** verification runs
- **THEN** it reports which cost codes a real reference budget uses that the pipeline does not fill
- **AND** reports the share of that budget's value the unfilled codes represent

#### Scenario: Method fidelity is reported against the costing specification
- **WHEN** verification runs
- **THEN** for each cost code the pipeline fills it reports whether the method used is one the
  costing specification states for that code
- **AND** reports the share of written cost that matches, partially matches, and does not match

#### Scenario: A cost code with no recorded verdict fails the run
- **WHEN** the pipeline writes a cost code that has no recorded method verdict, or stops writing one
  that has
- **THEN** verification fails and names that code
- **AND** does NOT infer a verdict, so that adding or changing a derivation cannot silently age the
  report

#### Scenario: The result summary does not overstate what was checked
- **WHEN** verification completes successfully
- **THEN** its summary states coverage and method fidelity alongside the baseline comparison
- **AND** does NOT describe the run in terms that imply the figures were checked for correctness
