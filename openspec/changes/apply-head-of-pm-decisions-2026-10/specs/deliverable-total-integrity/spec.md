## ADDED Requirements

### Requirement: The parking break-even cells show "N/A" without a parking area

The break-even rate cells for parking on `2. Budget-Management Fund` (`BK507`, the balancing rate, and `BK511`, the
increase or decrease needed) SHALL show "N/A" when the parking area is 0 or blank. Otherwise they SHALL show the
template's own result. Both cells SHALL be written as live formulas, so a parking area the PM types later gives a
number. The tool SHALL find the cells by their row labels, and SHALL stop the run if they are not where the labels say.

A scan of every formula in the standard template and in a generated deliverable found that only `BK511` reads `BK507`
and that nothing reads `BK511`, so the text "N/A" breaks no other formula. No recorded baseline moves. The count of
error cells inherited from the template falls.

#### Scenario: No parking area

- **WHEN** the parking area is 0
- **THEN** `BK507` and `BK511` SHALL show "N/A" and SHALL NOT show `#DIV/0!` or `#VALUE!`

#### Scenario: A parking area typed later

- **WHEN** the PM types a non-zero parking area into the deliverable after it is generated
- **THEN** `BK507` and `BK511` SHALL show numbers
