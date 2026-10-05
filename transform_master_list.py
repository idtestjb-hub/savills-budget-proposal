"""
Transforms input/project/2026_Master List.xlsx (Residential: 105 real properties, Commercial: 55
real properties) into clean, typed reference tables — CSV for Power BI, plus an Excel workbook for
human review. It adds the Master List to the project's comparables; it does not replace the 8
detailed project budgets. master_comparables.py reads Dim_Property_Residential.csv as its second pool
of comparables (property scale and management-fee rates for ~75 more properties), while the 8
detailed budgets still supply the Capex and OPEX line detail. The old 8-project data had property
scale and staff cost/headcount as two disjoint populations with no shared key (see
Budget_Agent/docs/15_Fact_Dim_Master_Mapping.pptx); this Master List has both on the SAME row for
73 of 105 residential properties, which is what lets a real staffing ratio be derived
(derive_staffing_benchmarks.py, derive_position_staffing_ratios.py) instead of assumed.

The source sheet is real operational data entered by different people over time, not a clean
database export, so most fields need real parsing, not a column copy:

  - Numbers appear in both locale conventions in the SAME column — "20,000" (comma = thousands)
    and "152.506,47" (period = thousands, comma = decimal) both occur. parse_numeric_token() picks
    the convention per-value: whichever separator is followed by exactly 3 digits is thousands;
    the other (if any) is decimal.
  - Many management-fee cells hold MULTIPLE rates for different product types in one string
    (e.g. "căn hộ 13.310 / officetel 22.000 / shophouse 25.300"). extract_fee_by_product() pulls
    each one out by keyword; MgmtFeeRate_Primary picks apartment (or the single blended number)
    for use in comparable-matching, and MgmtFeeRate_ByProduct keeps the rest.
  - Some fee cells aren't numbers at all — "N/A", "TBC", "Không thu phí" (no fee charged), "miễn
    phí 3 năm đầu" (free for first 3 years). These become MgmtFeeRate_Primary=blank with a
    MgmtFeeRate_Status explaining why, not a guessed 0.
  - Residential management fee is quoted INCL. VAT; Commercial is quoted EXCL. VAT (both stated on
    the sheet's own headers) — carried through as MgmtFeeVAT so nothing downstream compares them
    blind.
  - GFA is occasionally given in hectares instead of m² ("~22 hecta") — detected by unit word and
    converted (×10,000). Every parsed numeric field keeps its *_raw sibling column with the
    original cell text, so any parse can be audited or corrected without going back to Excel.

v2 additions:
  - Management fee is now split into per-product columns (Fee_Apartment, Fee_Officetel,
    Fee_Shophouse, Fee_Villa, Fee_Retail), the same shape as the existing per-product unit count
    columns (ApartmentUnits, OfficetelUnits, ...). MgmtFeeRate_Primary is kept as the "main" column
    (apartment rate, or the single blended rate when the source didn't break it out by product) —
    same relationship as TotalUnits is the main column alongside the per-product unit counts.
  - Address is split into Street / Ward / District / City_Province via parse_address(). The source
    mixes English and Vietnamese, HCMC urban wards/districts (Phường/Quận) with rural
    communes/districts in other provinces (Xã/Huyện), and pre- and post-2025-merger ward names —
    parse_address() extracts by administrative-qualifier keyword (Ward/Phường/P., District/Quận/Q.,
    Commune/Xã, Huyện, City/Tp./Thành phố, Province/Tỉnh) wherever it appears in the string, in
    either "qualifier name" or "name qualifier" order. It is real, tested keyword extraction, NOT a
    validated match against an official administrative gazetteer — AddressParseStatus flags rows
    where neither a ward nor a district keyword was found, and District_Raw / Address_Raw are
    always kept so any row can be corrected by hand rather than trusted blind.
  - District_Standardized normalizes spelling/case/diacritic variants of the ~12 most common HCMC
    districts seen in this sheet (e.g. "Binh Thanh Dist." / "Binh Thanh District" / "Bình Thạnh" all
    become "Bình Thạnh") and numbered districts to "District N". Anything not in that known list is
    passed through title-cased, unchanged in meaning — it is a spelling normalizer, not a gazetteer
    lookup, and does not attempt to resolve the 2025 ward-merger renaming.

Nothing here backfills a guess for a field that couldn't be parsed — it stays blank with a status/
raw column explaining why, same policy as the rest of this project's real-data handling.
"""
import os
import re
import csv
import unicodedata

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCE_PATH = os.path.join(BASE, 'input', 'project', '2026_Master List.xlsx')
OUT_DIR = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified')
CSV_RESIDENTIAL = os.path.join(OUT_DIR, 'Dim_Property_Residential.csv')
CSV_COMMERCIAL = os.path.join(OUT_DIR, 'Dim_Property_Commercial.csv')
REVIEW_XLSX = os.path.join(OUT_DIR, 'Master_List_Review.xlsx')

