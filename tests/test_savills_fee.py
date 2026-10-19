"""Group 7 of change apply-head-of-pm-decisions-2026-10 (design D9c): Savills' fee EMH1 (B1), the ERCS1 reason
(B7), the parking break-even cells BK507/BK511 (B10) and the '1. Summary' K14 revenue sentence (K14)."""
import re
import shutil

import openpyxl
import pytest

import breakeven_cells as be
import generate_project_budget as gpb
import operating_inputs as oi
import savills_fee as sf
from verification import checks

FIXTURE = 'verification/fixtures/Sample_Project_Input.xlsx'
# A cell address in any form a remark used to carry: 'Project Info!B36', 'B34', 'AC92'.
CELL_ADDRESS = re.compile(r'![A-Z]{1,3}\d+|\b[A-Z]{1,2}\d{2,3}\b')


def _no_address(text):
    assert not CELL_ADDRESS.search(text), CELL_ADDRESS.search(text).group(0)


# ---- 7.1 EMH1 ----

def test_fixed_fee_adds_each_months_vat_and_names_the_field():
    months, remark = sf.fixed_line(50_000_000, [1.08] * 3 + [1.10] * 9, 'cộng VAT 8% (01-03/2027), 10% (04-12/2027) '
                                                                       'theo từng tháng')
    assert months[0] == pytest.approx(54_000_000) and months[11] == pytest.approx(55_000_000)
    assert sum(months) == pytest.approx(3 * 54_000_000 + 9 * 55_000_000)
    for part in (sf.FIXED_LABEL, 'chưa gồm VAT', '600,000,000', f'{sum(months):,.0f}', '8%'):
        assert part in remark
    _no_address(remark)


def test_fixed_fee_under_khoan_adds_no_vat():
    months, remark = sf.fixed_line(50_000_000, [1.0] * 12, 'chưa cộng VAT theo mô hình tài chính đã chọn')
    assert months == [50_000_000] * 12
    assert 'chưa cộng VAT' in remark


def test_percent_fee_is_a_share_of_the_full_fee_with_no_vat_added():
    months, remark = sf.percent_line(0.10, 12_000_000_000)
    assert months == [100_000_000] * 12
    for part in (sf.PCT_LABEL, '10.0%', 'RM.0A', '12,000,000,000', '1,200,000,000', 'Không cộng thêm VAT'):
        assert part in remark
    _no_address(remark)


def test_zero_reason_and_stop_message_name_both_fields_by_label():
    for text in (sf.ZERO_REASON_VI, sf.both_filled_message()):
        assert sf.FIXED_LABEL in text and sf.PCT_LABEL in text
        _no_address(text)


@pytest.mark.parametrize('project, expected, absent', [
    ({'savills_fee_fixed_monthly': 50_000_000}, 'cố định', 'tỷ lệ'),
    ({'savills_fee_pct': 0.1}, 'tỷ lệ 10.0%', 'cố định'),
    ({}, 'chưa dự ước', 'cố định'),
])
def test_summary_clause_names_the_basis_used(project, expected, absent):
    text = sf.summary_clause_vi(project, 660_000_000)
    assert expected in text and absent not in text


def test_analysis_rows_show_the_entered_fee_or_not_entered():
    fixed = sf.analysis_rows({'savills_fee_fixed_monthly': 50_000_000}, "'Management Fee'!B9")
    assert fixed[1][1] == 50_000_000 and fixed[2][1] == 600_000_000
    pct = sf.analysis_rows({'savills_fee_pct': 0.1}, "'Management Fee'!B9")
    assert pct[2][1] == "=0.1*'Management Fee'!B9"
    blank = sf.analysis_rows({}, "'Management Fee'!B9")
    assert [v for _l, v, _f in blank] == [sf.NOT_ENTERED_VI] * 3


def _fee_input(tmp_path, fixed, pct):
    path = tmp_path / 'input.xlsx'
    shutil.copy(FIXTURE, path)
    wb = openpyxl.load_workbook(path)
    ws = wb['Project Info']
    for r in range(1, ws.max_row + 1):
        a = ws.cell(row=r, column=1).value
        if isinstance(a, str) and a.startswith(sf.FIXED_LABEL):
            ws.cell(row=r, column=2, value=fixed)
        elif isinstance(a, str) and a.startswith(sf.PCT_LABEL):
            ws.cell(row=r, column=2, value=pct)
    wb.save(path)
    return str(path)


