"""Optional intake fields for a project that is already operating (change use-operating-project-actuals).

An operating project can be described on the intake form with what is actually known about it:
- P3: the 'Stable Operation?' switch. 100% occupancy in every month and no developer top-up (RM.0A).
- P1: an actual management-fee rate per product, with its VAT basis, on the Product Mix rows.
- P2: the recorded average monthly revenue from car and motorbike monthly parking.
- P4: the water and electricity collected and paid on residents' behalf (thu hộ / chi hộ), per product.

Every field is optional. A form without a label reads that field as blank, and the run is then the
run before this change. `report_lines()` lists each field as filled, blank or not on the form, so a
misspelt label shows up in the printout instead of passing silently (design D6).

Each PM choice of the change sits in one named place here, so it can be changed later (answers
recorded 2026-10-11 in the change's design.md):
- PM-4, stable occupancy is 100%: fill_curve.STABLE_FILL.
- PM-3, recorded parking and collect-on-behalf amounts need the switch: require_stable().
- PM-5, which products have a collect-on-behalf revenue row: COB_SUFFIX (Villas is not mapped, so an
  amount entered for it stops the run).
- PM-2, the expense line paired with each collect-on-behalf revenue line: the 'paired_with' entry of
  that code in Costing_Method_Catalogue.csv, read by cob_pairing().
- PM-1, entered figures are applied as entered; a VAT basis that differs from the deliverable's is
  disclosed, never converted: DELIVERABLE_VAT_BASIS and vat_mismatch_vi().

The Vietnamese texts below were approved by the user on 2026-10-11 (design.md W1/W2) before they were
written into any workbook.
"""
import csv
import os

from input_labels import normalise

# ---- Labels on 'Project Info' ------------------------------------------------------------------
SECTION_TITLE = 'OPERATING PROJECT — leave blank for a new building'
STABLE_LABEL = 'Stable Operation?'
RATE_HEADER = 'Actual Rate (VND/m²/month)'
VAT_HEADER = 'Rate VAT Basis'
PRODUCT_HEADER = 'Product'                       # the Product Mix block's header row, column A
PARKING_CAR_LABEL = 'Actual Car Parking Revenue (VND/month)'
PARKING_MOTO_LABEL = 'Actual Motorbike Parking Revenue (VND/month)'
COB_SECTION = 'COLLECT ON BEHALF (THU HỘ CHI HỘ)'
COB_HEADER = 'Collect-on-behalf product'        # the block's header row, column A
COB_WATER_HEADER = 'Water (VND/month)'
COB_ELEC_HEADER = 'Electricity (VND/month)'
COB_ROW_PREFIX = 'Thu hộ chi hộ: '               # + the product's Product Mix label

VAT_INCL, VAT_EXCL = 'incl. VAT', 'excl. VAT'
VAT_BASES = (VAT_INCL, VAT_EXCL)
# The basis the deliverable states for its figures ('1. Summary' quotes rates "đã gồm VAT").
DELIVERABLE_VAT_BASIS = VAT_INCL
_VAT_VI = {VAT_INCL: 'đã gồm', VAT_EXCL: 'chưa gồm'}

# PM-5: product -> suffix of its RO3.<x> (water) / RO4.<x> (electricity) revenue rows. Products not
# here (Villas, Shop Apartment, Nursery) have no confirmed row; an amount entered for one stops the run.
COB_SUFFIX = {'Apartment': 'A', 'Officetel': 'T', 'Office': 'O', 'Shopping Mall': 'M',
              'Retail': 'R', 'Shophouse': 'S'}
COB_UTILITIES = ('water', 'electricity')
COB_REVENUE_PREFIX = {'water': 'RO3', 'electricity': 'RO4'}
_UTILITY_VI = {'water': 'nước', 'electricity': 'điện'}
COB_METHOD = 'collect-on-behalf-pair'

_HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE_PATH = os.path.join(os.path.dirname(_HERE), 'data', 'master_list_verified',
                              'Costing_Method_Catalogue.csv')


class OperatingInputError(ValueError):
    """An operating-project field holds a value the run cannot use. The message names the field."""


