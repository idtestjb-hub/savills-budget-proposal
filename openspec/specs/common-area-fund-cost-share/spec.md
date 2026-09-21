## Purpose

Governs whether, and on what basis, `2.2 Common area Fund`'s own expense leaf rows carry a figure
at all — a cross-fund cost-allocation question the pipeline cannot resolve without explicit
accounting sign-off.

## Requirements

### Requirement: Common-area-fund expense rows only carry a figure once the allocation basis is signed off

`2.2 Common area Fund`'s expense leaf rows (the ones matching a `2. Budget-Management Fund` code)
SHALL NOT be treated as a correct, final figure on any deliverable until PM/finance has confirmed
the allocation basis used to compute them.

#### Scenario: The activation is implemented but unsigned-off

- **WHEN** `_activate_common_area_passthrough_rows` has been implemented and is live in
  `generate_project_budget.py`, but no sign-off has been recorded
- **THEN** the change that implements it SHALL stay unarchived, and its own docs SHALL state
  plainly that the figures are pending confirmation of the allocation basis

#### Scenario: Sign-off confirms revenue-share is correct

- **WHEN** PM/finance confirms revenue-share (the template's own `F8` ratio) is the correct basis,
  and confirms it does not double-count against `RI1`'s own recovery mechanism
- **THEN** the activation SHALL be kept as implemented, the change SHALL record a baseline, and the
  change MAY be archived

#### Scenario: Sign-off rejects revenue-share or finds a double-count

- **WHEN** PM/finance determines revenue-share is not the correct basis, or that it double-counts
  against `RI1`
- **THEN** the pipeline SHALL NOT ship the activation as implemented — either the ratio is replaced
  with the confirmed correct basis, or `_activate_common_area_passthrough_rows` is reverted and
  `2.2 Common area Fund`'s expense rows return to blank, before this change is archived

### Requirement: This change's measured effect stays isolated from other changes' figures

Because this activation is separately gated, its measured year-one effect SHALL be reported and
recorded independently of any other change's measured effect — never summed into another change's
headline figure, even when both are measured on the same run of the same project.

#### Scenario: Another change also moves figures in the same generation run

- **WHEN** `fill-guideline-required-line-items` (or any other change) prices new codes on `2. Fund`
  in the same pipeline run this activation is also active in
- **THEN** the two effects SHALL be measured and reported separately, so each change's own sign-off
  reviews only the figure movement it is actually responsible for
