## Purpose

Defines how the client deliverable presents the finished budget proposal — the management fee a real
apartment owner would pay, the year-one management-fee revenue, and whether that revenue covers the
operating budget — alongside the nearest comparable projects Savills already manages, so a PM can
show a client the proposed fee is in line with the market rather than only assert it.

**Data scope**: this capability only re-presents figures the two generated workbooks already produce
and adds clearly-labelled "if charged at the comparable's rate" projections. It reads Generation B
comparable rates and scale (`master_comparables.py`), already read by this sheet, and writes no
data. No Generation A or Generation B table is modified and no Fact/Dim join key changes, so the
Copilot Studio package's live data is unaffected.

## ADDED Requirements

### Requirement: The client deliverable benchmarks the finished proposal, not only the rate

The `Comparison` sheet in the client deliverable SHALL present this project's finished proposal next
to the nearest comparable projects, expressed in the terms a client and a PM negotiate over, not
only the management-fee rate in VND per m² per month. It SHALL show, for this project and for each
comparable:

- the **management fee per apartment, in VND per month** — for this project, the derived Apartment
  rate times this project's average apartment net floor area (apartment net floor area divided by
  apartment unit count); for each comparable, its real Apartment rate times its average area per
  apartment. Where a comparable's apartment-only area is not separately on file, the sheet SHALL use
  its total building area divided by its apartment unit count and SHALL label that figure as an
  approximation and an upper bound (it includes shared and non-apartment area);
- this project's **year-one management-fee revenue, in VND** — the same total the deliverable's own
  management-fee lines produce — next to that revenue recomputed as if this project were charged at
  each comparable's Apartment rate.

The comparables used SHALL be the same projects, in the same order, that the sheet already uses to
derive and reality-check the Apartment rate — the nearest real projects by total building net floor
area that have a verified Apartment rate.

#### Scenario: A proposal is benchmarked on fee per apartment

- **WHEN** the client deliverable is generated for a project that contains apartments
- **THEN** the `Comparison` sheet SHALL show this project's management fee per apartment in VND per
  month, computed from the derived Apartment rate and this project's average apartment net floor area
- **AND** next to it the same figure for each comparable, computed from that comparable's real
  Apartment rate and its average area per apartment
- **AND** where a comparable's apartment-only area is not on file, its figure SHALL be marked as an
  approximation computed from total building area per apartment

#### Scenario: A proposal is benchmarked on year-one revenue

- **WHEN** the client deliverable is generated
- **THEN** the `Comparison` sheet SHALL show this project's year-one management-fee revenue in VND
- **AND** the same revenue recomputed at each comparable's Apartment rate, so the difference is a
  VND amount
- **AND** each recomputed figure SHALL be labelled as a projection, not as that comparable's actual
  revenue

#### Scenario: The benchmark uses the rate's own comparables

- **WHEN** the `Comparison` sheet has already selected the nearest comparables to derive the
  Apartment rate
- **THEN** the proposal benchmark SHALL use that same set of comparables in that same order
- **AND** SHALL NOT select a different set

### Requirement: The benchmark shows whether the operating budget balances

The `Comparison` sheet SHALL show, for year one and in VND: this project's management-fee revenue,
its total operating income (management fee plus parking, advertising and other operating income),
its total operating cost, and the operating surplus that leaves — before Savills' own fee and before
tax. It SHALL also show that surplus as a percentage of total operating income and classify the
percentage with a plain band — for example thin, normal, or generous — with the band thresholds
stated on the sheet.

The coverage figures cover the **operating fund only**. The sinking fund / capex reserve is a
separate, legally ring-fenced fund and is excluded from both the income and the cost side; the sheet
SHALL say so.

The revenue, income, cost and surplus figures SHALL be the deliverable's own — the same figures the
deliverable reports elsewhere — not separately derived numbers.

#### Scenario: Coverage is shown in VND and as a percentage