# ---- Reading ------------------------------------------------------------------------------------
def _amount(value, where, allow_zero=True):
    """None for blank; a float for a number; stops on text or a negative number."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperatingInputError(f"{where} is {value!r}: enter a number in VND, or leave it blank.")
    if value < 0 or (value == 0 and not allow_zero):
        raise OperatingInputError(f"{where} is {value!r}: a negative amount cannot be used.")
    return float(value)


def read_stable(L):
    """(value, status): True/False and 'filled' / 'blank' / 'not on the form'."""
    if not L.has(STABLE_LABEL):
        return False, 'not on the form'
    raw = L.value(STABLE_LABEL)
    if raw is None or not str(raw).strip():
        return False, 'blank'
    text = str(raw).strip().casefold()
    if text == 'yes':
        return True, 'filled'
    if text == 'no':
        return False, 'filled'
    raise OperatingInputError(f"Project Info '{STABLE_LABEL}' is {raw!r}; allowed: Yes, No or blank.")


def read_entered_rates(ws, L, products):
    """({product: dict(rate, vat)}, status, notes). Columns are found by their header text in the
    Product Mix header row, not by letter; a form without them reads every rate as blank."""
    if not L.has(PRODUCT_HEADER):
        return {}, 'not on the form', []
    header_row = L.row_of(PRODUCT_HEADER)
    cols = {normalise(ws.cell(row=header_row, column=c).value): c
            for c in range(1, (ws.max_column or 1) + 1) if ws.cell(row=header_row, column=c).value}
    rate_col, vat_col = cols.get(normalise(RATE_HEADER)), cols.get(normalise(VAT_HEADER))
    if not rate_col:
        return {}, 'not on the form', []
    if not vat_col:
        raise OperatingInputError(f"Project Info has a '{RATE_HEADER}' column but no '{VAT_HEADER}' "
                                  f"column beside it: every entered rate needs its VAT basis.")
    entered, notes = {}, []
    for product in products:
        if not L.has(product):
            continue
        row = L.row_of(product)
        where = f"Project Info '{RATE_HEADER}' for {product} (row {row})"
        rate = _amount(ws.cell(row=row, column=rate_col).value, where)
        if not rate:                      # blank or 0 = not entered
            continue
        raw_vat = ws.cell(row=row, column=vat_col).value
        vat = next((b for b in VAT_BASES if str(raw_vat or '').strip().casefold() == b.casefold()), None)
        if raw_vat is None or not str(raw_vat).strip():
            raise OperatingInputError(f"{product} has an entered rate of {rate:,.0f} VND/m²/month but "
                                      f"its '{VAT_HEADER}' is blank. Pick {VAT_INCL} or {VAT_EXCL}.")
        if vat is None:
            raise OperatingInputError(f"{product}'s '{VAT_HEADER}' is {raw_vat!r}; allowed: "
                                      f"{VAT_INCL} or {VAT_EXCL}.")
        if not (products.get(product) or {}).get('nfa'):
            notes.append(f'{product} has an entered rate ({rate:,.0f} VND/m²/month) but no chargeable '
                         f'area: nothing is priced for it.')
        entered[product] = dict(rate=rate, vat=vat)
    return entered, ('filled' if entered else 'blank'), notes


def read_parking(L):
    """({'car': float|None, 'moto': float|None}, {'car': status, 'moto': status})."""
    values, status = {}, {}
    for key, label in (('car', PARKING_CAR_LABEL), ('moto', PARKING_MOTO_LABEL)):
        if not L.has(label):
            values[key], status[key] = None, 'not on the form'
            continue
        values[key] = _amount(L.value(label), f"Project Info '{label}'")
        status[key] = 'blank' if values[key] is None else 'filled'
    return values, status


def read_collect_on_behalf(ws, L, products):
    """({product: {'water': float|None, 'electricity': float|None}}, status). Only rows with at least
    one non-blank amount are returned."""
    if not L.has(COB_SECTION):
        return {}, 'not on the form'
    if not L.has(COB_HEADER):
        raise OperatingInputError(f"Project Info has the '{COB_SECTION}' block but no "
                                  f"'{COB_HEADER}' header row under it.")
    header_row = L.row_of(COB_HEADER)
    cols = {normalise(ws.cell(row=header_row, column=c).value): c
            for c in range(1, (ws.max_column or 1) + 1) if ws.cell(row=header_row, column=c).value}
    col = {'water': cols.get(normalise(COB_WATER_HEADER)),
           'electricity': cols.get(normalise(COB_ELEC_HEADER))}
    missing = [h for u, h in (('water', COB_WATER_HEADER), ('electricity', COB_ELEC_HEADER)) if not col[u]]
    if missing:
        raise OperatingInputError(f"The '{COB_SECTION}' block has no column headed "
                                  f"{', '.join(repr(m) for m in missing)}.")
    amounts = {}
    for product in products:
        label = COB_ROW_PREFIX + product
        if not L.has(label):
            continue
        row = L.row_of(label)
        entry = {u: _amount(ws.cell(row=row, column=col[u]).value,
                            f"Project Info '{label}' {u} amount (row {row})") for u in COB_UTILITIES}
        if any(v is not None for v in entry.values()):
            amounts[product] = entry
    return amounts, ('filled' if amounts else 'blank')


def read_operating_inputs(ws, L, products):
    """Every operating-project field, validated. `ws`/`L` are 'Project Info' and its label index;
    `products` is read_input()'s product dict (for areas). Raises OperatingInputError naming the field."""
    stable, stable_status = read_stable(L)
    rates, rate_status, rate_notes = read_entered_rates(ws, L, products)
    parking, parking_status = read_parking(L)
    cob, cob_status = read_collect_on_behalf(ws, L, products)
    unmapped = [(p, u) for p, entry in cob.items() for u in COB_UTILITIES
                if entry[u] and p not in COB_SUFFIX]
    if unmapped:
        raise OperatingInputError(
            'No collect-on-behalf line is confirmed for '
            + ', '.join(f'{p} ({u})' for p, u in unmapped)
            + f". Only {', '.join(COB_SUFFIX)} map to the form's RO3/RO4 rows (decision PM-5). Clear the "
              f"amount, or confirm the mapping first.")
    ops = dict(stable=stable, rates=rates, parking=parking, cob=cob, rate_notes=rate_notes,
               status=dict(stable=stable_status, rates=rate_status, car=parking_status['car'],
                           moto=parking_status['moto'], cob=cob_status))
    require_stable(ops)
    return ops


