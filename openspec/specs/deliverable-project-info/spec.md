# deliverable-project-info Specification

## Purpose
Shows every project fact a budget was built from (scale, address, amenities, parking) on the deliverable's `0. Info`,
each with its unit and source, so the PM and the client see the basis of the lines costed from those facts and which
facts are still blank for the PM.

## Requirements

### Requirement: 0. Info lists every project fact with its source
Every deliverable, new project or Review, SHALL carry a block titled "QUY MÔ DỰ ÁN / PROJECT SCALE" on `0. Info`
starting at row 23, below the standard fee table. The block SHALL list one row per fact, with columns for the label
(Vietnamese / English), the value, the unit and the source (`Nguồn`):
- City / Province, District, Street Address;
- Site Area, Garden / Landscape Area, Circulation / Hardscape Area;
- Tower Count, Floor Count, Gate / Entrance Count, Passenger Elevators per Tower, Number of Basements;
- Has Swimming Pool?, Number of Pools, Pool Area, Pool Volume;
- Car Parking Slots, Moto Parking Slots;
- the units and NFA of every product with an area;
- the project mode and, for an existing project, the prior budget year.

The standard fee table, rows 6–21, SHALL keep its layout and formulas.

#### Scenario: Review run with facts from three sources
- **WHEN** a Review run takes the city from the page, the car slots from the approved file and the gate count from
  the master list
- **THEN** the block SHALL show each of these values with source "nhập trên trang web", "file ngân sách đã duyệt" and
  "danh sách master" respectively

#### Scenario: A blank fact is flagged, not dropped
- **WHEN** the run has no value for Number of Basements
- **THEN** the block SHALL still show the row, with the value cell blank and the source cell "Chưa có số — PM nhập",
  shaded like the other PM-filled cells

#### Scenario: New project from a filled form
- **WHEN** a new project runs from a filled input form
- **THEN** every fact the form holds SHALL appear in the block with source "form nhập liệu"

### Requirement: The parking rows of the fee table are filled
The deliverable SHALL write the car slots into F15 (car park owned by the developer) or F16 (owned in common). It SHALL
follow the row the approved file used. When there is no approved file, it SHALL use F16. It SHALL write the motorbike
slots into F18. It SHALL write the applied parking prices (VND per vehicle per month, the same figures as the parking
revenue lines) into I15 or I16 and I18. It SHALL NOT write the car slots into F12.

#### Scenario: Approved file puts car slots on the developer row
- **WHEN** the approved file's `0. Info` has the car slots on "Bãi xe ô tô thuộc Sở hữu riêng của CĐT"
- **THEN** the deliverable SHALL put the car slots and the car price on row 15 and leave row 16 blank

#### Scenario: New project
- **WHEN** a new project has 300 car slots and 2,000 motorbike slots
- **THEN** F16 SHALL be 300, F18 SHALL be 2,000, and F12 SHALL be blank

### Requirement: Each run records where every fact came from
The input form a run uses SHALL carry a `Fact Sources` sheet with one row per fact: label, value, source. The
generator SHALL read the source column from that sheet when it exists. When the sheet is absent, as on a form the PM
filled by hand, the source SHALL be "form nhập liệu".

#### Scenario: Old form without the sheet
- **WHEN** a run uses an input form saved before this change
- **THEN** the run SHALL complete and every non-blank fact SHALL show source "form nhập liệu"

### Requirement: Notes on 0. Info are Vietnamese
The note naming products that have no row in the standard fee table, at G7, SHALL be written in Vietnamese.

#### Scenario: Shopping Mall project
- **WHEN** a project has a Shopping Mall area
- **THEN** G7 SHALL read in Vietnamese that Shopping Mall is priced but has no row in this table, and SHALL point to
  row 21 and `2. Budget-Management Fund`
