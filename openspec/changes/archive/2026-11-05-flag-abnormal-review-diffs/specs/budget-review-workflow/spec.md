## ADDED Requirements

### Requirement: The Review flags an abnormal difference
For every compared line of a Review, the difference (the tool's figure minus the approved figure converted to the
deliverable's VAT basis, VND/year) SHALL be flagged *abnormal* when its absolute value is at least 50,000,000 VND/year
and its absolute percentage of the converted approved figure is at least 20%. A line whose approved figure is 0 (no
percentage) SHALL be flagged when the absolute difference alone is at least 50,000,000 VND/year. Group rows, section
totals and the fund summary SHALL NOT be flagged. The two thresholds SHALL be constants of `review.py`, stated on the
Review sheet (row 2) and in the page's guide. On the Review sheet an abnormal line SHALL have its "Chênh" and "%" cells
filled light red and its "Ghi chú" opening with "BẤT THƯỜNG"; row 3 SHALL state the number of abnormal lines.
`review_summary.json` SHALL carry `counts.abnormal`, the list `abnormal` of `{fund, code, diff, pct}` and `abnormal_rule`
`{pct, vnd}`; `review_summary.md` SHALL state the count. The rule reads no new file and moves no figure on the client
deliverable.

#### Scenario: Both thresholds reached
- **WHEN** ESS1 has approved 1,000,000,000 VND (converted) and tool 1,300,000,000 VND
- **THEN** the line is abnormal (+300,000,000 VND, +30%), its two difference cells are filled and its remark starts
  with "BẤT THƯỜNG"

#### Scenario: Large percentage, small amount
- **WHEN** ESM4 has approved 10,000,000 VND and tool 40,000,000 VND
- **THEN** the line is not abnormal (+30,000,000 VND is under 50,000,000 even though +300%)

#### Scenario: Large amount, small percentage
- **WHEN** RM.AP has approved 2,592,000,000 VND and tool 2,400,000,000 VND
- **THEN** the line is not abnormal (−7.4% is under 20% even though −192,000,000 VND)

#### Scenario: No approved figure
- **WHEN** RP2 has no approved figure and tool 50,000,000 VND
- **THEN** the line is abnormal (no percentage; the amount reaches the threshold)

#### Scenario: Zero-tool code
- **WHEN** ESS38 has approved 100,000,000 VND and tool 0
- **THEN** the line is abnormal (−100,000,000 VND, −100%) and still labelled "Chưa có phương pháp"