def require_stable(ops):
    """PM-3: recorded parking revenue and collect-on-behalf amounts are used only for a project
    declared at stable operation. Anything entered without the switch stops the run."""
    if ops['stable']:
        return
    entered = [label for key, label in (('car', PARKING_CAR_LABEL), ('moto', PARKING_MOTO_LABEL))
               if ops['parking'][key] is not None]
    entered += [f"{COB_ROW_PREFIX}{p} ({u})" for p, e in ops['cob'].items() for u in COB_UTILITIES
                if e[u] is not None]
    if entered:
        raise OperatingInputError(
            f"{', '.join(repr(e) for e in entered)} filled in, but '{STABLE_LABEL}' is not Yes. Recorded "
            f"parking revenue and collect-on-behalf amounts are used only for a project at stable "
            f"operation (decision PM-3): set '{STABLE_LABEL}' to Yes, or clear those fields.")


def blank_inputs():
    """What read_operating_inputs() returns for a form with none of the fields."""
    return dict(stable=False, rates={}, parking={'car': None, 'moto': None}, cob={}, rate_notes=[],
                status=dict(stable='not on the form', rates='not on the form', car='not on the form',
                            moto='not on the form', cob='not on the form'))


# ---- Collect-on-behalf pairing (PM-2, from the catalogue) -------------------------------------------
def _catalogue_rows(path=None):
    with open(path or CATALOGUE_PATH, encoding='utf-8-sig') as f:
        return list(csv.DictReader(line for line in f if not line.startswith('#')))


def parse_departure(note):
    """The 'key=value | key=value' record a departing entry keeps in its precedence_note."""
    out = {}
    for part in str(note or '').split(' | '):
        if '=' in part:
            k, v = part.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def cob_pairing(path=None):
    """{revenue code: paired expense code} for every catalogue entry using the collect-on-behalf
    method. The pairing is the catalogue's, so changing PM-2 is one edit there."""
    pairs = {}
    for row in _catalogue_rows(path):
        if (row.get('method') or '').strip() == COB_METHOD and row.get('section') == 'revenue':
            paired = parse_departure(row.get('precedence_note')).get('paired_with')
            if paired:
                pairs[row['code'].strip()] = paired
    return pairs


