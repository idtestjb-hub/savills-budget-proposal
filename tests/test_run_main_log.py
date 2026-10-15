"""run.main() and the run log (change add-budget-run-log, task 3.1).

Both generators are replaced by stand-ins, so nothing is generated and Excel is not touched.
  - a run whose internal analysis fails raises PartialRun and writes no record;
  - a normal run calls the log once, after the same-project check, and returns the same code as without it;
  - a log that blows up does not change the return code.
"""
import sys
import types

import pytest

import run


@pytest.fixture
def stub_run(tmp_path, monkeypatch):
    inp = tmp_path / 'input.xlsx'
    inp.write_bytes(b'x')
    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    deliverable = out_dir / 'Demo Tower Consulting Budget.xlsx'
    deliverable.write_bytes(b'x')

    gpb = types.ModuleType('generate_project_budget')
    gpb.INPUT_PATH = str(inp)
    gpb.BUDGET_OUT_DIR = str(out_dir)
    gpb.ROSTER_FINAL_OUT = str(out_dir / 'roster.xlsx')
    gpb.BUDGET_AGENT = str(tmp_path)
    gpb.main = lambda: None

    gpo = types.ModuleType('generate_project_output')
    gpo.OUTPUT_PATH = str(out_dir / 'analysis.xlsx')
    gpo.main = lambda: None

    monkeypatch.setitem(sys.modules, 'generate_project_budget', gpb)
    monkeypatch.setitem(sys.modules, 'generate_project_output', gpo)
    monkeypatch.setattr(run, '_project_name', lambda path, sheet: 'Demo Tower')
    monkeypatch.setattr(run, '_report_staffing_reasons', lambda p: 0)
    monkeypatch.setattr(run, '_report_utility_flags', lambda p: None)

    calls = []
    fake_log = types.ModuleType('run_log')
    fake_log.write = lambda *a, **k: calls.append(a) or (None, None)
    monkeypatch.setitem(sys.modules, 'run_log', fake_log)
    return types.SimpleNamespace(gpb=gpb, gpo=gpo, calls=calls, log=fake_log)


def test_a_failed_analysis_writes_no_record(stub_run):
    def boom():
        raise ValueError('analysis broke')
    stub_run.gpo.main = boom
    with pytest.raises(run.PartialRun):
        run.main()
    assert stub_run.calls == []


def test_a_normal_run_writes_one_record_and_keeps_its_return_code(stub_run):
    assert run.main() == 0
    assert len(stub_run.calls) == 1


def test_a_log_that_raises_does_not_change_the_return_code(stub_run, capsys):
    def boom(*a, **k):
        raise RuntimeError('log broke')
    stub_run.log.write = boom
    assert run.main() == 0
    assert 'Run log: not written' in capsys.readouterr().out


def test_a_project_mismatch_returns_one_and_writes_no_record(stub_run, monkeypatch):
    names = iter(['Other Tower', 'Demo Tower'])
    monkeypatch.setattr(run, '_project_name', lambda path, sheet: next(names))
    assert run.main() == 1
    assert stub_run.calls == []
