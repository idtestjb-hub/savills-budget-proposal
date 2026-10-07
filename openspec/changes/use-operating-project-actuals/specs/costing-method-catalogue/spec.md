## ADDED Requirements

### Requirement: A method that departs from the AI Guideline records who approved it

Where the catalogue records, for a code, a method different from the one the AI Guideline
instructs, that entry SHALL state four things:
- that it departs from the guideline;
- what the guideline itself says for the code;
- who approved the departure, and on what date;
- where the decision is recorded.

Verification's method-fidelity report SHALL treat an approved departure as the expected method for
that code. It SHALL report an entry that departs from the guideline without an approval record as a
mismatch.

The collect-on-behalf codes this change writes (`RO3.*` and `RO4.*`, and the expense lines paired
with them) SHALL each carry such an entry, together with the pairing between each revenue line and
its expense line. The entry SHALL keep the guideline's "not estimated" treatment, including its
remark, as the behaviour when no amount is entered. A project that enters no amount SHALL get the
same method-fidelity result and the same remarks as before this requirement.

This writes `Costing_Method_Catalogue.csv`: entries for the collect-on-behalf codes only. It moves
no recorded baseline figure.

#### Scenario: An approved departure is visible

- **WHEN** a reader opens the catalogue entry for `RO3.A`
- **THEN** the entry SHALL say that the guideline marks the line "not estimated"
- **AND** SHALL name the approver, the date and the decision record
- **AND** SHALL name the expense line paired with it

#### Scenario: A departure without approval is a mismatch

- **WHEN** a catalogue entry records a method different from the guideline's and carries no approval record
- **THEN** the method-fidelity report SHALL list that code as a mismatch

#### Scenario: A project with no amounts is judged as before

- **WHEN** verification runs on the standard synthetic project, which enters no collect-on-behalf
  amount, after the catalogue entries change
- **THEN** its method-fidelity figure and its remark assertions SHALL be the same as before

#### Scenario: Other entries are unchanged

- **WHEN** the catalogue is compared before and after this change
- **THEN** only the collect-on-behalf entries SHALL differ
