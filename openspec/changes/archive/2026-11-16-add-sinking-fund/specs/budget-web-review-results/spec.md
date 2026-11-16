## ADDED Requirements

### Requirement: The Review page shows a sinking-fund comparison table

The Review results SHALL include a folded section "Quỹ bảo trì". It SHALL have one row per sinking-fund code that
carries a figure on either side. The columns SHALL be:
- code and item;
- prior approved;
- the tool's new year;
- the median reference (VND per year for this project's NFA or lifts, blank when the code has none);
- the difference and the difference in %.

Rows in the warranty or left for the PM SHALL be tagged. The section SHALL show the fund totals. A Review whose file
has no sinking fund SHALL show the section with the line "file không có quỹ bảo trì".

#### Scenario: Line far from the median

- **WHEN** a code's new year is more than twice its median reference
- **THEN** the row SHALL be tagged "cao hơn trung vị"
