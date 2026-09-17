## Purpose

Prices the `B2.6` domestic-waste-collection line the standard form's own AI Guideline column
instructs (weight per unit per day, QĐ 67's three-part unit price), and writes its guideline-driven
remark — a line this pipeline does not price at all today, so both the figure and its explanation
are new.

## ADDED Requirements

### Requirement: The deliverable prices domestic waste collection for every project with residential units

For any project with apartment (or other residential) units, the deliverable SHALL compute a
`B2.6` waste-collection cost from the project's unit count, the guideline's assumed waste weight
per unit per day, and the QĐ 67 three-part unit price (collection, transport, treatment). A
project with no residential units MAY leave the line at zero.

#### Scenario: A residential project gets a priced waste-collection line

- **WHEN** the deliverable is generated for a project with apartment units
- **THEN** `B2.6` SHALL carry a non-zero figure computed from the unit count, the assumed
  per-unit waste weight, and the QĐ 67 unit price

#### Scenario: A project with no residential units is left at zero

- **WHEN** the deliverable is generated for a project with no residential (apartment-type) units
- **THEN** `B2.6` MAY be left at zero rather than priced from a zero unit count

### Requirement: `B2.6`'s remark states the weight assumption and its legal basis

The `B2.6` remark SHALL state the assumed waste weight per unit per day and cite QĐ 67 as the basis
for the three-part unit price, in the guideline's own wording.

#### Scenario: The remark states the assumption and citation

- **WHEN** `B2.6` carries a non-zero figure
- **THEN** its remark SHALL state the per-unit-per-day weight assumption used
- **AND** SHALL cite QĐ 67 as the basis for the collection/transport/treatment unit price

### Requirement: The new figure is measured and disclosed before it ships

Because `B2.6` was previously always zero, the first run that prices it moves the year-one surplus
by a real amount. That amount SHALL be measured on at least one real project and shown to the Head
of PM before this capability is archived.

#### Scenario: The new figure is presented before archive

- **WHEN** this capability is ready to archive
- **THEN** the VND amount `B2.6` adds SHALL have been measured on a real project and shown to the
  Head of PM
