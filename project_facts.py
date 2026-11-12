"""Project facts shown everywhere (change project-info-everywhere).

One list of the facts that describe a project — scale, address, amenities, parking, product mix, mode — read from the
input form's `Project Info` by label. Used by:
  - review_import.write_form / webapp.fill_input: write the `Fact Sources` sheet (label, value, source) on the form;
  - generate_project_budget: the "QUY MÔ DỰ ÁN / PROJECT SCALE" block on `0. Info` (from row 23);
  - webapp.results: the "Thông tin dự án" section of a run.
A form without `Fact Sources` (hand-filled, or saved before this change) reads every fact as "form nhập liệu".
"""
from input_labels import SheetLabels, normalise

SHEET = 'Fact Sources'
HEADERS = ('Label', 'Value', 'Source')
SRC_FORM = 'form nhập liệu'
SRC_FILE = 'file ngân sách đã duyệt'
SRC_PAGE = 'nhập trên trang web'
SRC_PACKAGE = 'dữ kiện đóng trong gói'
BLANK_TEXT = 'Chưa có số — PM nhập'

CAR_OWNER_LABEL = 'Car Parking Ownership'
CAR_OWNER_DEV, CAR_OWNER_COMMON = 'Riêng CĐT', 'Chung'

# (form label, Vietnamese label, English label, unit, kind) in the order of the 0. Info block and the run page.
# kind: 'text' | 'number' | 'yesno'. A number 0 counts as blank: the Review form writes 0 for "not given".
FACTS = (
    ('City / Province', 'Tỉnh / thành phố', 'City / Province', '', 'text'),
    ('District', 'Quận / huyện', 'District', '', 'text'),
    ('Street Address', 'Địa chỉ', 'Street address', '', 'text'),
    ('Site Area', 'Diện tích khu đất', 'Site area', 'm²', 'number'),
    ('Garden / Landscape Area', 'Diện tích cây xanh', 'Garden / landscape area', 'm²', 'number'),
    ('Circulation / Hardscape Area', 'Diện tích sân, đường nội bộ', 'Circulation / hardscape area', 'm²', 'number'),
    ('Tower Count', 'Số tháp', 'Towers', 'tháp', 'number'),
    ('Floor Count', 'Số tầng (cả dự án)', 'Floors (whole project)', 'tầng', 'number'),
    ('Gate / Entrance Count', 'Số cổng', 'Gates / entrances', 'cổng', 'number'),
    ('Passenger Elevators per Tower', 'Số thang máy mỗi tháp', 'Passenger lifts per tower', 'thang', 'number'),
    ('Number of Basements', 'Số tầng hầm', 'Basements', 'tầng', 'number'),
    ('Has Swimming Pool?', 'Có hồ bơi', 'Swimming pool', '', 'yesno'),
    ('Number of Pools', 'Số hồ bơi', 'Pools', 'hồ', 'number'),
    ('Pool Area', 'Diện tích hồ bơi', 'Pool area', 'm²', 'number'),
    ('Pool Volume', 'Thể tích hồ bơi', 'Pool volume', 'm³', 'number'),
    ('Car Parking Slots', 'Số chỗ ô tô', 'Car parking slots', 'chỗ', 'number'),
    (CAR_OWNER_LABEL, 'Bãi ô tô thuộc sở hữu', 'Car park ownership', '', 'text'),
    ('Moto Parking Slots', 'Số chỗ xe máy', 'Motorbike parking slots', 'chỗ', 'number'),
    ('Project Mode', 'Loại dự án', 'Project mode', '', 'text'),
    ('Prior Budget Year', 'Năm ngân sách đã duyệt', 'Prior budget year', '', 'number'),
)
PRODUCTS = ('Apartment', 'Officetel', 'Office', 'Shopping Mall', 'Retail', 'Shop Apartment', 'Shophouse', 'Villas',
            'Nursery / Nhà trẻ')
