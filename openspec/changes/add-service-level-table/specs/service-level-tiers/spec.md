## Purpose

Tells a PM whether the cleaning and security crews the tool proposes are lean, standard or generous next to real Savills projects. It keeps fixed, editable thresholds and an anonymous table of real projects, and shows the result on an internal sheet without moving any figure.

## ADDED Requirements

### Requirement: Thresholds live in a small editable data table

The thresholds SHALL be stored in one data table, one row per service, so they can be changed without changing code. Each row SHALL hold: the service; the measure and its unit; the two cut-off values; the direction (which end of the measure is the higher level); the two sanity bounds; the date the values were approved; and the source.

The approved values SHALL be:

| Service | Measure | Cut-offs | Levels | Sanity bounds |
|---|---|---|---|---|
| Cleaning | m² of fee-paying NFA per cleaner | 2,500 and 4,000 | below 2,500 = Nâng cao; 2,500 to below 4,000 = Tiêu chuẩn; 4,000 or more = Cơ bản | 1,000 and 8,000 |
| Security | 24-hour-equivalent posts per 10,000 m² of fee-paying NFA | 1.5 and 3.0 | below 1.5 = Cơ bản; 1.5 to below 3.0 = Tiêu chuẩn; 3.0 or more = Nâng cao | 0.5 and 8 |
| Landscape | none | not set | not classified | none |

A value exactly on a cut-off SHALL fall in the higher-numbered band of the table above (2,500 is Tiêu chuẩn for cleaning; 4,000 is Cơ bản; 1.5 is Tiêu chuẩn for security; 3.0 is Nâng cao).

The thresholds and bounds SHALL NOT be recomputed from data when data is added. Changing one is a decision that needs its own approval and a new approval date in the table. The table SHALL record 2026-10-16 as the approval date of the cut-offs and 2026-10-18 for the security upper cut-off (revised from 2.5) and the sanity bounds.

Data files read: none. Data files written: `Budget_Agent/data/service_levels/Ref_ServiceLevelThresholds.csv`.

#### Scenario: A threshold is edited without code

- **WHEN** a cut-off value in the threshold table is changed
- **THEN** the next run SHALL classify with the new value and the code SHALL be unchanged

#### Scenario: A value on a cut-off

- **WHEN** a project has exactly 4,000 m² per cleaner
- **THEN** its cleaning level SHALL be Cơ bản

#### Scenario: The security upper cut-off

- **WHEN** a project has 2.9 posts per 10,000 m² and another has exactly 3.0
- **THEN** the first SHALL be Tiêu chuẩn and the second Nâng cao

#### Scenario: Landscape has no threshold

- **WHEN** the threshold table is read
- **THEN** the landscape row SHALL be present and marked as not set, and no landscape level SHALL be produced anywhere

### Requirement: A service level is classified from fee-paying NFA and the headcount

For cleaning, the measure SHALL be the project's fee-paying NFA in m² divided by the number of cleaning positions. For security, the measure SHALL be the number of security positions, each counted as its hours of coverage divided by 24, divided by the fee-paying NFA in units of 10,000 m².

Cleaning and security SHALL each get their own level. The two levels SHALL NOT be merged into one label, average or minimum.

A project SHALL be marked "chưa phân loại" for a service, with the reason, when:
- its fee-paying NFA is missing or zero ("thiếu NFA");
- the headcount for that service is missing or zero ("thiếu số người");
- the measure cannot be computed; or
- the measure lies outside the service's sanity bounds ("ngoài cận, nghi đọc sai").

A guess SHALL NOT be made to fill any of these. A value outside the bounds SHALL stay in the table with its measure and SHALL NOT receive a level.

A measure within 10% of either cut-off (cut-off × 0.9 up to but excluding cut-off × 1.1) SHALL carry the mark "sát ngưỡng" beside its level. The mark SHALL NOT change the level.

#### Scenario: Cleaning level from the thresholds

- **WHEN** a project has 60,000 m² of fee-paying NFA and 20 cleaning positions
- **THEN** its measure SHALL be 3,000 m² per cleaner and its cleaning level SHALL be Tiêu chuẩn, with no "sát ngưỡng" mark

#### Scenario: Security counted in 24-hour equivalents

- **WHEN** a project has 100,000 m² of fee-paying NFA, 10 security positions of 24 hours and 10 positions of 12 hours
- **THEN** its security posts SHALL be 15 and its measure SHALL be 1.5 per 10,000 m², so its security level SHALL be Tiêu chuẩn with the mark "sát ngưỡng"

#### Scenario: Near a cut-off

- **WHEN** a project has 2,400 m² per cleaner
- **THEN** its cleaning level SHALL be Nâng cao with the mark "sát ngưỡng"

#### Scenario: No fee-paying area

- **WHEN** a project has no fee-paying NFA
- **THEN** both services SHALL show "chưa phân loại" with the reason "thiếu NFA"

#### Scenario: Suspected misread

- **WHEN** a security measure is 0.08 posts per 10,000 m²
- **THEN** the project SHALL show "chưa phân loại: ngoài cận, nghi đọc sai" for security, the value 0.08 SHALL stay in the table, and no security level SHALL be given

