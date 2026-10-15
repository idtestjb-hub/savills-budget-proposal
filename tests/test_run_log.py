"""Unit tests for run_log.py (change add-budget-run-log, spec budget-run-log).

Covered: the record's file name and the never-overwrite rule; the guard (a read-only folder, no Excel, a missing
sheet or label never raise and never write a 0 for a figure that was not read); and, where Excel is installed, the
measurement itself on a small INVENTED workbook with live formulas: the three classes of Required line, the
form-placeholder and EMA1-4 exceptions, group rows left out, a missing code, revenue / expense / surplus, the VAT
basis, error cells and the analysis profit fields read by label.
Not covered: the real deliverable's shape (verification/verify.py compares the record with an independent reading on the
synthetic project).

Invented project names and figures only. The Excel tests are skipped on a PC without Excel.
"""
import json
import os

import openpyxl
import pytest

import run_log


def _input_form(path, name='Invented Tower A', mode=None, stable='Yes'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Project Info'
    ws['A1'], ws['B1'] = 'Project Name', name
    ws['A2'], ws['B2'] = 'Project Mode', mode
    ws['A3'], ws['B3'] = 'Stable Operation?', stable
    wb.save(path)


def _required_csv(path, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('# invented classification\ncode,sheet,requirement_level,row\n')
        for code, sheet in rows:
            f.write(f'{code},{sheet},Required,1\n')
        f.write('NOPE,2. Budget-Management Fund,Optional,1\n')


def _deliverable(path, with_r_row=True):
    wb = openpyxl.Workbook()
    mf = wb.active
    mf.title = '2. Budget-Management Fund'
    mf['F7'] = 'KHOÁN'          # the form's switch: KHOÁN = amounts exclude VAT; anything else = inclusive
    mf.cell(5, 37, 'Budget Year:\nDự toán của năm:')
    mf.cell(5, 38, 2027)

    def put(r, code, g, remark=None):
        mf.cell(r, 25, code)
        mf.cell(r, 7, g)
        if remark:
            mf.cell(r, 20, remark)
    if with_r_row:
        put(12, 'R', '=SUBTOTAL(9,G13:G14)')
    put(13, 'RM.AP', 100)
    put(14, 'RP1', 0, 'chưa có dữ liệu')
    put(79, 'E', '=SUBTOTAL(9,G80:G84)')
    put(80, 'EMA1', 0)
    put(81, 'EMA15', 0, 'gộp các khoản văn phòng')
    put(82, 'ESS1', 40)
    put(83, 'ESS2', 0)
    ca = wb.create_sheet('2.2 Common area Fund')
    ca.cell(10, 25, 'RP5')
    ca.cell(10, 7, 0)
    ca.cell(10, 20, 'demo')
    other = wb.create_sheet('Other')
    other['A1'] = '=1/0'
    wb.save(path)


def _analysis(path, with_profit=True):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Summary'
    ws['A11'], ws['B11'] = 'View:', 'Must-Have Only'
    if with_profit:
        ws['A19'], ws['B19'] = 'Total Profit Value = Mgmt Fee Revenue (3) - costs', '=B35-300'
    ws['A35'], ws['B35'] = '(3) Annual Management Fee Revenue (VND)', 1000
    wb.save(path)


REQUIRED = [('RM.AP', '2. Budget-Management Fund'), ('RP1', '2. Budget-Management Fund'),
            ('EMA1', '2. Budget-Management Fund'), ('ESS1', '2. Budget-Management Fund'),
            ('ESS2', '2. Budget-Management Fund'), ('R', '2. Budget-Management Fund'),
            ('ZZZ', '2. Budget-Management Fund'), ('RP5', '2.2 Common area Fund')]


@pytest.fixture
def files(tmp_path):
    d = {k: str(tmp_path / v) for k, v in (('input', 'in.xlsx'), ('deliv', 'Invented Tower A - Budget.xlsx'),
                                           ('analysis', 'out.xlsx'), ('csv', 'req.csv'))}
    _input_form(d['input'])
    _deliverable(d['deliv'])
    _analysis(d['analysis'])
    _required_csv(d['csv'], REQUIRED)
    d['log'] = str(tmp_path / 'run_log')
    return d


# ---- no Excel needed ---------------------------------------------------------------------------------------------
def test_slug_folds_accents_and_spaces():
    assert run_log._slug('Chung cư Đảo Xanh (Giai đoạn 2)') == 'Chung-cu-Dao-Xanh-Giai-doan-2'
    assert run_log._slug('') == 'project'
    assert len(run_log._slug('x' * 100)) == 40


def test_two_records_in_the_same_second_never_overwrite(tmp_path):
    rec = {'run_id': '20261013-120000', 'project_name': 'Invented Tower A', 'status': 'ok'}
    p1 = run_log.write_record(rec, str(tmp_path))
    p2 = run_log.write_record(dict(rec, status='second'), str(tmp_path))
    assert p1 != p2 and os.path.basename(p2).endswith('-2.json')
    assert json.load(open(p1, encoding='utf-8'))['status'] == 'ok'


def test_record_parses_back_to_the_same_values(tmp_path):
    rec = run_log._blank_record(__import__('datetime').datetime(2026, 10, 13, 9, 5, 7), [])
    rec['project_name'] = 'Chung cư Đảo Xanh'
    p = run_log.write_record(rec, str(tmp_path))
    assert json.load(open(p, encoding='utf-8')) == rec


def test_no_excel_gives_blank_figures_and_a_status(files, monkeypatch, capsys):
    def boom(*_a, **_k):
        raise run_log.ExcelUnavailable('no excel')
    monkeypatch.setattr(run_log, '_excel_measure', boom)
    path, rec = run_log.write(files['deliv'], files['analysis'], files['input'], files['csv'], log_dir=files['log'])
    assert path and os.path.exists(path)
    assert rec['status'] == 'excel_unavailable'
    assert rec['project_name'] == 'Invented Tower A' and rec['deliverable_file'].endswith('Budget.xlsx')
    assert rec['stable_operation'] is True and rec['project_mode'] == 'New prospect'
    for k in ('revenue_vnd', 'expense_vnd', 'fund_surplus_vnd', 'savills_profit_vnd', 'required_total', 'required_pct',
              'error_cells'):
        assert rec[k] is None, k
    assert 'Run log:' in capsys.readouterr().out


def test_unwritable_folder_warns_and_does_not_raise(files, monkeypatch, capsys):
    monkeypatch.setattr(run_log, '_excel_measure', lambda *a, **k: {})

    def deny(*_a, **_k):
        raise PermissionError('read-only')
    monkeypatch.setattr(run_log.os, 'makedirs', deny)
    path, rec = run_log.write(files['deliv'], files['analysis'], files['input'], files['csv'], log_dir=files['log'])
    assert path is None and rec is not None
    assert 'no record written' in capsys.readouterr().out


def test_an_exception_while_measuring_is_a_warning(files, monkeypatch, capsys):
    monkeypatch.setattr(run_log, 'measure', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom')))
    assert run_log.write(files['deliv'], files['analysis'], files['input'], files['csv'], log_dir=files['log']) == (None, None)
    assert 'Run log:' in capsys.readouterr().out


def test_missing_classification_file_is_a_status_not_an_error(files, monkeypatch):
    monkeypatch.setattr(run_log, '_excel_measure', lambda *a, **k: {})
    rec = run_log.measure(files['deliv'], files['analysis'], files['input'], files['csv'] + '.missing')
    assert 'classification_unreadable' in rec['status']


# ---- Excel needed ------------------------------------------------------------------------------------------------
def _excel_or_skip():
    pytest.importorskip('win32com.client')
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        xl = win32com.client.DispatchEx('Excel.Application')
        xl.Quit()
        pythoncom.CoUninitialize()
    except Exception:
        pytest.skip('Excel cannot be driven on this PC')


def test_measurement_on_an_invented_workbook(files):
    _excel_or_skip()
    rec = run_log.measure(files['deliv'], files['analysis'], files['input'], files['csv'])
    assert rec['status'] == 'ok', rec['status']
    # RM.AP, ESS1 filled; RP1 and EMA1 (disclosed on EMA15) zero with a reason; ESS2 and RP5 (form placeholder) no reason;
    # R is a SUBTOTAL row (left out); ZZZ is not on the deliverable.
    assert (rec['required_filled'], rec['required_zero_with_reason'], rec['required_zero_no_reason']) == (2, 2, 2)
    assert rec['required_total'] == 6 and rec['required_missing_from_deliverable'] == 1
    assert rec['required_pct'] == pytest.approx(2 / 6)
    assert (rec['revenue_vnd'], rec['expense_vnd'], rec['fund_surplus_vnd']) == (100, 40, 60)
    assert rec['vat_basis'] == 'exclusive' and rec['budget_year'] == 2027
    assert rec['error_cells'] == 1
    assert rec['savills_profit_vnd'] == 700 and rec['mgmt_fee_revenue_vnd'] == 1000
    assert rec['profit_cost_basis'] == 'Must-Have Only'


def test_a_missing_revenue_row_leaves_revenue_and_surplus_blank(files):
    _excel_or_skip()
    _deliverable(files['deliv'], with_r_row=False)
    rec = run_log.measure(files['deliv'], files['analysis'], files['input'], files['csv'])
    assert rec['revenue_vnd'] is None and rec['fund_surplus_vnd'] is None
    assert rec['expense_vnd'] == 40
    assert 'missing_row:R' in rec['status']


def test_a_missing_profit_label_leaves_profit_blank_and_the_rest_filled(files):
    _excel_or_skip()
    _analysis(files['analysis'], with_profit=False)
    rec = run_log.measure(files['deliv'], files['analysis'], files['input'], files['csv'])
    assert rec['savills_profit_vnd'] is None and rec['mgmt_fee_revenue_vnd'] == 1000
    assert 'missing_label:Total Profit Value' in rec['status']
    assert rec['revenue_vnd'] == 100


def test_the_output_files_are_not_changed(files):
    _excel_or_skip()
    before = {k: (os.path.getmtime(files[k]), os.path.getsize(files[k])) for k in ('deliv', 'analysis')}
    run_log.write(files['deliv'], files['analysis'], files['input'], files['csv'], log_dir=files['log'])
    assert before == {k: (os.path.getmtime(files[k]), os.path.getsize(files[k])) for k in ('deliv', 'analysis')}
    assert len(os.listdir(files['log'])) == 1
