"""The budget period: twelve calendar months from an entered start month (change apply-head-of-pm-decisions-2026-10, D1).

One object per run. Both generators build it from the input form's 'Budget Start Month' and every month-dated lookup
(a tariff, a VAT rate, the paid-holiday calendar) takes its month from it, never from a column index. The occupancy
fill-up curve is NOT dated: it counts operational months, and operational month 1 is the first month of the period.

A blank field, or a form that has no such field, gives January 2027. Anything that is not a month stops the run and
names the field.
"""
import calendar
import datetime
import re
from dataclasses import dataclass

LABEL = 'Budget Start Month'
DEFAULT_START = (2027, 1)
_MIN_YEAR, _MAX_YEAR = 2000, 2100
_MONTH_NAMES = {name.casefold(): i for i, name in enumerate(calendar.month_name) if name}
_MONTH_NAMES.update({name.casefold(): i for i, name in enumerate(calendar.month_abbr) if name})


class BudgetPeriodError(ValueError):
    """The budget start month is not a month. The message names the field and says what to enter."""


def _invalid(value, why=''):
    return BudgetPeriodError(
        f"Project Info '{LABEL}' is {value!r}, which is not a month{(' (' + why + ')') if why else ''}. "
        f"Enter it as MM/YYYY (for example 07/2027), or leave it blank for January 2027.")


def parse_start(value):
    """(year, month) from the field's value. None / '' give DEFAULT_START."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_START
    if isinstance(value, bool):
        raise _invalid(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        y, m = value.year, value.month
    elif isinstance(value, str):
        text = ' '.join(value.split())
        hit = re.fullmatch(r'(\d{1,2})\s*[/.-]\s*(\d{4})', text)                    # 07/2027, 7-2027
        if hit:
            m, y = int(hit.group(1)), int(hit.group(2))
        else:
            hit = re.fullmatch(r'(\d{4})\s*[/.-]\s*(\d{1,2})', text)                # 2027-07
            if hit:
                y, m = int(hit.group(1)), int(hit.group(2))
            else:
                hit = re.fullmatch(r'([A-Za-z]+)\.?,?\s+(\d{4})', text)             # Jul 2027, July 2027
                if not hit or hit.group(1).casefold() not in _MONTH_NAMES:
                    raise _invalid(value)
                m, y = _MONTH_NAMES[hit.group(1).casefold()], int(hit.group(2))
    else:
        # A bare number (7, 2027, 7.5) is ambiguous between a month and a year: refuse rather than guess.
        raise _invalid(value, 'a bare number is ambiguous')
    if not 1 <= m <= 12:
        raise _invalid(value, 'month must be 1 to 12')
    if not _MIN_YEAR <= y <= _MAX_YEAR:
        raise _invalid(value, f'year must be {_MIN_YEAR} to {_MAX_YEAR}')
    return y, m


@dataclass(frozen=True)
class BudgetPeriod:
    start_year: int
    start_month: int

    @property
    def months(self):
        """The twelve (year, month) pairs, first to last."""
        return [((self.start_year * 12 + self.start_month - 1 + i) // 12,
                 (self.start_month - 1 + i) % 12 + 1) for i in range(12)]

    @property
    def first_day(self):
        return datetime.date(self.start_year, self.start_month, 1)

    @property
    def last_day(self):
        y, m = self.months[-1]
        return datetime.date(y, m, calendar.monthrange(y, m)[1])

    @property
    def budget_year(self):
        """The budget's year: the calendar year holding most of the twelve months, the later one on a 6/6 split
        (change budget-year-by-most-months). The Savills form calls 09/2026-08/2027 "2027"; the Review import and the
        scan store name an approved file's year the same way."""
        years = [y for y, _ in self.months]
        return max(set(years), key=lambda y: (years.count(y), y))

    @property
    def calendar_years(self):
        return sorted({y for y, _ in self.months})

    @property
    def is_default(self):
        return (self.start_year, self.start_month) == DEFAULT_START

    def label(self):
        return f'{self.first_day:%d/%m/%Y}–{self.last_day:%d/%m/%Y}'


def from_value(value):
    return BudgetPeriod(*parse_start(value))


def default():
    return BudgetPeriod(*DEFAULT_START)
