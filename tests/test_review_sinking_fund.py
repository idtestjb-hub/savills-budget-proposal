"""Budget Review of the sinking fund (change add-sinking-fund, task 5.5) on invented workbooks. TEST DATA only: no real
file, no real name, no real amount."""
import os
import shutil

import openpyxl
import pytest

import generate_project_budget as gpb
import review
import review_import as ri
import utility_tariffs as ut
from test_review_import import FIXTURE, build_prior_workbook

EXCL = '(Excluding VAT/ Chưa gồm thuế GTGT)'
INCL = '(Including VAT/ Đã gồm thuế GTGT)'
# (code, item, amount on H); ERE2 twice to check the sum, EZZ9 is not a line of the template's sheet 3
SF_LINES = [
    ('ERA1', 'TEST lift repair', 120_000_000.0),
    ('ERE2', 'TEST electrical repair', 30_000_000.0),
    ('ERE2', 'TEST electrical repair, second row', 6_000_000.0),
    ('ERB1', 'TEST zero line', 0.0),
    ('EZZ9', 'TEST code not on the form', 50_000_000.0),
]


def _sf_budget_sheet(ws, lines, year=2026, vat_text=EXCL):
    """Sheet 3 with the form's conventions: VAT text in the title rows, a "Budget Year" cell, CODE in Z, Total Price
    in H; a decoy approved column (AC) that must not be read."""
    ws.cell(row=4, column=26, value=vat_text)
    ws.cell(row=5, column=27, value='Budget Year:')
    ws.cell(row=5, column=28, value=year)
    ws.cell(row=10, column=26, value='CODE\nMã')
    ws.cell(row=10, column=27, value='ITEMS\nHạng mục')
    ws.cell(row=10, column=8, value='Total Price\nThành tiền')
    ws.cell(row=10, column=29, value=f'Approved budget of year {year - 1}')
    for i, (code, item, amount) in enumerate(lines):
        r = 15 + i
        ws.cell(row=r, column=26, value=code)
        ws.cell(row=r, column=27, value=item)
        ws.cell(row=r, column=8, value=amount)
        ws.cell(row=r, column=29, value=amount * 0.5 + 1 if amount is not None else None)


def _sf_report_sheet(ws, lines, year=2025, vat_text=EXCL):
    """3.1: CODE in E, total actual in H, the approved column of year `year` in N."""
    ws.cell(row=3, column=5, value=vat_text)
    ws.cell(row=10, column=5, value='CODE\nMã')
    ws.cell(row=10, column=6, value='ITEMS')
    ws.cell(row=10, column=8, value='Total Actual\nThực tế')
    ws.cell(row=10, column=14, value=f'Approved budget of year {year}')
    for i, (code, item, amount) in enumerate(lines):
        r = 15 + i
        ws.cell(row=r, column=5, value=code)
        ws.cell(row=r, column=6, value=item)
        ws.cell(row=r, column=8, value=amount * 0.8)
        ws.cell(row=r, column=14, value=amount)


def _approved(tmp_path, budget=None, report=None, budget_vat=EXCL, name='approved.xlsx'):
    p = os.path.join(tmp_path, name)
    build_prior_workbook(p)
    wb = openpyxl.load_workbook(p)
    if budget is not None:
        _sf_budget_sheet(wb.create_sheet('3. Budget-Sinking Fund'), budget, vat_text=budget_vat)
    if report is not None:
        _sf_report_sheet(wb.create_sheet('3.1 Report-Sinking Fund'), report)
    wb.save(p)
    return p


def test_sheet_3_figures_are_carried_from_column_h(tmp_path):
    prior = ri.read_prior_budget(_approved(tmp_path, budget=SF_LINES, report=SF_LINES), workdir=str(tmp_path))
    sf = prior.sf
    assert set(sf) == {'ERA1', 'ERE2'}                       # zero line and off-form code left out
    assert sf['ERA1']['approved'] == 120_000_000.0           # H, never the decoy column
    assert sf['ERE2']['approved'] == 36_000_000.0            # the two rows of one code summed
    assert sf['ERA1']['year'] == 2026
    assert sf['ERA1']['source'] == ri.SF_SRC_BUDGET.format(year=2026)
    assert sf['ERA1']['actual'] is None
    assert any(t == ri.NOTE_SF_NO_TOTAL for _, _, t in prior.notes)


