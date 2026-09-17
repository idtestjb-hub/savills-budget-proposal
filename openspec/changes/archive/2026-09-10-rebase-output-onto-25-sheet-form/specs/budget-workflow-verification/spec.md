## ADDED Requirements

### Requirement: Verification confirms the deliverable is built on the standard template

Verification SHALL check that the generated client deliverable was built from the current standard
budget template and carries its full sheet set. The recorded sheet-count expectation SHALL match the
standard template plus the sheets the pipeline adds itself.

This adds to the existing structural-soundness requirement; it does not change the "no formula
errors after recalculation" or "no corruption artifacts" checks, which continue to run against
whatever template is current.

#### Scenario: The deliverable carries the standard sheet set

- **WHEN** verification inspects a generated deliverable
- **THEN** every sheet name the standard template defines SHALL be present
- **AND** verification SHALL fail and name the missing sheets if any standard sheet is absent

#### Scenario: The sheet-count baseline moved with a stated reason

- **WHEN** the standard template changes and the deliverable's sheet count changes with it
- **THEN** the recorded sheet-count baseline SHALL be updated together with a stated reason
- **AND** subsequent runs compare against the updated count

#### Scenario: Figures are unchanged by the template switch

- **WHEN** verification runs after the deliverable is re-based onto a new template version
- **THEN** every compared headline figure SHALL still match its recorded baseline in VND
- **AND** a figure that changed only because of the switch SHALL be reported, not silently accepted
