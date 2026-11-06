"""
Vietnamese public holidays, computed rather than typed in.

WHY THIS EXISTS: the roster's holiday differential (+300% day / +390% night, Labour Code Article 98
and 112) needs to know which days of the rostered month are public holidays. That used to be a list
the PM typed by hand into Roster Setup, which is fine for one month and wrong the moment the month
changes and nobody remembers to update it.

Four of Vietnam's statutory holidays are fixed solar dates. Two are LUNAR — Tet and Gio To Hung
Vuong — so they move every year and cannot be hardcoded without going stale. This module converts
them, using Ho Ngoc Duc's algorithm for the Vietnamese lunar calendar (timezone UTC+7, which is what
makes it the VIETNAMESE lunar calendar rather than the Chinese one; the two differ by a day in some
years).

VALIDATED, not assumed: test_known_tet() checks the conversion against six Tet dates that already
happened (2020-2025). It is called on import. If the algorithm is ever broken by an edit, importing
this module raises rather than silently producing wrong holidays.

WHAT THIS DOES NOT KNOW: Article 112 grants 11 statutory days. The days actually taken off are set
each year by a government announcement that adds "hoan doi" swap days — shifting work to a weekend
to bridge a holiday to the weekend, which is how a 5-day Tet becomes 9 in practice. Those are a
policy decision, not a calculation, and this module does not invent them. It returns the STATUTORY
days, which is the correct basis for a budget: they are what carries the legal pay multiplier.
A PM who wants the observed calendar can still type dates into Roster Setup, which override these.

24 NOVEMBER: Nghị quyết 28/2026/QH16 (passed 24/04/2026, Article 2, in force 01/07/2026) makes
24 November "Ngày Văn hóa Việt Nam", a paid day off, so from 2026 the law gives 12 paid days.
statutory_holidays() returns the 11 days of Article 112 only. paid_holidays() applies the law in
force on a given date, 24 November included: Existing-project mode asks it for the calendar of an
approved budget (the law on 1 January of that year), and holidays_in_month() asks it for the days
actually paid in a roster month (change new-prospect-paid-holidays; docs/05-decisions.md, 2026-10-10).
"""
import datetime
import math

PI = math.pi
TIMEZONE = 7  # UTC+7 — this is what makes it the Vietnamese lunar calendar

def jd_from_date(dd, mm, yy):
    a = (14 - mm) // 12
    y = yy + 4800 - a
    m = mm + 12 * a - 3
    jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    if jd < 2299161:
        jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - 32083
    return jd

def jd_to_date(jd):
    if jd > 2299160:
        a = jd + 32044; b = (4 * a + 3) // 146097; c = a - (b * 146097) // 4
    else:
        b = 0; c = jd + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = b * 100 + d - 4800 + m // 10
    return day, month, year

def new_moon(k):
    T = k / 1236.85; T2 = T * T; T3 = T2 * T; dr = PI / 180
    Jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
    Jd1 += 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
    M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
    Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
    F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
    C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr) + 0.0021 * math.sin(2 * dr * M)
    C1 -= 0.4068 * math.sin(Mpr * dr) + 0.0161 * math.sin(dr * 2 * Mpr)
    C1 -= 0.0004 * math.sin(dr * 3 * Mpr)
    C1 += 0.0104 * math.sin(dr * 2 * F) - 0.0051 * math.sin(dr * (M + Mpr))
    C1 -= 0.0074 * math.sin(dr * (M - Mpr)) + 0.0004 * math.sin(dr * (2 * F + M))
    C1 -= 0.0004 * math.sin(dr * (2 * F - M)) - 0.0006 * math.sin(dr * (2 * F + Mpr))
    C1 += 0.0010 * math.sin(dr * (2 * F - Mpr)) + 0.0005 * math.sin(dr * (2 * Mpr + M))
    if T < -11:
        deltat = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
    else:
        deltat = -0.000278 + 0.000265 * T + 0.000262 * T2
    return Jd1 + C1 - deltat

def sun_longitude(jdn):
    T = (jdn - 2451545.0) / 36525; T2 = T * T; dr = PI / 180
    M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
    L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
    DL = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
    DL += (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M) + 0.000290 * math.sin(dr * 3 * M)
    L = L0 + DL; L = L * dr; L = L - PI * 2 * int(L / (PI * 2))
    return L

def get_sun_longitude(dayNumber, timeZone):
    return int(sun_longitude(dayNumber - 0.5 - timeZone / 24.0) / PI * 6)

def get_new_moon_day(k, timeZone):
    return int(new_moon(k) + 0.5 + timeZone / 24.0)