def cob_lines(ops, pairing):
    """The entered pairs as rows to write: [dict(product, utility, revenue_code, expense_code,
    monthly)], amounts > 0 only, in product then utility order. Stops when a mapped revenue code has
    no paired expense line in the catalogue."""
    lines = []
    for product, entry in ops['cob'].items():
        for utility in COB_UTILITIES:
            if not entry[utility]:
                continue
            revenue = f"{COB_REVENUE_PREFIX[utility]}.{COB_SUFFIX[product]}"
            if revenue not in pairing:
                raise OperatingInputError(f"{revenue} ({product}, {utility}) has no paired expense line "
                                          f"in Costing_Method_Catalogue.csv (method {COB_METHOD}).")
            lines.append(dict(product=product, utility=utility, revenue_code=revenue,
                              expense_code=pairing[revenue], monthly=entry[utility]))
    return lines


# ---- Approved Vietnamese texts (design.md W1/W2, 2026-10-11) --------------------------------------
STABLE_NOTE_VI = ("Dự án đang vận hành ổn định: tính lấp đầy 100% cả 12 tháng theo lựa chọn tại Project "
                  "Info, không dùng đường cong lấp đầy của dự án mới.")
RM0A_STABLE_VI = ("= 0 VND/tháng. Dự án đang vận hành, không còn căn chờ bàn giao nên chủ đầu tư không "
                  "đóng phí thay.")
PARKING_STABLE_VI = ("tính lấp đầy bãi xe 100% cả 12 tháng do dự án đang vận hành ổn định (lựa chọn tại "
                     "Project Info).")
ELECTRICITY_STABLE_VI = ("Dự án đang vận hành ổn định nên tính 100% chi phí điện cả 12 tháng (lựa chọn tại "
                         "Project Info), không áp dụng mức tối thiểu 40% của dự án mới.")
SUMMARY_RM_POINT3_STABLE_VI = ("3/ Dự án đang vận hành ổn định, không còn căn chờ bàn giao nên CĐT không "
                               "đóng PQL thay")
SUMMARY_RM_POINT4_STABLE_VI = ("4/ Tính lấp đầy 100% cả năm theo lựa chọn tại Project Info; tỷ lệ nợ xấu "
                               "theo kinh nghiệm QLVH của Savills tại các dự án tương đương")
SUMMARY_PARKING_STABLE_VI = "Tính lấp đầy bãi xe 100% (dự án đang vận hành ổn định)."
FILL_SHEET_REASON_VI = ("Dự án đang vận hành ổn định (lựa chọn tại Project Info): tỷ lệ lấp đầy 100% cả "
                        "12 tháng, không dùng đường cong lấp đầy của dự án mới.")
FALLBACK_ENTERED_APARTMENT_VI = " (đơn giá Apartment do PM nhập)"
COB_COMMON_AREA_VI = "Khoản chi hộ cư dân, không phân bổ cho quỹ khu vực chung."


def water_stable_vi(year):
    # 'lấp đầy cư dân' is a required part of the EEW narrative (check_remark_content); wording amended
    # with the user's approval on 2026-10-11 (session P15, W1a).
    return (f"Chi phí hạng mục này dự ước tại năm {year} với tỷ lệ lấp đầy cư dân 100% (dự án đang vận "
            f"hành ổn định).")


def vat_vi(basis):
    return _VAT_VI[basis]


def vat_mismatch_vi(basis):
    """PM-1 (a): the sentence added when the entered basis differs from the deliverable's; '' otherwise."""
    if basis == DELIVERABLE_VAT_BASIS:
        return ''
    return (f"Lưu ý: đơn giá nhập {_VAT_VI[basis]} VAT, số liệu ngân sách này trình bày "
            f"{_VAT_VI[DELIVERABLE_VAT_BASIS]} VAT; chưa quy đổi.")


def entered_rate_remark_vi(product_vi, rate, basis, nfa, monthly, annual):
    return (f"= Đơn giá {product_vi} thực tế do PM nhập ({rate:,.0f} VND/m²/tháng, {_VAT_VI[basis]} VAT) "
            f"x Diện tích tính phí {product_vi} ({nfa:,.0f} m²) = {monthly:,.0f} VND/tháng "
            f"({annual:,.0f} VND/năm).")


def summary_entered_rate_vi(label, rate, basis):
    return f"{label} là {rate:,.0f} VND/m2/tháng (đơn giá thực tế PM nhập, {_VAT_VI[basis]} VAT)"


