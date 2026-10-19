"""Parent rows and sub-rows for the deliverable's '4. Điều chỉnh' sheet (docs/32, section 2).

`collect(wb, project, demand)` reads back every budget line the pipeline wrote on the two fund sheets while the
figures are still numbers (build_budget() calls it right after the staff sheets are filled, before anything turns a
cell into a formula) and returns one parent row per line, each with the sub-rows a PM can adjust:

    {'code', 'sheet', 'row', 'name_vi', 'freq', 'months', 'annual', 'subs': [
        {'desc_vi', 'unit_vi', 'qty', 'unit_price', 'amount', 'qty_editable'}, ...]}

Real sub-rows (qty_editable True) come from the figures the pricing recorded in _HELPER_FIGURES and from
'A1. Staff cost' itself:
  ESS1 / ESS4 / ESS16  one row per Staffing Demand post (people, relief for the weekly day off included);
  EMH2                 one row per A1 title, qty = heads, unit price = one person's A1 cost (column AC) for the year;
  ESS9                 apartments and shophouses, qty = units;
  RA1.A / RA2          one row per advertising device type;
  RP1 / RP2            qty = bays (an entered actual revenue stays one lump row);
  RM.*                 qty = the product's NFA in m².
Every other line is one lump sub-row (qty 1, not editable) carrying the line's own figure.

Invariants (checked by tests/test_adjustment_detail.py and the verification's own check):
  - sum(sub amounts) == annual to the VND; a 'Chênh lệch làm tròn' row (qty 1, not editable) carries any residual;
  - qty x unit_price == amount to the VND (unit_price is the effective annual price per unit, amount / qty);
  - every non-zero line written on a fund sheet is present; zero lines are left out;
  - order = row order on the fund sheets, '2. Budget-Management Fund' before '2.2 Common area Fund'.

Lines whose cells are formulas (EMH3 from A1.1, EMH4 from A5, the EM#/ES#/EE# contingency lines) are left out:
they are derived from other cells and keep updating on their own. EMH2 is the one formula line that is included,
priced here from A1 the way the sheet computes it.
"""
import re

import generate_project_budget as g
from existing_staffing import excel_round

FUND_SHEET = '2. Budget-Management Fund'
COMMON_SHEET = '2.2 Common area Fund'
_FREQ_COL, _UNIT_PRICE_COL, _FIRST_MONTH_COL = 3, 6, 8
_CODE_COL, _NAME_COL = 25, 26

ROUNDING_DESC_VI = 'Chênh lệch làm tròn'
LUMP_UNIT_VI = 'khoản'

_CONTRACT_LINES = {'ESS1': 'Security', 'ESS4': 'Cleaning', 'ESS16': 'Landscape'}
_PARKING_LINES = {'RP1': ('moto', 'Chỗ xe máy'), 'RP2': ('car', 'Chỗ ô tô')}
_PRODUCT_OF_CODE = {code: product for product, code in g.PRODUCT_REVENUE_EXPECTED_CODE.items()}
_SHIFT_SUFFIX = re.compile(r'\s*\((?:Morning|Afternoon|Evening|Night|Day)\)\s*$')


