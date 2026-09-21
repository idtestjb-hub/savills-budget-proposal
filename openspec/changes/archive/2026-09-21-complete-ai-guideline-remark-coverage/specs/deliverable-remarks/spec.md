## ADDED Requirements

### Requirement: `0. Info` states each priced product's area basis

For every product row `0. Info` prices (Apartment/Officetel/Office/Shophouse and any other product
with a fee-table row), the deliverable SHALL write a remark stating the area's basis and the year
it was last confirmed, using the project's own "Area basis / drawing reference" intake field when
the PM has supplied one. When that field is blank, the remark SHALL say the area is PM-supplied
without inventing a drawing or legal citation.

#### Scenario: A PM-supplied area basis is shown

- **WHEN** the deliverable is generated and the PM has entered an area basis / drawing reference
  for a priced product
- **THEN** that product's `0. Info` remark SHALL state the basis text and the confirmation year
  entered

#### Scenario: No area basis was supplied

- **WHEN** a priced product has no area basis / drawing reference entered
- **THEN** its `0. Info` remark SHALL state the area is PM-supplied, without a fabricated drawing
  or legal citation

### Requirement: `A2`/`A3` carry every canonical position's duty description

The standard deliverable template already carries the AI Guideline's full duty description for
every canonical Security (`A2`) and Cleaning (`A3`) position, as its own shipped content — the
pipeline SHALL NOT overwrite it, and SHALL NOT need to write it. The deliverable SHALL still carry
that description, unmodified, for every canonical position the template defines.

#### Scenario: A canonical position keeps its template description

- **WHEN** the deliverable is generated
- **THEN** every canonical position defined on `A2`/`A3` SHALL still carry the template's own duty
  description, exactly as shipped

### Requirement: Verification confirms the extended remark coverage

Verification SHALL open the generated deliverable, and fail when: a priced `0. Info` product has no
area-basis remark; or a canonical `A2`/`A3` position (per the recorded canonical-position reference)
does not carry its duty description. This check SHALL run on every verification run and SHALL NOT
depend on a recorded numeric baseline, matching the existing remark-content check's independence
from baseline comparison.

#### Scenario: A missing `0. Info` remark fails the run

- **WHEN** verification runs and a priced product on `0. Info` has no area-basis remark
- **THEN** verification SHALL fail and name the product

#### Scenario: A missing canonical description fails the run

- **WHEN** verification runs and a canonical `A2`/`A3` position does not carry its recorded duty
  description
- **THEN** verification SHALL fail and name the position