- **WHEN** the client deliverable is generated
- **THEN** the `Comparison` sheet SHALL show year-one management-fee revenue, total operating
  income, total operating cost, and operating surplus (before Savills' fee and tax), each in VND
- **AND** the surplus as a percentage of total operating income
- **AND** a plain-language band for that percentage, with the numeric thresholds for each band
  shown on the sheet

#### Scenario: The figures are the deliverable's own

- **WHEN** the coverage figures are written
- **THEN** each SHALL resolve to the same value the deliverable reports for it on its summary sheet
- **AND** SHALL NOT be recomputed by a different method for the benchmark

#### Scenario: The sinking fund is excluded and the sheet says so

- **WHEN** the coverage figures are shown
- **THEN** the sheet SHALL state that they cover the operating fund only and exclude the sinking
  fund / capex reserve

#### Scenario: A negative surplus is shown as a shortfall

- **WHEN** total operating cost exceeds total operating income
- **THEN** the `Comparison` sheet SHALL show the shortfall as a negative surplus in VND and a
  negative percentage
- **AND** the verdict line SHALL state that the operating budget does not balance before Savills'
  fee

### Requirement: The benchmark distinguishes a peer comparison from an internal check

The `Comparison` sheet SHALL state, on the sheet, which parts of the proposal benchmark are a
comparison against real comparable projects and which parts are an internal consistency check on
this project's own figures. The fee-per-apartment and revenue-at-comparable-rate figures SHALL be
identified as drawn from comparable projects' real rates. The fee-to-cost coverage figure SHALL be
identified as an internal check, because this project's estimated operating cost is itself derived
from one reference property's cost ratios and is therefore not an independent second opinion.

#### Scenario: The fee comparison is labelled as a peer comparison

- **WHEN** the `Comparison` sheet shows fee per apartment or revenue at a comparable's rate
- **THEN** it SHALL state that these figures come from comparable projects' real Apartment rates

#### Scenario: The coverage figure is labelled as an internal check

- **WHEN** the `Comparison` sheet shows fee-to-cost coverage
- **THEN** it SHALL state that the operating-cost side is this project's own estimate, derived from
  reference-property ratios, and is a consistency check rather than a market benchmark

### Requirement: The benchmark ends with a plain-language verdict

The proposal benchmark SHALL end with a single plain-language line that a non-technical reader can
act on. It SHALL state whether the proposed management fee sits inside, below, or above the range
set by the comparables, and whether year-one operating income covers year-one operating cost (before
Savills' fee).

#### Scenario: The proposed fee is inside the comparable range

- **WHEN** this project's fee per apartment is between the lowest and highest comparable fee per
  apartment
- **THEN** the verdict line SHALL state that the proposed fee is within the range of what Savills
  charges for comparable buildings

#### Scenario: The proposed fee is outside the comparable range

- **WHEN** this project's fee per apartment is below the lowest, or above the highest, comparable
  fee per apartment
- **THEN** the verdict line SHALL state that, and by how much in percentage terms, so a PM can
  decide whether to adjust before the proposal goes out

#### Scenario: The operating budget does not balance

- **WHEN** year-one operating cost exceeds year-one operating income (before Savills' fee)
- **THEN** the verdict line SHALL say so explicitly, regardless of where the fee sits versus the
  comparables

### Requirement: The benchmark figures reconcile with the deliverable they appear in

The proposal benchmark's own-project revenue, income, cost and surplus figures SHALL resolve to the
same values the deliverable's `1. Summary` sheet reports for them — they carry the deliverable's own
figures forward, they do not restate them. Verification SHALL confirm this and fail if a benchmark
cell resolves to a different value, or to an error, than its `1. Summary` source.

#### Scenario: Revenue and cost reconcile

- **WHEN** verification runs against a generated deliverable
- **THEN** the benchmark's year-one management-fee revenue, total operating income, total operating
  cost and operating surplus SHALL each resolve to the same value, within rounding, as the matching
  `1. Summary` figure

#### Scenario: A broken reference fails verification

- **WHEN** a benchmark cell resolves to an error or to a value that differs from its `1. Summary`
  source beyond rounding
- **THEN** verification SHALL fail and name the figure, with both values in VND

#### Scenario: A projection is internally consistent

- **WHEN** a comparable's Apartment rate equals this project's derived Apartment rate
- **THEN** the "revenue if charged at that comparable's rate" figure SHALL equal this project's
  own year-one management-fee revenue within rounding

### Requirement: The benchmark degrades gracefully when comparable data is thin

The proposal benchmark SHALL still render, and SHALL state what is missing, when the comparable data
does not support every figure. It MUST NOT invent a comparable rate, a fee per apartment, or a
range to fill a gap.

#### Scenario: A new prospect with no known real rate

- **WHEN** the project is a new prospect for which Savills has no independently known management-fee
  rate
- **THEN** the benchmark SHALL show this project's proposed figures and the comparables' figures
- **AND** SHALL omit the reality-check gap rather than show a placeholder

#### Scenario: A comparable has no Apartment rate

- **WHEN** one of the nearest comparables has no verified Apartment rate on file
- **THEN** that comparable's fee-per-apartment and revenue-at-its-rate cells SHALL be shown as
  blank with a note, not as zero or an estimate

#### Scenario: Fewer than two comparables are available

- **WHEN** fewer than two comparable projects with a verified Apartment rate exist for this project
- **THEN** the benchmark SHALL show the comparables that do exist
- **AND** the verdict line SHALL state that the comparable base is narrow
