## ADDED Requirements

### Requirement: Comparable rates are averaged on one VAT basis

Before comparable management-fee rates are averaged, each rate SHALL be put on an including-VAT basis. The VAT basis of
each comparable and product SHALL come from a hand-checked reference table that names the source of each entry. A rate
recorded as excluding VAT SHALL be multiplied by (1 + the general VAT rate of the budget period's first month). A
comparable whose basis is not in the table SHALL be treated as including VAT, and the internal analysis SHALL flag it. A
rate the PM entered SHALL NOT be converted; its own VAT label still applies.

Data files read: the comparable VAT-basis table (new, git-ignored with the other reference data), and
`Dim_Property_Residential.csv`. The standard sample's derived Apartment rate and management-fee revenue move.

#### Scenario: One comparable quoted excluding VAT

- **WHEN** the two nearest comparables have Apartment rates of 20,000 VND/m²/month excluding VAT and 15,000 including
  VAT, and the budget starts in January 2027
- **THEN** the derived Apartment rate SHALL be the mean of 22,000 and 15,000, that is 18,500 VND/m²/month

#### Scenario: Unknown basis

- **WHEN** a comparable used in the average has no entry in the VAT-basis table
- **THEN** its rate SHALL be used as including VAT
- **AND** the analysis SHALL flag that comparable's basis as unverified

### Requirement: Real distance breaks ties among close comparables, within a cap

When this project's coordinates are known, comparables within 1 km of it SHALL rank by real distance, after location
tier and size band and before verified status. A rate that this ranking moves SHALL be capped at ±20% of the rate the
ranking would give without distance. The cap SHALL apply to every product's rate and to the blended fallback rate. The
analysis SHALL state when the cap was applied.

#### Scenario: A nearby comparable changes the rate

- **WHEN** distance ranking would move the Shophouse rate by 30%
- **THEN** the applied Shophouse rate SHALL move by 20%, and the analysis SHALL say the cap applied

#### Scenario: No coordinates

- **WHEN** the project has no coordinates
- **THEN** the ranking and every rate SHALL be the same as without the distance step
