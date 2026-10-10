"""Common-area electricity and water prices, read from one dated table instead of the code.

WHY THIS EXISTS: in Existing-project mode (change carry-forward-common-utilities) `EEE.C` and `EEW.C`
start from the building's own actual spend and move only when a published price or VAT rate moves.
Those prices live in `data/generation_B_verified/Ref_UtilityTariffs.csv`, one row per component with
its effective dates, legal basis and the date it was checked, like `Ref_LaborLawParams.csv`. A new
price decision is a new row, not a code change. The tool never adds a percentage of its own.

Components (design D2/D3):
  base               VND per kWh or m3, excluding VAT (per category; a PM bill price replaces it)
  wastewater_pct     water only, % of base: the drainage and wastewater charge (region-specific)
  vat_pct            VAT on electricity, or on clean water
  wastewater_vat_pct VAT on the drainage and wastewater charge

A row with a blank `category` applies to every category of its utility; a row with a blank `region`
applies everywhere. The price of a month is the one in force on the 1st of that month.
"""
import csv
import datetime
import os
import unicodedata

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UTILITY_TARIFF_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified', 'Ref_UtilityTariffs.csv')

COLUMNS = ['utility', 'category', 'component', 'value', 'unit', 'effective_from', 'effective_to',
           'region', 'legal_basis', 'source_url', 'checked_on', 'note']
ELECTRICITY = 'electricity'
WATER = 'water'
UTILITIES = (ELECTRICITY, WATER)
COMPONENTS = ('base', 'wastewater_pct', 'vat_pct', 'wastewater_vat_pct')
HCMC = 'TP.HCM'

CAT_E_LT6 = 'Hành chính sự nghiệp, dưới 6 kV'
CAT_E_GE6 = 'Hành chính sự nghiệp, từ 6 kV trở lên'
CAT_E_BILL = 'Kinh doanh (theo giá trên hóa đơn)'
CAT_W_HCMC = 'Sinh hoạt bậc cao nhất, TP.HCM'
CAT_W_BILL = 'Theo giá trên hóa đơn'
CATEGORIES = {ELECTRICITY: (CAT_E_LT6, CAT_E_GE6, CAT_E_BILL), WATER: (CAT_W_HCMC, CAT_W_BILL)}
DEFAULT_CATEGORY = {ELECTRICITY: CAT_E_LT6, WATER: CAT_W_HCMC}
UNITS = {ELECTRICITY: 'kWh', WATER: 'm3'}

# "City / Province" values that mean Ho Chi Minh City, compared after _fold().
_HCMC_ALIASES = ('ho chi minh', 'hcm', 'tphcm', 'tp hcm', 'sai gon', 'saigon')


class TariffError(ValueError):
    """A price the run needs is not in the table, or the table itself is malformed."""


def _fold(text):
    """Lower case, no Vietnamese diacritics, punctuation as spaces: 'TP. Hồ Chí Minh' -> 'tp ho chi minh'."""
    text = unicodedata.normalize('NFD', str(text or '')).replace('đ', 'd').replace('Đ', 'D')
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn').lower()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in text).split())


def region_of(city_province):
    """The table region for a project's "City / Province": TP.HCM, or the text as typed ('' if blank)."""
    folded = _fold(city_province)
    if not folded:
        return ''
    if any(alias in folded or alias == folded.replace(' ', '') for alias in _HCMC_ALIASES):
        return HCMC
    return str(city_province).strip()


def _date(text, row_no, column):
    try:
        return datetime.date.fromisoformat(text.strip())
    except ValueError:
        raise TariffError(f'Ref_UtilityTariffs.csv row {row_no}: {column} "{text}" is not a date '
                          f'(YYYY-MM-DD).') from None