### Requirement: Real projects are held in a separate anonymous service-level table

A build step SHALL read the real-budget scan store and write one data table with one row per project. Each row SHALL hold: an anonymous project id; the budget year; fee-paying NFA; for each of cleaning and security, the headcount measure, its level or "chưa phân loại" with the reason, its source and its "sát ngưỡng" mark; and any flag.

The source of each measure SHALL be marked "form" when the headcount was read from the project's own staffing form in the budget, and "chi phí" when it was inferred from the service's cost. Both SHALL be kept and marked. The inferred ones SHALL NOT be shown as if they were read.

The store SHALL be read under the approved scan rules: one file per project, the latest budget year; a file with no project name counts as its own project; no scanned PDF, no converted xlsb, no content duplicate. In addition, two files whose fee-paying NFA is identical to the square metre SHALL be treated as one project even when their names differ; the latest budget year SHALL win and, on a tie, the later file date.

The table SHALL carry no project name, file name, address or other identifying text. It SHALL be written under `Budget_Agent/data/`, outside the code folder pushed to GitHub. The store and the name-to-id map SHALL stay in `Savills-local`.

Data files read: the scan store in `Savills-local` (build step only). Data files written: `Budget_Agent/data/service_levels/Ref_ServiceLevelProjects.csv`.

#### Scenario: A project with two budget years

- **WHEN** the store holds a project's 2025 and 2026 budgets
- **THEN** only the 2026 file SHALL give that project's row

#### Scenario: Two names, one NFA

- **WHEN** two files carry different project names but the same fee-paying NFA to the square metre
- **THEN** the table SHALL hold one row for them, from the later file

#### Scenario: Form and inferred headcount

- **WHEN** a project's cleaning headcount was inferred from cost
- **THEN** its cleaning source SHALL read "chi phí", not "form"

#### Scenario: The table is anonymous

- **WHEN** the table is written
- **THEN** none of the store's project names or file names SHALL appear in it

#### Scenario: Regression check against the 2026-10-18 result

- **WHEN** the build runs on the scan store as it stood on 2026-10-07 (48 projects after the identical-NFA rule, 41 with NFA)
- **THEN** cleaning SHALL give 13 Nâng cao, 18 Tiêu chuẩn and 10 Cơ bản, and security SHALL give 9 Nâng cao, 19 Tiêu chuẩn, 12 Cơ bản and 1 "chưa phân loại: ngoài cận, nghi đọc sai". This is a regression check on the data the thresholds were read from, not a validation of the thresholds.

### Requirement: The internal analysis shows the tool's own service levels

The internal analysis workbook SHALL carry a sheet `Service Levels`. For the project being budgeted it SHALL show, for cleaning and security separately:
- the headcount the tool has just costed (equal to the roster) and the fee-paying NFA used;
- the measure, the level or "chưa phân loại" with the reason, the "sát ngưỡng" mark when it applies, and the thresholds applied;
- where the measure sits among the real projects of the same service: its percentile and the number of projects compared.

The comparison set for the percentile SHALL hold only real projects whose headcount for that service was read from a form and which have a level (not "chưa phân loại"). The number of projects with inferred headcount SHALL be shown beside it for reference and SHALL NOT enter the percentile. Each real project SHALL be counted only once, and the project being budgeted SHALL NOT be counted among its own comparison.

The sheet SHALL state in Vietnamese that the level is shown for information and changes no figure, that the area used is the fee-paying NFA and not the area to be cleaned, that the thresholds are round values read off the real projects and not an outside standard, that the comparison uses form-read projects only, and what "sát ngưỡng" means.

Landscape SHALL appear with "chưa đặt ngưỡng: thiếu diện tích cây xanh".

The sheet SHALL read the thresholds and the real-project table from their data files. It SHALL NOT change the client deliverable, the roster or any other sheet's figures.

Data files read: `Ref_ServiceLevelThresholds.csv`, `Ref_ServiceLevelProjects.csv`. Recorded baseline figures moving: none.

#### Scenario: A standard project

- **WHEN** a budget is generated for a project with 60,000 m² of fee-paying NFA and 20 costed cleaners
- **THEN** the `Service Levels` sheet SHALL show 3,000 m² per cleaner, Tiêu chuẩn, and the percentile among the form-read real projects with the count compared

#### Scenario: Inferred rows stay out of the percentile

- **WHEN** the real-project table holds 23 form-read and 18 inferred cleaning rows with a level
- **THEN** the cleaning percentile SHALL be computed over the 23 and the sheet SHALL show 18 as the inferred count for reference

#### Scenario: Headcount ties to the roster

- **WHEN** the sheet is written
- **THEN** its cleaning and security headcount SHALL equal the number of those positions on the roster

#### Scenario: Figures do not move

- **WHEN** the sheet is added to the workbook
- **THEN** every figure on the client deliverable and every existing sheet SHALL equal its value before the change

#### Scenario: Project with no fee-paying NFA

- **WHEN** the input has no fee-paying NFA
- **THEN** the sheet SHALL show "chưa phân loại" and the reason, and the run SHALL still complete