NA_TOKENS = {'n/a', 'na', 'none', '', '0'}  # '0' handled specially -- a real 0 is kept, not dropped
FREE_TOKENS = ['miễn phí', 'không thu', 'free', 'topup']
TBC_TOKENS = ['tbc', 'chưa có', 'chua co']


# ============================================================================================
# Parsing helpers
# ============================================================================================
def clean_text(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return re.sub(r'\s*\n\s*', ' / ', s).strip()


def parse_numeric_token(token):
    """'152.506,47' -> 152506.47 ; '119,335.24' -> 119335.24 ; '20,000' -> 20000.0 ; '13500' -> 13500.0
    Rule: whichever separator is followed by exactly 3 digits (and nothing after) is a thousands
    grouping; if the LAST separator is followed by 1-2 digits, that one is the decimal point.
    A trailing group of 4+ digits (e.g. '28.5600') is neither a clean thousands-grouping nor a
    plausible decimal -- almost certainly a source typo (missing/extra digit) -- so this raises
    rather than guessing which digit is wrong; callers already treat ValueError as unparseable."""
    seps = [m.start() for m in re.finditer(r'[.,]', token)]
    if not seps:
        return float(token)
    last = seps[-1]
    after = token[last + 1:]
    if len(after) == 3 and after.isdigit():
        return float(re.sub(r'[.,]', '', token))
    if len(after) >= 4:
        raise ValueError(f'ambiguous number format (trailing {len(after)}-digit group): {token}')
    integer_part = re.sub(r'[.,]', '', token[:last])
    return float(f'{integer_part}.{after}' if after else integer_part)


def first_number(raw):
    """Best-effort: pull the first numeric token out of any raw cell value. Returns (value, note)."""
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    s = str(raw).strip()
    if not s:
        return None, None
    m = re.search(r'\d[\d.,]*\d|\d', s)
    if not m:
        return None, 'no numeric token found'
    try:
        return parse_numeric_token(m.group(0)), None
    except ValueError:
        return None, f'unparseable token: {m.group(0)}'


def parse_area(raw):
    """Like first_number, but converts hectares to m² when the cell says 'ha'/'hecta' and has no
    explicit 'm2'."""
    val, note = first_number(raw)
    if val is None:
        return None, note
    s = str(raw).lower()
    if re.search(r'\bha\b|hecta', s) and 'm2' not in s and 'm²' not in s:
        return val * 10000, 'converted from hectares'
    return val, note


PRODUCT_KEYWORDS = [
    ('apartment', ['căn hộ', 'can ho', 'apartment', 'apt ', 'apt:', 'apt.']),
    ('officetel', ['officetel']),
    ('shophouse', ['shophouse', 'nhà phố thương mại']),
    ('villa', ['biệt thự', 'villa', 'townhouse']),
    ('retail', ['thương mại', 'retail', 'shopping mall', 'shop ']),
]


# Every real management fee in this sheet is >= ~1,000 VND/m² -- a smaller positive number is
# almost always a mis-extracted duration/count ("3" from "free for the first 3 years"), not a
# rate. A literal 0 is kept (some public/free areas genuinely charge nothing).
MIN_PLAUSIBLE_RATE = 1000


def extract_fee_by_product(raw):
    """Returns (dict of {product: rate}, status). status is None when at least one numeric rate
    was found (even if unlabeled -> 'blended')."""
    if raw is None:
        return {}, 'blank'
    if isinstance(raw, (int, float)):
        if raw != 0 and abs(raw) < MIN_PLAUSIBLE_RATE:
            return {}, 'implausible_value'
        return {'blended': float(raw)}, None
    s = str(raw)
    s_lower = s.lower()

    # A handful of rows quote a flat fee "per apartment/month" (e.g. "650,000vnđ/căn hộ") instead
    # of the VND/m²/month every other row uses. Numerically identical-looking but not comparable --
    # flagged rather than silently returned as if it were a per-m² rate.
    if re.search(r'/\s*(?:căn\s*hộ|căn|can\s*ho|unit)\b', s_lower) and 'm2' not in s_lower and 'm²' not in s_lower:
        return {}, 'per_unit_not_per_sqm'

    result = {}
    for canon, kws in PRODUCT_KEYWORDS:
        for kw in kws:
            for m in re.finditer(re.escape(kw), s_lower):
                window = s[m.end():m.end() + 40]
                num_m = re.search(r'\d[\d.,]*\d|\d', window)
                if num_m:
                    try:
                        val = parse_numeric_token(num_m.group(0))
                        if val >= MIN_PLAUSIBLE_RATE:
                            result.setdefault(canon, val)
                    except ValueError:
                        pass

    if not result:
        for num_m in re.finditer(r'\d[\d.,]*\d|\d', s):
            try:
                val = parse_numeric_token(num_m.group(0))
            except ValueError:
                continue
            if val >= MIN_PLAUSIBLE_RATE:
                result['blended'] = val
                break

    if result:
        return result, None

    low = s_lower.strip()
    if low in NA_TOKENS or low == 'n/a':
        return {}, 'not_applicable'
    if any(t in low for t in TBC_TOKENS):
        return {}, 'not_yet_determined'
    if any(t in low for t in FREE_TOKENS):
        return {}, 'free_or_waived'
    return {}, 'unparsed_text'


def primary_fee(fee_dict):
    if not fee_dict:
        return None
    return fee_dict.get('apartment', fee_dict.get('blended', next(iter(fee_dict.values()))))


def fee_by_product_str(fee_dict):
    if not fee_dict:
        return None
    return '; '.join(f'{k}={v:,.0f}' for k, v in fee_dict.items())


def yn(raw):
    """Normalize a Yes/No-ish cell to 'Yes'/'No'/None, preserving anything else as-is via caller."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in ('yes', 'có', 'y', 'true'):
        return 'Yes'
    if s in ('no', 'không', 'n', 'false', '0'):
        return 'No'
    return clean_text(raw)


def strip_diacritics(s):
    nfkd = unicodedata.normalize('NFKD', s)
    ascii_s = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_s.replace('đ', 'd').replace('Đ', 'D')


# canonical Vietnamese district name -> ascii/lowercase spelling variants seen in this sheet
DISTRICT_CANON = {
    'Bình Thạnh': ['binh thanh'],
    'Phú Nhuận': ['phu nhuan'],
    'Tân Bình': ['tan binh'],
    'Tân Phú': ['tan phu'],
    'Gò Vấp': ['go vap'],
    'Bình Chánh': ['binh chanh'],
    'Bình Tân': ['binh tan'],
    'Nhà Bè': ['nha be'],
    'Củ Chi': ['cu chi'],
    'Hóc Môn': ['hoc mon'],
    'Cần Giờ': ['can gio'],
    'Thủ Đức': ['thu duc'],
}
_DISTRICT_ALIAS_LOOKUP = {alias: canon for canon, aliases in DISTRICT_CANON.items() for alias in aliases}


def standardize_district(name):
    """Best-effort spelling/case normalizer for the districts actually seen in this sheet — not a
    validated gazetteer lookup. Numbered districts ('Quận 7', 'District 7', 'Dist.7') normalize to
    'District N'; named ones normalize via DISTRICT_CANON; anything else is passed through
    title-cased so it's at least consistently formatted, unchanged in meaning."""
    if not name:
        return None
    m = re.search(r'\d+', name)
    if m and len(re.sub(r'[^A-Za-z]', '', name)) <= 2:  # e.g. "7", "Q.7", "D.7" -- just a number + noise
        return f'District {int(m.group())}'
    ascii_name = strip_diacritics(name).lower().strip()
    if ascii_name in _DISTRICT_ALIAS_LOOKUP:
        return _DISTRICT_ALIAS_LOOKUP[ascii_name]
    if ascii_name == 'thu duc city':
        return 'Thủ Đức'
    return name.strip().title()


_QUALIFIER_BEFORE = {
    'ward': r'(?:\bward\b|\bphường\b|\bp\.)\s*([A-Za-zÀ-ỹ0-9][\w\sÀ-ỹ]*?)(?=,|$|\n)',
    'district': r'(?:\bdistrict\b|\bdistrct\b|\bdist\.|\bdist\b|\bquận\b|\bq\.)\s*([A-Za-zÀ-ỹ0-9][\w\sÀ-ỹ]*?)(?=,|$|\n)',
    'commune': r'(?:\bcommune\b|\bxã\b)\s+([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)(?=,|$|\n)',
    'huyen': r'\bhuyện\b\s+([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)(?=,|$|\n)',
    'city': r'(?:\bthành phố\b|\btp\.?)\s+([A-Za-zÀ-ỹ][\w\sÀ-ỹ.]*?)(?=,|$|\n)',
    'province': r'(?:\bprovince\b|\btỉnh\b)\s+([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)(?=,|$|\n)',
}
_QUALIFIER_AFTER = {
    'ward': r'([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)\s+(?:\bward\b|\bphường\b)',
    'district': r'([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)\s+(?:\bdistrict\b|\bdistrct\b|\bdist\.|\bdist\b|\bquận\b)',
    'commune': r'([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)\s+(?:\bcommune\b|\bxã\b)',
    'city': r'([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)\s+\bcity\b',
    'province': r'([A-Za-zÀ-ỹ][\w\sÀ-ỹ]*?)\s+(?:\bprovince\b|\btỉnh\b)',
}
_HCMC_TOKENS = ('hcmc', 'hcm city', 'ho chi minh', 'tp.hcm', 'tp hcm', 'sai gon', 'saigon')
_THU_DUC_TOKENS = ('thu duc',)


def parse_address(raw):
    """Extracts Street / Ward / District / City_Province from a free-text address by matching
    administrative-qualifier keywords wherever they appear, either before or after the place name.
    Returns a dict; ParseStatus is 'ok' if a ward or district was found, else 'low_confidence'
    (no qualifier keyword recognized at all -- the whole string is kept as Street)."""
    if raw is None:
        return dict(Street=None, Ward=None, District_Raw=None, District_Standardized=None,
                    City_Province=None, AddressParseStatus='blank')
    text = str(raw).strip()
    working = text
    found = {}

    for kind in ('ward', 'district', 'commune', 'huyen', 'city', 'province'):
        pat_before = _QUALIFIER_BEFORE.get(kind)
        pat_after = _QUALIFIER_AFTER.get(kind)
        m = re.search(pat_before, working, re.IGNORECASE) if pat_before else None
        if not m and pat_after:
            m = re.search(pat_after, working, re.IGNORECASE)
        if m:
            name = m.group(1).strip(' ,.\n')
            if name:
                found[kind] = name
                working = working[:m.start()] + working[m.end():]

    district = found.get('district') or found.get('huyen')
    city_province = found.get('city') or found.get('province')
    # "Thu Duc City" functions as a district-level unit under HCMC, not the top-level city --
    # if it landed in 'city' and no district was separately found, treat it as the district.
    if not district and city_province and any(t in strip_diacritics(city_province).lower() for t in _THU_DUC_TOKENS):
        district = city_province
        city_province = None
    if not city_province:
        low_full = strip_diacritics(text).lower()
        if any(t in low_full for t in _HCMC_TOKENS):
            city_province = 'Ho Chi Minh City'

    ward = found.get('ward') or found.get('commune')
    district_std = standardize_district(district) if district else None

    street = re.sub(r'\s*,\s*(?=,)', '', working)  # collapse "a, , b" gaps left by removed matches
    street = re.sub(r',\s*,+', ',', street)
    street = re.sub(r'^[\s,.-]+|[\s,.-]+$', '', street)
    street = re.sub(r'\s{2,}', ' ', street).strip(' ,') or None

    status = 'ok' if (ward or district) else 'low_confidence'
    return dict(Street=street, Ward=ward, District_Raw=district, District_Standardized=district_std,
                City_Province=city_province, AddressParseStatus=status)


# ============================================================================================
# Sheet transforms
# ============================================================================================
RESIDENTIAL_COLS = dict(
    no=1, name=2, address=3, gfa=4, nfa=5, towers=6, floors=7, basements=8, basement_sep=9,
    gates=10, compound=11, lobby_cs=12, lobby_no_cs=13, has_commercial=14, elevators=15,
    apt_units=16, officetel_units=17, shophouse_units=18, villa_units=19, retail_units=20,
    fee=21, fixed_fee=22, staff_cost=23, headcount=24, fee_other_areas=25, chiller=26,
    bike_slots=27, car_slots=28, car_fee=29, bike_fee=30, visitor_fee=31,
    free_amenities=32, paid_amenities=33, pool_count=34, pool_staffed=35, gym_count=36, gym_staffed=37,
)

COMMERCIAL_COLS = dict(
    no=1, name=2, address=3, gfa=4, nfa=5, towers=6, floors=7, basements=8, basement_sep=9,
    gates=10, compound=11, lobby_cs=12, lobby_no_cs=13, has_commercial=14, elevators=15,
    fee=16, fixed_fee=17, staff_cost=18, headcount=19,
    bike_slots=20, car_slots=21, car_fee=22, bike_fee=23, visitor_fee=24,
    free_amenities=25, paid_amenities=26,
)


def transform_residential(ws):
    rows = []
    r = 5
    while r <= ws.max_row:
        c = RESIDENTIAL_COLS
        name = clean_text(ws.cell(row=r, column=c['name']).value)
        if not name:
            r += 1
            continue
        gfa, gfa_note = parse_area(ws.cell(row=r, column=c['gfa']).value)
        nfa, nfa_note = parse_area(ws.cell(row=r, column=c['nfa']).value)
        towers, towers_note = first_number(ws.cell(row=r, column=c['towers']).value)
        floors, floors_note = first_number(ws.cell(row=r, column=c['floors']).value)
        basements, basements_note = first_number(ws.cell(row=r, column=c['basements']).value)
        gates, gates_note = first_number(ws.cell(row=r, column=c['gates']).value)
        elevators, elevators_note = first_number(ws.cell(row=r, column=c['elevators']).value)
        apt_u, _ = first_number(ws.cell(row=r, column=c['apt_units']).value)
        oft_u, _ = first_number(ws.cell(row=r, column=c['officetel_units']).value)
        shp_u, _ = first_number(ws.cell(row=r, column=c['shophouse_units']).value)
        vil_u, _ = first_number(ws.cell(row=r, column=c['villa_units']).value)
        ret_u, _ = first_number(ws.cell(row=r, column=c['retail_units']).value)
        total_units = sum(v for v in [apt_u, oft_u, shp_u, vil_u, ret_u] if v) or None

        fee_raw = ws.cell(row=r, column=c['fee']).value
        fee_dict, fee_status = extract_fee_by_product(fee_raw)
        staff_cost, _ = first_number(ws.cell(row=r, column=c['staff_cost']).value)
        headcount, _ = first_number(ws.cell(row=r, column=c['headcount']).value)
        cost_per_head = round(staff_cost / headcount) if staff_cost and headcount else None
        address_raw = ws.cell(row=r, column=c['address']).value
        addr = parse_address(address_raw)

        row = dict(
            PropertyType='Residential', SourceRow=r,
            No=ws.cell(row=r, column=c['no']).value, Name=name,
            Address_Raw=clean_text(address_raw),
            Street=addr['Street'], Ward=addr['Ward'],
            District=addr['District_Standardized'], District_Raw=addr['District_Raw'],
            City_Province=addr['City_Province'], AddressParseStatus=addr['AddressParseStatus'],
            GFA_m2=gfa, GFA_raw=clean_text(ws.cell(row=r, column=c['gfa']).value),
            NFA_m2=nfa, NFA_raw=clean_text(ws.cell(row=r, column=c['nfa']).value),
            TowerCount=towers, TowerCount_raw=clean_text(ws.cell(row=r, column=c['towers']).value),
            FloorCount=floors, FloorCount_raw=clean_text(ws.cell(row=r, column=c['floors']).value),
            BasementCount=basements, BasementCount_raw=clean_text(ws.cell(row=r, column=c['basements']).value),
            BasementSeparate_raw=clean_text(ws.cell(row=r, column=c['basement_sep']).value),
            GateCount=gates, GateCount_raw=clean_text(ws.cell(row=r, column=c['gates']).value),
            CompoundOrOpen=clean_text(ws.cell(row=r, column=c['compound']).value),
            LobbyWithCS=ws.cell(row=r, column=c['lobby_cs']).value,
            LobbyWithoutCS=ws.cell(row=r, column=c['lobby_no_cs']).value,
            HasCommercialArea=yn(ws.cell(row=r, column=c['has_commercial']).value),
            ElevatorCount=elevators, ElevatorCount_raw=clean_text(ws.cell(row=r, column=c['elevators']).value),
            ApartmentUnits=apt_u, OfficetelUnits=oft_u, ShophouseUnits=shp_u, VillaUnits=vil_u, RetailUnits=ret_u,
            TotalUnits=total_units,
            MgmtFeeRate_Primary=primary_fee(fee_dict),
            Fee_Apartment=fee_dict.get('apartment'), Fee_Officetel=fee_dict.get('officetel'),
            Fee_Shophouse=fee_dict.get('shophouse'), Fee_Villa=fee_dict.get('villa'), Fee_Retail=fee_dict.get('retail'),
            Fee_Blended=fee_dict.get('blended'),
            MgmtFeeRate_ByProduct=fee_by_product_str(fee_dict),
            MgmtFeeRate_Status=fee_status, MgmtFeeRate_Raw=clean_text(fee_raw), MgmtFeeVAT='incl_VAT',
            FixedFee=(first_number(ws.cell(row=r, column=c['fixed_fee']).value)[0]),
            StaffCost=staff_cost, Headcount=headcount, CostPerHeadcount=cost_per_head,
            MgmtFeeOtherAreas_raw=clean_text(ws.cell(row=r, column=c['fee_other_areas']).value),
            ChillerIncluded_raw=clean_text(ws.cell(row=r, column=c['chiller']).value),
            BikeParkingSlots=(first_number(ws.cell(row=r, column=c['bike_slots']).value)[0]),
            CarParkingSlots=(first_number(ws.cell(row=r, column=c['car_slots']).value)[0]),
            CarParkingFee_raw=clean_text(ws.cell(row=r, column=c['car_fee']).value),
            BikeParkingFee_raw=clean_text(ws.cell(row=r, column=c['bike_fee']).value),
            VisitorParkingFee_raw=clean_text(ws.cell(row=r, column=c['visitor_fee']).value),
            FreeAmenities=clean_text(ws.cell(row=r, column=c['free_amenities']).value),
            PaidAmenities=clean_text(ws.cell(row=r, column=c['paid_amenities']).value),
            PoolCount=(first_number(ws.cell(row=r, column=c['pool_count']).value)[0]),
            PoolStaffed_raw=clean_text(ws.cell(row=r, column=c['pool_staffed']).value),
            GymCount=(first_number(ws.cell(row=r, column=c['gym_count']).value)[0]),
            GymStaffed_raw=clean_text(ws.cell(row=r, column=c['gym_staffed']).value),
        )
        row['HasCompleteScaleAndFee'] = bool(row['GFA_m2'] and row['MgmtFeeRate_Primary'])
        row['HasCompleteStaffData'] = bool(row['StaffCost'] and row['Headcount'])
        rows.append(row)
        r += 1
    return rows


def transform_commercial(ws):
    rows = []
    r = 5
    while r <= ws.max_row:
        c = COMMERCIAL_COLS
        name = clean_text(ws.cell(row=r, column=c['name']).value)
        if not name:
            r += 1
            continue
        gfa, _ = parse_area(ws.cell(row=r, column=c['gfa']).value)
        nfa, _ = parse_area(ws.cell(row=r, column=c['nfa']).value)
        towers, _ = first_number(ws.cell(row=r, column=c['towers']).value)
        floors, _ = first_number(ws.cell(row=r, column=c['floors']).value)
        basements, _ = first_number(ws.cell(row=r, column=c['basements']).value)
        gates, _ = first_number(ws.cell(row=r, column=c['gates']).value)
        elevators, _ = first_number(ws.cell(row=r, column=c['elevators']).value)

        fee_raw = ws.cell(row=r, column=c['fee']).value
        fee_dict, fee_status = extract_fee_by_product(fee_raw)
        staff_cost, _ = first_number(ws.cell(row=r, column=c['staff_cost']).value)
        headcount, _ = first_number(ws.cell(row=r, column=c['headcount']).value)
        cost_per_head = round(staff_cost / headcount) if staff_cost and headcount else None
        address_raw = ws.cell(row=r, column=c['address']).value
        addr = parse_address(address_raw)

        row = dict(
            PropertyType='Commercial', SourceRow=r,
            No=ws.cell(row=r, column=c['no']).value, Name=name,
            Address_Raw=clean_text(address_raw),
            Street=addr['Street'], Ward=addr['Ward'],
            District=addr['District_Standardized'], District_Raw=addr['District_Raw'],
            City_Province=addr['City_Province'], AddressParseStatus=addr['AddressParseStatus'],
            GFA_m2=gfa, GFA_raw=clean_text(ws.cell(row=r, column=c['gfa']).value),
            NFA_m2=nfa, NFA_raw=clean_text(ws.cell(row=r, column=c['nfa']).value),
            TowerCount=towers, TowerCount_raw=clean_text(ws.cell(row=r, column=c['towers']).value),
            FloorCount=floors, FloorCount_raw=clean_text(ws.cell(row=r, column=c['floors']).value),
            BasementCount=basements, BasementCount_raw=clean_text(ws.cell(row=r, column=c['basements']).value),
            BasementSeparate_raw=clean_text(ws.cell(row=r, column=c['basement_sep']).value),
            GateCount=gates, GateCount_raw=clean_text(ws.cell(row=r, column=c['gates']).value),
            CompoundOrOpen=clean_text(ws.cell(row=r, column=c['compound']).value),
            LobbyWithCS=ws.cell(row=r, column=c['lobby_cs']).value,
            LobbyWithoutCS=ws.cell(row=r, column=c['lobby_no_cs']).value,
            HasCommercialArea=yn(ws.cell(row=r, column=c['has_commercial']).value),
            ElevatorCount=elevators, ElevatorCount_raw=clean_text(ws.cell(row=r, column=c['elevators']).value),
            MgmtFeeRate_Primary=primary_fee(fee_dict),
            Fee_Apartment=fee_dict.get('apartment'), Fee_Officetel=fee_dict.get('officetel'),
            Fee_Shophouse=fee_dict.get('shophouse'), Fee_Villa=fee_dict.get('villa'), Fee_Retail=fee_dict.get('retail'),
            Fee_Blended=fee_dict.get('blended'),
            MgmtFeeRate_ByProduct=fee_by_product_str(fee_dict),
            MgmtFeeRate_Status=fee_status, MgmtFeeRate_Raw=clean_text(fee_raw), MgmtFeeVAT='excl_VAT',
            FixedFee=(first_number(ws.cell(row=r, column=c['fixed_fee']).value)[0]),
            StaffCost=staff_cost, Headcount=headcount, CostPerHeadcount=cost_per_head,
            BikeParkingSlots=(first_number(ws.cell(row=r, column=c['bike_slots']).value)[0]),
            CarParkingSlots=(first_number(ws.cell(row=r, column=c['car_slots']).value)[0]),
            CarParkingFee_raw=clean_text(ws.cell(row=r, column=c['car_fee']).value),
            BikeParkingFee_raw=clean_text(ws.cell(row=r, column=c['bike_fee']).value),
            VisitorParkingFee_raw=clean_text(ws.cell(row=r, column=c['visitor_fee']).value),
            FreeAmenities=clean_text(ws.cell(row=r, column=c['free_amenities']).value),
            PaidAmenities=clean_text(ws.cell(row=r, column=c['paid_amenities']).value),
        )
        row['HasCompleteScaleAndFee'] = bool(row['GFA_m2'] and row['MgmtFeeRate_Primary'])
        row['HasCompleteStaffData'] = bool(row['StaffCost'] and row['Headcount'])
        rows.append(row)
        r += 1
    return rows


# ============================================================================================
# Output
# ============================================================================================
def write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')


def write_review_sheet(wb, title, rows):
    ws = wb.create_sheet(title)
    if not rows:
        ws['A1'] = 'No rows parsed.'
        return
    fieldnames = list(rows[0].keys())
    for c, h in enumerate(fieldnames, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for r, row in enumerate(rows, start=2):
        for c, key in enumerate(fieldnames, start=1):
            cell = ws.cell(row=r, column=c, value=row[key])
            cell.border = BORDER
    ws.freeze_panes = 'A2'
    for c in range(1, len(fieldnames) + 1):
        ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = 16


def write_quality_sheet(wb, res_rows, com_rows):
    ws = wb.create_sheet('Data Quality', 0)
    ws['A1'] = '2026 Master List — Transform Data Quality Summary'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:C1')
    ws['A2'] = 'Generated by transform_master_list.py. Replaces the old 8-project reference data.'
    ws['A2'].font = SUBTITLE_FONT
    ws.merge_cells('A2:C2')

    def stats(rows, label):
        total = len(rows)
        scale_fee = sum(1 for r in rows if r['HasCompleteScaleAndFee'])
        staff = sum(1 for r in rows if r['HasCompleteStaffData'])
        both = sum(1 for r in rows if r['HasCompleteScaleAndFee'] and r['HasCompleteStaffData'])
        fee_unparsed = sum(1 for r in rows if r['MgmtFeeRate_Status'] in ('unparsed_text',))
        addr_ok = sum(1 for r in rows if r['AddressParseStatus'] == 'ok')
        return [label, total, scale_fee, staff, both, fee_unparsed, addr_ok]

    r = 4
    headers = ['Sheet', 'Total Rows', 'Has GFA+Fee', 'Has StaffCost+Headcount', 'Has Both (usable for ratio work)',
               'Fee text unparsed', 'Address parsed OK (ward or district found)']
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    r += 1
    for stat_row in [stats(res_rows, 'Residential'), stats(com_rows, 'Commercial')]:
        for c, v in enumerate(stat_row, start=1):
            ws.cell(row=r, column=c, value=v).border = BORDER
        r += 1
    for col, w in {'A': 14, 'B': 12, 'C': 14, 'D': 22, 'E': 28, 'F': 16, 'G': 30}.items():
        ws.column_dimensions[col].width = w


def main():
    wb_in = openpyxl.load_workbook(SOURCE_PATH, data_only=True)
    res_rows = transform_residential(wb_in['Residential'])
    com_rows = transform_commercial(wb_in['Commercial'])

    os.makedirs(OUT_DIR, exist_ok=True)
    write_csv(CSV_RESIDENTIAL, res_rows)
    write_csv(CSV_COMMERCIAL, com_rows)
    print(f'Residential: {len(res_rows)} rows -> {CSV_RESIDENTIAL}')
    print(f'Commercial: {len(com_rows)} rows -> {CSV_COMMERCIAL}')

    res_both = sum(1 for r in res_rows if r['HasCompleteScaleAndFee'] and r['HasCompleteStaffData'])
    com_both = sum(1 for r in com_rows if r['HasCompleteScaleAndFee'] and r['HasCompleteStaffData'])
    print(f'Residential rows with GFA+Fee+StaffCost+Headcount all present: {res_both}/{len(res_rows)}')
    print(f'Commercial rows with GFA+Fee+StaffCost+Headcount all present: {com_both}/{len(com_rows)}')

    wb_out = openpyxl.Workbook()
    wb_out.remove(wb_out.active)
    write_quality_sheet(wb_out, res_rows, com_rows)
    write_review_sheet(wb_out, 'Residential', res_rows)
    write_review_sheet(wb_out, 'Commercial', com_rows)

    import tempfile, shutil
    local_out = os.path.join(tempfile.gettempdir(), 'Master_List_Review.xlsx')
    wb_out.save(local_out)
    print('Saved locally:', local_out)
    try:
        shutil.copyfile(local_out, REVIEW_XLSX)
        print('Copied into place:', REVIEW_XLSX)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', local_out)


if __name__ == '__main__':
    main()
