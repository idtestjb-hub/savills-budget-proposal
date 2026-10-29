"""Change log-review-runs: what a web run folder keeps for diagnosis, and the cleanup of old failed runs.

No pipeline run: the generators, the Review and the subprocess are replaced by stand-ins. Names are invented.
"""
import contextlib
import datetime
import json
import os
import subprocess
import sys
import types

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import history, review_run, server  # noqa: E402

NOW = datetime.datetime(2026, 11, 30, 9, 0, 0)


@pytest.fixture
def runs_dir(tmp_path, monkeypatch):
    d = tmp_path / 'web_runs'
    d.mkdir()
    monkeypatch.setattr(server, 'RUNS_DIR', str(d))
    server._runs.clear()
    server._active['id'] = None
    yield d
    server._runs.clear()
    server._active['id'] = None


# ---- 1. generator output --------------------------------------------------------------------------
def _fake_generators(monkeypatch, second_fails=False):
    from verification import run_workflow as rw

    def make(name, text, fail=False):
        def main():
            print(text)
            if fail:
                raise RuntimeError('boom')
        return types.SimpleNamespace(__name__=name, main=main)

    monkeypatch.setitem(sys.modules, 'generate_project_budget', make('generate_project_budget', 'budget says hello'))
    monkeypatch.setitem(sys.modules, 'generate_project_output',
                        make('generate_project_output', 'analysis says hello', second_fails))
    resolved = {'generate_project_budget.BUDGET_OUT_DIR': 'd', 'generate_project_output.OUTPUT_PATH': 'a',
                'generate_project_budget.ROSTER_FINAL_OUT': 'r'}
    monkeypatch.setattr(rw, 'redirected_paths', lambda sample, workdir: contextlib.nullcontext(resolved))
    monkeypatch.setattr(rw, 'snapshot', lambda: {})
    return rw


def test_generator_output_goes_to_the_log_file_under_headers(monkeypatch, tmp_path, capsys):
    rw = _fake_generators(monkeypatch)
    log = tmp_path / 'generator.log'
    rw.run_workflow(sample='s.xlsx', workdir=str(tmp_path), log_path=str(log))
    text = log.read_text(encoding='utf-8')
    assert text.index('===== budget generator (generate_project_budget.py) =====') < text.index('budget says hello')
    assert text.index('budget says hello') < text.index('===== analysis generator') < text.index('analysis says hello')
    assert 'hello' not in capsys.readouterr().out


def test_a_failing_generator_leaves_what_it_printed(monkeypatch, tmp_path):
    rw = _fake_generators(monkeypatch, second_fails=True)
    log = tmp_path / 'generator.log'
    with pytest.raises(rw.PartialRun):
        rw.run_workflow(sample='s.xlsx', workdir=str(tmp_path), log_path=str(log))
    text = log.read_text(encoding='utf-8')
    assert 'budget says hello' in text and 'analysis says hello' in text


def test_without_a_log_path_nothing_changes(monkeypatch, tmp_path, capsys):
    rw = _fake_generators(monkeypatch)
    rw.run_workflow(sample='s.xlsx', workdir=str(tmp_path))
    assert 'hello' not in capsys.readouterr().out and not list(tmp_path.iterdir())


# ---- 2. traceback of a stopped review -------------------------------------------------------------
class _Stream:
    """stdout / stderr stand-in that accepts review_run's reconfigure() and writes through to the captured stream."""

    def __init__(self, inner):
        self.inner = inner

    def reconfigure(self, **kwargs):
        pass

    def write(self, text):
        return self.inner.write(text)

    def flush(self):
        self.inner.flush()


def _run_review_run(monkeypatch, tmp_path, exc):
    import review

    def boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(review, 'run', boom)
    monkeypatch.setattr(review_run, 'store_names', lambda: set())
    monkeypatch.setattr(sys, 'argv', ['review_run.py', '--prior', str(tmp_path / 'p.xlsx'),
                                      '--workdir', str(tmp_path / 'wd')])
    monkeypatch.setattr(sys, 'stdout', _Stream(sys.stdout))
    monkeypatch.setattr(sys, 'stderr', _Stream(sys.stderr))
    monkeypatch.chdir(tmp_path)
    return review_run.main()


def test_a_known_stop_keeps_its_traceback(monkeypatch, tmp_path, capsys):
    import review_import as ri
    rc = _run_review_run(monkeypatch, tmp_path, ri.PriorBudgetError('no month columns'))
    assert rc == 2 and 'STOPPED: no month columns' in capsys.readouterr().out
    tb = (tmp_path / 'wd' / 'review_error.txt').read_text(encoding='utf-8')
    assert 'Traceback' in tb and 'PriorBudgetError: no month columns' in tb


def test_an_unexpected_exception_stops_with_a_message_and_a_traceback(monkeypatch, tmp_path, capsys):
    rc = _run_review_run(monkeypatch, tmp_path, TypeError('EN9 is None'))
    out = capsys.readouterr().out
    assert rc == 2 and "STOPPED: lỗi không lường trước (TypeError): EN9 is None" in out
    assert 'TypeError' in (tmp_path / 'wd' / 'review_error.txt').read_text(encoding='utf-8')


