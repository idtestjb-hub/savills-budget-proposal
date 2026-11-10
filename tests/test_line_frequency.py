"""line_frequency: the six frequencies, the first-month rule, the default table and the remark sentence
(change add-line-frequency, spec line-frequency). TEST DATA only."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import line_frequency as lf  # noqa: E402


@pytest.mark.parametrize('freq,first,expected', [
    ('Monthly', None, list(range(1, 13))),
    ('Quarterly', 1, [1, 4, 7, 10]),
    ('Quarterly', 3, [3, 6, 9, 12]),
    ('Half a Year', 1, [1, 7]),
    ('Half a Year', 6, [6, 12]),
    ('Yearly', 12, [12]),
    ('Schedule', None, list(range(1, 13))),
])
def test_months_of_cyclic_and_full_year(freq, first, expected):
    assert lf.months(freq, first) == expected


def test_no_first_month_means_t1():
    assert lf.months('Quarterly') == [1, 4, 7, 10]
    assert lf.months('Yearly', '') == [1]


def test_optional_months_are_the_ticks_sorted():
    assert lf.months('Optional', optional_months=[11, 2, 7]) == [2, 7, 11]
    assert lf.times('Optional', 3) == 3


@pytest.mark.parametrize('ticks', [[], list(range(1, 13))])
def test_optional_needs_one_to_eleven_months(ticks):
    with pytest.raises(ValueError):
        lf.months('Optional', optional_months=ticks)


def test_times_per_frequency():
    assert [lf.times(f) for f in ('Monthly', 'Quarterly', 'Half a Year', 'Yearly', 'Schedule')] == [12, 4, 2, 1, 12]
    with pytest.raises(ValueError):
        lf.times('Optional', 12)


def test_july_start_period_half_year_t6():
    # T1 is the period's first month: a July-2027 period with first month T6 pays in T6 and T12,
    # that is December 2027 and June 2028 (spec scenario "A half-yearly line in a July-start period").
    period_months = [(2027, m) for m in range(7, 13)] + [(2028, m) for m in range(1, 7)]
    paid = [period_months[t - 1] for t in lf.months('Half a Year', 6)]
    assert paid == [(2027, 12), (2028, 6)]


@pytest.mark.parametrize('freq,first,message', [
    ('Quarterly', 5, 'Tháng đầu của Hàng quý phải là T1, T2 hoặc T3'),
    ('Half a Year', 7, 'Tháng đầu của 6 tháng/lần phải từ T1 đến T6'),
    ('Yearly', 13, 'Tháng đầu của Hàng năm phải từ T1 đến T12'),
])
def test_first_month_out_of_range_is_refused(freq, first, message):
    assert lf.first_month_error(freq, first) == message
    with pytest.raises(ValueError, match=message):
        lf.months(freq, first)


def test_first_month_in_range_and_non_cyclic():
    assert lf.first_month_error('Quarterly', 3) is None
    assert lf.first_month_error('Monthly', 9) is None


def test_normalise_accepts_the_forms_lower_case_and_refuses_others():
    assert lf.normalise('Half a year') == 'Half a Year'
    assert lf.normalise('  quarterly ') == 'Quarterly'
    assert lf.normalise('') is None and lf.normalise(None) is None
    with pytest.raises(ValueError):
        lf.normalise('Weekly')


@pytest.mark.parametrize('freq,price,months,expected', [
    ('Quarterly', 3_500_000, [3, 6, 9, 12], 'Hàng quý, 4 lần/năm × 3,500,000 VND/lần, chi vào T3, T6, T9, T12'),
    ('Half a Year', 2_028_000, [1, 7], '6 tháng/lần, 2 lần/năm × 2,028,000 VND/lần, chi vào T1, T7'),
    ('Yearly', 14_000_000, [1], 'Hàng năm, 1 lần/năm × 14,000,000 VND/lần, chi vào T1'),
    ('Optional', 8_000_000, [2, 7, 11], '3 lần/năm, 8,000,000 VND/lần, chi vào T2, T7, T11'),
    ('Schedule', None, [1, 5], 'Chi theo lịch từng tháng: T1, T5'),
])
def test_sentence_per_frequency(freq, price, months, expected):
    text = lf.sentence(freq, price, months)
    assert text == expected
    assert lf.is_sentence(text)


def test_monthly_has_no_sentence():
    assert lf.sentence('Monthly', 1_000_000, list(range(1, 13))) is None
    assert not lf.is_sentence('= 1,352,000 VND/mẫu x 3 mẫu x 2 đợt/năm')


def test_table_reader(tmp_path):
    path = tmp_path / 'Ref_LineFrequency.csv'
    path.write_text('# TEST DATA\ncode,frequency,times,first_month,source,note\n'
                    'X1,Quarterly,4,2,test,\nX2,Yearly,1,,test,\n', encoding='utf-8-sig')
    table = lf.load_table(str(path))
    assert table['X1'].months == [2, 5, 8, 11]
    assert table['X2'].months == [1]
    assert 'X3' not in table


def test_table_refuses_wrong_times(tmp_path):
    path = tmp_path / 'bad.csv'
    path.write_text('code,frequency,times,first_month,source,note\nX1,Quarterly,3,1,test,\n', encoding='utf-8')
    with pytest.raises(ValueError):
        lf.load_table(str(path))


def test_shipped_table_lists_the_reviewed_codes():
    table = lf.load_table()
    # change default-frequency-from-real-budgets (signed off 2026-11-09): 11 codes; RO2a back to Monthly (not listed);
    # change near-threshold-and-unpriced-frequency: + ESC2, ESC3, ESS7, EMA18 Yearly by the user's choice = 15
    assert set(table) == {'EMB4', 'ERCS1', 'ESA16', 'ESC12', 'ESC4', 'ESC5', 'ESM2', 'ESM25', 'ESM3', 'ESM5', 'ESS10',
                          'ESC2', 'ESC3', 'ESS7', 'EMA18'}
    assert all(table[c].frequency == 'Yearly' for c in ('ESC2', 'ESC3', 'ESS7', 'EMA18'))
    assert 'RO2a' not in table and 'ESA1' not in table
    assert all(d.source for d in table.values())
    assert table['ESM25'].months == [1, 4, 7, 10] and table['ESC5'].months == [1]
