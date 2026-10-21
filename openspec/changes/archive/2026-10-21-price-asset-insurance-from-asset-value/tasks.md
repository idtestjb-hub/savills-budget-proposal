Rules decided by the user on 2026-10-19 (group I of the M3 deviation list). Measurements and logs go to
`Savills-local\budget-test\2026-10-19-laneC-esi1\`. Real project names stay in `Savills-local`.

## 1. Build

- [x] 1.1 `generate_project_budget.py`, verified with unit tests:
  - the labels and `_resolve_esi1`;
  - the read in `read_input`;
  - `_write_asset_insurance`, and the one-line call in `fill_management_fund_sheet`.
- [x] 1.2 `build_project_input_form.py`: `add_asset_insurance_fields`, a section appended below every other section
  of Project Info (fixed rows 57-62 are overwritten by the Existing and Operating sections), with notes and validation.
- [x] 1.3 Run the full test suite and `verify.py` with the baseline gates open. Verify: all pass.
  - Done 2026-10-19: 927 passed, 1 xfailed; verify (gates open) PASS, the same 13/6/0/12 baseline differences as before.

## 2. Measure and sign off

- [x] 2.1 A/B on the fixtures (unchanged; plus one with an invented value) and on the four real M3 projects. Masteri
  gets the value and rate stated in its own budget's ESI1 remark; the other three are left blank unless the user gives
  a value. Verify: only ESI1, the fund totals that include it, and ES# move.
  - Done 2026-10-19, before `2156f77`: the four fixtures and the five M3 runs without a value do not move. The invented
    20,000,000,000 VND value moves ESI1 0 to 11,000,004, ES# +220,008, RI1 +58,281. The M3 project with its own stated
    sum insured and 0.0375% gets ESI1 2,766,642,360 VND incl. VAT (its budget: 2,766,642,362); ES# +55.3m, RI1 +27.6m.
    Logs in `Savills-local/budget-test/2026-10-19-laneC-esi1/`.
- [x] 2.2 The user signs off the measured movement.
  - Signed off 2026-10-19 by the user, the 1% rate guard included, with the instruction to commit.
