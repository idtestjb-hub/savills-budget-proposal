## ADDED Requirements

### Requirement: Unit labels inside a Vietnamese remark are Vietnamese

A consumption figure quoted in a Vietnamese remark (on `1. Summary` or a fund sheet's column T)
SHALL carry its unit in Vietnamese: "m3/tháng" for water, "kWh/tháng" for electricity, "lít/tháng"
for diesel. The unit's source data and the internal analysis workbook MAY keep their English units;
only the client-facing Vietnamese text changes.

#### Scenario: The water remark quotes monthly consumption

- **WHEN** the pipeline writes the water (EEW) remark
- **THEN** the consumption figure SHALL read in "m3/tháng", not "m3/month"

#### Scenario: The electricity and diesel remarks quote monthly consumption

- **WHEN** the pipeline writes the electricity (EEE) or diesel (EED) remark
- **THEN** the consumption figure SHALL read in "kWh/tháng" or "lít/tháng" respectively

#### Scenario: A remark still carrying an English unit fails verification

- **WHEN** verification runs and a composed energy narrative on `1. Summary` lacks its Vietnamese
  unit ("m3/tháng" for water, "kWh/tháng" for electricity, "lít/tháng" for diesel)
- **THEN** verification SHALL fail and name the narrative and the missing part
