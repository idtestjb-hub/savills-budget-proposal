"""Budget period (change apply-head-of-pm-decisions-2026-10, group 1)."""
import datetime

import pytest

import budget_period as bp


def test_blank_gives_january_2027():
    for v in (None, '', '   '):
        p = bp.from_value(v)
        assert (p.start_year, p.start_month) == (2027, 1)
        assert p.first_day == datetime.date(2027, 1, 1) and p.last_day == datetime.date(2027, 12, 31)
        assert p.is_default


@pytest.mark.parametrize('value', [datetime.datetime(2027, 7, 15), datetime.date(2027, 7, 1), '07/2027', '7/2027',
                                   '2027-07', 'Jul 2027', 'July 2027', ' july  2027 '])
def test_valid_forms_for_july_2027(value):
    p = bp.from_value(value)
    assert (p.start_year, p.start_month) == (2027, 7)
    assert p.months[0] == (2027, 7) and p.months[-1] == (2028, 6)
    assert p.first_day == datetime.date(2027, 7, 1) and p.last_day == datetime.date(2028, 6, 30)
    assert p.calendar_years == [2027, 2028]
    assert not p.is_default


def test_twelve_months_across_a_year_end_and_a_leap_february():
    p = bp.from_value('10/2027')
    assert p.months == [(2027, 10), (2027, 11), (2027, 12), (2028, 1), (2028, 2), (2028, 3), (2028, 4), (2028, 5),
                        (2028, 6), (2028, 7), (2028, 8), (2028, 9)]
    assert bp.from_value('03/2027').last_day == datetime.date(2028, 2, 29)


@pytest.mark.parametrize('value', ['abc', '13/2027', '00/2027', '2027', 7, 2027, 7.5, True, '07/1899', '07/2500',
                                   'Foo 2027', '07-27'])
def test_invalid_values_stop_and_name_the_field(value):
    with pytest.raises(bp.BudgetPeriodError) as exc:
        bp.from_value(value)
    assert "'Budget Start Month'" in str(exc.value)
    assert 'MM/YYYY' in str(exc.value)


def test_label_text():
    assert bp.from_value('09/2026').label() == '01/09/2026–31/08/2027'
