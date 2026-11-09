"""The web adjust table and a code's frequency (change add-line-frequency, spec budget-web-adjust-table, task 4.1):
reading the frequency cells, the preview rule, the refusals, saving and reopening, the remark sentence and the
upgrade of an older sheet. Invented workbook and figures (TEST DATA); no Excel."""
import openpyxl
import pytest

import budget_adjustment as ba
from tests.test_budget_adjustment import _Eval
from tests.test_webapp_adjust import CA, DELIV, MF, _deliverable
from webapp import adjust


@pytest.fixture
def deliv(tmp_path):
    return _deliverable(str(tmp_path / DELIV))


def _items(path):
    return {i['key']: i for i in adjust.read_items(path)}


def _save(path, edits):
    wb = openpyxl.load_workbook(path)
    adjust.apply_edits(wb, edits)
    wb.save(path)
    return wb


def test_read_items_carries_the_frequency(deliv):
    it = _items(deliv)['MF|RM.AP']
    assert (it['freq'], it['freq_label'], it['orig_times'], it['orig_first']) == (
        'Monthly', 'Hàng tháng (Monthly)', 12, 1)
    assert it['new_freq'] == '' and it['first_month'] is None and it['freq_editable']
    assert it['ticks'] == [False] * 12 and it['remark_stale'] is False


def test_preview_quarterly_is_four_twelfths_of_the_adjusted_amount(deliv):
    it = _items(deliv)['MF|RM.AP']
    freq = dict(new_freq='Quarterly', first_month=3)
    assert adjust.new_amount(it, freq=freq) == 600.0 * 4 / 12
    assert adjust.new_amount(it, adj_type='Trượt giá', inflation=0.10, freq=freq) == pytest.approx(600 * 1.1 * 4 / 12)
    assert adjust.freq_months(dict(it, **freq)) == ('Quarterly', [3, 6, 9, 12])
    assert adjust.freq_sentence(it, freq=freq) == 'Hàng quý, 4 lần/năm × 50 VND/lần, chi vào T3, T6, T9, T12'


def test_preview_optional_and_schedule(deliv):
    it = _items(deliv)['MF|RM.AP']
    ticks = [m in (2, 7, 11) for m in range(1, 13)]
    assert adjust.new_amount(it, freq=dict(new_freq='Optional', ticks=ticks)) == 150.0
    amounts = [10.0] * 6 + [None] * 6
    assert adjust.new_amount(it, adj_type='Đơn giá', freq=dict(new_freq='Schedule', month_amounts=amounts)) == 60.0


def test_save_and_reopen_shows_quarterly_and_t3(deliv):
    wb = _save(deliv, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], new_freq='Quarterly', first_month=3)])
    ws = wb[ba.SHEET_NAME]
    prow = next(r for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1) if ws.cell(row=r, column=1).value == 'RM.AP')
    assert (ws.cell(row=prow, column=ba.COL['new_freq']).value, ws.cell(row=prow, column=ba.COL['first_month']).value) \
        == ('Quarterly', 3)
    assert _Eval(wb).cell(ba.SHEET_NAME, f'M{prow}') == 200.0
    it = _items(deliv)['MF|RM.AP']
    assert (it['new_freq'], it['first_month']) == ('Quarterly', 3)
    assert wb[MF].cell(row=10, column=20).value == 'Hàng quý, 4 lần/năm × 50 VND/lần, chi vào T3, T6, T9, T12'
    assert it['remark_stale'] is False


def test_the_sentence_replaces_the_last_line_and_keeps_the_pms_text(deliv):
    _save(deliv, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], remark='Theo hợp đồng mới.',
                       new_freq='Yearly', first_month=12)])
    wb = _save(deliv, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], new_freq='Half a Year', first_month=6)])
    assert wb[MF].cell(row=10, column=20).value == ('Theo hợp đồng mới.\n'
                                                    '6 tháng/lần, 2 lần/năm × 50 VND/lần, chi vào T6, T12')
    wb = _save(deliv, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], new_freq='')])
    assert wb[MF].cell(row=10, column=20).value == 'Theo hợp đồng mới.'


def test_an_offline_frequency_edit_flags_the_remark(deliv):
    wb = openpyxl.load_workbook(deliv)
    ws = wb[ba.SHEET_NAME]
    prow = next(r for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1) if ws.cell(row=r, column=1).value == 'RM.AP')
    ws.cell(row=prow, column=ba.COL['new_freq']).value = 'Yearly'
    wb.save(deliv)
    assert _items(deliv)['MF|RM.AP']['remark_stale'] is True


@pytest.mark.parametrize('freq, message', [
    (dict(new_freq='Optional', ticks=[True] * 12), 'chọn Hàng tháng khi chi đủ 12 tháng'),
    (dict(new_freq='Optional', ticks=[False] * 12), 'chọn Hàng tháng khi chi đủ 12 tháng'),
    (dict(new_freq='Quarterly', first_month=5), 'Tháng đầu của Hàng quý phải là T1, T2 hoặc T3'),
    (dict(new_freq='Schedule', month_amounts=[-1] + [0] * 11), 'không được âm'),
    (dict(new_freq='Weekly'), 'không hợp lệ'),
])
def test_refusals_write_nothing(deliv, freq, message):
    before = open(deliv, 'rb').read()
    wb = openpyxl.load_workbook(deliv)
    with pytest.raises(adjust.AdjustError, match=message):
        adjust.apply_edits(wb, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], **freq)])
    assert open(deliv, 'rb').read() == before


def test_an_edit_without_frequency_keys_leaves_the_cells(deliv):
    _save(deliv, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], new_freq='Yearly', first_month=12)])
    _save(deliv, [dict(key='MF|RM.AP', adj_type='Trượt giá', inflation=0.05, subs=[])])
    it = _items(deliv)['MF|RM.AP']
    assert (it['new_freq'], it['first_month'], it['adj_type']) == ('Yearly', 12, 'Trượt giá')


def test_a_code_without_detail_rows_on_the_common_area_fund(deliv):
    wb = _save(deliv, [dict(key='CA|ESS4', adj_type='', inflation=0, subs=[], new_freq='Monthly')])
    ws = wb[ba.SHEET_NAME]
    prow = next(r for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1) if ws.cell(row=r, column=1).value == 'ESS4')
    it = _items(deliv)['CA|ESS4']                     # original Yearly x1 (fixture), 60 a year -> Monthly x12
    assert it['orig_times'] == 1 and _Eval(wb).cell(ba.SHEET_NAME, f'M{prow}') == 720.0
    assert adjust.new_amount(it) == 720.0
