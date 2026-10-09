"""Unit tests for vn_holidays.py (statutory Vietnamese public holidays, lunar dates computed).

Covered: tet_first_day, statutory_holidays, holidays_in_month.
Not covered: the lunar-calendar helper functions on their own (exercised through the dates below).

Invented data only (public calendar dates, no client data). The module runs test_known_tet at
import, so it is imported by module name here and never with import *.

Expected dates come from public sources, not from running the module:
 - Tet 2020-2025: the six dates the module itself documents as validated.
 - Tet 2026 = 17 Feb 2026 and Hung Kings 2026 = Sunday 26 Apr 2026 (Tuoi Tre, "all you need to know
   about public holidays in Vietnam in 2026"); Tet 2027 = Sat 6 Feb 2027 (public holiday calendars).
 - Hung Kings (10th day of the 3rd lunar month): 10 Apr 2022, 29 Apr 2023, 18 Apr 2024, 7 Apr 2025
   (widely published holiday dates; 2023 and 2025 have a leap lunar month). Only 2026 was checked
   against a source in this work; 2022-2025 are not separately sourced.
Rules: Labour Code 2019 Article 112 as described in the module docstring (New Year 1, Tet 5, Hung
Kings 1, Reunification 1, Labour 1, National Day 2 = 11 days).
"""
import datetime

import pytest

import vn_holidays as vh

D = datetime.date


@pytest.mark.parametrize('year, expected', [
    (2020, D(2020, 1, 25)), (2021, D(2021, 2, 12)), (2022, D(2022, 2, 1)),
    (2023, D(2023, 1, 22)), (2024, D(2024, 2, 10)), (2025, D(2025, 1, 29)),
    (2026, D(2026, 2, 17)), (2027, D(2027, 2, 6)),
])
def test_tet_first_day(year, expected):
    assert vh.tet_first_day(year) == expected


@pytest.mark.parametrize('year, expected', [
    (2022, D(2022, 4, 10)), (2023, D(2023, 4, 29)), (2024, D(2024, 4, 18)),
    (2025, D(2025, 4, 7)), (2026, D(2026, 4, 26)),
])
def test_hung_kings_is_the_lunar_10th_of_month_3(year, expected):
    days = dict((name, d) for d, name in vh.statutory_holidays(year))
    assert days['Gio To Hung Vuong / Hung Kings'] == expected


def test_statutory_days_are_eleven_in_a_year():
    # not settled: 11 (Article 112, as the module returns) against 12 in the 2027 Resi template.
    # See docs/05-decisions.md Q2. A 2026 news item (vietcetera.com, "Vietnam Expands Public Holiday
    # List In 2026") suggests the count may be changing; its content was not checked. A change of the rule shows up here.
    for year in (2023, 2024, 2025, 2026):
        assert len(vh.statutory_holidays(year)) == 11


def test_statutory_days_are_distinct_sorted_and_inside_the_year():
    days = vh.statutory_holidays(2024)
    dates = [d for d, _ in days]
    assert dates == sorted(dates)
    assert len(set(dates)) == len(dates)
    assert all(d.year == 2024 for d in dates)


def test_statutory_holidays_2024_full_list():
    got = [d for d, _ in vh.statutory_holidays(2024)]
    assert got == [
        D(2024, 1, 1),
        D(2024, 2, 9), D(2024, 2, 10), D(2024, 2, 11), D(2024, 2, 12), D(2024, 2, 13),   # Tet block
        D(2024, 4, 18),
        D(2024, 4, 30), D(2024, 5, 1),
        D(2024, 9, 1), D(2024, 9, 2),
    ]


def test_tet_block_is_five_consecutive_days_opening_on_new_years_eve():
    # not settled: TET_LEAD_DAYS = 1 (the block starts the day before mung 1) is "the common shape,
    # not a legal certainty" per the module comment.
    tet = vh.tet_first_day(2025)
    block = [d for d, name in vh.statutory_holidays(2025) if name.startswith('Tet Am lich')]
    assert block == [tet + datetime.timedelta(days=i) for i in range(-1, 4)]
    assert len(block) == vh.TET_DAYS == 5
    assert vh.TET_LEAD_DAYS == 1


def test_statutory_holidays_does_not_add_swap_days():
    # rule source: module docstring (swap days are a yearly policy decision, not computed).
    # Tet 2026: official break was 14-22 Feb; the statutory days are 16-20 Feb only.
    feb = [d.day for d, _ in vh.statutory_holidays(2026) if d.month == 2]
    assert feb == [16, 17, 18, 19, 20]


@pytest.mark.parametrize('year, month, days', [
    (2024, 1, [1]),
    (2024, 2, [9, 10, 11, 12, 13]),
    (2024, 3, []),
    (2024, 4, [18, 30]),
    (2024, 5, [1]),
    (2024, 9, [1, 2]),
    (2024, 12, []),
    (2023, 1, [1, 21, 22, 23, 24, 25]),     # Tet 22 Jan: New Year and the Tet block share January
    (2022, 1, [1, 31]),                      # Tet 1 Feb: the lead day 31 Jan falls in January
    (2022, 2, [1, 2, 3, 4]),
    (2026, 4, [26, 30]),
])
def test_holidays_in_month(year, month, days):
    assert vh.holidays_in_month(year, month) == days


def test_holidays_in_month_are_sorted_ints():
    got = vh.holidays_in_month(2023, 1)
    assert got == sorted(got) and all(isinstance(d, int) for d in got)


def test_every_statutory_day_is_found_in_its_month():
    for year in (2022, 2024, 2026):
        from_months = sorted((year, m, d) for m in range(1, 13) for d in vh.holidays_in_month(year, m))
        direct = sorted((d.year, d.month, d.day) for d, _ in vh.statutory_holidays(year))
        assert from_months == direct


def test_holidays_in_month_outside_1_to_12_is_empty():
    assert vh.holidays_in_month(2024, 0) == []
    assert vh.holidays_in_month(2024, 13) == []
