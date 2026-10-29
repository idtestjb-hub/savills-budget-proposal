## ADDED Requirements

### Requirement: The adjust table is grouped as on the 2027 form
Within Thu and Chi, the adjust table SHALL list the codes by fund (MF before CA) and template row, nested in every
level of the form's groups as the Review sheet nests them (`review_import.group_chain`); a code not on the form SHALL
sit in a group "Mã ngoài form 2027". Each group SHALL have a row "Cộng <mã> · <tên>" above its codes whose money
columns equal the sum of the codes of that group shown on the table, refreshed while the PM edits. A group row SHALL
fold and unfold its codes and subgroups; all groups start open. Grouping SHALL NOT change any saved value.

#### Scenario: Subtotals tie
- **WHEN** a Review run's adjust table is shown
- **THEN** each "Cộng" row equals the sum of its direct subgroups and codes, and the Chi row equals the sum of its top-level groups

#### Scenario: Fold a group
- **WHEN** the PM folds "Cộng EM"
- **THEN** its codes and subgroups are hidden, its own row and figures stay, and unfolding shows them again

#### Scenario: Edit updates the group
- **WHEN** the PM sets an inflation of 10% on a code of group ESS
- **THEN** the "Cộng ESS" row's new amount and difference grow by that code's change without reloading
