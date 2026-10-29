# budget-web-adjust-table Specification

## Purpose
How the Budget web's adjust table stays readable on a normal screen: the unit column, the pinned code and item columns
and header, the toggles that hide the prior-year and Remark column groups (remembered on the PC), and full screen.

## Requirements

### Requirement: The adjust table shows the unit and keeps its code in sight

The web adjust table SHALL show, on each code row after Hạng mục, a column ĐVT: the unit of the code's detail rows when
they share one, "nhiều" with the units listed on hover when they differ, blank when the code has no detail row. The
year N-1 column headers SHALL be short and wrap (Duyệt <year>, Thực tế <period>, Dự kiến <year>) with the full label on
hover. The selection box, the +/- button, Mã and Hạng mục SHALL stay visible on the left while the table scrolls
sideways, and the header row SHALL stay visible while it scrolls down; the table SHALL scroll inside a box no taller
than the window so its horizontal scrollbar is on screen. No figure, saved value or file SHALL change.

#### Scenario: A code with several units
- **WHEN** a code's detail rows are in "người" and "vị trí"
- **THEN** its ĐVT cell SHALL read "nhiều" and list both units on hover

#### Scenario: Scrolling to the right
- **WHEN** the PM scrolls the table to the Remark column
- **THEN** Mã and Hạng mục of every row SHALL still be visible on the left

### Requirement: The PM can hide column groups and open the table full screen

The page SHALL offer buttons to hide or show the year N-1 columns and the Remark column; the choice SHALL be remembered
in the browser of that PC. A full-screen button SHALL open the adjust table and its tools over the whole window; Esc or
the same button SHALL close it. Hidden columns SHALL keep their values: hiding Remark SHALL NOT clear or skip a remark
when saving.

#### Scenario: Remark hidden, then saved
- **WHEN** the PM types a remark, hides the Remark column and saves
- **THEN** the remark SHALL be saved as if the column were shown

#### Scenario: Full screen
- **WHEN** the PM presses the full-screen button and then Esc
- **THEN** the table SHALL fill the window and then return to its place on the page with its edits kept

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
