## ADDED Requirements

### Requirement: The Review result sections fold
The sections "Ngân sách đã duyệt so với ngân sách năm mới do công cụ sinh" and "Đối chiếu tổng" of a Review run
SHALL each carry a button on their heading that folds the section to its heading and unfolds it again. Both SHALL
start open on first use; the browser SHALL remember each state across runs and reloads. Folding SHALL NOT change
any figure, request or saved value.

#### Scenario: Fold and reload
- **WHEN** the PM folds "Đối chiếu tổng" and reloads the page or opens another run
- **THEN** that section opens folded and "Ngân sách đã duyệt..." stays open

#### Scenario: Unfold
- **WHEN** the PM clicks the folded heading's button
- **THEN** the section's table is shown with the figures of the current run
