## ADDED Requirements

### Requirement: "The costing specification" names the method catalogue together with the logic workbook

Throughout this capability, "the costing specification" SHALL mean the combination of the method
catalogue and `EXENSIVE LOGIC.xlsx`. Where both describe a code, the catalogue SHALL determine which
method is used and `EXENSIVE LOGIC.xlsx` SHALL supply the detailed formula where the two agree on the
method. Where only one describes a code, that one applies.

#### Scenario: The two sources disagree on method

- **WHEN** the catalogue and `EXENSIVE LOGIC.xlsx` state different methods for the same filled code
- **THEN** the pipeline SHALL use the catalogue's method
- **AND** the requirement "A filled cost code uses the method its spec states" SHALL be judged
  against the catalogue's method for that code

#### Scenario: The two sources agree and only the workbook carries the formula

- **WHEN** both name the same method for a code and `EXENSIVE LOGIC.xlsx` carries the coefficients,
  rounding or frequency
- **THEN** the pipeline SHALL apply that formula detail

#### Scenario: A code only one source covers

- **WHEN** a filled code appears in only one of the two sources
- **THEN** that source SHALL be the method authority for the code

### Requirement: A filled code's remark carries the components its catalogue entry requires

Where the catalogue lists the components a code's remark must contain, the generated remark for that
code SHALL contain each of them, and SHALL cite any legal reference the catalogue entry names. This
adds to, and does not replace, the existing requirement that the remark state the calculation.

#### Scenario: Listed components appear in the remark

- **WHEN** a code is written and its catalogue entry lists required remark components
- **THEN** the code's remark SHALL contain each listed component

#### Scenario: A required legal citation appears

- **WHEN** a code's catalogue entry names a legal reference the remark must cite
- **THEN** the code's remark SHALL include that reference

#### Scenario: A code with no catalogue entry

- **WHEN** a filled code has no catalogue entry
- **THEN** the existing requirement that its remark state the inputs, the method and the reference
  data SHALL still apply
- **AND** no additional component check SHALL be imposed
