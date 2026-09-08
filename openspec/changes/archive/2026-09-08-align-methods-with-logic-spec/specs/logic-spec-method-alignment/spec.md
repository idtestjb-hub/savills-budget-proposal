## Purpose

Requires that a cost code the pipeline fills is computed by the method Savills' own costing
specification states for it, and defines what the pipeline does when that method cannot be
implemented from the data available.

**Data scope**: this capability changes how three existing cost lines are calculated in the
generated workbooks. It reads Generation B rate-card data as before and writes no data of its own;
no Generation A or Generation B table is modified and no Fact/Dim join key changes, so the Copilot
Studio package's live data is unaffected.

## ADDED Requirements

### Requirement: A filled cost code uses the method its spec states

Where the pipeline produces a figure for a cost code that the costing specification defines, it
SHALL compute that figure by one of the methods the specification states for that code.

#### Scenario: A contract-based code is costed as a contract

- **WHEN** the specification defines a code as a contract cost
- **THEN** the pipeline SHALL compute it as a contract value over the budget period
- **AND** SHALL NOT substitute an unrelated basis such as internal headcount

#### Scenario: Both workbooks use the same method

- **WHEN** both generators are run against the same input
- **THEN** each such code SHALL carry the same figure in both workbooks

### Requirement: An unimplementable method is disclosed, not silently swapped

Where the specification's stated method cannot be computed because the data it needs does not exist,
the pipeline SHALL use a stated alternative and record why.

#### Scenario: A missing rate basis is named in the output

- **WHEN** a code's primary method needs a unit rate that no reference data provides
- **THEN** the output SHALL state which method was used instead and why the primary one was not

#### Scenario: A method with no usable alternative is left unimplemented

- **WHEN** neither the specification's method nor any stated alternative can be computed
- **THEN** the pipeline SHALL NOT invent a figure for that code

### Requirement: The method used is visible on the output

A reader SHALL be able to tell from the generated budget which method produced a figure, without
access to the source code.

#### Scenario: The remark states the calculation

- **WHEN** a cost line is written
- **THEN** its remark SHALL state the inputs and the method that produced the figure
- **AND** SHALL identify the reference data the rate came from

### Requirement: A method blocked only by a missing input gains the input

Where the specification states a method the pipeline cannot compute because the intake form does not
collect one of its inputs, the pipeline SHALL collect that input rather than approximate it from a
different one.

#### Scenario: The missing quantity is collected, not derived

- **WHEN** a stated method needs a quantity the form does not capture
- **AND** no captured quantity converts to it without an assumption that has no source
- **THEN** the intake form SHALL collect that quantity directly
- **AND** the pipeline SHALL NOT substitute a converted value from a related quantity

#### Scenario: A form predating the input still produces a budget

- **WHEN** an input workbook was created before the field existed, or leaves it blank
- **THEN** the pipeline SHALL still produce the budget using a stated fallback
- **AND** the output SHALL identify the figure as a fallback, say what it does not vary with, and
  name the field that would replace it

#### Scenario: Absence is distinguished from zero

- **WHEN** the field is blank, zero, or not a number
- **THEN** the pipeline SHALL treat the input as unknown and use the fallback
- **AND** SHALL NOT compute the method against a quantity of zero

### Requirement: A method's stated uncertainty travels with its figure

Where the specification states a range rather than a single rate, every generated note quoting the
resulting figure SHALL also quote the range it came from.

#### Scenario: The range is reported alongside the figure

- **WHEN** a figure is produced from a rate the specification gives as a range
- **THEN** the note SHALL state which point in the range was used and why
- **AND** SHALL state the figures the ends of that range would produce for this project

#### Scenario: A priced method's known omissions are named

- **WHEN** the specification describes a cost component it does not price
- **THEN** the note SHALL state that the component is excluded from the figure
