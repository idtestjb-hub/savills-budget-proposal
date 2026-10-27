"""The N-1 approved, actual and expected columns of an approved budget of year N (change
add-review-prior-and-actual-columns): read on the fund sheet and its report sheet. Invented workbooks only."""
import os

import openpyxl
import pytest

import review_import as ri
import review_measures as rm
from tests.test_review_import import MF_LINES, build_prior_workbook

OFF_E = 12_000_000.0
# (header, factor of the approved figure, tie on E)
REPORT_COLS = [
    ('Approved budget of Year 2025\nNgân sách phê duyệt', 0.95, True),
    ('Total Actual From 01/2025 to 09/2025\nThực tế', 0.70, True),
    ('Total Expected From 10/2025\nTổng dự ước', 0.25, True),
    ('Expected Report Year 2025\nBáo cáo dự kiến', 0.95, False),      # E row off by OFF_E: does not tie
    ('Approved budget of Year 2026', 1.00, True),                      # wrong year for a 2026 file
]


def _report_sheet(ws):
    """'2.1 Report-Management Fund': indicator A, code B, item C, the five columns from E, head rows 1-9."""
    ws['A1'] = 'REPORT'
    for j, (h, _, _) in enumerate(REPORT_COLS):
        ws.cell(row=9, column=5 + j, value=h)
    r = 11
    totals = [{'R': 0.0, 'E': 0.0} for _ in REPORT_COLS]
    anchor = {}
    ws.cell(row=r, column=1, value='A')
    ws.cell(row=r, column=2, value='R')
    anchor['R'] = r
    r += 1
    section = 'R'
    for sec, code, ind, annual, _, item in MF_LINES:
        if sec == 'E' and section == 'R':
            ws.cell(row=r, column=1, value='B')
            ws.cell(row=r, column=2, value='E')
            anchor['E'] = r
            r += 1
            section = 'E'
        ws.cell(row=r, column=2, value=code)
        ws.cell(row=r, column=3, value=item)
        if ind:
            ws.cell(row=r, column=1, value=ind)
        elif annual is not None:
            for j, (_, f, _) in enumerate(REPORT_COLS):
                ws.cell(row=r, column=5 + j, value=annual * f)
                totals[j][sec] += annual * f
        r += 1
    ws.cell(row=r, column=2, value='PL1')
    for j, (_, _, ties) in enumerate(REPORT_COLS):
        ws.cell(row=anchor['R'], column=5 + j, value=totals[j]['R'])
        ws.cell(row=anchor['E'], column=5 + j, value=totals[j]['E'] + (0.0 if ties else OFF_E))


@pytest.fixture
def with_report(tmp_path):
    p = os.path.join(tmp_path, 'approved_2026.xlsx')
    build_prior_workbook(p)
    wb = openpyxl.load_workbook(p)
    del wb['2.1 Report-Management Fund']
    _report_sheet(wb.create_sheet('2.1 Report-Management Fund'))
    wb.save(p)
    return p


@pytest.fixture
def plain(tmp_path, monkeypatch):
    import tests.test_review_import as T
    monkeypatch.setattr(T._fund_sheet, '__defaults__', (T._fund_sheet.__defaults__[0], False))   # no decoy column
    p = os.path.join(tmp_path, 'plain_2026.xlsx')
    build_prior_workbook(p)
    return p


def test_three_columns_from_the_report_sheet(with_report, tmp_path):
    prior = ri.read_prior_budget(with_report, workdir=str(tmp_path))
    assert prior.n_year == 2026
    m = prior.measures['MF']
    # the tying report column beats the fund sheet's non-tying 'Approved budget of Year 2025' decoy
    assert m['n1']['sheet'] == '2.1 Report-Management Fund' and m['n1']['tie_ok']
    assert m['n1']['values'][('R', 'RM.AP')] == pytest.approx(2_400_000_000.0 * 0.95)
    assert (m['actual']['start'], m['actual']['end']) == ((2025, 1), (2025, 9))
    assert m['actual']['values'][('E', 'EMH2')] == pytest.approx(1_200_000_000.0 * 0.70)
    assert m['expected']['tie_ok'] is False                       # still used, flagged
    assert m['expected']['values'][('E', 'EEE.C')] == pytest.approx(480_000_000.0 * 0.95)


