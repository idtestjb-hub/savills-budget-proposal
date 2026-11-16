## ADDED Requirements

### Requirement: The package carries the anonymous sinking-fund reference

A site package SHALL carry the anonymous sinking-fund reference file, so a site run prices sheet 3 as the office
does. The package check SHALL scan that file for other projects' names as it scans every other data file. A site run
and an office run of the same input SHALL give the same sheet 3.

#### Scenario: Package build

- **WHEN** a site package is built
- **THEN** the sinking-fund reference file SHALL be in the package
- **AND** the leak check SHALL pass on it
