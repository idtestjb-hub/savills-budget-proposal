## MODIFIED Requirements

### Requirement: Each reference project has one key in one registry file
The reference projects the tool prices from SHALL be listed in one data file, the reference-project registry, with one
row per project carrying: a stable key (`R01`, `R02`, ...), a display name, the name variants other data files use for
the same project, the figures the tool needs (total NFA in m², apartment units and total units, the apartment
management-fee rate in VND/m²/month and its VAT basis), district and city, whether the project is excluded from the
comparables ranking, the roles the tool relies on (the utilities base, the parking base, "carries capex line items"),
and the source and location evidence. Rows added from the real-budget store SHALL also carry the store file id and
project id; figures the tool does not use for them MAY be blank. The registry SHALL live in the data folder of the
outer project, beside the master list, never in the source-code repository. Reading the registry SHALL be the only way
the tool learns a reference project's name. The registry reads no other file; nothing writes it at run time.

#### Scenario: Registry row
- **WHEN** the registry has a row with key `R02`, display name "Tháp Thử Nghiệm", NFA 64,124 m², role "utilities base"
- **THEN** the tool uses that project's usage per m² for any utility where the usage benchmark has fewer than five
  projects, and shows "Tháp Thử Nghiệm" in the internal analysis wherever it names the utilities base

#### Scenario: Store project row
- **WHEN** the registry has a row `R10` with a store file id, a capex NFA and the role "carries capex line items", and
  blank fee rate and units
- **THEN** the tool SHALL use it as a capex item source and SHALL NOT use it in the comparables ranking

#### Scenario: Registry missing
- **WHEN** the registry file is absent
- **THEN** the run SHALL stop with a message naming the file, before any sheet is written