def load_rows(path=UTILITY_TARIFF_CSV):
    """Every row of the table, validated. Raises TariffError naming the row on any gap."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise TariffError(f'Ref_UtilityTariffs.csv is missing columns: {", ".join(missing)}.')
        raw = list(reader)
    rows = []
    for row_no, r in enumerate(raw, start=2):   # row 1 is the header
        utility = (r['utility'] or '').strip()
        component = (r['component'] or '').strip()
        label = f'row {row_no} ({utility} {component})'
        if utility not in UTILITIES:
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: utility must be one of {", ".join(UTILITIES)}.')
        if component not in COMPONENTS:
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: component must be one of {", ".join(COMPONENTS)}.')
        if not (r['effective_from'] or '').strip():
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: effective_from is blank.')
        basis = (r['legal_basis'] or '').strip()
        if not basis:
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: legal_basis is blank. Every price needs its document.')
        if not (r['checked_on'] or '').strip():
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: checked_on is blank.')
        try:
            value = float(r['value'])
        except (TypeError, ValueError):
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: value "{r["value"]}" is not a number.') from None
        start = _date(r['effective_from'], row_no, 'effective_from')
        end = _date(r['effective_to'], row_no, 'effective_to') if (r['effective_to'] or '').strip() else None
        if end is not None and end < start:
            raise TariffError(f'Ref_UtilityTariffs.csv {label}: effective_to is before effective_from.')
        rows.append({'utility': utility, 'category': (r['category'] or '').strip(), 'component': component,
                     'value': value, 'unit': (r['unit'] or '').strip(), 'effective_from': start,
                     'effective_to': end, 'region': (r['region'] or '').strip(), 'legal_basis': basis,
                     'source_url': (r['source_url'] or '').strip(),
                     'checked_on': _date(r['checked_on'], row_no, 'checked_on'),
                     'note': (r['note'] or '').strip(), 'row_no': row_no})
    return rows


def _candidates(rows, utility, component, category, region):
    """Rows of a component that can apply to this category and region (specific or blank)."""
    return [r for r in rows if r['utility'] == utility and r['component'] == component
            and r['category'] in ('', category) and r['region'] in ('', region)]


def _in_force(cands, day):
    hits = [r for r in cands if r['effective_from'] <= day and (r['effective_to'] is None or day <= r['effective_to'])]
    if not hits:
        return None
    # A category- or region-specific row beats a general one; then the latest-starting row wins.
    return max(hits, key=lambda r: (bool(r['category']), bool(r['region']), r['effective_from']))


class MonthPrice:
    """The price parts of one month for one line. `rows` maps component -> the table row behind it
    (absent for a PM bill price and for a zero wastewater charge)."""

    def __init__(self, utility, year, month, base, wastewater_pct, vat_pct, wastewater_vat_pct, rows, bill):
        self.utility, self.year, self.month = utility, year, month
        self.base, self.wastewater_pct = base, wastewater_pct
        self.vat_pct, self.wastewater_vat_pct = vat_pct, wastewater_vat_pct
        self.rows, self.bill = rows, bill

    def net(self):
        """VND per kWh or m3, excluding VAT."""
        return self.base * (1 + self.wastewater_pct / 100)

    def gross(self, vat_pct=None, wastewater_vat_pct=None):
        """VND per kWh or m3, including VAT; the two rates may be replaced (bridge: price at another month's VAT)."""
        v = self.vat_pct if vat_pct is None else vat_pct
        wv = self.wastewater_vat_pct if wastewater_vat_pct is None else wastewater_vat_pct
        return self.base * (1 + v / 100) + self.base * self.wastewater_pct / 100 * (1 + wv / 100)

    def price(self, incl_vat):
        return self.gross() if incl_vat else self.net()


class LineTariff:
    """The prices of one line (electricity or water) for one project.

    category: one of CATEGORIES[utility]; blank = the default. bill_price: the PM's unit price from the
    bill (VND per unit, excluding VAT), which replaces `base` in every month. region: region_of() of the
    project's "City / Province"."""

    def __init__(self, utility, category='', region='', bill_price=None, bill_source='', rows=None,
                 path=UTILITY_TARIFF_CSV):
        if utility not in UTILITIES:
            raise TariffError(f'Unknown utility "{utility}".')
        self.utility = utility
        self.category = (category or '').strip() or DEFAULT_CATEGORY[utility]
        if self.category not in CATEGORIES[utility]:
            raise TariffError(f'Tariff category "{self.category}" is not one of: '
                              f'{"; ".join(CATEGORIES[utility])}.')
        self.region = region or ''
        self.bill_price = bill_price
        self.bill_source = (bill_source or '').strip()
        self.rows = load_rows(path) if rows is None else rows
        if bill_price is None:
            base_rows = _candidates(self.rows, utility, 'base', self.category, self.region)
            if not base_rows:
                any_base = [r for r in self.rows if r['utility'] == utility and r['component'] == 'base'
                            and r['category'] == self.category]
                if any_base:   # the category exists, but only for another region (HCMC water)
                    raise TariffError(
                        f'{utility}: the category "{self.category}" applies only to '
                        f'{", ".join(sorted({r["region"] for r in any_base}))}, and "City / Province" is '
                        f'"{self.region or "(blank)"}". Enter the unit price on the bill (and its source), '
                        f'or correct "City / Province".')
                raise TariffError(f'{utility}: the category "{self.category}" has no single table price. '
                                  f'Enter the unit price on the bill (VND, excluding VAT) and its source.')

    def month(self, year, month):
        """The MonthPrice in force on the 1st of `month`/`year`. Raises TariffError when the table does not
        cover it."""
        day = datetime.date(year, month, 1)
        used = {}

        def need(component):
            r = _in_force(_candidates(self.rows, self.utility, component, self.category, self.region), day)
            if r is None:
                raise TariffError(f'Ref_UtilityTariffs.csv has no {self.utility} {component} for '
                                  f'"{self.category}" in force on {day.strftime("%d/%m/%Y")}.')
            used[component] = r
            return r['value']

        base = self.bill_price if self.bill_price is not None else need('base')
        vat = need('vat_pct')
        ww = wvat = 0.0
        if self.utility == WATER:
            ww_rows = _candidates(self.rows, WATER, 'wastewater_pct', self.category, self.region)
            ww_rows = [r for r in ww_rows if r['region']]   # the charge is set city by city
            if ww_rows:
                ww = need('wastewater_pct')
                if ww:
                    wvat = need('wastewater_vat_pct')
        return MonthPrice(self.utility, year, month, float(base), ww, vat, wvat, used, self.bill_price is not None)

    def latest_effective(self):
        """The latest effective_from of the price rows (base, wastewater charge) this line can use, for the
        'no newer price' note. VAT rows are left out: a VAT step on 1 January is not a new price."""
        comps = ('wastewater_pct',) if self.bill_price is not None else ('base', 'wastewater_pct')
        dates = [r['effective_from'] for c in comps
                 for r in _candidates(self.rows, self.utility, c, self.category, self.region)
                 if c == 'base' or r['region']]
        return max(dates) if dates else None

    def year_note(self, year):
        """Vietnamese note when the budget year starts after the latest published row, else ''."""
        latest = self.latest_effective()
        if latest is not None and datetime.date(year, 1, 1) > latest:
            return (f'Chưa có văn bản giá mới cho năm {year} tại ngày kiểm tra bảng giá; '
                    f'áp dụng mức đang có hiệu lực từ {latest.strftime("%d/%m/%Y")}.')
        return ''
