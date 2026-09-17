## Purpose

Requires that a cost code the pipeline fills is computed by the method Savills' own costing
specification states for it, and defines what the pipeline does when that method cannot be
implemented from the data available.

**Data scope**: this capability changes how existing cost lines are calculated in the generated
workbooks and adds one field to the intake form. It reads Generation B rate-card data as before and
writes no data of its own; **no Generation A or Generation B table is modified and no Fact/Dim join
key changes**, so the Copilot Studio package's live data is unaffected.

## Requirements

### Requirement: A filled cost code uses the method its spec states

Where the pipeline produces a figure for a cost code that the costing specification defines, it
SHALL compute that figure by one of the methods the specification states for that code.

A figure the pipeline computes SHALL reach every workbook that reports that cost. A cost present in
one generated workbook and absent from the other is the same divergence as two different figures,
and SHALL be treated as one — a blank is harder to notice than a mismatch, because nothing invites
comparison.

Where a computed figure is an undecomposed aggregate over a section the budget form itemises, it
SHALL be placed on a row that accepts an aggregate without displacing the form's own arithmetic, and
SHALL NOT be spread across the section's individual items unless the pipeline holds data supporting
that breakdown.

#### Scenario: A contract-based code is costed as a contract

- **WHEN** the specification defines a code as a contract cost
- **THEN** the pipeline SHALL compute it as a contract value over the budget period
- **AND** SHALL NOT substitute an unrelated basis such as internal headcount

#### Scenario: Both workbooks use the same method

- **WHEN** both generators are run against the same input
- **THEN** each such code SHALL carry the same figure in both workbooks

#### Scenario: A computed cost reaches both workbooks

- **WHEN** the pipeline computes a cost category from its reference data
- **THEN** that category SHALL appear in the client deliverable and in the internal analysis
- **AND** the two SHALL carry the same figure for it
- **AND** the category SHALL NOT be reported in one workbook while left blank in the other

#### Scenario: An aggregate figure does not displace the form's own totals

- **WHEN** a computed figure covers a whole section that the budget form breaks into line items
- **THEN** the figure SHALL be written to a line item within that section
- **AND** SHALL NOT be written to a row holding the form's own subtotal formula
- **AND** the section's subtotal SHALL include the figure without that formula being altered

#### Scenario: A figure placed in a catch-all says what it does and does not cover

- **WHEN** a computed figure is written to a general or miscellaneous line item because no data
  supports allocating it across the section's specific items
- **THEN** the output SHALL state the basis of the figure and its sample size
- **AND** SHALL state which costs in that section the figure does not include, where the figure's
  own definition is narrower than the section it sits in

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

### Requirement: "The costing specification" names the method catalogue together with the logic workbook

Throughout this capability, "the costing specification" SHALL mean the combination of the method
catalogue and `EXENSIVE LOGIC.xlsx`. Where both describe a code, the catalogue SHALL determine which
method is used and `EXENSIVE LOGIC.xlsx` SHALL supply the detailed formula where the two agree on the
method. Where only one describes a code, that one applies.

#### Scenario: The two sources disagree on method

- **WHEN** the catalogue and `EXENSIVE LOGIC.xlsx` state different methods for the same filled code
- **THEN** the pipeline SHALL use the catalogue's method
- **AND** the requirement "A filled cost code uses the method its spec states" SHALL be judged
  against the catalogue's method for that code

#### Scenario: The two sources agree and only the workbook carries the formula

- **WHEN** both name the same method for a code and `EXENSIVE LOGIC.xlsx` carries the coefficients,
  rounding or frequency
- **THEN** the pipeline SHALL apply that formula detail

#### Scenario: A code only one source covers

- **WHEN** a filled code appears in only one of the two sources
- **THEN** that source SHALL be the method authority for the code

### Requirement: A filled code's remark carries the components its catalogue entry requires

Where the catalogue lists the components a code's remark must contain, the generated remark for that
code SHALL contain each of them, and SHALL cite any legal reference the catalogue entry names. This
adds to, and does not replace, the existing requirement that the remark state the calculation.

#### Scenario: Listed components appear in the remark

- **WHEN** a code is written and its catalogue entry lists required remark components
- **THEN** the code's remark SHALL contain each listed component

#### Scenario: A required legal citation appears

- **WHEN** a code's catalogue entry names a legal reference the remark must cite
- **THEN** the code's remark SHALL include that reference

#### Scenario: A code with no catalogue entry

- **WHEN** a filled code has no catalogue entry
- **THEN** the existing requirement that its remark state the inputs, the method and the reference
  data SHALL still apply
- **AND** no additional component check SHALL be imposed

### Requirement: A quantity-times-price method holds both halves, not their product

Where the costing specification states a method as a quantity multiplied by a price, the pipeline
SHALL hold the quantity and the price as separate values and SHALL compute the figure from them. It
SHALL NOT store or reuse only their product.

#### Scenario: The two halves are stored separately

- **WHEN** reference data is extracted for a cost the specification prices as quantity × price
- **THEN** the quantity and the price SHALL each be stored as a value with its unit named
- **AND** neither SHALL be recoverable only by dividing one recorded figure by another

#### Scenario: A price change moves the figure

- **WHEN** the price for such a cost is updated
- **AND** the pipeline is run again against an unchanged project input
- **THEN** the generated figure SHALL change in proportion to the price change

#### Scenario: Both halves appear on the output

- **WHEN** such a cost is written to a generated workbook
- **THEN** its note SHALL state the quantity assumed, the price applied, and the sample size behind
  each
- **AND** a reader SHALL be able to tell whether a figure is wrong because of the quantity or
  because of the price

#### Scenario: An unrecoverable price is disclosed, not invented

- **WHEN** the specification's method needs a price that the reference data does not record
- **THEN** the pipeline SHALL NOT substitute an assumed or externally guessed price
- **AND** SHALL state which cost could not be split and what it fell back to

### Requirement: A price that changes over time carries the date it was current

Any rate the pipeline applies that is expected to change over time SHALL be stored with the date it
was known to be current, and that date SHALL be reported wherever the resulting figure is.

#### Scenario: The rate's age is visible on the output

- **WHEN** a figure is produced from such a rate
- **THEN** the output SHALL state when that rate was current
- **AND** SHALL NOT present the figure as though the rate were verified as of the run

#### Scenario: A stale rate is visible rather than silent

- **WHEN** a rate's recorded date is older than the budget year being generated
- **THEN** the output SHALL make that visible to a reader of the generated workbook