def test_notes_list_the_choice_and_the_rejected_columns(with_report, tmp_path):
    prior = ri.read_prior_budget(with_report, workdir=str(tmp_path))
    texts = [t for k, _, t in prior.notes if k == ri.NOTE_MEASURE]
    assert any('Approved budget of Year 2026' in t and 'không phải năm 2025' in t for t in texts)
    assert any(t.startswith('Dự kiến 2025') and 'chưa khớp tổng' in t for t in texts)
    assert any(t.startswith('Thực tế 01–09/2025') and 'khớp tổng' in t for t in texts)


def test_lines_and_approved_figures_do_not_change(with_report, plain, tmp_path):
    a = ri.read_prior_budget(with_report, workdir=str(tmp_path))
    b = ri.read_prior_budget(plain, workdir=str(tmp_path))
    key = lambda pr: [(l.fund, l.section, l.code, l.annual, tuple(l.months), tuple(l.flags)) for l in pr.lines()]
    assert key(a) == key(b)
    assert b.measures == {}
    assert not [t for k, _, t in b.notes if k == ri.NOTE_MEASURE]


def test_decoy_alone_is_used_and_flagged(tmp_path):
    p = os.path.join(tmp_path, 'approved_2026.xlsx')
    build_prior_workbook(p)                                      # only the fund sheet's non-tying approved column
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    n1 = prior.measures['MF']['n1']
    assert n1['sheet'] == '2. Budget-Management Fund' and n1['col_letter'] == 'AI' and not n1['tie_ok']


def test_unrecognised_year_column_is_noted(tmp_path):
    p = os.path.join(tmp_path, 'approved_2026.xlsx')
    build_prior_workbook(p)
    wb = openpyxl.load_workbook(p)
    ws = wb['2. Budget-Management Fund']
    ws.cell(row=9, column=40, value='Kế hoạch 2025 bản B')
    for r in range(13, 40):
        if ws.cell(row=r, column=37).value:
            ws.cell(row=r, column=40, value=1.0)
    wb.save(p)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    assert any('chưa nhận diện' in t and 'Kế hoạch 2025' in t for k, _, t in prior.notes if k == ri.NOTE_MEASURE)


def test_head_year_from_the_head_cells():
    rows = [()] * 4 + [(None, 'Budget Year:', 2026)] + [()] * 4
    assert ri.head_year(rows) == 2026
    import datetime
    rows = [()] * 5 + [('Starting Month:', datetime.datetime(2026, 4, 1), 'Ending Month:', datetime.datetime(2027, 3, 31))]
    assert ri.head_year(rows) == 2026
    assert ri.head_year([()] * 9) is None
    assert rm.KINDS == ('n1', 'actual', 'expected')


# ---- review.assemble() and the Review sheet with the N-1 columns (tasks 4.1, 4.2) ----
import review                                                     # noqa: E402
from tests.test_review_sheet import _ctx, _data                   # noqa: E402

MONTHS_2025 = [(2025, m) for m in range(1, 13)]
TEMPLATE = {'MF': {'RM.AP': 14, 'RP1': 26, 'RP2': 27, 'EMH2': 81, 'EEE.C': 242, 'ESS1': 100, 'ESS38': 140, 'ESM4': 160}}


def _col(values, period='2025', months=MONTHS_2025, tie_ok=True, sums=None, anchors=None):
    sums = sums or {'R': sum(v for (s, _), v in values.items() if s == 'R'), 'E': sum(v for (s, _), v in values.items() if s == 'E')}
    return dict(values=values, months=months, incl=False, period=period, tie_ok=tie_ok, tie_state='ok' if tie_ok else 'mismatch',
                sums=sums, anchors=anchors or dict(sums), tie_notes=[])


def _measures():
    n1 = _col({('E', 'EMH2'): 1_000_000_000.0, ('E', 'ESS1'): 0.0, ('E', 'EXX7'): 5_000_000.0, ('R', 'RP1'): 100_000_000.0})
    act = _col({('E', 'EMH2'): 700_000_000.0}, period='01–09/2025', months=MONTHS_2025[:9])
    exp_sums = {'R': 0.0, 'E': 1_100_000_000.0}
    exp = _col({('E', 'EMH2'): 1_100_000_000.0}, tie_ok=False, sums=exp_sums, anchors={'R': 0.0, 'E': 1_100_000_000.0 + OFF_E})
    return {'MF': {'n1': n1, 'actual': act, 'expected': exp}}


