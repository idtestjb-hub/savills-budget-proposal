## 1. Builder

- [x] 1.1 `build_prior_coverage.py`: read every selectable store file with `review_import.read_prior_budget` (copy to a scratch folder, delete after), write `prior_coverage.csv` (file_id, budget_year, status, error_kind, n_year, and per kind n1/actual/expected: kept, tie, period; built_at, code_commit). No amount, name or message text. Unit test on a fake store.
- [x] 1.2 Run it on the client store `final_v4`; record counts. Done 2026-10-28 16:46 (code 13a6982 + this change, uncommitted): 53 selectable, 50 read; Duyệt N-1 41 (41 tie), Thực tế 41 (40), Dự kiến 41 (40); all three 40.

## 2. Web

- [x] 2.1 `library.overview()` returns `prior` (available, reason, built_at, per year and total: selectable, read, n1/actual/expected kept and tied, all three); unavailable when the file is missing, unreadable or lacks a selectable file. Unit tests: ties to the file, missing file, stale file, no names.
- [x] 2.2 Tab Kho, view "Dùng cho Review": a table "Cột năm trước (N-1) khi chạy Review" under the charts, with the measurement date and the reason when unavailable. Checked on the local web 28/10 (port 8095, client store): year rows sum to the total row, 53 = "chọn được", hidden in the price-table view.

## 3. Sign-off

- [x] 3.1 Web tests and full suite pass; `openspec validate --all --strict`; `python verification/verify.py` PASS. Done 2026-10-28: 1279 passed + 1 xfailed, openspec 46/46, verify.py PASS.
- [ ] 3.2 Release note for [Hub] (code + copy `prior_coverage.csv` into the server store `_kho_quet`); `docs/project-status.md` updated.
