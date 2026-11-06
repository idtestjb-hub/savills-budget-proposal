# reference-project-registry Specification

## Purpose
How the real budgets the tool estimates from are identified: one key per reference project in one registry file, the
same key on every row of theirs in the fact tables, and no project name in runtime code, so that a name can be shown,
masked or changed without moving a figure.

## Requirements

### Requirement: Each reference project has one key in one registry file
The reference projects the tool prices from SHALL be listed in one data file, the reference-project registry, with one
row per project carrying: a stable key (`R01`, `R02`, ...), a display name, the name variants other data files use for
the same project, the figures the tool needs (total NFA in m², apartment units and total units, the apartment
management-fee rate in VND/m²/month and its VAT basis), district and city, whether the project is excluded from the
comparables ranking, the roles the tool relies on (the utilities base, the parking base, "carries capex line items"),
and the source and location evidence. The registry SHALL live in the data folder of the outer project, beside the master
list, never in the source-code repository. Reading the registry SHALL be the only way the tool learns a reference
project's name. The registry reads no other file; nothing writes it at run time; no recorded baseline figure moves.

#### Scenario: Registry row
- **WHEN** the registry has a row with key `R02`, display name "Tháp Thử Nghiệm", NFA 64,124 m², role "utilities base"
- **THEN** the tool prices electricity, water and diesel from that project's usage per m² and shows "Tháp Thử Nghiệm" in
  the internal analysis wherever it names the utilities base

#### Scenario: Registry missing
- **WHEN** the registry file is absent
- **THEN** the run SHALL stop with a message naming the file, before any sheet is written

### Requirement: Fact tables carry the key and the tool joins on it
Every data file that holds a reference project's figures (utility costs and quantities, capex line items, capex
reserve observations, the VAT basis of a rate) SHALL carry a `RefKey` column holding the registry key on every row that
belongs to a reference project. The tool SHALL select rows by `RefKey`, never by the name column; the name column
stays as a label only. A row whose `RefKey` is blank or not in the registry SHALL be ignored for pricing and SHALL be
reported once in the run log. Adding `RefKey` to the four existing files is a one-off write to the outer project's data
folder, with a dated backup beside each file; afterwards the scripts that rebuild those files write `RefKey`
themselves. No figure in those files changes.

#### Scenario: Display name changes, figures do not
- **WHEN** the registry's display name of `R02` is changed and the fact files are left alone
- **THEN** every figure of the standard sample is identical to the run before the change

#### Scenario: A row without a key
- **WHEN** a capex line item row has an empty `RefKey`
- **THEN** it is not a candidate for any project's capex list and the run log says how many rows were skipped

### Requirement: Runtime code holds no reference project's name
No module that runs during a budget or Review (estimators, sheet builders, verification checks, package data builder)
SHALL contain a reference project's name as a text literal, in code, docstrings, remarks or source notes. Where the
internal analysis names the project a figure comes from, it SHALL take the registry's display name. The client
deliverable's rule that it names no other project is unchanged. A test SHALL scan the runtime modules for every display
name and name variant in the registry and fail on a match.

#### Scenario: Scan of the runtime modules
- **WHEN** the registry lists "Tháp Thử Nghiệm" and the variant "Thap Thu Nghiem"
- **THEN** no runtime module's text contains either string, and the test passes

#### Scenario: Internal analysis still names the base
- **WHEN** the internal analysis is generated on the office data
- **THEN** its utilities section names the utilities base by the registry's display name, as it did before this change

### Requirement: Figures are unchanged by the change
With the office data, every figure of the three verification samples, the recorded baselines and a City Garden Review
(fund totals, ties, top-10 differences, abnormal count) SHALL be identical before and after this change. The
verification run with its gates closed SHALL pass without re-recording a baseline.

#### Scenario: Before and after
- **WHEN** the standard sample is generated at the commit before and at the commit of this change
- **THEN** the two deliverables' figures are identical cell for cell
