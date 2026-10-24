## ADDED Requirements

### Requirement: A store file without its own fee-paying NFA takes a checked NFA

The per-file NFA table records, for a store file id, the fee-paying NFA (and, when known, the apartment NFA) that
the file states outside its info sheet, with the sheet and cell it came from and the user's approval. An approved
row SHALL be used for that file whether or not its profile has an NFA, because it is a reviewed correction (added
2026-10-22 during apply: one profile sums a tower's sub-rows twice). When a file has no approved row and its
profile has no fee-paying NFA, the build step SHALL take one from the master list of residential properties, when
the project name matches after removing accents, case, spaces and punctuation, and the match is unique.

An NFA from either source SHALL be used only when the fee rate it implies is within 15% of a reference rate. The
implied rate is the file's management-fee revenue per month on its main sheet (all `RM.*` lines, excluding VAT)
divided by the NFA. The reference rate is the master list's management-fee rate, taken out of VAT at the budget
year's rate when the master list marks it as including VAT, or the rate written in the file and recorded in the
per-file table. A file whose main sheet carries no management-fee revenue SHALL pass the check only through the
per-file table, with the user's approval recorded there.

A file that fails the check, or matches no name or more than one, SHALL stay out. The README SHALL list it by store
id with the reason, and SHALL count the files whose NFA came from each source. The master list gives no apartment
NFA, so a file whose NFA came from the master list SHALL be left out for `RM.AP` unless the per-file table gives its
apartment NFA.

Data files read: `Budget_Agent/data/master_list_verified/Dim_Property_Residential.csv`; the per-file NFA table in
`Savills-local`, beside the store.

#### Scenario: A master-list NFA that passes the check

- **WHEN** a 2026 file has no NFA, its main sheet carries 1,061.8 M VND of management-fee revenue per month excluding
  VAT, and the master list gives the same project an NFA of 61,987.75 m² at 18,500 VND per m² including VAT
- **THEN** the implied rate SHALL be 17,130 VND per m², the reference 18,500 ÷ 1.08 = 17,130 VND per m², and the file
  SHALL enter with an NFA of 61,987.75 m²

#### Scenario: A master-list NFA that fails the check

- **WHEN** a file's management-fee revenue gives 35,014 VND per m² on the master list's NFA of 54,624 m², and the
  master list's rate is 18,000 VND per m²
- **THEN** the file SHALL stay out, and the README SHALL give its store id with "NFA master lệch đơn giá"

#### Scenario: A table row corrects a profile NFA

- **WHEN** a file's profile gives 194,474.9 m² because it summed a tower's sub-rows twice, and an approved table row
  gives 97,237.5 m²
- **THEN** the file SHALL use 97,237.5 m², after the fee check, and the README SHALL say the NFA came from the table

#### Scenario: An NFA the file states outside its info sheet

- **WHEN** the per-file table gives a file 20,944.7 m² (apartments, retail and shophouse, without the developer's
  parking) and 18,641 m² of apartments, approved by the user
- **THEN** the file SHALL enter with a fee-paying NFA of 20,944.7 m² and an apartment NFA of 18,641 m²

### Requirement: An old-form main sheet without PL rows ties on its R and E rows

A main operating-fund sheet that has its R and E total rows but no `PL2` row (the old form has no D section; it may
have `PL1`) SHALL be tied on R and E alone, its E section ending at `PL1` or, without one, after its last coded row, with the tie and explanation rules that apply to every other sheet. It SHALL count as tying when both sums
equal the cached R and E cells to within 1 VND, or when every gap is traced to the row that causes it and explained
with a Vietnamese note. Otherwise the sheet SHALL count as not tying, and the file SHALL stay out.

#### Scenario: An old form that ties

- **WHEN** a 2021 sheet with `PL1` but no `PL2` has leaf sums equal to its R and E cells, its `EM#` and `ES#` lines
  counted as leaves as on the standard form
- **THEN** the sheet SHALL tie, and the file SHALL enter like any file whose sheet ties directly

#### Scenario: An old form with an unexplained gap

- **WHEN** a 2021 sheet's R ties but its E leaf sum is 5,000,000 VND below the E cell, and no row explains the gap
- **THEN** the file SHALL stay out, and the README SHALL give its store id with the gap

### Requirement: A budget on another form enters through an approved code map

A store file whose main budget sheet uses its own item numbers or item labels instead of Savills codes SHALL be read
through a code map: one row per item label of that form, giving the Savills code it maps to, or none when the item
is not a line the store reads. A code map SHALL be used only after the user has approved it, and the store SHALL
record which map, at which approval date, each such file was read with. The sheet SHALL then be tied and used under
the same rules as a sheet with Savills codes. An item of the sheet that has an amount above 0 and is missing from
the map SHALL stop that file, so that a new label is never dropped silently.

The code maps SHALL stay in `Savills-local` with the store.

#### Scenario: A departmental-form budget

- **WHEN** a departmental budget lists "MO fee from Residences" under item `A1` and the approved map gives `RM.A` for
  that label
- **THEN** the line SHALL be read as `RM.A`, and the file's values SHALL be written like those of a Savills-form file

#### Scenario: A label the map does not know

- **WHEN** a departmental budget carries an item with an amount above 0 whose label is not in the approved map
- **THEN** the file SHALL stay out, and the build log SHALL name the label
