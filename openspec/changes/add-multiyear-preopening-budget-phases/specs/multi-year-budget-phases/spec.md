## Purpose

Lets a project state how much of its operating life the budget should cover — an optional pre-opening
phase before handover, and one or more operating years after it — and produces a budget whose sheets,
ramp, cost escalation and summary all follow that stated horizon, instead of always producing a single
steady-state year.

**Data scope**: this capability changes the sheet set of the generated deliverable and the internal
analysis workbook, and the figures on any project that asks for more than one operating year or a
pre-opening phase. It reads and writes no Generation A or Generation B reference table and changes no
Fact/Dim join key, so the Copilot Studio package's live data is unaffected. Figures stay in VND.

## ADDED Requirements

### Requirement: The project states its budget horizon

The project's own inputs SHALL state how many operating years the budget covers and whether the
project has a pre-opening phase, with that phase's length in whole months. Absent an entry, the budget
SHALL cover exactly one operating year with no pre-opening phase — today's behaviour. An entry of
fewer than one operating year, a fractional year, or a negative or fractional pre-opening month count
SHALL stop generation with a message naming the field and the value, rather than being rounded or
silently treated as the default.

#### Scenario: A horizon is stated

- **WHEN** the project states two operating years and a three-month pre-opening phase
- **THEN** the budget SHALL cover a three-month pre-opening phase followed by two operating years

#### Scenario: No horizon is stated

- **WHEN** the project states no operating-year count and no pre-opening phase
- **THEN** the budget SHALL cover exactly one operating year with no pre-opening phase

#### Scenario: An invalid horizon stops generation

- **WHEN** the project states zero operating years, a fractional year count, or a negative pre-opening
  month count
- **THEN** generation SHALL stop and name the field and the rejected value
- **AND** SHALL NOT fall back to the default horizon

### Requirement: Each phase of the horizon has its own budget sheets

For every phase the horizon names — the pre-opening phase, when present, and each operating year —
the deliverable SHALL carry its own management-fund sheet and its own common-area-fund sheet, each
covering that phase's own months and carrying that phase's own figures. A phase's sheet SHALL NOT
report another phase's months, and every cost code the pipeline prices SHALL be priced on every
operating-year sheet, not only the first.

#### Scenario: A two-year project carries two sets of fund sheets

- **WHEN** the horizon states two operating years
- **THEN** the deliverable SHALL carry a management-fund sheet and a common-area-fund sheet for year 1
  and a second pair for year 2
- **AND** each pair SHALL report only its own year's twelve months

#### Scenario: A pre-opening phase carries its own sheet

- **WHEN** the horizon states a pre-opening phase of three months
- **THEN** the deliverable SHALL carry a pre-opening budget sheet covering exactly those three months

#### Scenario: Priced codes appear on every operating year

- **WHEN** the pipeline prices a cost code on the year-1 management-fund sheet
- **THEN** it SHALL price that same code on every later operating year's management-fund sheet

### Requirement: A pre-opening phase is costed on its own basis and reported separately

A pre-opening phase SHALL be costed on its own staffing and cost basis — a mobilisation roster and the
costs that genuinely arise before handover — not by repeating or pro-rating the steady-state operating
roster. It SHALL carry no management-fee revenue from residents. Its total SHALL be reported as its
own figure on the summary and SHALL NOT be folded into, netted against, or spread across any operating
year's total.

#### Scenario: Pre-opening staffing differs from operating staffing

- **WHEN** a pre-opening phase is costed
- **THEN** its staffing cost SHALL come from a pre-opening roster stated for that phase
- **AND** SHALL NOT be the operating roster's cost pro-rated to the phase's month count

#### Scenario: Pre-opening carries no resident fee revenue

- **WHEN** a pre-opening phase is costed
- **THEN** it SHALL report no management-fee revenue collected from residents

#### Scenario: The pre-opening total stands on its own

