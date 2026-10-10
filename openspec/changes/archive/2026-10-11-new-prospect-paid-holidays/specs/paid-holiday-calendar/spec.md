## ADDED Requirements

### Requirement: A computed holiday is a day the law in force on that day makes paid

When no holiday dates are typed on `Roster Setup`, the roster month's holidays SHALL be the days that the law in force on
each day makes paid public holidays: the 11 days of Labour Code 2019 Article 112 clause 1, and 24 November from
01/07/2026 under Nghị quyết 28/2026/QH16 Article 2. Typed dates SHALL replace the computed list. Existing-project mode's
prior-year calendar SHALL stay the law in force on 1 January of that year.

#### Scenario: A November roster from 2026

- **WHEN** the roster month is November 2026 or November 2027 and no dates are typed
- **THEN** 24 November SHALL be a holiday of that month

#### Scenario: A November roster before the resolution

- **WHEN** the roster month is November 2025
- **THEN** 24 November SHALL NOT be a holiday

### Requirement: The output names the holiday law

The roster's `Setup` sheet SHALL name Labour Code 2019 Article 112 clause 1 and Nghị quyết 28/2026/QH16 Article 2 beside
the holiday dates, and the input form's reference block SHALL list the paid holidays of each year it shows under the same
rule and name both texts.

#### Scenario: The roster states its basis

- **WHEN** a roster is generated
- **THEN** its `Setup` sheet SHALL carry a note naming both legal texts