# ------------------------------------------------------------------------------------------------
# Reading the fund sheets
# ------------------------------------------------------------------------------------------------
def _number(value):
    """A cell's figure: 0 for blank, None for a formula string or any other text."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if value in (None, ''):
        return 0.0
    return None


def _name_vi(raw, code):
    """The Vietnamese line name from the two-language name cell, as _collect_written reads it."""
    parts = [p.strip(' \t()') for p in str(raw or code).replace('\r', '').split('\n') if p.strip(' \t()')]
    if not parts:
        return code
    return parts[-1] if len(parts) > 1 else parts[0]


def _row_figures(ws, r):
    """(freq, months) for a line the pipeline wrote: ('Monthly', 12 x F) or ('Schedule', H:S); months is None when
    the figures are formulas; the whole result is None when the row carries no Monthly / Schedule frequency."""
    freq = ws.cell(row=r, column=_FREQ_COL).value
    if not isinstance(freq, str):
        return None
    kind = freq.strip().lower()
    if kind == 'monthly':
        f = _number(ws.cell(row=r, column=_UNIT_PRICE_COL).value)
        return 'Monthly', (None if f is None else [f] * 12)
    if kind == 'schedule':
        cells = [_number(ws.cell(row=r, column=c).value) for c in range(_FIRST_MONTH_COL, _FIRST_MONTH_COL + 12)]
        return 'Schedule', (None if any(v is None for v in cells) else cells)
    return None


def _parents(wb):
    """Every written line of both fund sheets, in sheet order: (sheet, row, code, name_vi, freq, months). `months`
    is None for a formula line (only EMH2 is kept among those)."""
    out = []
    for sheet in (FUND_SHEET, COMMON_SHEET):
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for r in range(1, (ws.max_row or 1) + 1):
            figures = _row_figures(ws, r)
            if figures is None:
                continue
            freq, months = figures
            code = ws.cell(row=r, column=_CODE_COL).value
            code = code.strip() if isinstance(code, str) else ('' if code is None else str(code))
            if months is None:
                if code != 'EMH2' or sheet != FUND_SHEET:   # '2.2' carries EMH2 as a pass-through formula
                    continue
            elif abs(sum(m or 0.0 for m in months)) < 1:
                continue
            out.append((sheet, r, code, _name_vi(ws.cell(row=r, column=_NAME_COL).value, code), freq, months))
    return out


# ------------------------------------------------------------------------------------------------
# Sub-rows
# ------------------------------------------------------------------------------------------------
def _sub(desc_vi, unit_vi, qty, amount, editable):
    qty = float(qty)
    return {'desc_vi': desc_vi, 'unit_vi': unit_vi, 'qty': qty, 'unit_price': amount / qty if qty else 0.0,
            'amount': float(amount), 'qty_editable': bool(editable)}


def _lump(name_vi, annual):
    return [_sub(name_vi, LUMP_UNIT_VI, 1, annual, False)]


def _finish(subs, annual):
    """Append the rounding row when the sub-rows do not add up to the line (to the VND)."""
    residual = annual - sum(s['amount'] for s in subs)
    if abs(residual) >= 1e-6:
        subs.append(_sub(ROUNDING_DESC_VI, LUMP_UNIT_VI, 1, residual, False))
    return subs


def _split(annual, parts):
    """Sub-rows sharing `annual` by weight: parts = [(desc_vi, unit_vi, qty, weight)], each amount rounded to the
    VND; None when nothing carries weight (the caller then falls back to a lump row)."""
    parts = [p for p in parts if p[3] and p[2]]
    total = sum(p[3] for p in parts)
    if not parts or not total:
        return None
    subs = [_sub(desc, unit, qty, excel_round(annual * weight / total), True) for desc, unit, qty, weight in parts]
    return _finish(subs, annual)


def _post_desc_vi(d):
    role = _SHIFT_SUFFIX.sub('', str(d.get('Position') or '')).strip()
    role_vi = g._SECURITY_CLEANING_ROLE_VI.get(role, role)
    shift = str(d.get('ShiftCode') or '').strip().upper()
    shift_vi = g._SHIFT_VI.get(shift)
    return f"{role_vi} ({shift_vi})" if shift_vi else role_vi


def _contract_subs(code, annual):
    fig = (g._HELPER_FIGURES.get('contract') or {}).get(_CONTRACT_LINES[code])
    if not fig:
        return None
    return _split(annual, [(_post_desc_vi(d), 'người', n, n) for d, n in fig.get('posts') or ()])


def _waste_subs(annual):
    waste = g._HELPER_FIGURES.get('waste')
    if not waste:
        return None
    apt, shop = waste.get('apt_units') or 0, waste.get('shop_units') or 0
    return _split(annual, [('Căn hộ', 'căn', apt, apt * g.WASTE_APARTMENT_KG_PER_UNIT_DAY),
                           ('Shophouse', 'căn', shop, shop * g.WASTE_SHOPHOUSE_KG_PER_UNIT_DAY)])


def _ads_subs(code, annual):
    ads = g._HELPER_FIGURES.get('ads') or []
    lift = code == 'RA2'
    items = [a for a in ads if ('inside elevator' in str(a.get('item', '')).lower()) == lift]
    return _split(annual, [(a['item_vi'], 'thiết bị', a['qty'], a['rate'] * a['qty']) for a in items])


def _parking_subs(code, annual):
    key, desc_vi = _PARKING_LINES[code]
    p = (g._HELPER_FIGURES.get('parking') or {}).get(key) or {}
    if p.get('recorded') is not None or not p.get('slots'):
        return None
    return _finish([_sub(desc_vi, 'chỗ', p['slots'], annual, True)], annual)


def _product_subs(code, annual, project):
    product = _PRODUCT_OF_CODE.get(code)
    if not product:
        return None
    nfa = ((project.get('products') or {}).get(product) or {}).get('nfa')
    if not nfa:
        return None
    label = g._PRODUCT_VI_LABEL.get(product, product)
    return _finish([_sub(f"Diện tích {label} (NFA)", 'm²', nfa, annual, True)], annual)


# ------------------------------------------------------------------------------------------------
# EMH2 from 'A1. Staff cost', the way the sheet computes it
# ------------------------------------------------------------------------------------------------
def _a1_value(ws, coord, env):
    """A reference cell of A1 as a number: its value, or its formula evaluated when it only combines numbers and the
    base cells I4 / I5 (the template's '=$I$4*20', '=4960000*(1+7.2%)*0+5310000')."""
    v = ws[coord].value
    n = _number(v)
    if n is not None:
        return n
    expr = str(v).strip()[1:]
    for ref, val in env.items():
        expr = expr.replace(ref, repr(val))
    expr = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1/100)', expr)
    if not re.fullmatch(r'[0-9.+\-*/() ]+', expr):
        raise ValueError(f"'{g.STAFF_COST_SHEET}'!{coord} is {v!r}; the adjustment sheet cannot price EMH2 from it.")
    return float(eval(expr, {'__builtins__': {}}, {}))


