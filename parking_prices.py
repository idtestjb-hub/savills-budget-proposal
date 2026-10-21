"""
Monthly parking prices per vehicle for RP1 (motorbike) and RP2 (car) — change price-fee-and-parking-from-portfolio,
design D5–D8, spec parking-revenue-pricing.

Before this change the two prices were constants copied from one reference project's parking proposal (DEFAULTS
below, still the last resort). Now the price is decided once per run by resolve(), in this order per vehicle type:
  recorded   the recorded monthly parking revenue the PM entered for a project at stable operation (spec
             parking-revenue-actuals): the line is that figure x 12, there is no per-bay price;
  entered    'Car Parking Price (VND/vehicle/month)' / 'Motorbike Parking Price (VND/vehicle/month)' on Project Info;
  range      the median first-vehicle monthly price of the master list's residential projects
             (Budget_Agent/data/master_list_verified/Dim_Property_Residential.csv, columns CarParkingFee_raw and
             BikeParkingFee_raw, free text): the project itself left out by name, IQR outliers dropped once, at least
             MIN_PROJECTS projects; used as quoted (including VAT, no CPI step: the master list is the 2026 snapshot
             of list prices, user's choice 2026-10-20);
  default    DEFAULTS, with the former wording.

Parsing rule (one rule, design D5): the first number in the text that falls inside the vehicle's plausible band is
the first-vehicle monthly price; "1.300.000", "1,300,000", "1300000" and "909090.9" are all read. A text with no
such number is classified blank / zero / no paid parking / number out of band / unparsed and listed, never priced.

Data files read: Dim_Property_Residential.csv. Nothing is written.
"""
import csv
import os
import re
from dataclasses import dataclass, field

import real_budget_ranges as rbr
from service_levels import name_key

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(os.path.dirname(SOURCE_DIR), 'data', 'master_list_verified', 'Dim_Property_Residential.csv')

MIN_PROJECTS = rbr.MIN_PROJECTS
IQR_K = rbr.IQR_K

# Real, from A&K Tower's own "B2.8 Đơn giá gửi xe-Parking pr" sheet, Section B (its proposed price, informed by six
# comparables in Section A). The last resort when the range cannot be formed.
DEFAULTS = {'car': 1_100_000, 'moto': 110_000}
VEHICLES = {
    'car': dict(column='CarParkingFee_raw', lo=300_000, hi=5_000_000, vi='ô tô', code='RP2'),
    'moto': dict(column='BikeParkingFee_raw', lo=30_000, hi=400_000, vi='xe máy', code='RP1'),
}
SOURCE_RECORDED, SOURCE_ENTERED, SOURCE_RANGE, SOURCE_DEFAULT = 'recorded', 'entered', 'range', 'default'

STATUS_PRICE = 'price'
STATUS_BLANK = 'blank'
STATUS_ZERO = 'zero'
STATUS_NO_PARKING = 'no paid parking'
STATUS_OUT_OF_BAND = 'number out of band'
STATUS_UNPARSED = 'unparsed'
NO_PARKING_WORDS = ('không', 'khong', 'n/a', 'free', 'miễn', 'chưa', 'đơn vị khác', 'cđt đã bán', 'đã bán', 'no')

_NUM = re.compile(r'(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d{4,9}(?:\.\d+)?)')


def _to_number(s):
    """A number token to a float: dotted or comma thousands, an optional 1–2 digit decimal part, or a plain number."""
    if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', s):
        return float(re.sub(r'[.,]', '', s))
    m = re.fullmatch(r'(\d{1,3}(?:[.,]\d{3})+)[.,](\d{1,2})', s)
    if m:
        return float(re.sub(r'[.,]', '', m.group(1)) + '.' + m.group(2))
    try:
        return float(s)
    except ValueError:
        return None


def parse(text, lo, hi):
    """(price, status): the first number of `text` inside [lo, hi], else None with why."""
    t = str(text or '').strip()
    if not t:
        return None, STATUS_BLANK
    if t in ('0', '-', '0.0'):
        return None, STATUS_ZERO
    nums = [v for v in (_to_number(m.group(1)) for m in _NUM.finditer(t)) if v is not None]
    inside = [v for v in nums if lo <= v <= hi]
    if inside:
        return inside[0], STATUS_PRICE
    if nums:
        return None, STATUS_OUT_OF_BAND
    low = t.casefold()
    if any(w in low for w in NO_PARKING_WORDS):
        return None, STATUS_NO_PARKING
    return None, STATUS_UNPARSED


def load_rows(path=None):
    """Residential master-list rows: name, district, city and the two fee texts. [] when the file is absent."""
    path = path or MASTER_CSV
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            out.append(dict(name=(r.get('Name') or '').strip(), district=r.get('District') or '',
                            city=r.get('City_Province') or '', car=r.get('CarParkingFee_raw') or '',
                            moto=r.get('BikeParkingFee_raw') or ''))
    return out


OUT_SELF = 'chính dự án'
OUT_LOW = rbr.OUT_LOW
OUT_HIGH = rbr.OUT_HIGH


