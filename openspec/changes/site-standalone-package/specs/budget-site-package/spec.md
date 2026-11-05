## ADDED Requirements

### Requirement: A site package holds everything one site needs and nothing of other sites
A site package SHALL be one folder `BudgetAgent-<site>\` (delivered as a zip) holding: a Python 3.14 runtime with
the packages the generators and the web import; the generators, `data\`, the 2027 form template and the input form
under `app\`; the site's approved budget `.xlsx` and `site.json` (project name, approved file name, pre-filled facts,
build time, code version) under `site\`; an empty `runs\`; the launchers `Chay Budget Agent.cmd` and `Chay mot
lan.cmd`; and `HUONG-DAN.txt`. It SHALL NOT contain the scan store, `input\budget_planning`, tests, legacy code,
OpenSpec, docs, git metadata, compiled bytecode, earlier web runs, another site's budget, or any user name, machine
name or path of the build PC.

#### Scenario: Package content
- **WHEN** `build_site_package.py` finishes for one site
- **THEN** the folder has exactly the parts above, `site\` holds one `.xlsx` and `site.json`, and no file under the
  package names another project of the scan store

#### Scenario: Build-PC paths are not written
- **WHEN** the package is searched for the build PC's user folder name or machine name
- **THEN** nothing is found

### Requirement: The runtime is built from the build PC without network
`build_site_runtime.py` SHALL build the `python\` folder by copying the build PC's Python 3.14 (interpreter, DLLs,
standard library without tests, IDLE, tkinter and ensurepip) and only the needed packages from its site-packages,
with the `pywin32` system DLLs placed beside `python.exe`. It SHALL refuse a package whose version differs from the
pinned one and SHALL NOT download anything.

#### Scenario: Runtime check
- **WHEN** the build runs `python\python.exe -c "import openpyxl, win32com.client, fastapi, uvicorn, msal"` inside the
  package
- **THEN** the command exits 0

#### Scenario: Version mismatch
- **WHEN** the build PC's `openpyxl` is not the pinned version
- **THEN** the build stops naming the package and both versions, and writes no runtime

### Requirement: One click starts the local web for that site
`Chay Budget Agent.cmd` SHALL start the web on 127.0.0.1 on a free port from 8090 upward, with login off, the
package's `runs\` and `tmp\` folders, `BUDGET_WEB_SITE` pointing at `site\`, and open the browser on the page once
it answers. A second click while the web runs SHALL only open the browser. Closing the console window SHALL stop
the web. Nothing SHALL be written outside the package folder except the browser's own files.

#### Scenario: First start
- **WHEN** the PM double-clicks the launcher on a PC with Excel and no Python
- **THEN** the browser opens the Review page of the site within a few seconds and the console says which window to
  close to stop

#### Scenario: Port in use
- **WHEN** port 8090 is taken by another program
- **THEN** the web starts on the next free port and the browser opens that address

### Requirement: The one-shot run gives the Review without a server
`Chay mot lan.cmd` SHALL run one Review on the packaged budget and facts into `runs\<lượt>\`, write the three
workbooks there, render `ket-qua.html` (approved vs tool per fund, the eight ties, the 10 largest differences with
the tool's method, entry notes, links to the files) and open it. A stop SHALL show the `STOPPED:` line and hint on
the page.

#### Scenario: One-shot run completes
- **WHEN** the one-shot launcher is run and Excel is present
- **THEN** `runs\<lượt>\` holds the three workbooks and `ket-qua.html`, the page shows the same figures as
  `review_summary.json`, and adjustments can be made on sheet `4. Điều chỉnh` in Excel
