## Why

The server Review stops of 2026-10-28 took three causes to find because the run folders hold too little (read-only check
of session P17's side session, 2026-10-29):

- A Review runs the two generators with `run_workflow(quiet=True)` (`review.py:683`); their stdout goes into an
  in-memory buffer that is thrown away (`verification/run_workflow.py:92-99`). A "Tạo ngân sách" run keeps it.
- A Review that stops writes one line, `STOPPED: <message>` (`webapp/review_run.py:83-88`), and no traceback.
- `POST /api/runs` and `POST /api/reviews` create the run folder before anything can fail (writing the input form,
  copying the library file). A failure there leaves a folder with no `web_meta.json`; History shows it as "Thất bại"
  under a project name guessed from the folder name, with no reason (`webapp/history.py:118-121`).
- Nothing ever removes old runs from `reports/web_runs`.

## What Changes

User's choices on 2026-10-29 (all recommended options):

- **Generator output of a Review** goes to `<run>/generator.log` (both generators, in order, each under a header
  line). `run.log` gets one line pointing at it. The page stays as short as today.
- **Traceback of a stopped Review** goes to `<run>/review_error.txt` (internal file: not in the output list; a viewer cannot
  download it, as today for every unlisted file). The page still shows `STOPPED:` and the Vietnamese hint. An unexpected exception (not one of the
  known stop types) is also caught, written the same way, and exits 2 with `STOPPED: lỗi không lường trước (<type>)`.
- **A run that fails before its subprocess starts** keeps its folder and gets `web_meta.json` with `status=failed`,
  the project name and `error=<message>`. History shows the reason under the status. The HTTP reply stays the same
  error as today.
- **Cleanup**: a failed run whose finish time (else start time) is more than 30 days old is deleted, at server start
  and then once a day. Done runs are never deleted automatically (a done deliverable is next year's "ngân sách năm
  ngoái"). The running run is never touched. A folder with a junction or symbolic link inside is skipped and logged,
  never followed. Each deletion is one line in the server log.

## Capabilities

### New Capabilities
- `budget-web-run-records`: what each web run folder keeps for diagnosis (generator output, stop traceback, failure
  reason) and which run folders are cleaned up.

### Modified Capabilities

## Impact

- `verification/run_workflow.py`: `run_workflow` can hand back the captured generator output (new optional argument;
  default behaviour unchanged for `verify.py`).
- `review.py`: writes `generator.log` in the Review workdir.
- `webapp/review_run.py`: traceback file, catch-all stop.
- `webapp/server.py`: failure before the subprocess writes meta; cleanup at start and daily.
- `webapp/history.py`: `error` in `describe()`; the cleanup function (`prune_failed`).
- `webapp/static/index.html`: History shows `error` under "Thất bại".
- Tests: new `tests/test_webapp_run_records.py`; `tests/test_webapp_review.py` for the two Review files.
- No change to budget figures, the deliverable, the analysis or the Review sheet. Needs one deploy through [Hub].