@dataclass
class PriceRange:
    vehicle: str
    n_rows: int = 0
    n_price: int = 0                    # rows with a readable price (before leave-one-out and IQR)
    used: list = field(default_factory=list)       # [(name, price)]
    left_out: list = field(default_factory=list)   # [(name, price, why)]
    parsed: list = field(default_factory=list)     # [(name, text, price, status)] every row
    p25: float | None = None
    median: float | None = None
    p75: float | None = None

    @property
    def n_used(self):
        return len(self.used)

    @property
    def usable(self):
        return self.n_used >= MIN_PROJECTS and self.median is not None

    @property
    def price(self):
        """The applied price when usable: the median, rounded to the VND."""
        return round(self.median) if self.usable else None


def form_range(vehicle, rows, self_name=None):
    """Leave out the project itself (by name key), then IQR outliers once; PERCENTILE.INC statistics."""
    spec = VEHICLES[vehicle]
    pr = PriceRange(vehicle=vehicle, n_rows=len(rows))
    self_keys = rbr.self_keys(self_name)
    cands = []
    for r in rows:
        price, status = parse(r[vehicle], spec['lo'], spec['hi'])
        pr.parsed.append((r['name'], r[vehicle], price, status))
        if price is None:
            continue
        pr.n_price += 1
        if name_key(r['name']) in self_keys:
            pr.left_out.append((r['name'], price, OUT_SELF))
        else:
            cands.append((r['name'], price))
    if cands:
        vals = [v for _, v in cands]
        q1, q3 = rbr.percentile_inc(vals, 0.25), rbr.percentile_inc(vals, 0.75)
        lo, hi = q1 - IQR_K * (q3 - q1), q3 + IQR_K * (q3 - q1)
        for name, v in cands:
            if v < lo:
                pr.left_out.append((name, v, OUT_LOW))
            elif v > hi:
                pr.left_out.append((name, v, OUT_HIGH))
            else:
                pr.used.append((name, v))
    if pr.used:
        vals = [v for _, v in pr.used]
        pr.p25, pr.median, pr.p75 = (rbr.percentile_inc(vals, 0.25), rbr.percentile_inc(vals, 0.5),
                                     rbr.percentile_inc(vals, 0.75))
    return pr


def resolve(project, rows=None):
    """{vehicle: dict(price, source, range, recorded)} — the one decision both workbooks read (design D5).
    `price` is VND per vehicle per month (None under a recorded figure); `recorded` is the recorded monthly revenue
    or None. Cached on project['parking_prices'] by the caller."""
    rows = load_rows() if rows is None else rows
    ops = project.get('operating') or {}
    recorded = ops.get('parking') or {}
    entered = ops.get('parking_price') or {}
    out = {}
    for vehicle in VEHICLES:
        pr = form_range(vehicle, rows, project.get('name'))
        rec = recorded.get(vehicle)
        if rec is not None:
            out[vehicle] = dict(price=None, source=SOURCE_RECORDED, range=pr, recorded=rec)
        elif entered.get(vehicle):
            out[vehicle] = dict(price=float(entered[vehicle]), source=SOURCE_ENTERED, range=pr, recorded=None)
        elif pr.usable:
            out[vehicle] = dict(price=float(pr.price), source=SOURCE_RANGE, range=pr, recorded=None)
        else:
            out[vehicle] = dict(price=float(DEFAULTS[vehicle]), source=SOURCE_DEFAULT, range=pr, recorded=None)
    return out


def resolved(project):
    """project['parking_prices'], resolving once on first use."""
    if project.get('parking_prices') is None:
        project['parking_prices'] = resolve(project)
    return project['parking_prices']


# ---- wording -------------------------------------------------------------------------------------------------
DEFAULT_CLAUSE_VI = 'đơn giá thực tế, theo đề xuất giữ xe của một dự án tham chiếu'


def source_clause_vi(vehicle, entry):
    """The parenthetical source clause of the RP1/RP2 remark (spec deliverable-remarks). Names no project."""
    if entry['source'] == SOURCE_ENTERED:
        return 'đơn giá giữ xe do PM nhập, đã gồm VAT'
    if entry['source'] == SOURCE_RANGE:
        pr = entry['range']
        return (f'trung vị giá giữ xe {VEHICLES[vehicle]["vi"]} tháng niêm yết hiện hành của {pr.n_used} dự án do '
                f'Savills quản lý, đã gồm VAT; khoảng giữa P25–P75: {pr.p25:,.0f}–{pr.p75:,.0f} VND/xe/tháng')
    return DEFAULT_CLAUSE_VI


def source_label_en(entry):
    """The analysis workbook's source column."""
    if entry['source'] == SOURCE_RECORDED:
        return ('Recorded average monthly revenue entered by the PM (Project Info, project at stable operation); '
                'not slots x rate.')
    if entry['source'] == SOURCE_ENTERED:
        return 'Monthly price per vehicle entered by the PM on Project Info (incl. VAT); wins over the portfolio range.'
    if entry['source'] == SOURCE_RANGE:
        pr = entry['range']
        return (f'Median of the first-vehicle monthly list prices of {pr.n_used} Savills-managed residential projects '
                f'(master list, incl. VAT, as quoted; P25–P75 {pr.p25:,.0f}–{pr.p75:,.0f}; {pr.n_price} rows with a '
                f'price, {len(pr.left_out)} left out).')
    pr = entry['range']
    return (f'Former constant (A&K Tower\'s proposed price): the portfolio range could not be formed '
            f'({pr.n_used} usable price(s), floor {MIN_PROJECTS}).')