MODE_VI = {'New prospect': 'Dự án mới', 'Existing project': 'Dự án đang vận hành'}


def is_blank(value, kind='text'):
    if value is None or (isinstance(value, str) and not value.strip()):
        return True
    if kind == 'number':
        try:
            return float(value) == 0
        except (TypeError, ValueError):
            return False
    return False


def _label_value(L, label):
    return L.value(label) if L.has(label) else None


def write_sources(wb, sources, default=SRC_FORM):
    """Write (replace) the `Fact Sources` sheet from the form's current values. `sources` = {form label: source};
    a fact with a value and no listed source gets `default`; a blank fact gets no source."""
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    pi = wb['Project Info']
    L = SheetLabels(pi)
    ws = wb.create_sheet(SHEET)
    for c, h in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=c, value=h)
    want = {normalise(k): v for k, v in (sources or {}).items()}
    r = 2
    for label, _vi, _en, _unit, kind in FACTS:
        value = _label_value(L, label)
        blank = is_blank(value, kind)
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=None if blank else value)
        ws.cell(row=r, column=3, value='' if blank else want.get(normalise(label), default))
        r += 1
    for product in PRODUCTS:
        if not L.has(product):
            continue
        row = L.row_of(product)
        nfa, units = pi.cell(row=row, column=3).value, pi.cell(row=row, column=4).value
        if is_blank(nfa, 'number') and is_blank(units, 'number'):
            continue
        ws.cell(row=r, column=1, value=product)
        ws.cell(row=r, column=2, value=f'NFA {nfa or 0}; units {units or 0}')
        ws.cell(row=r, column=3, value=want.get(normalise(product), default))
        r += 1
    ws.sheet_state = 'hidden'
    return ws


def read_sources(wb):
    """{normalised form label: source} from `Fact Sources`, or {} when the form has none."""
    if SHEET not in wb.sheetnames:
        return {}
    ws = wb[SHEET]
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and row[0]:
            out[normalise(row[0])] = (row[2] if len(row) > 2 else '') or ''
    return out


def facts_of(wb):
    """[dict(label, vi, en, unit, value, source, blank)] for every fact plus every product with an area, read from the
    form `wb` (an openpyxl workbook of the input form)."""
    pi = wb['Project Info']
    L = SheetLabels(pi)
    sources = read_sources(wb)
    out = []
    for label, vi, en, unit, kind in FACTS:
        value = _label_value(L, label)
        if label == 'Project Mode' and value:
            value = MODE_VI.get(str(value).strip(), value)
        if label == 'Prior Budget Year' and not is_blank(value, 'number'):
            value = str(int(float(value)))          # a year, not a quantity: no thousands separator
            kind = 'text'
        if label == CAR_OWNER_LABEL and is_blank(value) and not is_blank(_label_value(L, 'Car Parking Slots'), 'number'):
            value = CAR_OWNER_COMMON
        if kind == 'yesno' and not is_blank(value):
            value = 'Có' if str(value).strip().lower() in ('yes', 'có', 'co') else 'Không'
        blank = is_blank(value, kind)
        source = '' if blank else (sources.get(normalise(label)) or SRC_FORM)
        out.append(dict(label=label, vi=vi, en=en, unit=unit, value=None if blank else value, source=source,
                        blank=blank))
    for product in PRODUCTS:
        if not L.has(product):
            continue
        row = L.row_of(product)
        nfa, units = pi.cell(row=row, column=3).value, pi.cell(row=row, column=4).value
        if is_blank(nfa, 'number') and is_blank(units, 'number'):
            continue
        source = sources.get(normalise(product)) or SRC_FORM
        out.append(dict(label=f'{product} NFA', vi=f'NFA {product}', en=f'{product} NFA', unit='m²', value=nfa or 0,
                        source=source, blank=False))
        out.append(dict(label=f'{product} units', vi=f'Số sản phẩm {product}', en=f'{product} units', unit='sản phẩm',
                        value=units or 0, source=source, blank=False))
    return out