def test_a_viewer_cannot_download_the_traceback(runs_dir):
    wd = runs_dir / '20261020-090000_review-Khu-Thu'
    wd.mkdir()
    (wd / 'review_error.txt').write_text('Traceback ...', encoding='utf-8')
    history.write_meta(str(wd), kind='review', status='failed', rc=2)
    c = TestClient(server.app)
    r = c.get(f'/api/runs/{wd.name}/files/review_error.txt', headers={'X-Hub-Role': 'viewer'})
    assert r.status_code in (403, 404)


# ---- 3. failure before the subprocess -------------------------------------------------------------
def test_a_new_run_that_cannot_write_its_input_says_why(runs_dir, monkeypatch):
    def broken(values, path):
        raise ValueError('ô Tower Count không đọc được')

    monkeypatch.setattr(server.fill_input, 'write_input', broken)
    c = TestClient(server.app)
    r = c.post('/api/runs', json=dict(scalars=dict(project_name='Demo Tower')))
    assert r.status_code == 400 and 'Không ghi được file nhập liệu' in r.json()['detail']
    (wd,) = list(runs_dir.iterdir())
    meta = json.loads((wd / 'web_meta.json').read_text(encoding='utf-8'))
    assert meta['status'] == 'failed' and meta['project'] == 'Demo Tower' and meta['kind'] == 'new'
    assert 'Tower Count' in meta['error'] and meta['finished']
    row = c.get('/api/history').json()['runs'][0]
    assert row['status'] == 'failed' and row['project'] == 'Demo Tower' and 'Tower Count' in row['error']
    viewer = c.get('/api/history', headers={'X-Hub-Role': 'viewer'}).json()['runs'][0]
    assert viewer['error'] == ''
    assert server._active['id'] is None


def test_a_review_whose_library_copy_fails_says_why(runs_dir, monkeypatch):
    entry = dict(id='abc123', project='Khu Thu', file_name='NS 2025.xlsx', path='x', selectable=True, reason='')
    monkeypatch.setattr(server.library, 'find', lambda fid: entry)

    def broken(path):
        raise OSError('file đang bị khoá')

    monkeypatch.setattr(server.library, 'long_path', broken)
    c = TestClient(server.app, raise_server_exceptions=False)
    r = c.post('/api/reviews', data={'library_id': 'abc123', 'facts': json.dumps({'city': 'Ho Chi Minh City'})})
    assert r.status_code == 500 and 'Không chuẩn bị được lượt chạy' in r.json()['detail']
    (wd,) = list(runs_dir.iterdir())
    meta = json.loads((wd / 'web_meta.json').read_text(encoding='utf-8'))
    assert meta['status'] == 'failed' and meta['kind'] == 'review' and 'bị khoá' in meta['error']
    assert server._active['id'] is None


# ---- 4. cleanup -------------------------------------------------------------------------------------
def _run(runs_dir, run_id, status, finished):
    wd = runs_dir / run_id
    wd.mkdir()
    stamp = finished.isoformat(timespec='seconds')
    history.write_meta(str(wd), kind='new', status=status, finished=stamp, started=stamp)
    if status == 'done':
        for _, pattern, _ in history.OUTPUT_KINDS:
            (wd / pattern.replace('*', 'Khu Thu')).write_bytes(b'PK')
    return wd


def test_prune_deletes_old_failed_runs_only(runs_dir):
    old_failed = _run(runs_dir, '20261001-090000_a', 'failed', NOW - datetime.timedelta(days=31))
    new_failed = _run(runs_dir, '20261102-090000_b', 'failed', NOW - datetime.timedelta(days=29))
    old_done = _run(runs_dir, '20251001-090000_c', 'done', NOW - datetime.timedelta(days=400))
    active = _run(runs_dir, '20261001-100000_d', 'failed', NOW - datetime.timedelta(days=60))
    (runs_dir / 'not a run').mkdir()
    lines = []
    deleted, skipped = history.prune_failed(str(runs_dir), active.name, max_age_days=30, now=NOW, log=lines.append)
    assert deleted == [old_failed.name] and skipped == []
    assert not old_failed.exists() and new_failed.exists() and old_done.exists() and active.exists()
    assert (runs_dir / 'not a run').exists() and any(old_failed.name in ln for ln in lines)


def test_prune_dry_run_deletes_nothing(runs_dir):
    wd = _run(runs_dir, '20261001-090000_a', 'failed', NOW - datetime.timedelta(days=31))
    deleted, _ = history.prune_failed(str(runs_dir), None, now=NOW, log=lambda m: None, dry_run=True)
    assert deleted == [wd.name] and wd.exists()


@pytest.mark.skipif(os.name != 'nt', reason='junction')
def test_prune_skips_a_folder_with_a_junction_and_keeps_its_target(runs_dir, tmp_path):
    target = tmp_path / 'outside'
    target.mkdir()
    (target / 'keep.txt').write_text('keep', encoding='utf-8')
    wd = _run(runs_dir, '20261001-090000_a', 'failed', NOW - datetime.timedelta(days=31))
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(wd / 'link'), str(target)], check=True, capture_output=True)
    try:
        deleted, skipped = history.prune_failed(str(runs_dir), None, now=NOW, log=lambda m: None)
        assert deleted == [] and skipped == [wd.name]
        assert wd.exists() and (target / 'keep.txt').read_text(encoding='utf-8') == 'keep'
    finally:
        os.rmdir(wd / 'link')