def test_both_fields_filled_stops_the_run_naming_both_labels(tmp_path):
    with pytest.raises(ValueError) as exc:
        gpb.read_input(_fee_input(tmp_path, 50_000_000, 0.1))
    assert sf.FIXED_LABEL in str(exc.value) and sf.PCT_LABEL in str(exc.value)
    _no_address(str(exc.value))


def test_one_field_filled_is_read(tmp_path):
    project = gpb.read_input(_fee_input(tmp_path, None, 0.1))[0]
    assert sf.basis(project) == sf.PERCENT and project['savills_fee_pct'] == pytest.approx(0.1)


# ---- 7.2 ERCS1 ----

def test_ercs1_reason_says_residential_quotes_are_awaited():
    assert 'đang chờ báo giá dịch vụ cho chung cư' in gpb.ERCS1_REASON_VI.lower()
    assert 'đơn giá' in gpb.ERCS1_REASON_VI      # still says no sourced unit price exists


# ---- 7.3 BK507 / BK511 ----

def _breakeven_sheet(be_formula='=-BK505/BK10', ch_formula='=BK507+BK509', extra_label=False):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = be.SHEET
    ws['BG507'], ws['BK507'] = 'Gía dịch vụ quản lý  cân bằng', be_formula      # double space: matched loosely
    ws['BG509'], ws['BK509'] = 'Gía dịch vụ quản lý hiện tại', "='0. Info'!I12"
    ws['BG511'], ws['BK511'] = 'Gía dịch vụ quản lý cần tăng / giảm', ch_formula
    if extra_label:
        ws['BG600'] = 'Gía dịch vụ quản lý cân bằng'
    return ws


def test_breakeven_cells_are_guarded_live_formulas():
    ws = _breakeven_sheet()
    written = be.guard(ws)
    assert ws['BK507'].value == '=IF(N(BK10)=0,"N/A",-BK505/BK10)'
    assert ws['BK511'].value == '=IF(ISNUMBER(BK507),BK507+BK509,"N/A")'
    assert set(written) == {'BK507', 'BK511'}
    assert ws['BJ507'].value is None                    # only BK is touched


@pytest.mark.parametrize('kwargs', [dict(be_formula='=BK505/BK10'), dict(ch_formula='=BK508+BK509'),
                                    dict(extra_label=True)])
def test_breakeven_cells_stop_on_a_changed_template(kwargs):
    with pytest.raises(ValueError, match='B10'):
        be.guard(_breakeven_sheet(**kwargs))


def test_breakeven_label_missing_stops():
    ws = _breakeven_sheet()
    ws['BG511'] = None
    with pytest.raises(ValueError, match='cần tăng'):
        be.guard(ws)


# ---- 7.4 K14 ----

def test_k14_ends_with_the_revenue_sentence(monkeypatch):
    wb = openpyxl.Workbook()
    wb.active.title = '2. Budget-Management Fund'
    wb.active['AL5'] = 2027
    monkeypatch.setattr(gpb, '_UNIT_RATES', {'RM.AP': 15_000})
    monkeypatch.setattr(gpb, '_ENTERED_RATE_VAT', {})
    project = {'products': {'Apartment': {'nfa': 10_000}}}
    written = {'RM.AP': {'row': 14, 'value': 1, 'name_vi': 'Căn hộ', 'name_en': 'Apartment'},
               'RM.0A': {'row': 23, 'value': 5_000, 'name_vi': 'CĐT', 'name_en': 'Developer'}}
    k = gpb._recipe_narrative('RM', wb, project, [], 2026, written)
    assert k.endswith(oi.entered_rate_year_vi('2027'))
    monkeypatch.setattr(gpb, '_ACTIVE_VAT_SENTENCE', 'Chi phí hạng mục này đã bao gồm VAT và dự ước tại năm 2027.')
    assert gpb._append_vat(k) == k                       # the generic VAT sentence is not added after it


@pytest.mark.parametrize('k, ok', [
    ('Dự ước doanh thu...\nDoanh thu hạng mục này dự ước tại năm 2027.', True),
    ('Dự ước doanh thu...', False),
    ('Dự ước doanh thu...\nChi phí hạng mục này đã bao gồm VAT và dự ước tại năm 2027.', False),
    ('Doanh thu hạng mục này dự ước tại năm 2027.\nChi phí hạng mục này đã bao gồm VAT và dự ước tại năm 2027.',
     False),
])
def test_k14_check(k, ok):
    problem = checks.k14_revenue_sentence_problem(
        k, '2027', 'Chi phí hạng mục này đã bao gồm VAT và dự ước tại năm 2027.')
    assert (problem is None) == ok
