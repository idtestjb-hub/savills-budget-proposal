## 1. Runtime

- [x] 1.1 `build_site_runtime.py`: copy the build PC's Python 3.14 pruned (D2), the closure of the seven top-level packages with pinned-version check (conditional requirements of older Pythons skipped), `pywin32_system32` DLLs beside `python.exe`; `--out <folder>`; prints sizes (05/11: 28 distributions, 72 MB)
- [x] 1.2 Check: `python\python.exe -I -c "import openpyxl, win32com.client, fastapi, uvicorn, msal"` exits 0 from a folder outside the repo (05/11, no user site-packages on `sys.path`)

## 2. Site mode of the web

- [x] 2.1 `webapp/server.py`: `SITE_DIR` from `BUDGET_WEB_SITE`, `site_info()`; `GET api/site` (site.json without paths); `POST api/reviews` source `site=1` (copy to `prior\`, tag `review-<site>`); `api/library` empty and `api/library/*` 404 in site mode; `_page()` passes `__SITE__`
- [x] 2.2 `webapp/static/index.html`: `body.site .site-hide` hides tabs `nhap`, `ketqua`, `kho`, the "Dự án có sẵn" button, guide sections `hd-new`, `hd-arch` and the library bullet; source "Ngân sách đã duyệt của dự án" (default, `#rv-site`); `loadSite()` pre-fills section 2 from `api/site`; title with the project name
- [x] 2.3 Tests `tests/test_webapp_site.py` (10): `api/site` with and without the variable; page flag; library empty / 404; `site=1` run folder (`prior\`, `facts.json`, meta, History); refusals; page without the variable unchanged (6 tabs)

## 3. Launchers

- [x] 3.1 `webapp/start_site.py` (D5): env, free port from 8090, `tmp\port.txt`, already-running check, browser open after first 200, uvicorn in-process
- [x] 3.2 `webapp/static_report.py`: `render(workdir, project) -> path`; same sections as the page; palette tokens; no logo; no person names; stop line from `run.log` when the summary is missing
- [x] 3.3 `webapp/site_once.py` (D6): run folder, `web_meta.json` at start and end, subprocess `review_run.py` with `run.log`, `ket-qua.html`, open; `--dry-run` reads the packaged budget only; `--no-open`
- [x] 3.4 Tests: `static_report.render` on the recorded review fixture (figures, top row, ties, notes, relative file links) and on a stopped run; `start_site.free_port` with a taken port

## 4. Package build

- [x] 4.1 `build_site_package.py`: `--site --prior --runtime --out [--library-id] [--facts] [--city] [--zip] [--check] [--check-only <gói>]`; copies per D1/D8 (`*.md` and `build_site_*.py` left out: they carry office paths and the scan words); `site.json` per D3; the two `.cmd`, `HUONG-DAN.txt`; `--check` per D7 (import, dry-run read, text scan, sizes); read-only flags cleared on rebuild
- [x] 4.2 Built `BudgetAgent-City-Garden` in `C:\ZWork` (05/11): check OK (80 MB, scan clean); `start_site.py` answers `/budget/` 200 with the site flag, `api/site` filled, `api/library` empty, History lists the one-shot run; one-shot run result recorded in `docs/project-status.md` (P19)
- [ ] 4.3 Decide with the user: keep or strip the Comparison / Service Levels sheets and `master_list_verified` names (proposal, Impact); apply the choice in the build. Current build keeps them.

## 5. Docs and verify

- [x] 5.1 `webapp/README.md` (section "Gói chạy riêng cho một site"), `RUNNING.md` (section "Site packages"), `docs/project-status.md`
- [x] 5.2 `python verification/verify.py` from `Budget_Agent/source_code/` PASS (05/11, method fidelity 99.9%); full test run 1329 passed, 1 xfailed
