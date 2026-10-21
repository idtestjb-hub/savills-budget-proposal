## Purpose

Guarantees that the client deliverable's grand total sheet (`1. Summary`) ties to the detail sheets
it aggregates — every code's year total, the two year-total columns of the budget sheet, and the
staff figure against the deliverable's own payroll calculator — so a PM can defend a budget whose
own pages agree.

**Generation**: this capability governs the **Generation A** deliverable-writing pipeline only
(`generate_project_budget.py`, with a matching adjustment in `generate_project_output.py`). It
reads no new data, modifies no Generation A or Generation B table, and changes no Fact/Dim join
key — the Copilot Studio package's live data is unaffected.

## Requirements

### Requirement: The grand total ties to the detail sheet

Every figure on `1. Summary` SHALL equal the corresponding figure on the sheet it aggregates. For
each budget code the summary reports, its year total SHALL equal the code's year total on
`2. Budget-Management Fund`. The summary's operating surplus SHALL equal that sheet's own operating
surplus. Where the summary reads a specific total column of the budget sheet, that column SHALL
equal the sheet's other year-total column for every line item it sums.

#### Scenario: Summary and detail agree per code

- **WHEN** a deliverable is generated and recalculated
- **THEN** for every code shown on `1. Summary`, the summary's year total SHALL equal the code's
  year total on `2. Budget-Management Fund` within rounding

#### Scenario: The two year-total columns of the budget sheet agree

- **WHEN** a deliverable is generated and recalculated
- **THEN** for every line item, the `F × occurrences` year total and the month-by-month year total
  SHALL be equal within rounding — no line item may show two different annual figures

#### Scenario: The surplus ties out

- **WHEN** a deliverable is generated and recalculated
- **THEN** the operating surplus on `1. Summary` SHALL equal total operating income minus total
  operating cost as computed on `2. Budget-Management Fund`, within rounding

### Requirement: A time-spread cost or revenue line is written so its two totals agree

Any line the pipeline writes SHALL be written on a frequency basis where its `F × occurrences`
annual total and its month-by-month annual total are equal by construction — a flat monthly line,
or an explicit twelve-month schedule. The pipeline MUST NOT leave a line on a "yearly / half-yearly
/ quarterly" frequency with fewer payment-month dates filled than its occurrence count, because the
two total columns then disagree and the summary reads the lower one.

#### Scenario: A line the pipeline writes never splits its own total

- **WHEN** the pipeline writes any cost or revenue line
- **THEN** that line's two year-total columns SHALL be equal within rounding

#### Scenario: A carried template placeholder that splits its total is neutralised

- **WHEN** the standard template ships a line on a multi-payment frequency with an incomplete set
  of payment-month dates, and the pipeline does not otherwise populate that line
- **THEN** the pipeline SHALL clear that line so both its year totals read zero, rather than let the
  deliverable ship a line whose two totals disagree
- **AND** the cleared line SHALL be one a PM can fill with a real figure

### Requirement: The staff figure reflects the deliverable's own payroll calculator

The in-house staff cost on `1. Summary` (`EMH`) SHALL equal the total on the deliverable's own
`A1. Staff cost` payroll-calculator sheet, plus the cost of any in-house roster position that has no
row-group on that sheet. It SHALL NOT be a separately derived figure that differs from the payroll
sheet the same deliverable presents.

#### Scenario: EMH equals the payroll sheet

- **WHEN** a deliverable is generated and recalculated
- **THEN** the `EMH` figure on `1. Summary` SHALL equal the `A1. Staff cost` sheet's annual total,
  plus any in-house position costed outside that sheet, within rounding

#### Scenario: Every in-house position is counted once

- **WHEN** a roster contains a position with no row-group on `A1. Staff cost` (for example
  Reception)
- **THEN** that position's cost SHALL be included in `EMH` exactly once
- **AND** an outsourced position (security, cleaning, landscape) SHALL NOT be counted in `EMH` — it
  is priced on its own outsourced-contract line

#### Scenario: The two workbooks agree on staff cost

- **WHEN** both generators run against the same input
- **THEN** the client deliverable and the internal analysis workbook SHALL derive the in-house staff
  cost on the same payroll basis (13th-month, statutory insurance, union, admin markup)
- **AND** SHALL report totals that agree within rounding, or — where an exact replication of the
  payroll calculator's bracket maths is not practical — a residual no larger than 1% of the staff
  total, with its cause stated on the analysis sheet

### Requirement: The deliverable carries no error cell the pipeline could resolve, and no dead-end write

A sheet the pipeline writes any value into SHALL NOT ship with a spreadsheet error cell
(`#DIV/0!`, `#REF!`, `#NAME?`, `#VALUE!`, `#N/A`, `#NUM!`) that filling that sheet's own input cells
would resolve. The pipeline SHALL NOT write a value into a sheet whose cells no formula anywhere in
the deliverable reads.

#### Scenario: A written helper sheet is error-free

- **WHEN** the pipeline writes rates or counts into a helper sheet
- **THEN** that sheet SHALL recalculate with no error cell that its own inputs would have resolved

#### Scenario: A dead-end write is removed

- **WHEN** no formula in the deliverable reads any cell of a sheet
- **THEN** the pipeline SHALL NOT write values into that sheet
- **AND** the figure that sheet was meant to hold SHALL still be computed and placed where the
  deliverable actually consumes it

### Requirement: Verification enforces the reconciliation on every run

Verification SHALL open the generated deliverable, recalculate it, and fail when: `1. Summary`
disagrees with `2. Budget-Management Fund` on any code's year total or on the surplus; any line
item's two year-total columns disagree; `EMH` does not equal the `A1. Staff cost` total plus
outside-costed positions; or the deliverable's count of unresolved error cells exceeds a recorded
ceiling. The ceiling SHALL only ever be lowered.

#### Scenario: A reconciliation break fails the run

- **WHEN** verification runs and any of the reconciliations above does not hold
- **THEN** verification SHALL fail and name the figure, with each side's value in VND

#### Scenario: The error-cell ceiling ratchets down

- **WHEN** a change reduces the deliverable's unresolved error-cell count
- **THEN** the recorded ceiling SHALL be lowered to the new count
- **AND** a later run that reintroduces errors above it SHALL fail

### Requirement: The figure movement is measured, signed off, and re-baselined

The effect of this reconciliation on the client-facing figures SHALL be measured for a named real
project, reviewed by the Head of PM, and recorded before the change is archived.

#### Scenario: The movement is recorded

- **WHEN** the reconciliation is applied
- **THEN** the year-one estimated surplus before and after SHALL be recorded for a named project,
  in VND, with the `RO2a` and staff components shown separately

#### Scenario: Baselines are re-recorded with a reason

- **WHEN** the movement has been reviewed and accepted
- **THEN** the deliverable and analysis baselines SHALL be re-recorded with a stated reason naming
  this change
- **AND** verification SHALL pass on the following run

### Requirement: The summary discloses what it does not consolidate

`1. Summary` SHALL state, in a note that moves no figure, that its chargeable-area figure covers
only the products shown on `0. Info` (a further product priced on the budget sheet is not in that
area total), and that common-area advertising revenue sits on `2.2 Common area Fund`, a separate
fund not consolidated here.

#### Scenario: The area caveat is present

- **WHEN** the deliverable contains a product priced on the budget sheet that has no row on
  `0. Info`
- **THEN** `1. Summary` SHALL carry a note that its chargeable-area figure is the `0. Info` subset

#### Scenario: The advertising caveat is present

- **WHEN** the deliverable is generated
- **THEN** `1. Summary` SHALL carry a note that advertising revenue is on `2.2 Common area Fund`

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