_VEHICLE_VI = {'car': 'ô tô', 'moto': 'xe máy'}


def parking_recorded_remark_vi(vehicle, monthly):
    v = _VEHICLE_VI[vehicle]
    if not monthly:
        return f"PM ghi nhận dự án không có doanh thu giữ xe {v} tháng (nhập 0 VND/tháng)."
    return (f"= Doanh thu giữ xe {v} tháng bình quân thực tế do PM nhập ({monthly:,.0f} VND/tháng) x 12 = "
            f"{monthly * 12:,.0f} VND/năm. Số liệu thực tế đã phản ánh số chỗ thực sự được thuê, nên "
            f"không tính theo số chỗ x đơn giá x tỷ lệ lấp đầy.")


def summary_parking_recorded_vi(vehicle, monthly, year):
    return (f"Bãi xe {_VEHICLE_VI[vehicle]}: doanh thu gửi tháng bình quân thực tế {monthly:,.0f} VND/tháng "
            f"do PM nhập - dự ước {monthly * 12:,.0f} VND năm {year}")


def cob_revenue_remark_vi(utility, product_vi, monthly, expense_code):
    return (f"= Tiền {_UTILITY_VI[utility]} thu hộ cư dân {product_vi} do PM nhập ({monthly:,.0f} VND/tháng) "
            f"x 12 = {monthly * 12:,.0f} VND/năm. Khoản thu hộ - chi hộ: cùng số tiền được chi trả thay "
            f"cư dân tại dòng {expense_code}, không làm thay đổi thặng dư.")


def cob_expense_remark_vi(utility, monthly, revenue_codes):
    return (f"= Tiền {_UTILITY_VI[utility]} chi hộ cư dân ({monthly:,.0f} VND/tháng) x 12 = "
            f"{monthly * 12:,.0f} VND/năm, chi trả thay cư dân từ khoản thu hộ tại dòng "
            f"{', '.join(revenue_codes)}. Không làm thay đổi thặng dư.")


# ---- The run's printout (design D6) ------------------------------------------------------------------
def report_lines(ops, rates=None):
    """The 'Operating-project inputs:' block. `rates` is resolve_product_rates()'s result, when the
    caller has it, so the block can name each product's source and the entered-vs-comparable gap."""
    st = ops['status']
    out = ['Operating-project inputs:']
    out.append(f"  {STABLE_LABEL:<46} {('Yes' if ops['stable'] else 'No') if st['stable'] == 'filled' else st['stable']}")
    out.append(f"  {RATE_HEADER + ' / ' + VAT_HEADER:<46} {st['rates']}")
    for product, e in ops['rates'].items():
        line = f"    {product}: {e['rate']:,.0f} VND/m²/month, {e['vat']}"
        info = ((rates or {}).get('products') or {}).get(product)
        if info and info.get('comparable_rate'):
            gap = (e['rate'] - info['comparable_rate']) / info['comparable_rate'] * 100
            line += f" (comparables give {info['comparable_rate']:,.0f}; {gap:+.1f}%)"
        if e['vat'] != DELIVERABLE_VAT_BASIS:
            line += f" — VAT basis differs from the deliverable ({DELIVERABLE_VAT_BASIS}); applied as entered"
        out.append(line)
    for note in ops.get('rate_notes') or []:
        out.append(f'    NOTE: {note}')
    if rates:
        from_comparables = [p for p, info in rates['products'].items() if info['source'] != 'entered']
        if from_comparables:
            out.append('    priced without an entered rate: ' + ', '.join(
                f"{p} ({rates['products'][p]['source']})" for p in from_comparables))
    for key, label in (('car', PARKING_CAR_LABEL), ('moto', PARKING_MOTO_LABEL)):
        v = ops['parking'][key]
        shown = st[key] if v is None else f'{v:,.0f}'
        flag = '   << ZERO: no monthly parking revenue recorded' if v == 0 else ''
        out.append(f"  {label:<46} {shown}{flag}")
    out.append(f"  {COB_SECTION:<46} {st['cob']}")
    for product, e in ops['cob'].items():
        for u in COB_UTILITIES:
            if e[u] is None:
                continue
            note = '   << entered at 0, not written' if e[u] == 0 else ''
            out.append(f"    {product} {u}: {e[u]:,.0f} VND/month{note}")
    return out