def _a1_params(ws):
    """The reference cells A1's rows read: insurance caps and rates, the 13th month, training, checkup, markup."""
    env = {}
    for base in ('I4', 'I5'):
        env[f'${base[0]}${base[1:]}'] = _a1_value(ws, base, {})
    p = {k: _a1_value(ws, k, env) for k in ('N8', 'S8', 'T7', 'T8', 'U7', 'U8', 'V7', 'V8', 'W7', 'W8', 'AB1')}
    p['AC92'] = _a1_value(ws, 'AC92', env)
    p['AC95'] = _a1_value(ws, 'AC95', env) or 12.0
    return p


def _a1_row(ws, r, p):
    """(code, proposed gross I, monthly cost AC) of one A1 row, following the row's own formula chain (column AC =
    AA + AB; the employee-side columns L, M, P, Q do not feed it). A numeric X (Existing mode zeroes the empty PM
    row's accident insurance) or Y is taken as written. Returns None for a row that carries neither a gross nor a
    numeric AC."""
    code = str(ws.cell(row=r, column=4).value or '').strip()
    gross = _number(ws.cell(row=r, column=7).value)
    ac_written = _number(ws.cell(row=r, column=29).value)
    if gross is None:
        return None
    if ac_written is not None and ac_written:
        return code, 0.0, ac_written             # a carried / adjustment row written as a value (Existing mode)
    if not gross:
        return (code, 0.0, _a1_cost(ws, r, p, code, 0.0)) if code == 'PM' else None
    return code, excel_round(gross), _a1_cost(ws, r, p, code, gross)


def _a1_cost(ws, r, p, code, gross):
    """Column AC for one row: the template's chain on columns G and H."""
    h = _number(ws.cell(row=r, column=8).value) or 0.0
    i = excel_round(gross * h + gross)
    j = i
    n = i / p['N8']
    r_ = 1_000_000 if (code == 'PM' and i > 0) else (300_000 if i > 0 else 0)
    s = i * p['S8']
    t = p['T7'] * p['T8'] if i > p['T7'] else i * p['T8']
    u = p['U7'] * p['U8'] if i > p['U7'] else i * p['U8']
    v = p['V7'] * p['V8'] if i > p['V7'] else i * p['V8']
    w = p['W7'] / p['W8'] if i > 0 else 0
    x = _number(ws.cell(row=r, column=24).value)
    if x is None:
        if code == 'PM':
            x = (j * 30 * 0.00099 + j * 3 * 0.0044 + 446985 + 2456000) * 0.58 / 12
        elif j == 0:
            x = 0
        else:
            base = (j * 30 * 0.00099 + j * 3 * 0.0044 + 446985) * 0.40 / 12
            x = 30000 if base < 30000 else base
    y = _number(ws.cell(row=r, column=25).value) or 0.0
    z = 300_000 if i > 0 else 0
    aa = excel_round(i + n + r_ + s + t + u + v + w + x + y + z)
    ab = excel_round(aa * p['AB1'])
    return aa + ab


def _title_of(label):
    """The title an A1 row carries, without its running number or ' (thêm n)' suffix."""
    text = re.sub(r'\s*\(thêm \d+\)\s*$', '', str(label or '')).strip()
    return re.split(r'\s*\d', text)[0].strip() or text


