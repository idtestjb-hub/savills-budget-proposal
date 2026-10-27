"""review_measures.py: the scan store's header, period and flag rules for the N-1 columns of an approved budget
(change add-review-prior-and-actual-columns). Header texts are the store's most frequent ones, without project names."""
import pytest

import review_measures as rm

STORE_HEADERS = [
    ('Approved budget of Year 2025 Ngân sách phê duyệt Approved budget', 'approved_prior'),
    ('Approved Budget of Year 2025/ Tổng Ngân sách được duyệt năm 2025', 'approved_prior'),
    ('Approved Budget of Year 2024 (From 01-12/24)/ Tổng Ngân sách được duyệt', 'approved_prior'),
    ('Actual', 'actual'),
    ('Total Actual From 01/2025 to 09/2025 Thực tế số liệu', 'actual'),
    ('Thực tế', 'actual'),
    ('Expected Report Year 2025 Báo cáo dự kiến Expected', 'expected_year'),
    ('Total Expected From 10/2025 Tổng dự ước doanh thu/ chi phí', 'expected_rest'),
    ('Total Expected From 10/2025 to 12/2025 Tổng dự ước', 'expected_rest'),
    ('Total Budget of Year\nTổng ngân sách', 'budget'),
    ('Estimate budget of Year 2026', 'budget'),
    ('Chênh lệch so với ngân sách', 'variance'),
    ('% increase', 'variance'),
    ('Ngân sách tham khảo dự án khác', 'reference'),
    ('Số lần thực hiện', 'other'),
    ('Average Month', 'average'),
    ('Budget Year: / Dự toán của năm:', 'empty'),
]


@pytest.mark.parametrize('header,measure', STORE_HEADERS)
def test_classify_matches_the_store(header, measure):
    assert rm.classify(header) == measure


def test_periods():
    assert rm.parse_period('Total Actual From 01/2025 to 09/2025', '', None)[:2] == ((2025, 1), (2025, 9))
    assert rm.parse_period('Total Expected From 10/2025', '', None)[:2] == ((2025, 10), (2025, 12))
    assert rm.parse_period('Approved budget of Year 2025', '', None)[:2] == ((2025, 1), (2025, 12))
    assert rm.parse_period('Actual 3', '', 2025)[:2] == ((2025, 3), (2025, 3))
    assert rm.parse_period('Lũy kế', '', None) == (None, None, 'unknown')
    # the header's own year wins over a month-group label picked up from the sheet's Starting Month cell
    assert rm.parse_period('Expected Report Year 2025', 'tháng 1/2026', None)[:2] == ((2025, 1), (2025, 12))
    assert rm.parse_period('Actual', 'tháng 3/2025', None)[:2] == ((2025, 3), (2025, 3))


def _col(measure, header='', start=None, end=None, n=5, tie_ok=True, kind='budget', state='visible', how='header_year'):
    return dict(measure=measure, header=header, start=start, end=end, n_nonzero=n, tie_ok=tie_ok, sheet_kind=kind,
                sheet_state=state, how=how)


def test_cumulative_actual_ends_before_expected_from():
    cols = [_col('actual', 'Lũy kế', how='unknown'), _col('expected_rest', 'Total Expected From 10/2025', (2025, 10), (2025, 12))]
    rm.infer_cumulative(cols)
    assert (cols[0]['start'], cols[0]['end']) == ((2025, 1), (2025, 9))
    assert rm.months_between(cols[0]['start'], cols[0]['end']) == 9


def test_flags():
    assert rm.flags_of(_col('approved_prior', 'Approved budget of Year 2025', (2025, 1), (2025, 12))) == []
    assert 'chua_dien' in rm.flags_of(_col('approved_prior', 'Approved 2025', (2025, 1), (2025, 12), n=0))
    assert 'mau_AAA' in rm.flags_of(_col('actual', 'AAA Total Actual From 09/2023 to 07/2024', (2023, 9), (2024, 7)))
    assert 'du_an_khac' in rm.flags_of(_col('expected_year', 'ZZ OTHER TOWER Expected Report Year 2025', (2025, 1), (2025, 12)),
                                       own_name='ZZ TEST TOWER', other_names={'ZZ OTHER TOWER', 'ZZ TEST TOWER'})
    assert rm.flags_of(_col('expected_year', 'ZZ TEST TOWER Expected Report Year 2025', (2025, 1), (2025, 12)),
                       own_name='ZZ TEST TOWER', other_names={'ZZ OTHER TOWER', 'ZZ TEST TOWER'}) == []
    assert 'mau_ky_sau_ngay_luu_file' in rm.flags_of(_col('actual', 'Actual', (2025, 1), (2025, 11)), saved_month=(2025, 10))
    assert 'khong_ro_ky' in rm.flags_of(_col('actual', 'Thực tế'))


def test_year_check_is_n_minus_1():
    assert rm.year_ok(_col('approved_prior', start=(2025, 1), end=(2025, 12)), 2026)
    assert not rm.year_ok(_col('approved_prior', start=(2026, 1), end=(2026, 12)), 2026)     # "Approved … 2026" in a 2026 file
    assert rm.year_ok(_col('actual', start=(2025, 1), end=(2025, 9)), 2026)
    assert not rm.year_ok(_col('actual', start=(2026, 1), end=(2026, 3)), 2026)
    assert rm.year_ok(_col('expected_year', start=(2025, 1), end=(2025, 12)), 2026)
    assert rm.year_ok(_col('approved_prior', start=(2026, 1), end=(2026, 12)), 2027)          # rolling year


def test_choice_order():
    a = _col('approved_prior', start=(2025, 1), end=(2025, 12), tie_ok=False, kind='report', n=50)
    b = _col('approved_prior', start=(2025, 1), end=(2025, 12), tie_ok=True, kind='budget', n=10)
    assert rm.choose([a, b]) is b                                    # ties first
    c = _col('approved_prior', start=(2025, 1), end=(2025, 12), tie_ok=True, kind='report', n=10)
    assert rm.choose([b, c]) is c                                    # then a report sheet
    one = _col('actual', start=(2025, 3), end=(2025, 3), kind='report', n=90)
    cum = _col('actual', start=(2025, 1), end=(2025, 9), kind='budget', n=20)
    assert rm.choose([one, cum]) is cum                              # a cumulative actual before a one-month column


def test_period_text():
    assert rm.period_text(_col('actual', start=(2025, 1), end=(2025, 9))) == '01–09/2025'
    assert rm.period_text(_col('approved_prior', start=(2025, 1), end=(2025, 12))) == '2025'
