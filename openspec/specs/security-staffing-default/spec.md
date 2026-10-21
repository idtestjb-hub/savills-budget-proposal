# security-staffing-default Specification

## Purpose

Sizes the 24-hour security posts from the total fee-paying NFA and a Roster Setup ratio (default 1.7 posts per 10,000 m², the median of real Savills projects), never below the gate posts plus one CCTV post, with the posts above that floor as patrol on three shifts (change `size-security-from-fee-nfa`, signed off 2026-10-20).

## Requirements

### Requirement: Security posts are sized from fee-paying NFA, with the gates as the floor

When the security patrol rows of `Staffing Demand` hold their seeded formula, or are blank or zero, the tool SHALL
size the security 24-hour posts as max(ROUNDUP(total fee-paying NFA ÷ 10,000 × ratio), gate posts + 1), where the
ratio is the Roster Setup field `Security: 24h Posts per 10,000 m² Fee-paying NFA` and the gate posts are
ROUNDUP(Gate Count × Staff per Gate). The gate and CCTV rows SHALL stay as before. Each of the three patrol shift rows
SHALL be the total minus the gate posts minus 1, at least 0. The open-space area SHALL NOT change the security count.
A number the PM typed on a security row SHALL be used as typed.

#### Scenario: A large project
- **WHEN** a project has 101,948 m² of fee-paying NFA, 1 gate, Staff per Gate 1 and the default ratio
- **THEN** the posts SHALL be 18, and each patrol shift row SHALL be 16

#### Scenario: The gates are the floor
- **WHEN** a project has 10,000 m² of fee-paying NFA and 3 gates
- **THEN** the posts SHALL be 4 (3 gate posts and the CCTV room), and the patrol rows SHALL be 0

#### Scenario: Open space does not count
- **WHEN** two projects differ only in `Circulation / Hardscape Area`
- **THEN** their security rows SHALL be equal

### Requirement: The ratio defaults to 1.7 and says where the default came from

The input form SHALL carry `Security: 24h Posts per 10,000 m² Fee-paying NFA` in Roster Setup row 5, filled with 1.7,
with a note that it is the median of the form-read real Savills projects in the service-level table (rounded) and sits
in the Tiêu chuẩn band. When the field is blank, zero or not on the form, the tool SHALL use 1.7, and the row's basis
SHALL say that the standard default was used. The label `Security: m² Open Space per Patrol Staff` of older forms SHALL
NOT be read as this ratio.

#### Scenario: An older form
- **WHEN** a form made before this change is run, with one `Security - Patrol / Open Space` row on the morning shift
- **THEN** the run SHALL use 1.7, add the afternoon and night patrol rows, and price the same posts as a new form

### Requirement: The new form has three patrol shift rows

The form builder SHALL write `Security - Patrol (Morning)`, `Security - Patrol (Afternoon)` and
`Security - Patrol (Night)` on Staffing Demand, each with the formula
`MAX(0, ROUNDUP(fee-paying NFA ÷ 10,000 × ratio) − ROUNDUP(Gate Count × Staff per Gate) − 1)`.

#### Scenario: The formula and the rule agree
- **WHEN** the built form is read back
- **THEN** each patrol row's value SHALL equal the Python rule for the same Project Info and Roster Setup