def test_including_vat_sheet_is_taken_out_of_vat(tmp_path):
    prior = ri.read_prior_budget(_approved(tmp_path, budget=SF_LINES, budget_vat=INCL), workdir=str(tmp_path))
    div = 1 + sum(ut.vat_rate(2026, m) for m in range(1, 13)) / 12 / 100
    assert prior.sf['ERA1']['approved'] == pytest.approx(120_000_000.0 / div)


def test_report_only_file_uses_the_approved_column_with_its_year(tmp_path):
    prior = ri.read_prior_budget(_approved(tmp_path, budget=[('ERA1', 'blank', None)], report=SF_LINES),
                                 workdir=str(tmp_path))
    sf = prior.sf
    assert set(sf) == {'ERA1', 'ERE2'}
    assert sf['ERA1']['approved'] == 120_000_000.0 and sf['ERA1']['year'] == 2025
    assert sf['ERA1']['actual'] == pytest.approx(96_000_000.0)
    assert sf['ERA1']['source'] == ri.SF_SRC_REPORT.format(year=2025)
    assert any('3.1' in t and '2025' in t for _, _, t in prior.notes)


@pytest.mark.parametrize('budget', [None, []])
def test_file_without_a_sinking_fund_gives_a_note(tmp_path, budget):
    prior = ri.read_prior_budget(_approved(tmp_path, budget=budget), workdir=str(tmp_path))
    assert prior.sf == {}
    assert any(t == ri.NOTE_SF_NONE for _, _, t in prior.notes)


def test_management_and_common_area_funds_do_not_move(tmp_path):
    plain = ri.read_prior_budget(_approved(tmp_path, name='plain.xlsx'), workdir=str(tmp_path))
    with_sf = ri.read_prior_budget(_approved(tmp_path, budget=SF_LINES, report=SF_LINES, name='sf.xlsx'),
                                   workdir=str(tmp_path))
    assert set(with_sf.funds) == set(plain.funds) == set(ri.FUNDS)
    for fund in ri.FUNDS:
        a = [(l.code, l.annual, l.months) for l in plain.funds[fund].lines]
        b = [(l.code, l.annual, l.months) for l in with_sf.funds[fund].lines]
        assert a == b
    assert with_sf.measures == plain.measures
    assert with_sf.budget_year == plain.budget_year and with_sf.period == plain.period


def test_input_form_carries_the_prior_sheet_to_the_generator(tmp_path):
    p = _approved(tmp_path, report=SF_LINES)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    wb, _ = ri.open_workbook(p, str(tmp_path))
    base = os.path.join(tmp_path, 'base.xlsx')
    shutil.copyfile(FIXTURE, base)
    path, _, _ = ri.write_form(prior, ri.read_info(wb), {}, os.path.join(tmp_path, 'out'), base_form=base)
    back, actual = gpb.read_sf_prior(path)
    assert back['ERA1'] == (120_000_000.0, 2025, ri.SF_SRC_REPORT.format(year=2025))
    assert back['ERE2'][0] == 36_000_000.0
    assert actual['ERA1'] == pytest.approx(96_000_000.0)


def test_form_of_a_file_without_sinking_fund_still_marks_a_review(tmp_path):
    p = _approved(tmp_path)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    wb, _ = ri.open_workbook(p, str(tmp_path))
    base = os.path.join(tmp_path, 'base.xlsx')
    shutil.copyfile(FIXTURE, base)
    path, _, _ = ri.write_form(prior, ri.read_info(wb), {}, os.path.join(tmp_path, 'out'), base_form=base)
    assert gpb.read_sf_prior(path) == ({}, {})                # the sheet exists, empty: a Review with no prior


