## Context

The web (`webapp/`) reads everything through `SOURCE_DIR`-relative paths: `BUDGET_AGENT = source_code\..`,
`BASE = source_code\..\..`; the template at `BASE\input\template\...`, data at `BUDGET_AGENT\data\`, the input form
at `BUDGET_AGENT\reports\Project_Budget_Input.xlsx`. The library needs `BUDGET_WEB_LIBRARY_STORE`; without it the page
already switches the Review source to "Tải file lên". SSO is off with `BUDGET_WEB_AUTH=off`. A Review needs Excel
(`review.recalc_copy` through COM) and the `run_log` step tolerates a PC without Excel. The two generators import only
`openpyxl`; the web adds `fastapi`, `uvicorn`, `starlette`, `pydantic`, `python-multipart`, `itsdangerous`, `msal`
(imported at start even when SSO is off) and `pywin32`.

The tenant's OneDrive policy blocks `.cmd`, `.bat`, `.exe`, `.vbs`, `.ps1` from syncing, so packages travel as zip.

## Goals / Non-Goals

**Goals:** one zip per site that runs with a double-click on a Windows PC with Excel and no Python; the site sees its
own budget only; the Hub deployment is untouched; the build is repeatable from the committed code.

**Non-Goals:** code signing; an installer; auto-update of packages; a site without Excel; macOS; queueing more than
one run; sending results back to the office (the PM mails the workbook as today).

## Decisions

**D1. Package layout.** `BudgetAgent-<site>\python\`, `app\Budget_Agent\source_code\`, `app\Budget_Agent\data\`,
`app\Budget_Agent\reports\Project_Budget_Input.xlsx`, `app\input\template\<form>.xlsx`, `site\site.json`,
`site\<approved>.xlsx`, `runs\`, `tmp\`, `Chay Budget Agent.cmd`, `Chay mot lan.cmd`, `HUONG-DAN.txt`. Keeping the
`Budget_Agent\source_code` depth means every existing relative path in the generators works unchanged.

**D2. Runtime from the build PC, not downloaded.** `build_site_runtime.py` copies the build PC's Python 3.14
(`python.exe`, `pythonw.exe`, `python3.dll`, `python314.dll`, `vcruntime140*.dll`, `DLLs\`, `Lib\` without `test`,
`idlelib`, `tkinter`, `turtledemo`, `ensurepip`, `__pycache__`) and only the listed packages from its
`site-packages` (closure: fastapi, starlette, pydantic, pydantic_core, typing_extensions, typing_inspection,
annotated_types, anyio, sniffio, idna, uvicorn, h11, click, colorama, python_multipart, itsdangerous, msal, PyJWT,
cryptography, cffi, pycparser, requests, urllib3, certifi, charset_normalizer, openpyxl, et_xmlfile, pywin32 with
`win32`, `win32com`, `win32comext`, `pythonwin`, `pywin32_system32`). The `pywin32_system32\*.dll` are copied beside
`python.exe` too, so `pythoncom` loads without the post-install step. Pinned versions are those in
`requirements.txt` / `webapp\requirements.txt`; the script refuses a different version. No network is used.
Learned in the 2026-11-05 trial (ZWork, runtime 72 MB, 28 distributions): the package list is the closure of
`Requires-Dist` from the seven top-level packages (hand lists missed `annotated-doc`); each distribution is copied
from its own install root (`dist.locate_file('')`), because on the build PC several of them, `pywin32` and
`openpyxl` included, sit in the user site-packages, not under `C:\Python314`; `python314._pth` lists
`python314.zip`, `DLLs`, `Lib`, `Lib\site-packages`, `..\app\Budget_Agent\source_code` and `import site`, which
makes `-m webapp` work from any folder and keeps the host PC's user site-packages and `PYTHONPATH` out; a
`pywin32.pth` adds `win32`, `win32\lib`, `pythonwin`. The launcher also sets `PYTHONNOUSERSITE=1` and runs with
`-s`. Checked with `python.exe -I -c "import openpyxl, fastapi, uvicorn, msal, win32com.client, pythoncom"`.

**D3. `site.json`** = `{"project", "prior_file", "facts": {...}, "store_id", "built_at", "code": "<git hash>"}`.
Facts come from `facts_prefill.prefill()` on the build PC (previous runs, sheet 0. Info, master list), values only.
No path, user name or machine name is written.

**D4. Site mode in the server.** `BUDGET_WEB_SITE` names the `site\` folder. `GET api/site` returns `site.json`
without the file path. `POST api/reviews` accepts `site=1` as a fourth source: the packaged file is copied into the
run's `prior\` like a library file (same snapshot rule). The library routes answer as if the store were empty:
this is a must, not a nicety, because `library.DEFAULT_STORE` is a `%USERPROFILE%` path that exists on the build
PC (the 2026-11-05 trial package served all 87 store rows from there until the variable was handled).
`index.html` gets `__SITE__` (`1` or empty) from `_page()`; the page hides the tabs `nhap`, `ketqua`, `kho`, hides
the "Dự án có sẵn" source button, shows a "Ngân sách đã duyệt của dự án" button selected by default with the project
name and file name, and fills section 2 from `api/site`. Guide sections about new projects and the library get
`class="site-hide"`.

**D5. Launcher `webapp/start_site.py`.** Sets `BUDGET_WEB_AUTH=off`, `BUDGET_WEB_PREFIX=/budget`,
`BUDGET_WEB_HOST=127.0.0.1`, `BUDGET_WEB_RUNS=<package>\runs`, `BUDGET_WEB_SITE=<package>\site`, `TEMP`/`TMP` =
`<package>\tmp`, `PYTHONDONTWRITEBYTECODE=1`; picks a free port from 8090 upward; writes `tmp\port.txt`; if a server
of this package already answers on that port, only opens the browser; else starts uvicorn in-process and opens the
browser after the first successful `GET /`. The `.cmd` runs
`python\python.exe app\Budget_Agent\source_code\webapp\start_site.py` with `chcp 65001` and the console left open
("Đóng cửa sổ này để tắt").

**D6. One-shot `webapp/site_once.py`.** Creates `runs\<yyyymmdd-hhmmss>_review-<site>\`, copies the packaged file to
`prior\`, writes `facts.json` from `site.json`, runs `review_run.py` as a subprocess (same command the server uses),
then `static_report.render(workdir)` writes `ket-qua.html` from `results.review_summary()` (same sections and
wording as the page; Arial, Savills palette tokens, no logo) and opens it with the default browser. On `STOPPED` the
page shows the stop line and the hint. The one-shot run writes `web_meta.json` the way the server does
(`history.write_meta`) at start and at the end, so the Dự án đã tạo tab of the local web lists it correctly (a run
folder without that file shows as "Thất bại" with the folder name as project, seen in the trial).

**D7. Build checks** (`build_site_package.py --check`): runs
`python\python.exe -c "import openpyxl, win32com.client, fastapi, uvicorn, msal"` inside the package, then
`site_once.py --dry-run` (reads the packaged budget with `review_import`, no Excel) and reports size per folder. A full
one-shot run on one package before delivery is a task, done by hand because it needs Excel.

**D8. What is not in the package.** The scan store, `input\budget_planning`, tests, `legacy\`, `openspec\`, docs,
`.git`, `__pycache__`, other sites' files, `prior_coverage.csv`, any `web_runs`.

## Risks / Trade-offs

- A PC that blocks running unsigned `.cmd` or `python.exe` from a user folder stops the package. Mitigation: the
  guide tells the PM to extract to `C:\BudgetAgent\` and names the file to allow; signing is out of scope.
- `msal` and `requests` are imported at start although SSO is off; kept to avoid touching `auth.py` in this change.
- Excel absent: the Review stops at [4/4] with the existing message; the one-shot HTML says so.
- Each package carries the reference data; a change in data or code means rebuilding and resending every package.
  The build script writes `code` (git hash) into `site.json` and the guide so the office can tell versions apart.