def get_lunar_month_11(yy, timeZone):
    off = jd_from_date(31, 12, yy) - 2415021
    k = int(off / 29.530588853)
    nm = get_new_moon_day(k, timeZone)
    if get_sun_longitude(nm, timeZone) >= 9:
        nm = get_new_moon_day(k - 1, timeZone)
    return nm

def get_leap_month_offset(a11, timeZone):
    k = int((a11 - 2415021.076998695) / 29.530588853 + 0.5)
    last = 0; i = 1
    arc = get_sun_longitude(get_new_moon_day(k + i, timeZone), timeZone)
    while True:
        last = arc; i += 1
        arc = get_sun_longitude(get_new_moon_day(k + i, timeZone), timeZone)
        if not (arc != last and i < 14):
            break
    return i - 1

def lunar_to_solar(lunarD, lunarM, lunarY, lunarLeap, timeZone=7):
    if lunarM < 11:
        a11 = get_lunar_month_11(lunarY - 1, timeZone); b11 = get_lunar_month_11(lunarY, timeZone)
    else:
        a11 = get_lunar_month_11(lunarY, timeZone); b11 = get_lunar_month_11(lunarY + 1, timeZone)
    k = int(0.5 + (a11 - 2415021.076998695) / 29.530588853)
    off = lunarM - 11
    if off < 0:
        off += 12
    if b11 - a11 > 365:
        leapOff = get_leap_month_offset(a11, timeZone)
        leapM = leapOff - 2
        if leapM < 0:
            leapM += 12
        if lunarLeap != 0 and lunarM != leapM:
            return 0, 0, 0
        elif lunarLeap != 0 or off >= leapOff:
            off += 1
    monthStart = get_new_moon_day(k + off, timeZone)
    return jd_to_date(monthStart + lunarD - 1)


# --- Statutory holidays, Labour Code 2019 Article 112 ---------------------------------------
# 11 days: New Year 1, Tet 5, Hung Kings 1, Reunification 1, Labour 1, National Day 2.
# The 2027 Resi template's own Allowance sheet assumes 12 (H6=353=365-12, L6=12, P6=12) while
# one project's assumes 11. Article 112 says 11, and that is what this returns.
TET_DAYS = 5          # Article 112: "Tet Am lich: 05 ngay"
TET_LEAD_DAYS = 1     # the block conventionally opens on New Year's Eve (30 Tet); the exact
                      # split of the 5 days across the year boundary is set by the annual
                      # announcement, so this is the common shape, not a legal certainty.


def _lunar_date(day, month, year):
    d, m, y = lunar_to_solar(day, month, year, 0, TIMEZONE)
    return datetime.date(y, m, d)


def tet_first_day(year):
    """Solar date of mung 1 Tet (1st day of the 1st lunar month) for a given solar year."""
    return _lunar_date(1, 1, year)


def statutory_holidays(year):
    """Every statutory public holiday in `year`, as [(date, name)] sorted by date."""
    tet = tet_first_day(year)
    days = [
        (datetime.date(year, 1, 1), 'Tet Duong lich / New Year'),
        (_lunar_date(10, 3, year), 'Gio To Hung Vuong / Hung Kings'),
        (datetime.date(year, 4, 30), 'Ngay Giai phong mien Nam / Reunification Day'),
        (datetime.date(year, 5, 1), 'Quoc te Lao dong / Labour Day'),
        (datetime.date(year, 9, 1), 'Quoc khanh (ngay lien ke) / National Day, adjacent'),
        (datetime.date(year, 9, 2), 'Quoc khanh / National Day'),
    ]
    for i in range(TET_DAYS):
        offset = i - TET_LEAD_DAYS
        days.append((tet + datetime.timedelta(days=offset), f'Tet Am lich ({i + 1}/{TET_DAYS})'))
    return sorted(days)


# Nghị quyết 28/2026/QH16, Article 2: 24 November is a paid day off, in force from 01/07/2026.
CULTURE_DAY = (11, 24)
CULTURE_DAY_IN_FORCE = datetime.date(2026, 7, 1)
CULTURE_DAY_NAME = 'Ngay Van hoa Viet Nam / Vietnam Culture Day'
CULTURE_DAY_NAME_VN = 'Ngày Văn hóa Việt Nam (24/11)'
LAW_NOTE_VN = ('Ngày lễ hưởng nguyên lương theo Bộ luật Lao động 2019 Điều 112 khoản 1 (11 ngày) và, từ '
               '01/07/2026, ngày 24/11 (Ngày Văn hóa Việt Nam) theo Nghị quyết 28/2026/QH16 Điều 2.')


