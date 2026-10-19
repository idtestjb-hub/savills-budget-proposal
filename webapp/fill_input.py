"""
Read the form's default values from the template input workbook, and write a filled copy.

Every field is addressed by the LABEL in column A of `Project Info` / `Roster Setup`, through the
pipeline's own resolver (input_labels.SheetLabels), never by cell address. A label the template
does not carry (older forms predate `Budget Start Month`, `District`, `City / Province`) is
appended below the sheet's last used row, which is where the pipeline's reader expects optional
fields to appear.

Nothing here writes into Budget_Agent/reports: the template is only read, and the filled copy is
written to the path the caller gives.
"""
import datetime
import os
import shutil
import sys

import openpyxl

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from input_labels import SheetLabels, normalise  # noqa: E402

BUDGET_AGENT = os.path.dirname(SOURCE_DIR)
TEMPLATE_INPUT = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx')

PRODUCTS = ['Apartment', 'Officetel', 'Office', 'Shopping Mall', 'Retail', 'Shop Apartment',
            'Shophouse', 'Villas', 'Nursery / Nhà trẻ']

# form key -> (sheet, label, kind). kind: 'text' | 'number' | 'yesno' | 'month'
SCALARS = {
    'project_name':  ('Project Info', 'Project Name', 'text'),
    'district':      ('Project Info', 'District', 'text'),
    'city':          ('Project Info', 'City / Province', 'text'),
    'site_area':     ('Project Info', 'Site Area', 'number'),
    'garden_area':   ('Project Info', 'Garden / Landscape Area', 'number'),
    'open_space':    ('Project Info', 'Circulation / Hardscape Area', 'number'),
    'floor_count':   ('Project Info', 'Floor Count', 'number'),
    'tower_count':   ('Project Info', 'Tower Count', 'number'),
    'car_slots':     ('Project Info', 'Car Parking Slots', 'number'),
    'moto_slots':    ('Project Info', 'Moto Parking Slots', 'number'),
    'has_pool':      ('Project Info', 'Has Swimming Pool?', 'yesno'),
    'pool_area':     ('Project Info', 'Pool Area', 'number'),
    'pool_volume':   ('Project Info', 'Pool Volume', 'number'),
    'gate_count':    ('Project Info', 'Gate / Entrance Count', 'number'),
    'budget_start':  ('Project Info', 'Budget Start Month', 'month'),
    'roster_month':  ('Roster Setup', 'Month', 'number'),
    'roster_year':   ('Roster Setup', 'Year', 'number'),
}

# Labels written exactly like build_project_input_form.py writes them, when they must be appended.
APPEND_LABELS = {
    'District': 'District — leave blank if unknown',
    'City / Province': 'City / Province — leave blank if unknown',
    'Budget Start Month': 'Budget Start Month',
}


def _month_out(value):
    """A month cell as the form stores it: a date on the 1st, or None when blank."""
    if value is None:
        return None
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime('%m/%Y')
    return str(value)


def read_defaults(template=TEMPLATE_INPUT):
    """{'scalars': {key: value}, 'products': [{name, gfa, nfa, units}]} read from the template."""
    wb = openpyxl.load_workbook(template, data_only=True)
    try:
        sheets = {name: SheetLabels(wb[name]) for name in ('Project Info', 'Roster Setup')}
        scalars = {}
        for key, (sheet, label, kind) in SCALARS.items():
            L = sheets[sheet]
            value = L.value(label) if L.has(label) else None
            if kind == 'month':
                value = _month_out(value) or '01/2027'
            elif kind == 'yesno':
                value = 'Yes' if str(value or '').strip().lower() == 'yes' else 'No'
            scalars[key] = value
        pi = wb['Project Info']
        L = sheets['Project Info']
        products = []
        for name in PRODUCTS:
            if L.has(name):
                row = L.row_of(name)
                products.append(dict(name=name,
                                     gfa=pi.cell(row=row, column=2).value or 0,
                                     nfa=pi.cell(row=row, column=3).value or 0,
                                     units=pi.cell(row=row, column=4).value or 0))
            else:
                products.append(dict(name=name, gfa=0, nfa=0, units=0))
        return dict(scalars=scalars, products=products)
    finally:
        wb.close()


def _to_number(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    number = float(str(value).replace(',', ''))
    return int(number) if number.is_integer() else number


def _to_month(value):
    """'MM/YYYY' or 'YYYY-MM' -> datetime on the 1st. Blank -> None (the pipeline then uses 01/2027)."""
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in ('%m/%Y', '%Y-%m', '%Y-%m-%d', '%m-%Y'):
        try:
            d = datetime.datetime.strptime(text, fmt)
            return datetime.datetime(d.year, d.month, 1)
        except ValueError:
            continue
    raise ValueError(f"Tháng bắt đầu ngân sách '{text}' không đúng dạng MM/YYYY.")


def _ensure_label(ws, L, label):
    """Row of `label`; appended below the last used row when the sheet does not carry it."""
    if L.has(label):
        return L.row_of(label)
    row = (ws.max_row or 1) + 1
    ws.cell(row=row, column=1, value=APPEND_LABELS.get(label, label))
    L._index[normalise(label)] = row
    return row


def write_input(values, dest, template=TEMPLATE_INPUT):
    """Copy `template` to `dest` and write `values` (same shape as read_defaults) into it by label.

    Formulas on the other sheets are kept as formulas: the pipeline recomputes the seeded staffing
    suggestions itself instead of trusting cached results (generate_project_budget._staff_on_duty).
    """
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(template, dest)
    wb = openpyxl.load_workbook(dest)
    try:
        sheets = {name: (wb[name], SheetLabels(wb[name])) for name in ('Project Info', 'Roster Setup')}
        scalars = values.get('scalars', {})
        for key, (sheet, label, kind) in SCALARS.items():
            if key not in scalars:
                continue
            ws, L = sheets[sheet]
            raw = scalars[key]
            if kind == 'number':
                cell_value = _to_number(raw)
            elif kind == 'yesno':
                cell_value = 'Yes' if str(raw).strip().lower() in ('yes', 'có', 'co', 'true', '1') else 'No'
            elif kind == 'month':
                cell_value = _to_month(raw)
            else:
                cell_value = (str(raw).strip() or None) if raw is not None else None
            row = _ensure_label(ws, L, label)
            cell = ws.cell(row=row, column=2, value=cell_value)
            if kind == 'month' and cell_value is not None:
                cell.number_format = 'mm/yyyy'
        ws, L = sheets['Project Info']
        for product in values.get('products', []):
            name = product['name']
            if not L.has(name):
                raise ValueError(f"Mẫu nhập liệu không có dòng sản phẩm '{name}'.")
            row = L.row_of(name)
            ws.cell(row=row, column=2, value=_to_number(product.get('gfa')) or 0)
            ws.cell(row=row, column=3, value=_to_number(product.get('nfa')) or 0)
            ws.cell(row=row, column=4, value=_to_number(product.get('units')) or 0)
        wb.save(dest)
    finally:
        wb.close()
    return dest


if __name__ == '__main__':
    import json
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read_defaults(), ensure_ascii=False, indent=2, default=str))
