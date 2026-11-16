# budget-site-package Specification

## Purpose
What a per-site package built by `build_site_package.py` carries in its data folder and what its check scans for,
so a package handed to one project's PM holds only that project's data and anonymised reference figures. The build
reads the office `data\` folder and the scan store's file list and writes only into the package; every figure is
unchanged and no recorded baseline figure moves.

## Requirements

### Requirement: A site package carries only its own project's data and anonymised reference figures
The data folder of a site package SHALL contain only the reference files a Review run reads (the list `site_data.KEEP`,
the reference-project registry included) and SHALL NOT contain any other file of the office `data\` folder. In those
files every project name other than the site's own SHALL be replaced by "Dự án tham chiếu NN", the same code for the
same name in every file, the reference budgets the tool prices from included; addresses, source file names and
raw-text columns SHALL be blank; keys and figures SHALL be unchanged. A Review run inside the package SHALL give the
same fund totals, ties and top-10 differences as the same Review on the office data. The build reads the office data
folder and writes only into the package; no recorded baseline figure moves.

#### Scenario: Master list row of another project
- **WHEN** the office master list has "Tháp Mây Xanh, 12 Đường Lớn, Quận 1, NFA 50,000, rate 15,000" and the package is
  built for "Khu Thu Nghiem"
- **THEN** the package's master list has a row "Dự án tham chiếu 01" with blank address and street, District "Quận 1",
  NFA 50,000 and rate 15,000, and the location file names the same row "Dự án tham chiếu 01"

#### Scenario: Own project and coded names
- **WHEN** the master list also holds "KHU THU NGHIEM" (the site) and the utilities base "Tháp Thử Nghiệm" (registry
  key `R02`)
- **THEN** "KHU THU NGHIEM" keeps its name; "Tháp Thử Nghiệm" reads "Dự án tham chiếu NN" in the master list, the
  registry and the utility cost file alike, its key `R02` and its figures are unchanged, and the package's Review prices
  utilities exactly as the office run does

### Requirement: The package check scans for other projects' names
`build_site_package.py --check` (and `--check-only`) SHALL scan every text file and every Excel string of the package
outside the Python runtime for every name of the two master lists, every display name and name variant of the
reference-project registry and every file-name stem of the scan store, minus the site's own name and names shorter than
4 characters, and SHALL fail with the list of files and names when any is found. No name is exempt because code looks
it up.

#### Scenario: A name slipped into a note
- **WHEN** a text file of the package mentions "tháp mây xanh" in lower case
- **THEN** the check reports that file with "Tháp Mây Xanh" and the build is not accepted

#### Scenario: A reference budget's name in the package
- **WHEN** the internal analysis template inside the package still says "Tháp Thử Nghiệm"
- **THEN** the check reports that file with "Tháp Thử Nghiệm" and the build is not accepted

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

### Requirement: The package carries the anonymous sinking-fund reference

A site package SHALL carry the anonymous sinking-fund reference file, so a site run prices sheet 3 as the office
does. The package check SHALL scan that file for other projects' names as it scans every other data file. A site run
and an office run of the same input SHALL give the same sheet 3.

#### Scenario: Package build

- **WHEN** a site package is built
- **THEN** the sinking-fund reference file SHALL be in the package
- **AND** the leak check SHALL pass on it
