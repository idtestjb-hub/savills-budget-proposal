## Context

Run folders live in `RUNS_DIR` (`reports/web_runs`, server: `BUDGET_WEB_RUNS`). The server's `_worker` streams the
subprocess's stdout+stderr into `run.log` and the page. A Review subprocess is `webapp/review_run.py`, which calls
`review.run(..., quiet=False)`; inside, step [3/4] calls `run_workflow(sample=form, workdir=run_dir, quiet=True)`,
which redirects the generators' stdout into a `StringIO` that nobody reads. History (`history.describe`) reads
`web_meta.json`, falling back to the files present.

## Goals / Non-Goals

**Goals:** enough left in a run folder to diagnose a failed Review without rerunning it; a reason for every failed run
in History; bounded growth of failed runs.

**Non-Goals:** changing what the page log shows; changing the "Tạo ngân sách" run (its generators already print to
run.log); deleting done runs; a size quota; an admin page for cleanup.

## Decisions

**D1. `run_workflow(..., log_path=None)`.** When `log_path` is given, the generators' stdout is written to that file
(opened once, a header `===== <label> (<module>.py) =====` before each generator, flushed after each), instead of the
`StringIO`. `quiet` keeps its meaning for callers that pass no path; `verify.py` and the tests that call it are
unchanged. Written as the generators print, so a crash keeps the partial output. stderr is not redirected (a warning
there already reaches run.log through the subprocess pipe).

**D2. Review passes `log_path=<workdir>/generator.log`** and says `    log hai generator: generator.log` under step
[3/4]. The line names the file only, not a server path. It contains none of `_INTERNAL_LOG_MARKERS`, so a viewer sees
it; the file itself is not an output, so a viewer cannot download it (existing `may_download`).

**D3. `review_run.py` catch-all.** The known stop tuple keeps its message format. A second `except Exception` covers
the rest with `STOPPED: lỗi không lường trước (<type>): <message>`. Both write `traceback.format_exc()` to
`review_error.txt` (UTF-8) and return 2. Writing the file is itself wrapped so a disk error cannot hide the stop line.
`KeyboardInterrupt`/`SystemExit` are not caught.

**D4. Failure before the subprocess.** In `start_run` and `start_review`, the steps between `os.makedirs` and `_start`
move into a `try`; on `HTTPException` or any `Exception` the handler calls `history.write_meta(workdir, kind=...,
project=..., user=..., started=..., finished=_now(), status='failed', rc=None, error=<detail>)`, logs one server line,
and re-raises (an `HTTPException` as is; anything else as `HTTPException(500, 'Không chuẩn bị được lượt chạy: ...')`
so the page always gets a message). `describe()` adds `error=meta.get('error') or ''`; History renders it in a muted
line under "Thất bại".

**D5. Cleanup = `history.prune_failed(runs_dir, active_id, max_age_days=30, now=None, log=print, dry_run=False)`.** Uses `scan()` so
status follows the same rules as History. Age from `finished`, else `started`, else `os.path.getmtime`. Before
deleting, walk the folder with `os.scandir` (no following): any entry that `is_symlink()` or is a junction
(`os.path.isjunction`, Python 3.12+) skips the folder. The resolved folder must be a direct child of the resolved
`runs_dir`. Delete with `shutil.rmtree`. Returns `(deleted, skipped)`. The server starts a daemon thread at app start
that calls it, then sleeps 24 h, in a loop; every call inside `try/except Exception` that logs and continues. The
active id is read under `_lock`.

## Risks / Trade-offs

- A failed run a PM still wants to look at disappears after 30 days. Accepted by the user; the server log names it.
- `generator.log` adds about 100–400 KB per Review. Small next to the three workbooks.
- A History entry for a run that failed before start now says "Thất bại" with a reason instead of a guessed name. No
  other History change.

## Migration

None. Old folders without `web_meta.json` keep today's inferred status; the first cleanup deletes those that read as
failed and are older than 30 days. Before the first deploy, [Hub] can list them with
`python -B -c "from webapp import history; ..."` (task 5.2 gives the exact dry-run command).
