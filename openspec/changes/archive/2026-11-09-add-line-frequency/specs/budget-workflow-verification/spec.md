## ADDED Requirements

### Requirement: Verification confirms the form's frequency checks

`verification/verify.py` SHALL fail when, after Excel recalculates a generated deliverable, any written line of either
fund sheet has a non-zero number-of-times check (column U) or a FALSE total check (column V), or a frequency outside
the form's six. It SHALL also exercise sheet `4. Điều chỉnh` on one fixture with one code set to each of Quarterly, Half
a Year, Yearly, Optional and Schedule, and confirm that each code's fund row, its new amount and `1. Summary` follow
the rule of requirement "The frequency of a budget code is set on its total row". Annual baseline figures SHALL NOT
move from the defaults alone; per-time prices and month figures of the defaulted lines SHALL be re-recorded once, after
the user signs off the before/after.

#### Scenario: A broken months check
- **WHEN** a Quarterly line is written with only three months of payment
- **THEN** verify SHALL fail and name the code, the sheet and the U value

#### Scenario: Each frequency through sheet 4
- **WHEN** verify runs on the standard sample
- **THEN** it SHALL report the five frequency edits as passing, each with its new amount in VND
