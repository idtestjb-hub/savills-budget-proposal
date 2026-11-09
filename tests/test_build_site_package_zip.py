"""--zip luôn chạy bước kiểm và không nén khi kiểm không đạt (build_site_package.main). TEST DATA: dự án giả."""
import pytest

import build_site_package as bsp


@pytest.fixture
def calls(tmp_path, monkeypatch):
    prior = tmp_path / 'Du an Gia - da duyet.xlsx'
    prior.write_bytes(b'')
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'python.exe').write_bytes(b'')
    pkg = tmp_path / 'out' / 'BudgetAgent-Du-an-Gia'
    log = {'check': 0, 'zip': 0, 'result': True}

    monkeypatch.setattr(bsp, 'facts_for', lambda *a, **k: {'city': 'Hồ Chí Minh'})
    monkeypatch.setattr(bsp, 'build', lambda *a, **k: str(pkg))
    monkeypatch.setattr(bsp, '_leak_words', lambda *a, **k: [])

    def fake_check(p, words=None):
        log['check'] += 1
        return log['result']

    def fake_zip(p):
        log['zip'] += 1
        return p + '.zip'

    monkeypatch.setattr(bsp, 'check', fake_check)
    monkeypatch.setattr(bsp, 'make_zip', fake_zip)
    log['argv'] = ['--site', 'Du an Gia', '--prior', str(prior), '--runtime', str(runtime),
                   '--out', str(tmp_path / 'out')]
    return log


def test_zip_without_check_flag_still_checks(calls):
    assert bsp.main(calls['argv'] + ['--zip']) == 0
    assert calls['check'] == 1
    assert calls['zip'] == 1


def test_zip_refused_when_check_fails(calls, capsys):
    calls['result'] = False
    assert bsp.main(calls['argv'] + ['--zip', '--check']) == 1
    assert calls['zip'] == 0
    assert 'KHÔNG nén' in capsys.readouterr().out


def test_zip_refused_when_check_fails_even_without_check_flag(calls):
    calls['result'] = False
    assert bsp.main(calls['argv'] + ['--zip']) == 1
    assert calls['zip'] == 0


def test_no_zip_no_check_builds_only(calls):
    assert bsp.main(calls['argv']) == 0
    assert calls['check'] == 0
    assert calls['zip'] == 0
