## MODIFIED Requirements

### Requirement: The client deliverable benchmarks the finished proposal, not only the rate

The `Comparison` sheet in the client deliverable SHALL present this project's finished proposal in the terms a client
and a PM negotiate over, not only the management-fee rate in VND per m² per month. It SHALL show this project's own
figures only and SHALL NOT name another project or show another project's rate (decision D3, 2026-10-11):

- the **management fee per apartment, in VND per month**: the derived Apartment rate times this project's average
  apartment net floor area (apartment net floor area divided by apartment unit count);
- this project's **year-one management-fee revenue, in VND**: the same total the deliverable's own management-fee lines
  produce.

The internal analysis workbook SHALL carry the peer comparison: for each comparable, by name, its fee per apartment from
its real Apartment rate and its average area per apartment, and this project's year-one revenue recomputed at that
comparable's rate. Where a comparable's apartment-only area is not separately on file, the analysis SHALL use its total
building area divided by its apartment unit count and SHALL label that figure as an approximation and an upper bound.

The comparables SHALL be the same projects, in the same order, that are used to derive and reality-check the Apartment
rate: the nearest real projects by the matching method in effect that have a verified Apartment rate.

#### Scenario: A proposal is benchmarked on fee per apartment

- **WHEN** the client deliverable is generated for a project that contains apartments
- **THEN** the `Comparison` sheet SHALL show this project's management fee per apartment in VND per month, computed from
  the derived Apartment rate and this project's average apartment net floor area
- **AND** SHALL NOT show any comparable's name, rate or fee per apartment
- **AND** the internal analysis SHALL show the same figure for each named comparable, marking an approximation where a
  comparable's apartment-only area is not on file

#### Scenario: A proposal is benchmarked on year-one revenue

- **WHEN** the client deliverable is generated
- **THEN** the `Comparison` sheet SHALL show this project's year-one management-fee revenue in VND
- **AND** the internal analysis SHALL show that revenue recomputed at each comparable's Apartment rate, labelled as a
  projection, not as that comparable's actual revenue

#### Scenario: The benchmark uses the rate's own comparables

- **WHEN** the nearest comparables have been selected to derive the Apartment rate
- **THEN** the peer comparison and the deliverable's range statement SHALL use that same set of comparables in that same
  order, whatever matching method selected them
- **AND** SHALL NOT select a different set

### Requirement: The benchmark distinguishes a peer comparison from an internal check

The `Comparison` sheet SHALL state, on the sheet, which statements rest on real reference projects and which are an
internal consistency check on this project's own figures. The range statement in the verdict SHALL be identified as
drawn from reference projects' real rates, which the internal analysis lists. The fee-to-cost coverage figure SHALL be
identified as an internal check, because this project's estimated operating cost is itself derived from reference
property ratios and is therefore not an independent second opinion.

#### Scenario: The fee comparison is labelled as a peer comparison

- **WHEN** the `Comparison` sheet states where the proposed fee sits against the reference projects
- **THEN** it SHALL say the statement comes from reference projects' real Apartment rates, without naming them

#### Scenario: The coverage figure is labelled as an internal check

- **WHEN** the `Comparison` sheet shows fee-to-cost coverage
- **THEN** it SHALL state that the operating-cost side is this project's own estimate, derived from reference-property
  ratios, and is a consistency check rather than a market benchmark

### Requirement: The benchmark ends with a plain-language verdict

The proposal benchmark SHALL end with a single plain-language line that a non-technical reader can act on. It SHALL
state whether the proposed management fee sits inside, below, or above the range set by the reference projects, without
naming them or quoting their rates, and whether year-one operating income covers year-one operating cost (before
Savills' fee).

#### Scenario: The proposed fee is inside the comparable range

- **WHEN** this project's fee per apartment is between the lowest and highest comparable fee per apartment
- **THEN** the verdict line SHALL state that the proposed fee is within the range of the reference projects
- **AND** SHALL NOT quote the range's end points

#### Scenario: The proposed fee is outside the comparable range

- **WHEN** this project's fee per apartment is below the lowest, or above the highest, comparable fee per apartment
- **THEN** the verdict line SHALL state that, and by how much in percentage terms, so a PM can decide whether to adjust
  before the proposal goes out

#### Scenario: The operating budget does not balance

- **WHEN** year-one operating cost exceeds year-one operating income (before Savills' fee)
- **THEN** the verdict line SHALL say so explicitly, regardless of where the fee sits against the reference projects
