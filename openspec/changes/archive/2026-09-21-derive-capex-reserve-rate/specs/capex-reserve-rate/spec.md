## Purpose

Defines how the pipeline determines the ongoing Capex reserve contribution for the years following
initial equipment purchase, and how the evidence behind that figure is presented, so that a
multi-year budget rests on what real projects did rather than on a rule of thumb.

**Data scope**: this capability adds one Generation A reference table extracted from the real
project budgets and reads it at run time. No existing Generation A or Generation B table is
modified, and no Fact/Dim join key changes, so the Copilot Studio package's live data is unaffected.

## ADDED Requirements

### Requirement: The reserve rate is derived from real projects, not hardcoded

The pipeline SHALL compute the Capex reserve rate from observed later-year Capex in real project
budgets. It MUST NOT depend on a constant written into the code.

#### Scenario: The rate reflects the reference data

- **WHEN** a budget is generated
- **THEN** the reserve rate applied SHALL be derived from the recorded real-project observations

#### Scenario: Adding a project changes the rate

- **WHEN** a further real project is added to the reference data
- **THEN** the derived rate SHALL take that project into account without any code change

#### Scenario: The reference data cannot be read

- **WHEN** the reference data is missing or unreadable
- **THEN** the pipeline SHALL fail and say so
- **AND** it MUST NOT silently substitute a default rate

### Requirement: The evidence behind the rate is shown

A reader of the generated budget SHALL be able to see what the rate was derived from, without access
to the source code or the underlying workbooks.

#### Scenario: The output states the basis

- **WHEN** a budget applies the reserve rate
- **THEN** the output SHALL state the number of real projects behind it and the range observed

#### Scenario: A thin sample is disclosed, not hidden

- **WHEN** the rate is derived from a small number of projects
- **THEN** the output SHALL make that sample size visible rather than presenting the rate as settled

### Requirement: The year the reserve begins is an input, not an assumption

The year in which Capex drops from full purchase to the ongoing reserve SHALL be an input to the
budget, because real projects differ on it.

#### Scenario: A project that repeats full Capex in year two

- **WHEN** a project's equipment purchase spans two years before settling
- **THEN** the budget SHALL apply full Capex in both years and the reserve from the year given
- **AND** it MUST NOT force the reserve to begin in year two

#### Scenario: The default matches the observed majority

- **WHEN** no drop year is specified for a project
- **THEN** the pipeline SHALL use the year most of the reference projects use
- **AND** SHALL state in the output that a default was applied

### Requirement: The reserve applies to the equipment already purchased

The reserve SHALL be expressed against the project's own initial Capex, and SHALL NOT be scaled by
occupancy.

#### Scenario: Capex does not follow the fill-up curve

- **WHEN** a budget models a project filling up over time
- **THEN** the Capex reserve SHALL NOT be reduced in proportion to occupancy
- **AND** the output SHALL state that equipment is bought regardless of how full the building is

### Requirement: The change in multi-year figures is measurable and deliberate

The effect on the budget SHALL be visible and recorded, not absorbed silently.

#### Scenario: Verification detects the change

- **WHEN** verification is run after this capability is implemented with the previously recorded
  baseline in place
- **THEN** any figure that moved SHALL be named with its recorded and current values

#### Scenario: Year-one figures are unaffected

- **WHEN** the reserve rate changes
- **THEN** figures that describe year one only SHALL be unchanged, since the reserve applies to
  later years
