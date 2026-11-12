## ADDED Requirements

### Requirement: The package carries its own project's master facts
`build_site_package.py` SHALL find the package project's own row in the master list. It SHALL match by the folded
`--site` name, or SHALL take the row whose exact name is given with `--master-row`. It SHALL write that row's facts
into `site.json` (`facts`) together with `fact_notes` (the master rules' notes). The rules are those of the Review
master prefill:
- the tower count is a note only;
- the floor count is used only for a one-tower project.

Facts given with `--facts` SHALL win over the master. The package's coded master list SHALL stay as it is: the own
project's facts travel in `site.json`, not as a readable name in the master list.

#### Scenario: One matching row
- **WHEN** the package is built for a project whose folded name matches one master row
- **THEN** `site.json` SHALL hold that row's gates, basements, pools, elevators, car and motorbike slots, address and
  district where present, plus a tower note

#### Scenario: Several rows match
- **WHEN** the name matches two master rows (for example two phases of one project)
- **THEN** the build SHALL stop and list the matching master names, and SHALL go on only with `--master-row` naming
  one of them, or with `--no-master`

#### Scenario: No row matches
- **WHEN** no master row matches and neither `--master-row` nor `--no-master` is given
- **THEN** the build SHALL stop and say so
