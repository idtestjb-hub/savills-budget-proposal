## Purpose

Defines what the deliverable's helper sheets (`A2`–`A5`, `B1`–`B5`) show, so that a client sees this project's own posts,
duty calendar and helper figures instead of the form's sample values, and so that the service helper sheets agree with
the budget lines they explain.

Data files read: none besides the input workbook and the tool's own staffing and service figures. Data files written:
none besides the output workbooks. No recorded baseline moves. No fund line reads `A2`–`A4` or `B1`–`B5`, and `A5`, which
feeds `EMH4`, keeps its current figures.

## ADDED Requirements

### Requirement: The service helper sheets list this project's posts and tie to their lines

`A2` (security), `A3` (cleaning) and `A4` (landscape) SHALL list the tool's own posts for this project, with the tool's
unit prices and night blend. Each sheet's annual total SHALL equal its budget line: `ESS1`, `ESS4` and `ESS16`. Every
canonical position SHALL keep its duty description. The allocation bases SHALL stay non-zero. Verification SHALL confirm
the three ties.

#### Scenario: Security ties

- **WHEN** the deliverable is generated
- **THEN** `A2`'s annual total SHALL equal `ESS1`'s annual figure

#### Scenario: Form sample values are gone

- **WHEN** the deliverable is generated
- **THEN** no `A2`–`A4` row SHALL keep the form's sample quantity or unit price

### Requirement: `B1` shows the reception duty calendar

`B1` SHALL show this project's reception duty calendar from the tool's roster. When the project has no reception post,
the form's sample calendar SHALL be cleared and the sheet SHALL say there is no reception post.

#### Scenario: A project with reception

- **WHEN** the staffing input has a Reception position
- **THEN** `B1` SHALL show its duty codes for the roster month

### Requirement: `B2`–`B5` carry the tool's own figures or say they are not used

Where the tool has its own figure for a `B2`–`B5` item (elevator advertising quantities, parking prices), the sheet SHALL
show it. Every other sample value SHALL be cleared, and the sheet SHALL say "chưa áp dụng".

#### Scenario: Parking prices

- **WHEN** the deliverable is generated
- **THEN** the parking-price sheet SHALL show the parking prices the budget uses

### Requirement: `A5` keeps the form's fire-team calculation

`A5` SHALL keep its current team and formulas, so that `EMH4` does not move.

#### Scenario: EMH4 unchanged

- **WHEN** this change is applied to the standard sample
- **THEN** `EMH4` SHALL equal its value before the change
