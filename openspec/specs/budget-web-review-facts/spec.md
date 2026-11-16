# budget-web-review-facts Specification

## Purpose
Section 2 of the web Review tab ("Dữ kiện file ngân sách không có") is filled when the PM picks an approved budget, from
the earlier run of the same project, the file's `0. Info` sheet and the master list `Dim_Property_Residential.csv`, each
field labelled with its source; the PM's entry still wins. Code: `webapp/facts_prefill.py`, `GET /api/library/{id}/facts`.

## Requirements

### Requirement: Section 2 is filled from known sources when a library file is picked

When the PM picks an approved budget in the Review tab's library list, the page SHALL fill each field of section 2 from,
in order of priority: the latest earlier run of the same project, the file's `0. Info` sheet, and the master list. A
zero or blank SHALL count as no value. A field no source fills SHALL stay blank.

#### Scenario: Earlier run wins

- **WHEN** an earlier run of the project entered 400 car bays and the master list says 246
- **THEN** the field SHALL show 400 with the source of that run
- **AND** the page SHALL show that the master list says 246

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

### Requirement: The master's tower count is never filled

The master list's TowerCount SHALL NOT fill "Số tháp"; the field SHALL say what the master gives and stay for the PM,
unless an earlier run fills it. A tower count from the master SHALL still decide whether the master's floor count is used.

#### Scenario: Master gives 22 towers

- **WHEN** the master list gives 22 towers and no earlier run has a tower count
- **THEN** "Số tháp" SHALL stay blank with the note that the master gives 22 towers

### Requirement: The PM's entry wins

The run SHALL use the values the fields hold when the PM starts it; a value the PM changed SHALL overwrite the filled one
and the Info sheet's.

#### Scenario: PM corrects a filled value

- **WHEN** the page filled 472 car bays and the PM types 480
- **THEN** the run SHALL use 480

### Requirement: Section 2 carries the four extra project facts
Section 2 of the Review tab SHALL have cells for Passenger Elevators per Tower, Number of Basements, Number of Pools
and Street Address, in addition to the existing cells. Their values SHALL go onto the input form's labels of the same
name. These cells SHALL be filled from the same sources and with the same priority as the other cells of section 2.

#### Scenario: PM types the basements
- **WHEN** the PM types 2 into Number of Basements and starts the Review
- **THEN** the run's input form SHALL hold 2 at "Number of Basements" with source "nhập trên trang web"

### Requirement: Blank facts are filled from the master list at run time
When a Review run starts with a fact left blank on the page, the run SHALL look the project up in the master list by
its folded name. This applies to an upload, a library file and an earlier run. A blank fact SHALL then take the
master's value, with source "danh sách master", under the existing master rules:
- floor count only for a one-tower project;
- tower count never filled, only noted;
- two or more matching rows: nothing used, and a note says so.

A value from the page or from the approved file SHALL always win over the master.

#### Scenario: Upload with blank gate count
- **WHEN** a file is uploaded, section 2 leaves Gate / Entrance Count blank, and the master holds 2 gates for that
  project
- **THEN** the run SHALL use 2 gates with source "danh sách master", and the run log SHALL say so

#### Scenario: Two master rows match
- **WHEN** the folded name matches two master rows
- **THEN** no master value SHALL be used and the run log SHALL name the count of matching rows

### Requirement: A site package prefills section 2 from its own facts and shows the notes
In a site package, section 2 SHALL be prefilled from `site.json` `facts`, with the note "Nguồn: dữ kiện đóng trong
gói (sửa được)". Each `fact_notes` entry SHALL be shown under its cell, for example the master's tower count, which is
never filled.

#### Scenario: Package with master facts
- **WHEN** `site.json` holds gates 2, car slots 964 and a tower note "master ghi 5 tháp; số tháp để PM kiểm và nhập"
- **THEN** the gate and car cells SHALL be prefilled, the tower cell SHALL stay blank, and the note SHALL be shown
  under it
