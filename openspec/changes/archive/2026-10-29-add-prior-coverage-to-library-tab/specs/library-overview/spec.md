## ADDED Requirements

### Requirement: The Review view shows N-1 column coverage measured by the Review reader
The "Dùng cho Review" view of the "Kho ngân sách" tab SHALL show, per store budget year and in total, the number of
selectable files, the number the Review reader read, the number with a kept Management Fund column of each kind of year
N-1 (Duyệt, Thực tế, Dự kiến) with how many of those tie, and the number with all three. The counts SHALL come from
`prior_coverage.csv` in the store folder, written by `build_prior_coverage.py` with `review_import.read_prior_budget`
and the store's project names, so that a file counts exactly when a Review run of that file would show the column. The
view SHALL show the measurement date. When the file is missing, unreadable, or lacks a selectable file of the store,
the block SHALL show a reason instead of counts. The block and the endpoint stay aggregates only.

#### Scenario: Counts tie to the coverage file
- **WHEN** `prior_coverage.csv` lists every selectable file
- **THEN** each year row and the total row of the block equal the counts of that file for the same files, and the
  selectable count equals the view's "chọn được" count

#### Scenario: Coverage file missing or stale
- **WHEN** the file is absent, or a selectable file of the store has no row in it
- **THEN** `prior.available` is false with a reason, and no coverage counts are shown

#### Scenario: Unreadable file
- **WHEN** the Review reader stops on a selectable file
- **THEN** that file counts as selectable but not read, and the file stores only the exception class, not its message

#### Scenario: No names
- **WHEN** the endpoint answers with the `prior` block
- **THEN** no string in the response equals or contains a store file name, project name or path
