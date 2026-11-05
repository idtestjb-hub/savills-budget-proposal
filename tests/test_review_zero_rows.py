"""review.py: the lines the Review adds to '4. Điều chỉnh' for codes the approved budget carries and the tool prices at 0
(change adjust-rows-for-zero-tool-codes). Invented workbook and figures; no Excel."""
import openpyxl
import pytest

import budget_adjustment as ba
import review
from tests.test_budget_adjustment import MGMT, COMMON, _Eval, _fund_row, _items, _workbook


def _row(code, approved, tool, on_form=True, item=None):
    return dict(code=code, item=item or f'Dòng {code}', approved=approved, tool_num=tool, on_form=on_form)


def _data(*rows, fund='MF', sec='E'):
    return {'rows_by': {(fund, sec): {'rows': list(rows)}}}


def test_zero_tool_rows_keeps_only_approved_with_tool_zero_on_the_form():
    data = _data(_row('A', 100.0, 0.0), _row('B', 100.0, 50.0), _row('C', 0.0, 0.0), _row('D', 100.0, 0.3),
                 _row('E', 100.0, 0.0, on_form=False), _row('F', -80.0, 0.0))
    assert [(f, r['code']) for f, r in review.zero_tool_rows(data)] == [('MF', 'A'), ('MF', 'D'), ('MF', 'F')]


def _deliverable(tmp_path, extra=()):
    wb = _workbook()
    ba.apply(wb, _items())
    for code, row, freq in extra:
        _fund_row(wb[MGMT], row, code, freq, [None] * 12)
        wb[MGMT].cell(row=row, column=6).value = None
    wb[MGMT].cell(row=31, column=25, value='GRP')                       # a group row: SUBTOTAL, no =SUM(AQ
    wb[MGMT].cell(row=31, column=37, value='=SUBTOTAL(9,AK32:AK33)')
    p = str(tmp_path / 'deliverable.xlsx')
    wb.save(p)
    return p


def test_add_zero_rows_appends_linked_lines_and_logs_the_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr('generate_project_output._strip_onedrive_zip_artifacts', lambda *a, **k: None)
    p = _deliverable(tmp_path, extra=[('ESS99', 30, 'Monthly'), ('ESS98', 32, 'Schedule')])
    rows = [('MF', _row('ESS99', 120.0, 0.0)), ('MF', _row('ESS98', 60.0, 0.0)), ('MF', _row('GRP', 5.0, 0.0)),
            ('MF', _row('NOPE', 5.0, 0.0)), ('MF', _row('ESS1', 5.0, 0.0))]
    added, skipped = review.add_zero_rows(p, rows)
    assert added == ['MF|ESS99', 'MF|ESS98']
    assert [k for k, _ in skipped] == ['MF|GRP', 'MF|NOPE', 'MF|ESS1']      # ESS1 is already on the sheet
    wb = openpyxl.load_workbook(p)
    ws = wb[ba.SHEET_NAME]
    assert [ws.cell(row=r, column=1).value for r in (14, 16)] == ['ESS99', 'ESS98']
    assert (ws['P14'].value, ws['Q14'].value, ws['R14'].value) == (MGMT, 30, 'Monthly')
    assert ws['R16'].value == 'Schedule' and ws['B14'].value == 'Dòng ESS99'
    ev = _Eval(wb)                                                    # untouched: still zero
    assert ev.cell(MGMT, 'AK30') == 0 and ev.cell(MGMT, 'AK32') == 0
    ws['D14'], ws['K15'] = 'Nhập số', 1_200_000.0                     # a typed figure moves the fund line
    ws['D16'], ws['K17'] = 'Nhập số', 600_000.0
    ev = _Eval(wb)
    assert ev.cell(MGMT, 'AK30') == 1_200_000.0 and ev.cell(MGMT, 'S30') == 100_000.0
    assert ev.cell(MGMT, 'AK32') == 600_000.0 and ev.cell(MGMT, 'H32') == 50_000.0


def test_a_blank_frequency_becomes_monthly(monkeypatch, tmp_path):
    monkeypatch.setattr('generate_project_output._strip_onedrive_zip_artifacts', lambda *a, **k: None)
    p = _deliverable(tmp_path, extra=[('ESS97', 34, 'Yearly')])
    added, _ = review.add_zero_rows(p, [('MF', _row('ESS97', 10.0, 0.0))])
    assert added == ['MF|ESS97']
    wb = openpyxl.load_workbook(p)
    assert wb[MGMT]['C34'].value == 'Monthly' and wb[ba.SHEET_NAME]['R14'].value == 'Monthly'


def test_nothing_to_add_leaves_the_file_alone(tmp_path):
    p = _deliverable(tmp_path)
    before = open(p, 'rb').read()
    assert review.add_zero_rows(p, []) == ([], [])
    assert open(p, 'rb').read() == before


def test_common_area_fund_uses_its_own_layout(monkeypatch, tmp_path):
    monkeypatch.setattr('generate_project_output._strip_onedrive_zip_artifacts', lambda *a, **k: None)
    wb = _workbook()
    ba.apply(wb, _items())
    ws = wb[COMMON]
    ws.cell(row=40, column=25, value='RA9')
    ws.cell(row=40, column=3, value='Monthly')
    ws.cell(row=40, column=33, value='=SUM(AL40:AW40)')                # CA annual is column AG, first month AL
    p = str(tmp_path / 'd.xlsx')
    wb.save(p)
    added, skipped = review.add_zero_rows(p, [('CA', _row('RA9', 9.0, 0.0, item='Quảng cáo khác'))])
    assert added == ['CA|RA9'] and not skipped
    ws4 = openpyxl.load_workbook(p)[ba.SHEET_NAME]
    assert (ws4['A14'].value, ws4['P14'].value, ws4['Q14'].value, ws4['B14'].value) == ('RA9', COMMON, 40, 'Quảng cáo khác')
