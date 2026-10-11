## ADDED Requirements

### Requirement: The new optional inputs are read by label with stated defaults

The pipeline SHALL read these inputs by label. A blank field, or a label absent from an older form, SHALL take the
default, and the remark that uses it SHALL say a default was used.

| Input | Default |
|---|---|
| Budget start month | January 2027 |
| Water customer group | business (`Kinh doanh`) for a new prospect; Existing mode keeps its own default |
| Contingency rate | 2% |
| ESI2 premium (USD per year) | 1,000 |
| USD exchange rate (VND per USD) | 26,190, the Vietcombank selling rate on 05/10/2026 |

A value of the wrong kind SHALL stop the run and name the field. Examples: a month that is not a month; a group other
than the two; a negative rate.

Data files read: the input workbook only. No recorded baseline moves through reading alone. The standard sample leaves
these fields blank, and the defaults' effects are stated under the capabilities that use them.

#### Scenario: An older form without the new labels

- **WHEN** the input workbook was built before these fields existed
- **THEN** every new input SHALL take its default, and the run SHALL NOT fail

#### Scenario: A wrong value

- **WHEN** the contingency rate is −1%
- **THEN** the run SHALL stop and name the contingency rate field
