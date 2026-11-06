## MODIFIED Requirements

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
