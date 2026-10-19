Rules decided by the user on 2026-10-19 (group G of the M3 deviation list). Measurements and logs go to
`Savills-local\budget-test\2026-10-19-laneC-villa\`. Real project names stay in `Savills-local`.

## 1. Build

- [x] 1.1 `generate_project_budget.py`, verified with unit tests:
  - the `read_input` gate (total NFA above 0);
  - `_apartment_column_weight`;
  - `_fill_product_mix_fallbacks` (BG10/BG9, parking sheet D6 and 0-bay rows), called after `fill_management_fund_sheet`;
  - the A2-A4 basis in `_fill_service_post_sheet`;
  - `_parking_allocation_weights` (the moved block, with the nominal BM11);
  - the `RM` narrative skip.
- [x] 1.2 `verification/fixtures/build_villa_fixture.py`: an invented villa-only, 0-bay form built from the standard
  sample.
- [x] 1.3 Run the full test suite and `verify.py` with the baseline gates open. Verify: all pass.
  - Done 2026-10-19: 915 passed, 1 xfailed; verify (gates open) PASS, the same 13/6/0/12 baseline differences as `4e06955`.

## 2. Measure and sign off

- [x] 2.1 A/B, before (`4e06955`) and after, on the four fixtures, the villa fixture and the four real M3 projects
  (`run_m3.py`, with Verosa entered as villas with 0 bays). Verify: the recalculated villa deliverables have no error
  cell, and the projects with apartments and bays do not move.
  - Done 2026-10-19: the four fixtures and the four M3 projects as entered before do not move; the villa fixture and
    the villa entry of the low-rise M3 project run with 0 error cells (2,112 before). Details in
    `Savills-local/budget-test/2026-10-19-laneC-villa/task_log.md`.
- [x] 2.2 The user signs off the measured movement.
  - Signed off 2026-10-19 by the user, with the instruction to commit. ESS9 at 0 for a villa-only project (waste is
    counted on apartments and shophouses) is left for after core v1, with group K.
