## 1. Module

- [x] 1.1 `site_data.py`: `KEEP` (measured list), `MASK`, `Pseudonyms`, `build()`, `leak_words()`, `find_leaks()`
- [x] 1.2 `tests/test_site_data.py`: KEEP files exist; build copies only KEEP and masks consistently across files; blanked columns; own and coded names kept; leak words and the scan (text and xlsx); pseudonyms stable

## 2. Builder

- [x] 2.1 `build_site_package.py`: `build()` uses `site_data.build`; `check()` runs `find_leaks` with words from the office data and the store (`--store`, default the known store folder) and fails on a hit; `--check-only` too
- [x] 2.2 `webapp/README.md` (gói site: dữ liệu rút gọn, ẩn danh, kiểm rò rỉ)

## 3. Measure and ship

- [x] 3.1 Rebuild the City Garden package with `--check --zip`; the check reports 0 leaks
- [x] 3.2 (measured, design.md; user sign-off pending) Run the Review inside the package on the packed approved file; compare with the full-data run of the same day (design.md "Measured"); the user signs off
- [x] 3.3 (05/11: 1355 passed + 1 xfailed; verify.py PASS) Full test run passes; `python verification/verify.py` from `Budget_Agent/source_code/` passes
