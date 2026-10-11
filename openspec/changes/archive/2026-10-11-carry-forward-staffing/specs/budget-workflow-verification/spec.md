## ADDED Requirements

### Requirement: Verification fails on a changed staffing line without a reason

Verification SHALL fail, naming the line, when in Existing-project mode a staffing line differs from the baseline and
carries no reason, or carries the code "Khác" without a note. It SHALL pass when every changed line has a reason.

#### Scenario: A change without a reason

- **WHEN** a generated budget has a changed staffing line with no reason
- **THEN** the verification run fails and names that line

#### Scenario: Nothing changed

- **WHEN** a generated budget has no changed staffing line
- **THEN** the check passes with nothing to report

### Requirement: Verification confirms the Staff bridge ties

Verification SHALL confirm, in Existing-project mode, that the Staff bridge total equals EMH2 plus EMH3 plus EMH4 of
the client deliverable as Excel recalculates it, and that the bridge is absent from the client deliverable. In
New-prospect mode it SHALL confirm that the bridge is not produced. Verification SHALL run the pipeline on an invented
Existing-project sample, in its own section, besides the standard New-prospect sample, whose recorded figures do not
move.

#### Scenario: The bridge disagrees with the deliverable

- **WHEN** the bridge total differs from EMH2 plus EMH3 plus EMH4
- **THEN** verification fails with both numbers

### Requirement: Verification confirms each staffing line equals its detail sheet

Verification SHALL confirm, in Existing-project mode, that EMH2, EMH3 and EMH4 are formulas into their detail sheets and
that each equals its detail sheet's total as Excel recalculates it, within 1 VND per year. Verification SHALL run this
and the other Existing-project checks on two invented samples: one with a roster, and one without a roster that carries
approved amounts, a PM override with a reason, and an approved EMH4 of zero.

#### Scenario: A typed amount on a staffing line

- **WHEN** EMH2 on the fund sheet is a number instead of a formula
- **THEN** verification fails and names the line
