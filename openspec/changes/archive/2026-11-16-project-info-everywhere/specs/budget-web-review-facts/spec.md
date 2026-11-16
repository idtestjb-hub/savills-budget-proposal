## ADDED Requirements

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
