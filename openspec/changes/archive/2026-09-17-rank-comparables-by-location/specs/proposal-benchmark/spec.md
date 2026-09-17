## MODIFIED Requirements

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
derive and reality-check the Apartment rate — the nearest real projects by the matching method in
effect (Total NFA, refined by the project's own district and city where a comparable shares them)
that have a verified Apartment rate.

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
- **THEN** the proposal benchmark SHALL use that same set of comparables in that same order,
  whatever matching method (location-refined or NFA-only fallback) selected them
- **AND** SHALL NOT select a different set