def paid_holidays(year, as_of=None):
    """Paid public holidays of `year` under the law in force on `as_of` (default: 1 January of `year`).

    The default answers "which calendar did a budget for this year use when it was approved":
    a 2026 budget was approved before Nghị quyết 28/2026/QH16 existed, so it has 11 days; a 2027
    budget has 12. Pass as_of explicitly to ask about the law at another date.
    """
    as_of = as_of or datetime.date(year, 1, 1)
    days = statutory_holidays(year)
    culture = datetime.date(year, *CULTURE_DAY)
    if as_of >= CULTURE_DAY_IN_FORCE and culture >= CULTURE_DAY_IN_FORCE:
        days = sorted(days + [(culture, CULTURE_DAY_NAME)])
    return days


def paid_days_of_year(year):
    """The days of `year` that are paid holidays under the law in force on each day (24 November
    counts from 2026, since its resolution took effect on 01/07/2026)."""
    return paid_holidays(year, as_of=datetime.date(year, 12, 31))


def paid_holidays_in_period(first_day, last_day):
    """Paid public holidays that fall in [first_day, last_day], as [(date, name)] sorted by date, under the law in
    force on `first_day` (the same "law when the budget was approved" convention as `paid_holidays`). For a
    calendar year it equals `paid_holidays(year)`; for a period that straddles two years it joins the two calendars."""
    out = []
    for y in range(first_day.year, last_day.year + 1):
        out += [(d, n) for d, n in paid_holidays(y, as_of=first_day) if first_day <= d <= last_day]
    return sorted(out)


def holidays_in_month(year, month):
    """Day-of-month numbers that are paid holidays — the shape Roster Setup wants."""
    return sorted(d.day for d, _ in paid_days_of_year(year) if d.year == year and d.month == month)


def weekly_working_days(coverage_days):
    """The weekdays (Monday = 0) one person works for a position covered `coverage_days` days a week.

    A position on 6 or 7 coverage days works Monday to Saturday: a 7-day position's headcount already carries the
    7/6 uplift, so each person still works 6 days. Below 6, the person works Monday to the N-th weekday, the same
    shape the roster grid uses (5 = Monday to Friday)."""
    n = int(coverage_days or 0)
    if n < 1:
        raise ValueError(f'Coverage days is {coverage_days!r}; a staffed position works at least 1 day a week.')
    return frozenset(range(min(n, 6)))


def working_days_by_month(first_day, last_day, coverage_days=6):
    """A person's working days in each calendar month of [first_day, last_day]: the days on their weekly pattern
    (see weekly_working_days) minus the paid holidays, under the law in force on `first_day` (the same convention as
    paid_holidays_in_period). Returns [((year, month), days)] in date order (change apply-head-of-pm-decisions-2026-10,
    D6: one count for both workbooks)."""
    pattern = weekly_working_days(coverage_days)
    holidays = {d for d, _ in paid_holidays_in_period(first_day, last_day)}
    out = {}
    day = first_day
    while day <= last_day:
        key = (day.year, day.month)
        out.setdefault(key, 0)
        if day.weekday() in pattern and day not in holidays:
            out[key] += 1
        day += datetime.timedelta(days=1)
    return list(out.items())


def working_days(first_day, last_day, coverage_days=6):
    """A person's working days in [first_day, last_day] (see working_days_by_month). 302 for 2027 on 6 days."""
    return sum(n for _, n in working_days_by_month(first_day, last_day, coverage_days))


def test_known_tet():
    """Validate the lunar conversion against Tet dates that already happened.

    Run on import. A wrong holiday calendar is worse than none, because it silently moves a
    +300%/+390% pay multiplier onto the wrong days.
    """
    known = {2020: (1, 25), 2021: (2, 12), 2022: (2, 1),
             2023: (1, 22), 2024: (2, 10), 2025: (1, 29)}
    for year, (m, d) in known.items():
        got = tet_first_day(year)
        if (got.month, got.day) != (m, d):
            raise AssertionError(
                f'Vietnamese lunar conversion is wrong: Tet {year} computed as {got}, '
                f'but it actually fell on {year}-{m:02d}-{d:02d}. Refusing to produce a '
                f'holiday calendar from a broken algorithm.')
    return True


test_known_tet()


if __name__ == '__main__':
    for y in (datetime.date.today().year, datetime.date.today().year + 1):
        print(f'--- {y} — {len(statutory_holidays(y))} statutory days (Tet: {tet_first_day(y)}) ---')
        for d, name in statutory_holidays(y):
            print(f'  {d}  {d.strftime("%a")}  {name}')
