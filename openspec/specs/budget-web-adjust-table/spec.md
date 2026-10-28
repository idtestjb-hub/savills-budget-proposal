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
