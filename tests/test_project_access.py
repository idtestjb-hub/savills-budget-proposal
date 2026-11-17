"""Bộ đọc file phân quyền theo dự án (change budget-web-project-access). TEST DATA: tên và email giả."""
import os
import time

import openpyxl
import pytest

from webapp import project_access as pa
from webapp.make_access_book import build


def _book(path, projects, people):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet('Du an')
    ws.append(['Mã', 'Tên', 'Tên khác'])
    for r in projects:
        ws.append(r)
    ws = wb.create_sheet('Nguoi dung')
    ws.append(['Email', 'Mã dự án'])
    for r in people:
        ws.append(r)
    wb.save(path)
    return str(path)


PROJECTS = [['P012', 'Khu Thử Nghiệm', 'KTN; Khu Thu Nghiem Giai Doan 1'], ['P020', 'Tháp Mây Xanh', '']]


def test_one_project_person(tmp_path):
    acl = pa.load(_book(tmp_path / 'a.xlsx', PROJECTS, [[' PM.A@Example.com ', 'P012']]))
    s = acl.scope_for('pm.a@example.com')
    assert s.kind == pa.KIND_PROJECT and s.codes == {'P012'}
    assert s.may_see('P012') and not s.may_see('P020') and not s.may_see(None)


def test_all_is_office(tmp_path):
    acl = pa.load(_book(tmp_path / 'a.xlsx', PROJECTS, [['boss@example.com', 'all']]))
    s = acl.scope_for('BOSS@example.com')
    assert s.kind == pa.KIND_OFFICE and s.may_see('P020') and s.may_see(None)


def test_unknown_email_sees_nothing(tmp_path):
    acl = pa.load(_book(tmp_path / 'a.xlsx', PROJECTS, [['pm.a@example.com', 'P012']]))
    s = acl.scope_for('someone@example.com')
    assert s.kind == pa.KIND_NONE and not s.may_see('P012')
    assert acl.scope_for('').kind == pa.KIND_NONE


def test_unknown_code_is_dropped_not_widened(tmp_path):
    acl = pa.load(_book(tmp_path / 'a.xlsx', PROJECTS, [['pm.x@example.com', 'P999'], ['pm.y@example.com', 'P012; P999']]))
    assert acl.scope_for('pm.x@example.com').kind == pa.KIND_NONE
    assert acl.scope_for('pm.y@example.com').codes == {'P012'}
    assert any('P999' in w for w in acl.warnings)


def test_duplicate_code_rejects_whole_book(tmp_path):
    with pytest.raises(pa.AccessBookError):
        pa.load(_book(tmp_path / 'a.xlsx', PROJECTS + [['P012', 'Khác', '']], []))


def test_missing_sheet(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = 'Du an'
    wb.active.append(['Ma', 'Ten', 'Ten khac'])
    wb.save(tmp_path / 'b.xlsx')
    with pytest.raises(pa.AccessBookError):
        pa.load(str(tmp_path / 'b.xlsx'))


def test_match_by_name_and_alias():
    acl = pa.AccessList(projects={'P012': dict(name='Khu Thử Nghiệm', aliases=['KTN']),
                                  'P020': dict(name='Tháp Mây Xanh', aliases=[])})
    assert acl.match('KHU THU NGHIEM') == 'P012'
    assert acl.match('khu-thử_nghiệm') == 'P012'
    assert acl.match('ktn') == 'P012'
    assert acl.match('Tháp Mây Xanh') == 'P020'
    assert acl.match('Đồi Gió') is None
    assert acl.match('') is None
    assert acl.names_of('P012') == ['Khu Thử Nghiệm', 'KTN']


def test_fold_vietnamese():
    assert pa.fold('Đường Lê Lợi, Quận 1') == 'duong le loi quan 1'


def test_reader_keeps_previous_list_when_book_breaks(tmp_path):
    path = _book(tmp_path / 'a.xlsx', PROJECTS, [['pm.a@example.com', 'P012']])
    logs = []
    r = pa.Reader(path, interval=0, log=logs.append)
    assert r.current().scope_for('pm.a@example.com').kind == pa.KIND_PROJECT
    time.sleep(0.01)
    wb = openpyxl.Workbook()
    wb.active.title = 'Du an'
    wb.save(path)                                   # sheet Nguoi dung mất
    os.utime(path, None)
    acl = r.current()
    assert acl is not None and acl.scope_for('pm.a@example.com').codes == {'P012'}
    assert r.last_error and any('NOT reloaded' in m for m in logs)


def test_reader_with_no_list_ever(tmp_path):
    r = pa.Reader(str(tmp_path / 'khong-co.xlsx'), interval=0, log=lambda m: None)
    assert r.current() is None


def test_reader_reloads_on_change(tmp_path):
    path = _book(tmp_path / 'a.xlsx', PROJECTS, [['pm.a@example.com', 'P012']])
    r = pa.Reader(path, interval=0, log=lambda m: None)
    assert r.current().scope_for('pm.b@example.com').kind == pa.KIND_NONE
    time.sleep(0.01)
    _book(path, PROJECTS, [['pm.a@example.com', 'P012'], ['pm.b@example.com', 'P020']])
    assert r.current().scope_for('pm.b@example.com').codes == {'P020'}


def test_template_reads_back(tmp_path):
    out = build(str(tmp_path / 'mau.xlsx'), sample=True)
    acl = pa.load(out)
    assert set(acl.projects) == {'P001', 'P002'}
    assert acl.scope_for('pm.ab@example.com').codes == {'P001', 'P002'}
    assert acl.scope_for('office@example.com').kind == pa.KIND_OFFICE
    with pytest.raises(FileExistsError):
        build(out)
