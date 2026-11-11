"""Gói site không kèm file ngân sách đã duyệt (--prior bỏ trống), và mã nguồn mang sang gói không nhắc tên dự án nào.

TEST DATA: dự án giả "Du an Gia"; bước quét tên đọc danh sách master thật (chỉ đọc) và chỉ in tên file khi trượt.
"""
import json
import os
import shutil
import subprocess

import pytest

import build_site_package as bsp
import site_data

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # source_code/
DATA = os.path.join(os.path.dirname(HERE), 'data')


@pytest.fixture
def stub_build(tmp_path, monkeypatch):
    """build() without copying the runtime, the source, the data or the office files."""
    copied = []
    monkeypatch.setattr(bsp, 'copy_tree', lambda *a, **k: None)
    monkeypatch.setattr(bsp.site_data, 'build', lambda *a, **k: {'copied': [], 'pseudonyms': {}, 'masked': []})
    monkeypatch.setattr(bsp, 'git_hash', lambda: 'abc1234')
    monkeypatch.setattr(bsp, 'DIAGRAM', str(tmp_path / 'missing.html'))
    real_copy2 = shutil.copy2

    def copy2(src, dst, *a, **k):
        copied.append(os.path.basename(src))
        if str(src).startswith(str(tmp_path)):
            return real_copy2(src, dst, *a, **k)
        return dst

    monkeypatch.setattr(bsp.shutil, 'copy2', copy2)
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    return tmp_path, runtime, copied


def _site(pkg):
    with open(os.path.join(pkg, 'site', 'site.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _guide(pkg):
    with open(os.path.join(pkg, 'HUONG-DAN.txt'), encoding='utf-8-sig') as fh:
        return fh.read()


def test_build_without_prior_leaves_site_folder_empty_and_tells_the_site_to_upload(stub_build):
    tmp_path, runtime, copied = stub_build
    pkg = bsp.build('Du an Gia', '', str(runtime), str(tmp_path / 'out'), {'city': 'Hồ Chí Minh'})
    assert _site(pkg)['prior_file'] == '' and _site(pkg)['code'] == 'abc1234'
    assert os.listdir(os.path.join(pkg, 'site')) == ['site.json']
    g = _guide(pkg)
    assert 'CHƯA kèm ngân sách đã duyệt' in g and 'Tải file lên' in g and 'Nhập liệu dự án mới' in g and '{' not in g
    assert 'file trong thư mục site' not in g


def test_build_with_prior_keeps_the_file_and_the_old_guide(stub_build):
    tmp_path, runtime, copied = stub_build
    prior = tmp_path / 'Du an Gia - da duyet.xlsx'
    prior.write_bytes(b'x')
    pkg = bsp.build('Du an Gia', str(prior), str(runtime), str(tmp_path / 'out'), {})
    assert _site(pkg)['prior_file'] == prior.name
    assert os.path.isfile(os.path.join(pkg, 'site', prior.name))
    g = _guide(pkg)
    assert '(file trong thư mục site\\)' in g and 'Có file duyệt mới hơn' in g and 'CHƯA kèm' not in g


@pytest.fixture
def no_prior_main(tmp_path, monkeypatch):
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'python.exe').write_bytes(b'')
    seen = {}
    monkeypatch.setattr(bsp, 'facts_for', lambda *a, **k: {'city': 'Hồ Chí Minh'})
    monkeypatch.setattr(bsp, '_leak_words', lambda *a, **k: [])

    def fake_build(site, prior, *a, **k):
        seen['prior'] = prior
        return str(tmp_path / 'out' / 'BudgetAgent-Du-an-Gia')

    monkeypatch.setattr(bsp, 'build', fake_build)
    monkeypatch.setattr(bsp, 'check', lambda *a, **k: True)
    monkeypatch.setattr(bsp, 'make_zip', lambda p: p + '.zip')
    return ['--site', 'Du an Gia', '--runtime', str(runtime), '--out', str(tmp_path / 'out')], seen


def test_main_accepts_a_missing_prior(no_prior_main, capsys):
    argv, seen = no_prior_main
    assert bsp.main(argv + ['--zip']) == 0
    assert seen['prior'] == ''
    assert 'không có --prior' in capsys.readouterr().out


def test_main_still_refuses_a_prior_that_is_not_an_xlsx(no_prior_main, tmp_path):
    argv, _ = no_prior_main
    with pytest.raises(SystemExit):
        bsp.main(argv + ['--prior', str(tmp_path / 'khong-co.xlsx')])


@pytest.mark.parametrize('prior_file, reads', [('', False), ('Du an Gia - da duyet.xlsx', True)])
def test_check_reads_the_prior_only_when_the_package_has_one(tmp_path, monkeypatch, prior_file, reads):
    pkg = tmp_path / 'BudgetAgent-Du-an-Gia'
    (pkg / 'site').mkdir(parents=True)
    (pkg / 'site' / 'site.json').write_text(json.dumps({'project': 'Du an Gia', 'prior_file': prior_file}),
                                            encoding='utf-8')
    calls = []

    def fake_run(args, **k):
        calls.append(args[-1])
        return subprocess.CompletedProcess(args, 0, stdout='', stderr='')

    monkeypatch.setattr(bsp.subprocess, 'run', fake_run)
    monkeypatch.setattr(bsp, 'scan_text', lambda p: [])
    assert bsp.check(str(pkg)) is True
    assert (bsp.READ_CHECK in calls) is reads


def test_shipped_source_names_no_project(tmp_path):
    """Every file build() copies from source_code must be free of master-list and registry names, for ANY site
    (a name in a comment slipped through for years because it was the only site ever packaged)."""
    words = site_data.leak_words(DATA, own_names=())
    if not words:
        pytest.skip('office data folder not present')
    dst = tmp_path / 'source_code'
    shutil.copytree(HERE, dst, ignore=bsp.SOURCE_IGNORE)
    leaks = site_data.find_leaks(str(dst), words, skip_dirs=())
    assert not leaks, [p for p, _ in leaks]
