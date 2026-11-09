"""Lines left for the PM (change leave-unpriced-lines-for-pm, spec pm-filled-lines): the kind of each zero, the
"Nhập số" row on sheet 4 marked "PM điền", the shaded blank fund cells, the web remark lead and the static check.
TEST DATA: invented workbook and figures, no Excel."""
import openpyxl
import pytest

import budget_adjustment as ba
import generate_project_budget as gpb
import real_budget_ranges as rbr
from tests.test_budget_adjustment import MGMT, _fund_row, _items, _workbook
from verification import checks
from webapp import adjust


@pytest.fixture(autouse=True)
def _clean_registries():
    gpb._PM_LINES.clear()
    gpb._ZERO_REASONS.clear()
    yield
    gpb._PM_LINES.clear()
    gpb._ZERO_REASONS.clear()


# ---- kind of each zero --------------------------------------------------------------------------
def test_zero_reason_kind_decides_the_lead_and_the_registry():
    ws = openpyxl.Workbook().active
    gpb._write_zero_reason(ws, 5, 'ESM6', 'Chưa có phương pháp định giá được ghi nhận.', 'A')
    gpb._write_zero_reason(ws, 6, 'ESS23', 'dự án không có hồ bơi.', gpb.ZERO_KIND)
    assert ws.cell(row=5, column=20).value.startswith('PM điền: Chưa có phương pháp')
    assert ws.cell(row=6, column=20).value.startswith('Để ở mức 0: dự án không có hồ bơi')
    assert gpb._PM_LINES == {'ESM6': dict(row=5, kind='A', reason='Chưa có phương pháp định giá được ghi nhận.')}
    assert set(gpb._ZERO_REASONS) == {'ESM6', 'ESS23'}


def test_zero_reason_needs_a_known_kind():
    with pytest.raises(ValueError):
        gpb._write_zero_reason(openpyxl.Workbook().active, 5, 'X1', 'lý do', 'pm')


def test_range_reasons_carry_pm_fill_only_for_missing_data():
    rows = {}                                    # a values file with no project for the code: fewer than 10
    no_file = rbr.price_line('ESC2', None, nfa=10_000, vat_rate=0.1)
    too_few = rbr.price_line('ESC2', rows, nfa=10_000, vat_rate=0.1)
    no_pool = rbr.price_line('ESS23', rows, nfa=10_000, vat_rate=0.1, has_pool=False)
    assert (no_file.pm_fill, too_few.pm_fill, no_pool.pm_fill) == (True, True, False)


def test_no_method_list_kind_a_excludes_emo2_and_the_priced_codes():
    assert 'EMO2' not in gpb.PM_KIND_A_CODES and 'EMO2' in gpb._NO_METHOD_ZERO_CODES
    assert not set(gpb.PM_KIND_A_CODES) & set(gpb.REAL_BUDGET_RANGE_ROWS)
    assert len(gpb.PM_KIND_A_CODES) == 16


# ---- sheet 4 rows and the fund cells -------------------------------------------------------------
def _with_pm_line(code='ESS99', row=30):
    wb = _workbook()
    ba.apply(wb, _items())
    _fund_row(wb[MGMT], row, code, 'Monthly', [None] * 12)
    wb[MGMT].cell(row=row, column=6).value = None
    wb[MGMT].cell(row=row, column=20, value='PM điền: Chưa có phương pháp định giá được ghi nhận.')
    return wb


def test_add_pm_rows_marks_the_row_presets_nhap_so_and_shades_the_fund_cells():
    wb = _with_pm_line()
    added, skipped = ba.add_pm_rows(wb, [dict(code='ESS99', name='Dòng thử', reason='Chưa có phương pháp.')],
                                    MGMT, 'AK', 'AQ')
    assert (added, skipped) == (['ESS99'], [])
    ws = wb[ba.SHEET_NAME]
    (prow, reason), = [v for (c, _s), v in ba.pm_rows(ws).items() if c == 'ESS99']
    assert reason == 'Chưa có phương pháp.'
    assert ws.cell(row=prow, column=ba.COL['adj_type']).value == ba.TYPE_ENTER
    assert ws.cell(row=prow + 1, column=ba.COL['new_price']).value is None
    fund = wb[MGMT]
    for col in [6] + list(range(8, 20)):
        cell = fund.cell(row=30, column=col)
        assert isinstance(cell.value, str) and cell.value.startswith('=')     # linked, no typed number
        assert cell.fill.fgColor.rgb.endswith('FFF2CC')
        assert cell.number_format == ba.FMT_BLANK_ZERO
    problems, lines = checks.pm_line_problems(wb)
    assert lines == ['ESS99'] and problems == []


def test_static_check_catches_a_typed_zero_and_a_missing_row():
    wb = _with_pm_line()
    ba.shade_pm_fund_row(wb[MGMT], 30)
    wb[MGMT].cell(row=30, column=8, value=0)
    problems, _lines = checks.pm_line_problems(wb)
    reasons = ' / '.join(r for _c, r in problems)
    assert 'có số 0, phải để trống' in reasons


def test_static_check_catches_a_kind_a_code_left_as_zero():
    wb = _with_pm_line()
    _fund_row(wb[MGMT], 32, 'ESM6', 'Monthly', [None] * 12)
    wb[MGMT].cell(row=32, column=20, value='Để ở mức 0: Chưa có phương pháp định giá được ghi nhận.')
    problems, _lines = checks.pm_line_problems(wb)
    assert any(c == 'ESM6' and 'PM điền' in r for c, r in problems)


# ---- web --------------------------------------------------------------------------------------------
def test_web_remark_lead_follows_the_figure():
    base = 'PM điền: Chưa có phương pháp định giá được ghi nhận.\nCâu VAT.'
    filled = adjust.pm_remark_text(base, 24_000_000)
    assert filled == ('Số do PM nhập: 24,000,000 VND/năm. Công cụ không tính được: Chưa có phương pháp định giá được '
                      'ghi nhận.\nCâu VAT.')
    assert adjust.pm_remark_text(filled, 0) == base
    assert adjust.pm_remark_text('Remark PM tự viết.', 5) == 'Remark PM tự viết.'


def test_web_reads_the_mark_and_rewrites_the_remark_on_save(tmp_path):
    wb = _with_pm_line()
    ba.add_pm_rows(wb, [dict(code='ESS99', name='Dòng thử', reason='Chưa có phương pháp.')], MGMT, 'AK', 'AQ')
    items = {it['code']: it for it in adjust._read_wb(wb)}
    it = items['ESS99']
    assert it['pm_fill'] and it['pm_empty'] and it['pm_reason'] == 'Chưa có phương pháp.'
    assert not items[next(c for c in items if c != 'ESS99')]['pm_fill']
    adjust.apply_edits(wb, [dict(key=it['key'], adj_type=ba.TYPE_ENTER, inflation=0,
                                 subs=[dict(idx=0, new_price=24_000_000)])])
    assert wb[MGMT].cell(row=30, column=20).value.startswith('Số do PM nhập: 24,000,000 VND/năm.')
    assert not {i['code']: i for i in adjust._read_wb(wb)}['ESS99']['pm_empty']



def test_an_older_sheet_without_the_pm_columns_reads_as_no_pm_line():
    wb = _workbook()
    ba.apply(wb, _items())
    assert ba.pm_rows(wb[ba.SHEET_NAME]) == {}
    assert not any(it['pm_fill'] for it in adjust._read_wb(wb))
