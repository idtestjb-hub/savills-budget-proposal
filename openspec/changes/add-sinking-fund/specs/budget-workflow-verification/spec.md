## ADDED Requirements

### Requirement: Verification confirms the sinking fund

Verification SHALL check, on the standard new-project sample and on the Existing / Review sample:
- `1. Summary` rows 66–70 equal the sheet 3 totals they read;
- every priced sheet 3 line equals its reference median × driver, or the prior approved × CPI on a review;
- every warranty-month line outside the warranty list is 0, with its remark;
- every sheet 3 line left for the PM has a "Nhập số" `SF|` row;
- no code carries an amount on both sheet 2 and sheet 3;
- sheets 3 and 3.1 are visible exactly when they hold figures.

The baselines SHALL be re-recorded once for this change, with the sinking-fund movement measured and reported.

#### Scenario: Code on both funds

- **WHEN** a code has an amount on sheet 2 and on sheet 3
- **THEN** verification SHALL fail and name the code
