"""The labour-law numbers behind the staff cost, read from one dated table instead of the code.

WHY THIS EXISTS: the payroll chain (gross salary, employer social/health/unemployment insurance,
trade union) depends on numbers the state changes: the regional minimum wage, the insurance base
and its 20x ceiling, the employer rates. They used to sit in the code as `STATUTORY_*_2026`
constants and drifted from the law the moment the law changed. They now live in
`data/generation_B_verified/Ref_LaborLawParams.csv`, one row per value with its effective dates,
legal basis and the date it was last checked. A new decree is a new row, not a code change.

Rows whose legal_basis is "template" are Savills policy carried by the budget template (13th
month, 10% admin markup). They are not law; they are listed so the Staff bridge can show them.

The tool never invents a percentage: for any month it returns exactly the values in force that
month. When the budget year starts after the latest effective date, it uses the latest values and
says so (`YearParams.note`), because no newer rule had been published when the table was checked.
"""
import csv
import datetime
import os

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LABOR_LAW_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified', 'Ref_LaborLawParams.csv')

COLUMNS = ['parameter', 'region', 'value', 'unit', 'effective_from', 'effective_to',
           'legal_basis', 'source_url', 'checked_on']
REGIONS = ('I', 'II', 'III', 'IV')
DEFAULT_REGION = 'I'   # the template's own A1!I5 (5,310,000 VND) is the Region I minimum wage
TEMPLATE_BASIS = 'template'
# Parameters that differ by region. Every other parameter has a blank region.
REGIONAL = {'min_wage_region'}
# What a budget year needs; a table missing one of these is unusable.
REQUIRED = ('min_wage_region', 'insurance_base', 'si_hi_ceiling_multiple', 'ui_ceiling_multiple',
            'employer_si_rate', 'employer_hi_rate', 'employer_ui_rate', 'union_rate',
            'thirteenth_month', 'admin_markup')


def _date(text, row_no, column):
    try:
        return datetime.date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(f'Ref_LaborLawParams.csv row {row_no}: {column} "{text}" is not a date '
                         f'(YYYY-MM-DD).') from None


def load_rows(path=LABOR_LAW_CSV):
    """Every row of the table, validated. Raises ValueError naming the row on any gap."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f'Ref_LaborLawParams.csv is missing columns: {", ".join(missing)}.')
        raw = list(reader)
    rows = []
    for row_no, r in enumerate(raw, start=2):   # row 1 is the header
        name = (r['parameter'] or '').strip()
        if not name:
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no}: parameter is blank.')
        if not (r['effective_from'] or '').strip():
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): effective_from is blank.')
        basis = (r['legal_basis'] or '').strip()
        if not basis:
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): legal_basis is blank. '
                             f'A legal value needs its document; a Savills policy value says "template".')
        if not (r['checked_on'] or '').strip():
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): checked_on is blank.')
        region = (r['region'] or '').strip()
        if name in REGIONAL and region not in REGIONS:
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): region "{region}" '
                             f'is not one of {", ".join(REGIONS)}.')
        if name not in REGIONAL and region:
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): this parameter has no region.')
        try:
            value = float(r['value'])
        except (TypeError, ValueError):
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): value "{r["value"]}" '
                             f'is not a number.') from None
        start = _date(r['effective_from'], row_no, 'effective_from')
        end = _date(r['effective_to'], row_no, 'effective_to') if (r['effective_to'] or '').strip() else None
        if end is not None and end < start:
            raise ValueError(f'Ref_LaborLawParams.csv row {row_no} ({name}): effective_to is before effective_from.')
        rows.append({'parameter': name, 'region': region, 'value': value, 'unit': r['unit'].strip(),
                     'effective_from': start, 'effective_to': end, 'legal_basis': basis,
                     'source_url': (r['source_url'] or '').strip(),
                     'checked_on': _date(r['checked_on'], row_no, 'checked_on'), 'row_no': row_no})
    return rows


def _in_force(rows, parameter, day, region):
    """The one row of `parameter` in force on `day`; the latest-starting one wins an overlap."""
    hits = [r for r in rows
            if r['parameter'] == parameter
            and (parameter not in REGIONAL or r['region'] == region)
            and r['effective_from'] <= day
            and (r['effective_to'] is None or day <= r['effective_to'])]
    if not hits:
        where = f' for region {region}' if parameter in REGIONAL else ''
        raise ValueError(f'Ref_LaborLawParams.csv has no {parameter}{where} in force on {day.isoformat()}.')
    return max(hits, key=lambda r: r['effective_from'])


class YearParams:
    """The values in force in each month of one budget year, for one minimum-wage region.

    months[m][parameter] -> value for m = 1..12; rows[m][parameter] -> the table row behind it.
    note is a Vietnamese sentence, empty unless the year starts after the latest published rule.
    """

    def __init__(self, year, region, months, rows, note, latest_effective):
        self.year = year
        self.region = region
        self.months = months
        self.rows = rows
        self.note = note
        self.latest_effective = latest_effective

    def value(self, parameter, month=1):
        return self.months[month][parameter]

    def annual_average(self, parameter):
        """Mean of the 12 monthly values (a mid-year change weighs by the months it covers)."""
        return sum(self.months[m][parameter] for m in range(1, 13)) / 12

    def is_constant(self, parameter):
        return len({self.months[m][parameter] for m in range(1, 13)}) == 1

    def legal_bases(self):
        """Distinct legal documents used in the year, in table order (template rows left out)."""
        seen = []
        for m in range(1, 13):
            for r in self.rows[m].values():
                if r['legal_basis'] != TEMPLATE_BASIS and r['legal_basis'] not in seen:
                    seen.append(r['legal_basis'])
        return seen


def params_for_year(year, region=None, path=LABOR_LAW_CSV, rows=None):
    """Values in force for each month of `year` in `region` (blank region = Region I)."""
    region = (region or DEFAULT_REGION).strip().upper()
    if region not in REGIONS:
        raise ValueError(f'Minimum Wage Region "{region}" is not one of {", ".join(REGIONS)}.')
    rows = load_rows(path) if rows is None else rows
    names = {r['parameter'] for r in rows}
    missing = [p for p in REQUIRED if p not in names]
    if missing:
        raise ValueError(f'Ref_LaborLawParams.csv has no row for: {", ".join(missing)}.')
    months, used = {}, {}
    for m in range(1, 13):
        day = datetime.date(year, m, 1)
        picked = {p: _in_force(rows, p, day, region) for p in REQUIRED}
        months[m] = {p: r['value'] for p, r in picked.items()}
        used[m] = picked
    legal = [r for r in rows if r['legal_basis'] != TEMPLATE_BASIS]
    latest = max(r['effective_from'] for r in legal)
    note = ''
    if datetime.date(year, 1, 1) > latest:
        note = (f'Chưa có quy định mới cho năm {year} tại ngày kiểm tra bảng tham số; '
                f'áp dụng mức đang có hiệu lực từ {latest.strftime("%d/%m/%Y")}.')
    return YearParams(year, region, months, used, note, latest)
