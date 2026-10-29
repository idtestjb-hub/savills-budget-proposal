## 1. Generator output of a Review

- [x] 1.1 `verification/run_workflow.py`: optional `log_path`; when given, write each generator's stdout to it under a header line, flushed after each generator (D1)
- [x] 1.2 `review.py` step [3/4]: pass `<workdir>/generator.log`, print the pointer line (D2)
- [x] 1.3 Tests: both headers and output present; a raising second generator leaves the first's output and the partial second; `run_workflow` without `log_path` unchanged

## 2. Traceback of a stopped Review

- [x] 2.1 `webapp/review_run.py`: write `review_error.txt` for the known stops; catch-all with `STOPPED: lỗi không lường trước (<type>): <message>`, exit 2 (D3)
- [x] 2.2 Tests: known stop and unexpected exception each give the stop line, the file and exit 2; a viewer cannot download `review_error.txt`

## 3. Failure before the subprocess

- [x] 3.1 `webapp/server.py` `start_run` / `start_review`: on failure between folder creation and `_start`, write failed meta with `error`, log, re-raise (D4)
- [x] 3.2 `webapp/history.py` `describe()`: `error`; `webapp/static/index.html`: show it under "Thất bại"
- [x] 3.3 Tests: input-form failure and library-copy failure leave meta with status failed and the error; History returns it

## 4. Cleanup of old failed runs

- [x] 4.1 `webapp/history.py` `prune_failed(runs_dir, active_id, max_age_days=30, now=None, log=print, dry_run=False)` (D5)
- [x] 4.2 `webapp/server.py`: daemon thread at app start, then every 24 h; errors logged, never raised
- [x] 4.3 Tests: failed 31 days deleted; failed 29 days kept; done 400 days kept; running kept; junction inside skipped and its target untouched; folder name not matching the run-id pattern ignored

## 5. Verify and hand over

- [x] 5.1 Full test suite, `openspec validate --all --strict`, `python verification/verify.py` PASS
- [ ] 5.2 Dry run of `prune_failed` on a copy of a local runs folder (list of what would go); write the dry-run command into the release note for [Hub]
- [ ] 5.3 Release note `releases\YYYY-MM-DD-budget-web-log-review.txt`; deploy through [Hub]; after the deploy, check one Review on the server leaves `generator.log`
