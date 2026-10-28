## 1. Sheet `4. Điều chỉnh` (`budget_adjustment.py`)

- [x] 1.1 `TYPE_QTY_PRICE = 'Số lượng + Đơn giá'` in `ADJUSTMENT_TYPES` (dropdown order of design D1), column M of the detail rows `J*K` under it, guide line names it. Verify: unit test on the formula text, and an Excel COM test on a built sheet: 4 posts at 300,000,000 → 5 at 330,000,000 gives M = 1,650,000,000 and the fund row follows; a lumped row gives G × K; the three old types give the same M as before. Done 2026-10-27: `tests/test_budget_adjustment.py` (formula evaluator and Excel COM) pass.

## 2. Web (`webapp/adjust.py`, `webapp/static/index.html`)

- [x] 2.1 `new_amount()` and `_validate()` know the type (refused without detail rows); `apply_edits()` upgrades M and the dropdown of an older sheet before writing. Verify in `tests/test_webapp_adjust.py`: preview figures, refusal message, an old-form sheet upgraded with identical figures for the old types (formula evaluator of the tests). Done 2026-10-27: 37 adjustment tests pass.
- [x] 2.2 Page: option in the dropdown, both input columns open, preview, "cách tính" table and guide lines. Verify on a local server (ZWork run folder, auth off) at 1280 and 400 px: pick the type, edit both, the row and code totals match the server's saved file after Excel recalculation. Done 2026-10-27 on a copy of an older run (fake project ZZ TEST TOWER, made before this change): ESS1 4 × 85,000,000 on the first row, preview 3,343,000,000; saved through the web (backup kept), Excel COM: the sheet upgraded (formula and dropdown), first row 340,000,000, code 3,343,000,000, the other 31 codes' new amounts identical to the backup, 0 error cells; the save job's own recalculation 0 error cells. The dropdown was widened (120 → 168 px) so the new name shows in full; no sideways page scroll at 400 px.

## 3. Sign-off

- [x] 3.1 Full test suite passes; `openspec validate --all --strict` passes; `python verification/verify.py`, run from `Budget_Agent/source_code/`, PASS (no baseline figure moves).
- [x] 3.2 Release note for [Hub] (`releases\2026-10-27-budget-web-sl-don-gia.txt`) after the user says commit; `docs/project-status.md` updated. Done 2026-10-27 with this commit (user's request).
