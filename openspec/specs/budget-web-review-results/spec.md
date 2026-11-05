# budget-web-review-results Specification

## Purpose
What the Budget web's Review results block shows for a Review run: the counts line and the list of the ten
largest differences, with the abnormal-difference flags the Review computed. The page reads only the run's
`review_summary.json`; it writes no data file and moves no recorded baseline figure.

## Requirements

### Requirement: The Review page shows the abnormal count and tags the top list
The counts line of a Review run SHALL state the number of abnormal lines with the rule in brackets, and each line of "10
dòng lệch lớn nhất" that the Review flagged SHALL carry the tag "Bất thường" after its code. A run recorded before the
rule SHALL show the counts line without the abnormal count and the top list without tags.

#### Scenario: Counts and tags
- **WHEN** a Review run flagged 12 lines and 9 of the top 10 are among them
- **THEN** the counts line ends with "bất thường (≥20% và ≥50 triệu/năm): 12" and 9 rows of the top table carry the tag