def _meta_with(meta):
    m = dict(meta)
    m['measures'] = {'MF': {'n1': dict(period='2025', months=12, tie_ok=True, tie_diff=0.0),
                            'actual': dict(period='01–09/2025', months=9, tie_ok=True, tie_diff=0.0),
                            'expected': dict(period='2025', months=12, tie_ok=False, tie_diff=OFF_E)}}
    return m


def test_assemble_adds_the_n1_figures_and_three_pct():
    prior_lines, anchors, tool, meta = _data()
    data = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template=TEMPLATE, measures=_measures())
    e = {x['code']: x for x in data['rows_by'][('MF', 'E')]['rows']}
    emh2 = e['EMH2']                                             # salary: VAT factor 1
    assert emh2['n1'] == 1_000_000_000.0 and emh2['actual'] == 700_000_000.0 and emh2['expected'] == 1_100_000_000.0
    assert emh2['p_n_n1'] == pytest.approx(0.2)                  # Duyệt 2026 so Duyệt 2025
    assert emh2['p_exp_n1'] == pytest.approx(0.1)                # Dự kiến 2025 so Duyệt 2025
    assert emh2['p_n_exp'] == pytest.approx(1.2 / 1.1 - 1)       # Duyệt 2026 so Dự kiến 2025
    assert e['ESS1']['n1'] == 0.0 and e['ESS1']['p_n_n1'] is None   # a 0 base gives a blank %
    assert e['EEE.C']['n1'] is None and e['EEE.C']['p_n_n1'] is None
    assert e['EXX7']['approved'] == 0.0 and e['EXX7']['n1'] == pytest.approx(5_400_000.0)   # only in N-1: a row; 8% VAT of 2025


def test_existing_figures_and_ties_do_not_move():
    prior_lines, anchors, tool, meta = _data()
    a = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template=TEMPLATE)
    b = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template=TEMPLATE, measures=_measures())
    keys = ('approved', 'factor', 'converted', 'tool', 'diff', 'pct', 'label')
    for k in a['rows_by']:
        ra = {x['code']: x for x in a['rows_by'][k]['rows']}
        rb = {x['code']: x for x in b['rows_by'][k]['rows']}
        for code in ra:
            assert all(ra[code][f] == rb[code][f] for f in keys), code
        for f in ('approved', 'converted', 'tool', 'diff', 'pct'):
            assert a['rows_by'][k]['total'][f] == b['rows_by'][k]['total'][f]
    assert a['ties'] == b['ties']                                # the exit code reads these only
    bad = [t for t in b['measure_ties'] if not t['ok']]
    assert len(bad) == 1 and bad[0]['section'] == 'E' and bad[0]['diff'] == -OFF_E
    assert a['measure_ties'] == []


def test_sheet_headers_and_summary_with_and_without_columns(tmp_path):
    prior_lines, anchors, tool, meta = _data()
    meta2 = _meta_with(meta)
    data = review.assemble(prior_lines, anchors, tool, meta2, _ctx(), template=TEMPLATE, measures=_measures())
    wb = openpyxl.Workbook()
    ws = review.build_review_sheet(wb, data, meta2)
    texts = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
    assert ws['A1'].value.startswith('Review — ngân sách đã duyệt 2026 so với ngân sách 2027')
    assert 'Duyệt NS 2025 (năm trước, quy đổi)' in texts
    assert 'Thực tế 01–09/2025 (9 tháng, quy đổi)' in texts
    assert 'Dự kiến cả năm 2025 (quy đổi)\n(chưa khớp tổng, lệch 12,000,000)' in texts
    assert '% 2026 so 2025' in texts and '% Dự kiến 2025 so Duyệt 2025' in texts and '% 2026 so Dự kiến 2025' in texts
    assert 'Duyệt NS 2026 (quy đổi)' in texts                       # the N column keeps its header
    md = review.summary_md(data, meta2)
    assert 'Năm 2025 trong file' in md and 'tham khảo, không tính vào kết quả' in md
    assert 'measure_ties' in review.summary_json(data, meta2)
    # without columns: blank columns with 'File không có số', summaries as before
    plain = review.assemble(prior_lines, anchors, tool, meta, _ctx(), template=TEMPLATE)
    ws2 = review.build_review_sheet(openpyxl.Workbook(), plain, meta)
    texts2 = [str(c.value) for row in ws2.iter_rows() for c in row if c.value is not None]
    assert 'Duyệt NS 2025 (năm trước)\nFile không có số' in texts2
    assert 'Năm 2025 trong file' not in review.summary_md(plain, meta)
    assert 'measure_ties' not in review.summary_json(plain, meta)
