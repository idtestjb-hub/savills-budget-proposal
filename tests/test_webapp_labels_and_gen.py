"""Danh sách có sẵn ghi rõ trạng thái đối soát (nhãn và câu giải thích có số lệch), và nút Gen budget for new year xám
kèm lý do khi bản giao thuộc năm của mẫu (2026-10-21, sau 9ebb244).

Kho quét giả dựng trong thư mục tạm; tên dự án và tên file đều bịa.
"""
import csv
import os

import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')

from webapp import library, server  # noqa: E402
from tests.test_review_import import build_prior_workbook  # noqa: E402


def _write(path, header, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def year_2027(monkeypatch):
    monkeypatch.setattr(library, '_template_year', {'value': 2027})


def test_confidence_labels_and_notes():
    assert library.CONFIDENCE_VI['medium'] == 'Tổng không khớp'
    assert library.CONFIDENCE_VI['low'] == 'Form cũ, chưa đối soát'
    note = library.confidence_note(dict(status='mismatch', R_diff='-1820000.0', E_diff='0.0', D_diff='0.0'))
    assert note.startswith('cộng các dòng thu thấp hơn dòng tổng của file 1,82 tr') and 'sheet Review' in note
    note = library.confidence_note(dict(status='mismatch', R_diff='0', E_diff='7572780000', D_diff=''))
    assert note.startswith('cộng các dòng chi cao hơn dòng tổng của file 7.572,78 tr')
    assert library.confidence_note(dict(status='no_anchor')) == library.NO_ANCHOR_NOTE
    assert library.confidence_note(dict(status='no_value_col')) == library.NO_VALUE_COL_NOTE
    assert library.confidence_note(dict(status='ok')) == '' and library.confidence_note(None) == ''


def test_entries_carry_the_note_of_the_primary_sheet(tmp_path, year_2027):
    root = tmp_path / 'budget_planning'
    root.mkdir()
    build_prior_workbook(str(root / 'NS 2025 Khu K.xlsx'))
    build_prior_workbook(str(root / 'NS 2024 Khu L.xlsx'))
    st = tmp_path / 'final_v2'
    st.mkdir()
    _write(st / 'dim_file.csv', ['file_id', 'file_name', 'rel_path', 'source_group', 'ext', 'content_dup_of'],
           [('kkk999', 'NS 2025 Khu K.xlsx', 'NS 2025 Khu K.xlsx', 'old8', 'xlsx', ''),
            ('lll000', 'NS 2024 Khu L.xlsx', 'NS 2024 Khu L.xlsx', 'old8', 'xlsx', '')])
    _write(st / 'project_map.csv', ['file_id', 'file_name', 'project_name', 'year_in_name'], [])
    _write(st / 'file_profile.csv', ['file_id', 'primary_confidence', 'primary_sheet', 'budget_year_v2',
                                     'vat_basis_v2', 'nfa_total'],
           [('kkk999', 'medium', '2. Budget-Management Fund', '2025', 'excl', ''),
            ('lll000', 'low', 'Budget 2024 - Management Fund', '2024', 'excl', '')])
    _write(st / 'reconcile.csv', ['file_id', 'sheet', 'status', 'R_diff', 'E_diff', 'D_diff'],
           [('kkk999', '2.1 Report-Management Fund', 'ok', '0', '0', '0'),
            ('kkk999', '2. Budget-Management Fund', 'mismatch', '-1820000', '0', '0'),
            ('lll000', 'Budget 2024 - Management Fund', 'no_anchor', '', '', '')])
    by = {e['id']: e for e in library.load(str(root), str(st))}
    k, l_ = by['kkk999'], by['lll000']
    assert k['selectable'] and k['confidence_vi'] == 'Tổng không khớp' and '1,82 tr' in k['confidence_note']
    assert l_['selectable'] and l_['confidence_vi'] == 'Form cũ, chưa đối soát'
    assert l_['confidence_note'] == library.NO_ANCHOR_NOTE


def test_gen_block_greys_a_deliverable_of_the_template_year(year_2027):
    assert server._gen_block('2027').startswith('Bản giao này là ngân sách năm 2027')
    assert '2028' in server._gen_block(2027)
    assert server._gen_block(2026) == '' and server._gen_block(None) == '' and server._gen_block('') == ''