def staff_subs(wb, annual=None):
    """EMH2's sub-rows from 'A1. Staff cost': one per title (qty = heads, unit price = one person's column AC x the
    contract months), the carried / adjustment rows below the table as lump rows, and the rounding row for what the
    sheet counts without a head (the empty PM row's accident insurance, AC92). Returns (subs, annual): `annual` is
    the line the sheet computes, (AC89 + AC92) x AC95 + 12 x the rows below the table, unless the caller gives it."""
    ws = wb[g.STAFF_COST_SHEET]
    p = _a1_params(ws)
    titles, lumps = {}, []
    table_total = 0.0
    headless = 0.0
    for r in range(15, 89):
        row = _a1_row(ws, r, p)
        if row is None:
            continue
        code, i, ac = row
        table_total += ac
        if i > 0:
            key = (_title_of(ws.cell(row=r, column=2).value), ac * p['AC95'])
            titles[key] = titles.get(key, 0) + 1
        else:
            headless += ac * p['AC95']
    below_total = 0.0
    for r in range(g._A1_UNPLACED_FIRST_ROW, (ws.max_row or g._A1_UNPLACED_FIRST_ROW) + 1):
        row = _a1_row(ws, r, p)
        if row is None:
            continue
        code, i, ac = row
        below_total += ac
        label = ws.cell(row=r, column=2).value
        if i > 0:
            key = (_title_of(label), ac * 12)
            titles[key] = titles.get(key, 0) + 1
        else:
            lumps.append((str(label or code or 'EMH2').strip(), ac * 12))
    computed = (excel_round(table_total) + p['AC92']) * p['AC95'] + below_total * 12
    subs = [_sub(title, 'người', heads, heads * price, True) for (title, price), heads in titles.items()]
    subs += [_sub(label, LUMP_UNIT_VI, 1, amount, False) for label, amount in lumps]
    total = computed if annual is None else annual
    return _finish(subs, total), total


def _subs_for(code, name_vi, annual, project):
    if code in _CONTRACT_LINES:
        subs = _contract_subs(code, annual)
    elif code == 'ESS9':
        subs = _waste_subs(annual)
    elif code in ('RA1.A', 'RA2'):
        subs = _ads_subs(code, annual)
    elif code in _PARKING_LINES:
        subs = _parking_subs(code, annual)
    elif code in _PRODUCT_OF_CODE:
        subs = _product_subs(code, annual, project)
    else:
        subs = None
    return subs if subs else _lump(name_vi, annual)


def collect(wb, project, demand):
    """One parent row per written, non-zero fund line, in sheet order, each with its sub-rows (module docstring)."""
    items = []
    for sheet, row, code, name_vi, freq, months in _parents(wb):
        if months is None:                      # EMH2: a formula into A1, priced here from A1 itself
            subs, annual = staff_subs(wb)
            months = [annual / 12] * 12
            freq = 'Monthly'
        else:
            annual = float(sum(months))
            subs = _subs_for(code, name_vi, annual, project)
        items.append({'code': code, 'sheet': sheet, 'row': row, 'name_vi': name_vi, 'freq': freq,
                      'months': [float(m) for m in months], 'annual': float(annual), 'subs': subs})
    return items


def check_invariants(items, tolerance=1.0):
    """The interface's invariants on a collected list, as a list of problems (empty when all hold). Shared with the
    tests and the verification."""
    problems = []
    seen = set()
    for it in items:
        code = it['code']
        if code in seen:
            problems.append(f"{code}: listed twice")
        seen.add(code)
        if abs(sum(it['months']) - it['annual']) > tolerance:
            problems.append(f"{code}: annual {it['annual']:,.0f} != sum of months {sum(it['months']):,.0f}")
        if not it['subs']:
            problems.append(f"{code}: no sub-rows")
        total = sum(s['amount'] for s in it['subs'])
        if abs(total - it['annual']) > tolerance:
            problems.append(f"{code}: sub-rows {total:,.0f} != annual {it['annual']:,.0f}")
        for s in it['subs']:
            if abs(s['qty'] * s['unit_price'] - s['amount']) > tolerance:
                problems.append(f"{code} / {s['desc_vi']}: qty x unit price != amount")
            if s['desc_vi'] == ROUNDING_DESC_VI and s['qty_editable']:
                problems.append(f"{code}: the rounding row must not be quantity-editable")
    return problems