def _deliverable(tmp_path, lines):
    """A minimal deliverable: sheet 3 rows the way the generator leaves them (code in Z, the form's Total Price
    formula in H, remark in U) and the year in AF as Excel's recalculation leaves it. `lines`: (code, remark, AF)."""
    p = os.path.join(tmp_path, 'deliverable.xlsx')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = gpb.SF_SHEET
    for i, (code, remark, af) in enumerate(lines):
        r = gpb.SF_FIRST_EXPENSE_ROW + i
        ws.cell(row=r, column=gpb.SF_CODE_COL, value=code)
        ws.cell(row=r, column=27, value=f'TEST item\nHạng mục {code}')
        ws.cell(row=r, column=8, value=f'=IF(D{r}="Schedule",SUM(I{r}:T{r}),G{r}*F{r})')
        ws.cell(row=r, column=gpb.SF_REMARK_COL, value=remark)
        ws.cell(row=r, column=32, value=af)
    wb.save(p)
    return p


def test_review_rows_tags_and_zero_rows(tmp_path):
    d = _deliverable(tmp_path, [
        ('ERA1', 'Theo số duyệt năm 2026 × CPI', 130_000_000.0),
        ('ERE2', 'Ước tính từ quỹ bảo trì của 12 dự án', 90_000_000.0),
        ('ERB1', f'{gpb.PM_FILL_LEAD} chưa đủ 10 dự án', 0.0),
        ('ERM', 'Để 0: đang tính ở quỹ quản lý', 0.0),
    ])
    prior_sf = {'ERA1': dict(item='a', year=2026, approved=120_000_000.0, source='s'),
                'ERB1': dict(item='b', year=2026, approved=10_000_000.0, source='s'),
                'ERM': dict(item='m', year=2026, approved=20_000_000.0, source='s')}
    sf = review.sf_review(prior_sf, d, d, dict(deliverable_incl=False, budget_year=2027), refs={'ERE2': 40_000_000.0})
    rows = {r['code']: r for r in sf['rows']}
    assert set(rows) == {'ERA1', 'ERE2', 'ERB1', 'ERM'}
    assert rows['ERA1']['approved'] == 120_000_000 and rows['ERA1']['new'] == 130_000_000
    assert rows['ERA1']['diff'] == 10_000_000 and rows['ERA1']['tags'] == []
    assert rows['ERE2']['approved'] == 0 and review.SF_TAG_HIGH in rows['ERE2']['tags']    # above twice the median
    assert rows['ERE2']['median_ref'] == 40_000_000
    assert review.SF_TAG_PM in rows['ERB1']['tags']
    assert review.SF_TAG_B8 in rows['ERM']['tags']
    assert sf['totals'] == dict(approved=150_000_000, new=220_000_000)
    assert sf['none'] is False
    # approved with a tool 0: a "Nhập số" row, except the code held on sheet 2 (B8)
    assert [r['code'] for _, r in review.sf_zero_rows(sf)] == ['ERB1']


def test_review_of_a_file_without_sinking_fund(tmp_path):
    d = _deliverable(tmp_path, [('ERE2', 'Ước tính từ quỹ bảo trì của 12 dự án', 12_000_000.0)])
    sf = review.sf_review({}, d, d, dict(deliverable_incl=False, budget_year=2027))
    assert sf['none'] is True
    assert [r['code'] for r in sf['rows']] == ['ERE2'] and sf['rows'][0]['approved'] == 0


def test_including_vat_deliverable_converts_the_approved_figure(tmp_path):
    d = _deliverable(tmp_path, [('ERA1', 'Theo số duyệt năm 2026 × CPI', 0.0)])
    sf = review.sf_review({'ERA1': dict(item='a', year=2026, approved=100_000_000.0, source='s')}, d, d,
                          dict(deliverable_incl=True, budget_year=2027))
    f = sum(1 + ut.vat_rate(2026, m) / 100 for m in range(1, 13)) / 12
    assert sf['rows'][0]['approved'] == round(100_000_000.0 * f)
