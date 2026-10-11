## ADDED Requirements

### Requirement: Verification exercises every path the PM decisions add

Verification SHALL run invented samples that reach each new path:
- a project with coordinates, so the distance ranking runs;
- a filled Savills fee, once fixed and once as a %;
- two Accountants and two Property Managers, so the `A1` overflow rows are written;
- a qualifying 24/7 position and a night position, so `A1.1` is filled;
- a non-default budget start month, a water customer group and an entered ESI2 premium.

It SHALL tie each staffing line to its detail sheet on the standard sample as well as on the Existing samples. It SHALL
confirm the helper-sheet ties and the contingency formulas. It SHALL run the deliverable name scan on every sample.

#### Scenario: A double-counted allowance

- **WHEN** a change makes `EMH2` include the `A1.1` allowance while `EMH3` also carries it
- **THEN** verification SHALL fail on the standard sample

#### Scenario: Distance path reached

- **WHEN** verification runs
- **THEN** at least one sample SHALL reach the distance ranking, and its result SHALL be checked

### Requirement: The baselines are re-recorded once for this change, with each movement measured

Each decision SHALL be measured on its own, before and after, on the standard sample and on a regression clone kept
outside the repository, and the movement in VND SHALL be recorded in the change. The recorded baselines (analysis,
deliverable, operating) SHALL be re-recorded once, after every decision is built, with the reason written beside the
new figures.

#### Scenario: Re-record

- **WHEN** every decision in this change is built and measured
- **THEN** the baselines SHALL be re-recorded in one step, with the reason stated
- **AND** verification SHALL pass against the new baselines
