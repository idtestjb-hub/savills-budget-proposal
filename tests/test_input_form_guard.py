"""Unit tests for the overwrite guard in build_project_input_form.py.

Covered: main() refusing to build when the live input exists and force is off; the dated backup
(_backup_existing) made before a forced rebuild; a failed backup stopping the overwrite.
Not covered: the full build itself (first-time creation of the blank form, the forced full
rebuild). Those need a real openpyxl build and are left to the verification run.

Invented data only. FINAL_OUT, OUT_DIR and OUT are redirected into pytest's tmp folder (OUT
defaults to the system temp folder, so it must be patched too), and the module's openpyxl is
replaced with a stub whose Workbook() raises: reaching it means "the guard let the build start",
and nothing is ever really built.

Rule source: openspec/specs/input-form-protection/spec.md (all scenarios here). The backup name
pattern and the "_2" counter are described in the _backup_existing docstring.
"""
import datetime
import os
from types import SimpleNamespace

import pytest

import build_project_input_form as bpf

LIVE_BYTES = b'FILLED-IN PROJECT (invented placeholder bytes)'


class BuildReached(Exception):
    """Raised by the stub Workbook: the guard let the build start."""


class FakeDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 7, 9, 5, 3)


@pytest.fixture
def env(tmp_path, monkeypatch):
    reports = tmp_path / 'reports'
    reports.mkdir()
    live = reports / 'Project_Budget_Input.xlsx'
    monkeypatch.setattr(bpf, 'OUT_DIR', str(reports))
    monkeypatch.setattr(bpf, 'FINAL_OUT', str(live))
    monkeypatch.setattr(bpf, 'OUT', str(tmp_path / 'scratch_Project_Budget_Input.xlsx'))

    def no_build():
        raise BuildReached()

    monkeypatch.setattr(bpf, 'openpyxl', SimpleNamespace(Workbook=no_build))
    return SimpleNamespace(tmp=tmp_path, reports=reports, live=live)


def make_live(env):
    env.live.write_bytes(LIVE_BYTES)
    os.utime(env.live, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    st = env.live.stat()
    return st.st_mtime_ns


def listing(folder):
    return sorted(p.name for p in folder.iterdir())


def snapshot_tree(env):
    return listing(env.reports), listing(env.tmp)


# ---------------------------------------------------------------- unforced build over a live input

def test_unforced_main_stops_before_building_when_live_input_exists(env):
    mtime = make_live(env)
    before = snapshot_tree(env)
    with pytest.raises(bpf.LiveInputExists):         # BuildReached would mean the guard let it through
        bpf.main()
    assert env.live.read_bytes() == LIVE_BYTES
    assert env.live.stat().st_mtime_ns == mtime
    assert snapshot_tree(env) == before              # no backup, no scratch file, nothing new


def test_unforced_stop_message_names_the_file_and_the_force_option(env):
    make_live(env)
    with pytest.raises(bpf.LiveInputExists) as err:
        bpf.main(force=False)
    msg = str(err.value)
    assert str(env.live) in msg and '--force' in msg
    assert err.value.path == str(env.live)


def test_live_input_exists_is_a_runtime_error():
    assert issubclass(bpf.LiveInputExists, RuntimeError)
    assert issubclass(bpf.LiveInputBackupFailed, RuntimeError)


def test_without_a_live_input_the_guard_lets_the_build_start(env):
    # first-time creation path: only the start is checked here, the stub stops the build
    with pytest.raises(BuildReached):
        bpf.main()
    assert listing(env.reports) == []


# ---------------------------------------------------------------- forced rebuild: backup first

def test_forced_main_backs_up_before_building(env, capsys):
    mtime = make_live(env)
    with pytest.raises(BuildReached):
        bpf.main(force=True)
    backups = [p for p in env.reports.iterdir() if p.name.startswith(bpf.BACKUP_PREFIX)]
    assert len(backups) == 1
    assert backups[0].read_bytes() == LIVE_BYTES
    assert backups[0].suffix == '.xlsx'
    assert env.live.read_bytes() == LIVE_BYTES and env.live.stat().st_mtime_ns == mtime   # build never ran
    assert str(backups[0]) in capsys.readouterr().out


def test_backup_is_a_dated_copy_in_the_same_folder(env, monkeypatch):
    make_live(env)
    monkeypatch.setattr(bpf, 'datetime', SimpleNamespace(datetime=FakeDatetime))
    backup = bpf._backup_existing(str(env.live))
    assert os.path.dirname(backup) == str(env.reports)
    assert os.path.basename(backup) == 'Project_Budget_Input_PRE_FORCE_2026-10-07_090503.xlsx'
    with open(backup, 'rb') as f:
        assert f.read() == LIVE_BYTES
    assert env.live.read_bytes() == LIVE_BYTES


def test_second_backup_in_the_same_second_gets_a_counter_and_keeps_the_first(env, monkeypatch):
    make_live(env)
    monkeypatch.setattr(bpf, 'datetime', SimpleNamespace(datetime=FakeDatetime))
    first = bpf._backup_existing(str(env.live))
    env.live.write_bytes(b'second project')
    second = bpf._backup_existing(str(env.live))
    third = bpf._backup_existing(str(env.live))
    assert os.path.basename(second).endswith('090503_2.xlsx')
    assert os.path.basename(third).endswith('090503_3.xlsx')
    with open(first, 'rb') as f:
        assert f.read() == LIVE_BYTES              # the first backup was not overwritten
    with open(second, 'rb') as f:
        assert f.read() == b'second project'


# ---------------------------------------------------------------- failed backup blocks the overwrite

def test_forced_main_with_failing_copy_leaves_the_live_file_alone(env, monkeypatch):
    mtime = make_live(env)

    def failing_copy(src, dst):
        raise OSError('disk full (invented)')

    monkeypatch.setattr(bpf, 'shutil', SimpleNamespace(copy2=failing_copy, copyfile=failing_copy))
    before = snapshot_tree(env)
    with pytest.raises(bpf.LiveInputBackupFailed) as err:          # BuildReached would mean it went on
        bpf.main(force=True)
    assert 'disk full' in str(err.value) and 'Nothing was replaced' in str(err.value)
    assert env.live.read_bytes() == LIVE_BYTES and env.live.stat().st_mtime_ns == mtime
    assert snapshot_tree(env) == before


def test_backup_that_differs_from_the_original_blocks_the_overwrite(env, monkeypatch):
    make_live(env)
    monkeypatch.setattr(bpf, 'filecmp', SimpleNamespace(cmp=lambda *a, **k: False))
    with pytest.raises(bpf.LiveInputBackupFailed) as err:
        bpf.main(force=True)
    assert 'differs' in str(err.value)
    assert env.live.read_bytes() == LIVE_BYTES
