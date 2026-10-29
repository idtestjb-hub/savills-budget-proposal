## ADDED Requirements

### Requirement: A Review keeps the generators' output in its run folder
A Review run SHALL write everything the budget generator and the analysis generator print to
`<run>/generator.log`, in run order, each generator's part under a header line naming it. `run.log` SHALL get one
line naming that file. A generator that fails SHALL still leave what it printed before the failure in the file.
`verification/run_workflow.py` without the new argument SHALL behave as before.

#### Scenario: A Review completes
- **WHEN** a Review run finishes with exit code 0 or 1
- **THEN** `<run>/generator.log` exists, holds a header line for each of the two generators followed by their output,
  and `run.log` contains a line naming `generator.log`

#### Scenario: The analysis generator raises
- **WHEN** the budget generator completes and the analysis generator raises
- **THEN** `generator.log` holds the budget generator's full output and the analysis generator's output up to the
  failure, and the Review stops as it does today

### Requirement: A stopped Review keeps its traceback
When a Review stops, `webapp/review_run.py` SHALL write the full traceback to `<run>/review_error.txt` and print the
`STOPPED:` line (and the Vietnamese year hint where it applies) as today. An exception outside the known stop types
SHALL also be caught: its traceback written the same way, `STOPPED: lỗi không lường trước (<exception type>): <message>`
printed, exit code 2. The file SHALL NOT be listed as an output, and a viewer SHALL NOT be able to download it.

#### Scenario: Known stop
- **WHEN** the prior file raises `PriorBudgetError`
- **THEN** run.log shows `STOPPED: <message>`, `review_error.txt` holds the traceback, the exit code is 2

#### Scenario: Unexpected exception
- **WHEN** the Review raises a `KeyError`
- **THEN** run.log shows `STOPPED: lỗi không lường trước (KeyError): ...`, `review_error.txt` holds the traceback,
  the exit code is 2

#### Scenario: Viewer asks for the file
- **WHEN** a viewer requests `/api/runs/<id>/files/review_error.txt`
- **THEN** the request is refused, as for every file not in the viewer's output list

### Requirement: A run that fails before it starts says why
When `POST /api/runs` or `POST /api/reviews` fails after the run folder is created and before the subprocess starts,
the server SHALL write `web_meta.json` in that folder with `status` `failed`, the run kind, the project name (when
known), the user, the start time, `finished` and `error` (the message returned to the page). The HTTP reply SHALL be
unchanged. History SHALL show `error` under the status of any run whose meta has one.

#### Scenario: Input form cannot be written
- **WHEN** `fill_input.write_input` raises for a "Tạo ngân sách" request for project "Demo Tower"
- **THEN** the reply is the same 400 as today, the run folder holds `web_meta.json` with `status` `failed`, project
  "Demo Tower" and the error text, and History lists the run as "Thất bại" with that text

#### Scenario: Library file cannot be copied
- **WHEN** copying the picked library file into `<run>/prior` raises
- **THEN** the folder holds `web_meta.json` with `status` `failed`, kind `review` and the error, and the page gets an
  error reply instead of a server crash

### Requirement: Old failed runs are cleaned up, done runs never
The server SHALL delete a run folder in its runs directory when all hold: its status (as History reads it) is
`failed`; its age, counted from `finished`, else `started`, else the folder's modification time, is more than 30
days; it is not the running run. Done runs SHALL never be deleted automatically. A folder that holds a junction or
symbolic link anywhere inside SHALL be skipped, never followed, and logged. Only folders whose name matches the run-id
pattern and that sit directly in the runs directory SHALL be considered. The cleanup SHALL run at server start and
then once every 24 hours, and log one server line per deleted or skipped folder. A cleanup error SHALL NOT stop the
server or a run.

#### Scenario: Old failed run
- **WHEN** a failed run finished 31 days ago
- **THEN** its folder is deleted and the server log names it

#### Scenario: Old done run
- **WHEN** a done run finished 400 days ago
- **THEN** its folder stays

#### Scenario: Recent failed run
- **WHEN** a failed run finished 29 days ago
- **THEN** its folder stays

#### Scenario: Junction inside
- **WHEN** an old failed run folder contains a junction
- **THEN** nothing in it is deleted, the junction target is untouched, and the server log says it was skipped