- **WHEN** the summary reports a horizon that includes a pre-opening phase
- **THEN** that phase's total SHALL appear as its own reported figure
- **AND** no operating year's reported total SHALL include any part of it

### Requirement: Cost escalation between years is applied from a stated rate, and the fee rate is not escalated silently

Where a horizon covers more than one operating year, each year after the first SHALL apply a stated
year-on-year cost escalation rate to the cost lines it escalates, compounding from the first operating
year, and each escalated line's remark SHALL state the rate and the number of years compounded. Absent
a stated rate, later years SHALL repeat the first year's cost basis unescalated rather than apply an
assumed rate. The management-fee rate charged to residents SHALL NOT be escalated automatically; it
SHALL stay at the first year's rate unless the project states a different rate for that year.

#### Scenario: A stated escalation rate is applied and disclosed

- **WHEN** the horizon covers three operating years and states a year-on-year cost escalation rate
- **THEN** year 3's escalated cost lines SHALL carry that rate compounded twice from year 1
- **AND** each escalated line's remark SHALL state the rate and that it was compounded twice

#### Scenario: No stated rate means no escalation

- **WHEN** the horizon covers more than one operating year and states no escalation rate
- **THEN** every later year's cost lines SHALL carry the first year's cost basis unescalated

#### Scenario: The fee rate does not escalate on its own

- **WHEN** a later operating year is priced and the project states no separate fee rate for that year
- **THEN** that year's management-fee rate SHALL equal the first operating year's rate

### Requirement: The summary reports every phase of the horizon

The summary sheet SHALL report every phase the horizon names, each as its own set of figures, so a
reader sees the pre-opening phase and each operating year side by side rather than a single blended
result. The first operating year's figures SHALL occupy the same position they occupy for a
single-year project, and later phases SHALL be added alongside without displacing it.

#### Scenario: Each phase is reported

- **WHEN** the horizon covers a pre-opening phase and two operating years
- **THEN** the summary SHALL report a set of figures for the pre-opening phase, for year 1, and for
  year 2

#### Scenario: Year one keeps its position

- **WHEN** a multi-phase summary is compared with a single-year project's summary
- **THEN** the first operating year's figures SHALL be in the same position in both

### Requirement: A single-year project with no pre-opening phase is unchanged

A project whose horizon is one operating year with no pre-opening phase SHALL produce the sheet names,
the sheet set, the summary layout and every figure that the same project produced before this
capability existed. This SHALL be demonstrated against a recorded baseline, not asserted.

#### Scenario: The default horizon reproduces today's output

- **WHEN** a project whose horizon is one operating year with no pre-opening phase is generated
- **THEN** every sheet name SHALL match the name that project's output carried before this capability
- **AND** every figure the pipeline writes SHALL equal its recorded pre-change baseline value in VND

### Requirement: Both generated workbooks describe the same horizon

The client deliverable and the internal analysis workbook SHALL cover the same phases for the same
project, and report the same figure for the same phase. A run that produces one workbook on one
horizon and the other on a different horizon SHALL fail rather than deliver two workbooks that
disagree about how long the project was budgeted for.

#### Scenario: The two workbooks agree on the horizon

- **WHEN** both generators run against the same input
- **THEN** both SHALL cover the same phases
- **AND** SHALL report the same total in VND for each phase

#### Scenario: A horizon mismatch fails the run

- **WHEN** the two workbooks cover different phase sets for the same project
- **THEN** verification SHALL fail and name the phases each workbook covers

### Requirement: The figure movement is measured and disclosed before adoption

Because a horizon of more than one operating year or a pre-opening phase changes what the budget
reports, the change SHALL measure the effect on a named real project — each phase's reported revenue,
cost and surplus in VND — and record it for review before the capability is relied on for a client
deliverable.

#### Scenario: The effect on a real project is on record

- **WHEN** the capability is implemented
- **THEN** the change SHALL record, for a named real project, each phase's revenue, cost and surplus
  in VND
- **AND** SHALL record the same project's single-year figures for comparison
