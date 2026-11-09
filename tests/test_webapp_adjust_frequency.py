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


# ---- change fix-stale-frequency-remarks: the button that fixes the flagged remarks (TEST DATA) ----

def _offline(path, freq, first=None, remark=None):
    """The PM changes RM.AP's frequency in Excel on sheet 4 (AE, AF), optionally with a remark of their own."""
    wb = openpyxl.load_workbook(path)
    ws = wb[ba.SHEET_NAME]
    prow = next(r for r in range(ba.FIRST_DATA_ROW, ws.max_row + 1) if ws.cell(row=r, column=1).value == 'RM.AP')
    ws.cell(row=prow, column=ba.COL['new_freq']).value = freq
    ws.cell(row=prow, column=ba.COL['first_month']).value = first
    if remark is not None:
        wb[MF].cell(row=10, column=20).value = remark
    wb.save(path)


def _sheet4_values(wb):
    ws = wb[ba.SHEET_NAME]          # reading creates empty cells, so compare the filled ones
    return {c.coordinate: c.value for row in ws.iter_rows() for c in row if c.value is not None}


def test_fixed_remark_keeps_the_pms_text_and_replaces_the_sentence(deliv):
    it = dict(_items(deliv)['MF|RM.AP'], new_freq='Half a Year', first_month=1)
    old = 'Theo hợp đồng mới.\nHàng quý, 4 lần/năm × 50 VND/lần, chi vào T3, T6, T9, T12'
    assert adjust.fixed_remark(it, old) == 'Theo hợp đồng mới.\n6 tháng/lần, 2 lần/năm × 50 VND/lần, chi vào T1, T7'
    assert adjust.fixed_remark(it, 'Theo hợp đồng mới.') == ('Theo hợp đồng mới.\n'
                                                          '6 tháng/lần, 2 lần/năm × 50 VND/lần, chi vào T1, T7')
    monthly = dict(it, new_freq='Monthly')
    assert adjust.fixed_remark(monthly, old) == 'Theo hợp đồng mới.'


def test_fix_remark_rewrites_only_column_t_and_clears_the_flag(deliv):
    _offline(deliv, 'Yearly', 6, remark='Theo hợp đồng mới.')
    assert _items(deliv)['MF|RM.AP']['remark_stale'] is True
    wb = openpyxl.load_workbook(deliv)
    before = _sheet4_values(wb)
    report = {}
    assert adjust.apply_edits(wb, [dict(key='MF|RM.AP', fix_remark=True)], report=report) == []
    assert _sheet4_values(wb) == before                       # no cell of sheet 4 changes
    assert report == dict(remarks_fixed=['RM.AP'], remarks_skipped=[])
    assert wb[MF].cell(row=10, column=20).value == ('Theo hợp đồng mới.\n'
                                                    'Hàng năm, 1 lần/năm × 50 VND/lần, chi vào T6')
    wb.save(deliv)
    assert _items(deliv)['MF|RM.AP']['remark_stale'] is False


def test_fix_remark_skips_a_line_that_is_no_longer_flagged(deliv):
    wb = openpyxl.load_workbook(deliv)
    report = {}
    adjust.apply_edits(wb, [dict(key='MF|RM.AP', fix_remark=True)], report=report)
    assert report == dict(remarks_fixed=[], remarks_skipped=[])
    assert wb[MF].cell(row=10, column=20).value == openpyxl.load_workbook(deliv)[MF].cell(row=10, column=20).value


def test_fix_remark_leaves_a_formula_remark_and_lists_it(deliv):
    _offline(deliv, 'Yearly', 6, remark='="Theo hợp đồng"')
    wb = openpyxl.load_workbook(deliv)
    report = {}
    adjust.apply_edits(wb, [dict(key='MF|RM.AP', fix_remark=True)], report=report)
    assert wb[MF].cell(row=10, column=20).value == '="Theo hợp đồng"'
    assert report == dict(remarks_fixed=[], remarks_skipped=[('RM.AP', 'remark là công thức Excel')])


def test_a_frequency_save_keeps_a_formula_remark(deliv):
    _offline(deliv, None, remark='="Theo hợp đồng"')
    wb = openpyxl.load_workbook(deliv)
    report = {}
    adjust.apply_edits(wb, [dict(key='MF|RM.AP', adj_type='', inflation=0, subs=[], new_freq='Yearly', first_month=6)],
                       report=report)
    assert wb[MF].cell(row=10, column=20).value == '="Theo hợp đồng"'
    assert report['remarks_skipped'] == [('RM.AP', 'remark là công thức Excel')]


@pytest.mark.parametrize('edits, message', [
    ([dict(key='MF|RM.AP', fix_remark=True, adj_type='Trượt giá')], 'không được kèm thay đổi khác'),
    ([dict(key='MF|RM.AP', fix_remark=True), dict(key='MF|RM.AP', fix_remark=True)], 'gửi hai lần'),
    ([dict(key='MF|NOPE', fix_remark=True)], 'Không có mã'),
])
def test_fix_remark_refusals_write_nothing(deliv, edits, message):
    before = open(deliv, 'rb').read()
    wb = openpyxl.load_workbook(deliv)
    with pytest.raises(adjust.AdjustError, match=message):
        adjust.apply_edits(wb, edits)
    assert open(deliv, 'rb').read() == before
