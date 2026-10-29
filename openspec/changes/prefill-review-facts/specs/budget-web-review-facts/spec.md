## ADDED Requirements

### Requirement: Section 2 is filled from known sources when a library file is picked

When the PM picks an approved budget in the Review tab's library list, the page SHALL fill each field of section 2 from,
in order of priority: the latest earlier run of the same project, the file's `0. Info` sheet, and the master list. A
zero or blank SHALL count as no value. A field no source fills SHALL stay blank.

#### Scenario: Earlier run wins

- **WHEN** an earlier run of the project entered 3 towers and the master list says 2
- **THEN** the field SHALL show 3 with the source of that run
- **AND** the page SHALL show that the master list says 2

#### Scenario: Master list only

- **WHEN** the project has no earlier run and its Info sheet carries no such fact
- **THEN** the field SHALL take the master list's value and say so

### Requirement: Projects are matched by their folded name only

Two names SHALL be the same project when they are equal after removing accents, turning đ into d, lower-casing and
dropping every character that is not a letter or a digit. No other match SHALL be used. A master name matching two or
more rows SHALL fill nothing and SHALL be reported.

#### Scenario: Spacing and accents differ

- **WHEN** the library names "HOÀNG ANH GIAI VIỆT" and the master list "Hoang Anh Giai Viet"
- **THEN** they SHALL match

#### Scenario: Similar but different names

- **WHEN** the library names "Masteri West Heights" and the master list has only "Masteri Thao Dien"
- **THEN** nothing SHALL be filled from the master list

### Requirement: The master's floor count is used for one-tower projects only

The master list's FloorCount SHALL fill "Số tầng" only when its TowerCount is 1; otherwise the field SHALL say the
master's figure is per tower and stay for the PM.

#### Scenario: Three towers

- **WHEN** the master list gives 3 towers and 29 floors
- **THEN** "Số tầng" SHALL stay blank with the note that the master gives 29 floors per tower

### Requirement: The PM's entry wins

The run SHALL use the values the fields hold when the PM starts it; a value the PM changed SHALL overwrite the filled one
and the Info sheet's.

#### Scenario: PM corrects a filled value

- **WHEN** the page filled 472 car bays and the PM types 480
- **THEN** the run SHALL use 480
