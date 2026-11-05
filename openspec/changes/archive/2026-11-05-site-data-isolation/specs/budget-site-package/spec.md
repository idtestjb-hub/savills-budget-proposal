## ADDED Requirements

### Requirement: A site package carries only its own project's data and anonymised reference figures
The data folder of a site package SHALL contain only the reference files a Review run reads (the list `site_data.KEEP`,
15 files on 2026-11-05) and SHALL NOT contain any other file of the office `data\` folder. In those files every project
name other than the site's own and the names the code looks up (`site_data.code_names()`) SHALL be replaced by
"Dự án tham chiếu NN", the same code for the same name in every file; addresses, source file names and raw-text columns
SHALL be blank; figures SHALL be unchanged. A Review run inside the package SHALL give the same fund totals, ties and
top-10 differences as the same Review on the office data.

#### Scenario: Master list row of another project
- **WHEN** the office master list has "Tháp Mây Xanh, 12 Đường Lớn, Quận 1, NFA 50,000, rate 15,000" and the package is
  built for "Khu Thu Nghiem"
- **THEN** the package's master list has a row "Dự án tham chiếu 01" with blank address and street, District "Quận 1",
  NFA 50,000 and rate 15,000, and the location file names the same row "Dự án tham chiếu 01"

#### Scenario: Own project and coded names
- **WHEN** the master list also holds "KHU THU NGHIEM" and "A&K Tower"
- **THEN** both rows keep their names in the package

### Requirement: The package check scans for other projects' names
`build_site_package.py --check` (and `--check-only`) SHALL scan every text file and every Excel string of the package
outside the Python runtime for every name of the two master lists and every file-name stem of the scan store, minus the
site's own and the coded names and names shorter than 4 characters, and SHALL fail with the list of files and names when
any is found.

#### Scenario: A name slipped into a note
- **WHEN** a text file of the package mentions "tháp mây xanh" in lower case
- **THEN** the check reports that file with "Tháp Mây Xanh" and the build is not accepted
