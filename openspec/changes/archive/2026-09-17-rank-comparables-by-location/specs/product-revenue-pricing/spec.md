## MODIFIED Requirements

### Requirement: The two workbooks report the same revenue

The client deliverable and the internal analysis workbook SHALL report the same management-fee
revenue for the same project. Both SHALL derive their rates from comparable projects selected and
ranked by the **same matching method** — the project's total building net floor area (Total NFA, in
m²) refined by the project's own location — so that neither workbook can pick different comparable
projects, or weight them differently, for the same input. Location ranking SHALL account for the
project's district and city in addition to Total NFA, such that a comparable in the same district as
the project SHALL rank at least as favorably as an equally-NFA-distant comparable in a different
district. Within whichever district/city tier and coordinate-precision grouping a comparable already
falls into, a comparable backed by a real, individually-verified budget workbook SHALL rank at least
as favorably as an otherwise-equivalent comparable that is not, but this preference SHALL NOT let an
individually-verified comparable outrank a real, more location-precise comparable — precision-of-match
takes priority over verification status, not the reverse. Where one workbook shows its comparables to
the reader, it SHALL present them in the same ranked order the matching method produces and SHALL
label the matching basis actually used (not always "Total NFA" — the label SHALL reflect location when
location narrowed the pool, and SHALL state when a shown comparable is individually-verified).

#### Scenario: Both workbooks agree on total revenue

- **WHEN** both generators are run against the same input
- **THEN** the total management-fee revenue, in VND, SHALL match between the two workbooks within
  rounding

#### Scenario: Both workbooks agree per product

- **WHEN** both generators are run against the same input
- **THEN** each product's revenue, in VND, SHALL match between the two workbooks within rounding

#### Scenario: Both workbooks select the same comparable projects

- **WHEN** both generators are run against the same input
- **THEN** the set of comparable projects each uses to derive the management-fee rate SHALL be the
  same set, in the same order
- **AND** any comparables table shown to a reader SHALL be ordered by the matching method actually
  used and labelled accordingly

#### Scenario: A same-district comparable is preferred over an equally-close different-district one

- **WHEN** the comparable pool contains two projects equally distant from this project's Total NFA,
  one in this project's own district and one in a different district
- **THEN** the same-district comparable SHALL rank at or above the different-district comparable

#### Scenario: A project's own district has no comparable

- **WHEN** no comparable project shares this project's district or city
- **THEN** ranking SHALL fall back to today's Total-NFA-only ordering
- **AND** SHALL NOT fail, error, or return an empty comparable set

#### Scenario: An individually-verified comparable is preferred over an equally-ranked one that isn't

- **WHEN** the comparable pool, within the same district/city tier and coordinate-precision grouping,
  contains both an individually-verified project and one that is not
- **THEN** the individually-verified comparable SHALL rank at or above the non-verified one

#### Scenario: A precise location match is not displaced by verification status

- **WHEN** a real, coordinate-precise comparable exists for the project and an individually-verified
  comparable exists only outside that precision grouping (a different tier, or no usable coordinates)
- **THEN** the coordinate-precise comparable SHALL still rank ahead of the individually-verified one

#### Scenario: An apartment-dominant project's rate barely moves

- **WHEN** a project's Apartment NFA is at or close to its Total NFA
- **THEN** its derived management-fee rate SHALL move little or not at all from what the pipeline
  produced before this change

#### Scenario: A mixed-use project's deliverable rate moves onto the analysis basis

- **WHEN** a project has substantial non-apartment area (for example parking, retail or office) so
  its Apartment NFA is well below its Total NFA
- **THEN** the client deliverable's derived management-fee rate SHALL change to the value the
  analysis workbook derives for that project
- **AND** the change SHALL be recorded for a named real project with both the before and after
  values in VND
