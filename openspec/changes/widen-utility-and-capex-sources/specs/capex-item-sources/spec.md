## Purpose

Defines which real projects supply a new prospect's capex item list, how a project is admitted to that pool, and how
the nearest one is chosen and scaled.

## ADDED Requirements

### Requirement: Eleven projects supply capex item lists

The projects with the "carries capex line items" role in the reference-project registry SHALL be the seven of today
(`R01`..`R07`) and four store projects of the 55 (`R09`..`R12`) whose budgets carry priced item lists. Each of the four
SHALL have its items in the capex item table under its key, with category (MO, M&E, Public area, Amenity area), item,
unit, quantity, unit price, total, source sheet and row, and the budget year of the source. When one budget repeats
the same item sheet for several blocks, only one copy SHALL be kept.

#### Scenario: A store project joins

- **WHEN** a store project's budget has a "Capex khu công cộng" sheet with priced item rows and a checked NFA
- **THEN** it SHALL be admitted with a new key and the capex role, and its rows SHALL carry that key

#### Scenario: Repeated block sheets

- **WHEN** one budget holds two copies of the same MO item sheet for two blocks
- **THEN** the item table SHALL hold one copy and the duplicate SHALL be named in the extraction log

### Requirement: The nearest project by NFA supplies the list, scaled

The new prospect's capex items SHALL come from the one admitted project whose capex NFA is nearest to the new
prospect's NFA, excluding the project being budgeted, with each quantity scaled by the NFA ratio (at least 1 where the
source quantity is above 0) and the source's unit price kept. The internal analysis SHALL name the source project, its
NFA and the scale factor.

#### Scenario: A 40,000 m² prospect

- **WHEN** the admitted NFAs are 18,000, 36,500 and 61,000 m² and the prospect has 40,000 m²
- **THEN** the 36,500 m² project SHALL supply the list with scale 40,000 / 36,500

### Requirement: Category ratios come from the same pool

The per-1,000 m² quantity ratio of each capex category used as a cross-check SHALL be the median over the admitted
projects that have items in that category, and the analysis SHALL state the count behind each ratio.

#### Scenario: Ratio count

- **WHEN** ten admitted projects have Amenity area items
- **THEN** the Amenity area ratio SHALL be their median and SHALL show "n = 10"
