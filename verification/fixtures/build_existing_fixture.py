"""Build Sample_Existing_Input.xlsx: the standard sample, switched to Existing-project mode.

Change carry-forward-staffing, tasks 7.1 and 8.3. Every figure below is INVENTED; no real project,
person or payroll is in it. It starts from Sample_Project_Input.xlsx (left untouched), adds the
Existing-project fields with the same helper a PM uses (add_existing_project_sheets.py), and fills
them so that one run exercises every rule of the change:

- Region II, prior budget 2026 -> budget year 2027 (the template's year);
- a salary below the Region II minimum wage (raised, automatic reason), in the roster and in the
  holiday-duty block;
- a salary above the 2026 insurance ceiling (law effect from the 01/07/2026 insurance-base step);
- a headcount change and a "Khác" salary change, each with its reason;
- Building Executive with more heads than A1 has rows (overflow below the table);
- four in-house positions the roster does not cover, priced from Staffing Demand as new positions
  with a reason each;
- 24 November added to the 2027 calendar (automatic EMH3 reason);
- EMH4 carried forward, an approved EMH2 for the back-cast check, and two actual-headcount rows.

It also builds Sample_Existing_Lump_Input.xlsx (design D15), the lump-sum path: no roster, region left
blank (Region I), approved EMH2 with a PM override and its reason, approved EMH3 with an empty
holiday-duty block and an override, and an approved EMH4 of 0. Also invented.

Change carry-forward-common-utilities (task 6.1, design D9) adds the 'Prior-Year Utilities' sheet to both:
- the first sample is in Ho Chi Minh City ("City / Province" appended to Project Info) and has 12 months
  09/2025-08/2026 of VAT-inclusive amounts, consumption on the first six electricity months, one zero water
  month, and approved amounts for both lines;
- the lump sample leaves the city blank: electricity has 2 months plus an approved amount (the fallback)
  and a consumption override with its reason; water has 12 months of amounts at an invented bill price.

Run from Budget_Agent/source_code:  python verification/fixtures/build_existing_fixture.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, SOURCE)

import openpyxl  # noqa: E402

import add_existing_project_sheets  # noqa: E402
import existing_staffing as es  # noqa: E402
import existing_utilities as eu  # noqa: E402

BASE_FIXTURE = os.path.join(HERE, 'Sample_Project_Input.xlsx')
OUT = os.path.join(HERE, 'Sample_Existing_Input.xlsx')
OUT_LUMP = os.path.join(HERE, 'Sample_Existing_Lump_Input.xlsx')
NAME = 'ZZ Sample Residence (TEST DATA - NOT A REAL PROJECT)'
NAME_LUMP = 'ZZ Sample Lump Residence (TEST DATA - NOT A REAL PROJECT)'
LINES_LUMP = {  # approved, override, reason code, reason note
    'EMH2': (3_600_000_000, 3_780_000_000, 'Thay đổi quy định pháp luật', 'Đề xuất tăng 5% (dữ liệu thử)'),
    'EMH3': (30_000_000, 31_500_000, 'Thay đổi mô hình ca hoặc giờ làm việc', 'Thêm ca trực Tết (dữ liệu thử)'),
    'EMH4': (0, None, None, None),
}

ROSTER = [  # position, shift, heads, gross, new heads, new gross, reason code, reason note
    ('Property Manager', 'HC', 1, 60_000_000, None, None, None, None),
    ('Chief Engineer', 'HC', 1, 30_000_000, None, None, None, None),
    ('Technician', '24H', 4, 9_000_000, 5, None, 'Bàn giao hoặc bổ sung khu vực quản lý',
     'Nhận bàn giao thêm khu B'),
    ('Customer Service', 'HC', 3, 4_500_000, None, None, None, None),
    ('Building Executive', 'HC', 7, 12_000_000, None, None, None, None),
    ('Accountant', 'HC', 1, 15_000_000, None, 16_000_000, es.REASON_OTHER, 'Lên bậc lương nội bộ'),
]
DUTY = {'TN': (1, 1, 2, 9_000_000), 'CS': (0, 0, 1, 4_500_000)}
LINES = {'EMH2': (4_330_000_000, None), 'EMH3': (None, None), 'EMH4': (12_000_000, None)}
ACTUAL = [('Technician', 5, 'C&B payroll'), ('Customer Service', 2, 'PM timesheet')]

def _months(start_y, start_m, n):
    out, y, m = [], start_y, start_m
    for _ in range(n):
        out.append(f'{m:02d}/{y}')
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


_E_KWH = [30_000, 29_100, 28_500, 29_400, 30_600, 31_500, 32_400, 33_000, 31_800, 30_900, 30_300, 29_700]
_W_M3 = [1_500, 1_450, 1_400, 1_380, 1_420, 0, 1_520, 1_600, 1_650, 1_580, 1_550, 1_500]
# line, month, amount (VND), includes VAT, consumption — 2,226 VND/kWh + 8% and 19,785.6 VND/m3 all-in (2026).
UTILITY_ACTUALS = (
    [('EEE.C', m, round(k * 2_226 * 1.08), 'Yes', k if i < 6 else None)
     for i, (m, k) in enumerate(zip(_months(2025, 9, 12), _E_KWH))]
    + [('EEW.C', m, round(q * 19_785.6), 'Yes', None) for m, q in zip(_months(2025, 9, 12), _W_M3)])
UTILITY_LINES = {  # category, bill price, source, approved, approved incl. VAT, override, reason code, note
    'EEE.C': (None, None, None, 850_000_000, 'Yes'),
    'EEW.C': (None, None, None, 320_000_000, 'Yes'),
}
UTILITY_ACTUALS_LUMP = (
    [('EEE.C', m, round(k * 2_226 * 1.08), 'Yes', None) for m, k in zip(_months(2026, 7, 2), (24_000, 24_500))]
    + [('EEW.C', m, round(900 * 12_500 * 1.05), 'Yes', None) for m in _months(2025, 9, 12)])
UTILITY_LINES_LUMP = {
    'EEE.C': (None, None, None, 600_000_000, 'Yes', 26_000, 'Thay đổi số cư dân vào ở',
              'Thêm cư dân dọn vào (dữ liệu thử)'),
    'EEW.C': ('Theo giá trên hóa đơn', 12_500, 'Hóa đơn nước tháng 08/2026 (dữ liệu thử)', None, None),
}
NEW_POSITION_REASONS = {
    'Reception': 'Theo yêu cầu của cư dân hoặc chủ sở hữu',
    'Shift Leader': 'Thay đổi mô hình ca hoặc giờ làm việc',
    'Pool Attendant': 'Mở dịch vụ hoặc tiện ích mới',
    'Amenities Attendant': 'Mở dịch vụ hoặc tiện ích mới',
}


def _section_first_data_row(ws, title):
    for r in range(1, ws.max_row + 1):
        if es.normalise(ws.cell(row=r, column=1).value) == es.normalise(title):
            return r + 2
    raise LookupError(title)


def _build(out, name, region, roster, duty, lines, actual, new_position_reasons, city=None,
           utility_actuals=(), utility_lines=None):
    tmp = tempfile.mkdtemp(prefix='existing_fixture_')
    try:
        src = os.path.join(tmp, 'Sample_Project_Input.xlsx')
        shutil.copyfile(BASE_FIXTURE, src)
        copy = add_existing_project_sheets.add_to_copy(src)
        wb = openpyxl.load_workbook(copy)
        pi = wb['Project Info']
        labels = {es.normalise(pi.cell(row=r, column=1).value): r for r in range(1, pi.max_row + 1)
                  if pi.cell(row=r, column=1).value}
        pi.cell(row=labels[es.normalise('Project Name')], column=2, value=name)
        pi.cell(row=labels[es.normalise(es.MODE_LABEL)], column=2, value=es.MODE_EXISTING)
        pi.cell(row=labels[es.normalise(es.REGION_LABEL)], column=2, value=region)
        pi.cell(row=labels[es.normalise(es.PRIOR_YEAR_LABEL)], column=2, value=2026)
        if city:
            last = max(labels.values())
            pi.cell(row=last + 2, column=1, value='City / Province — leave blank if unknown')
            pi.cell(row=last + 2, column=2, value=city)

        uw = wb[eu.SHEET]
        r = _section_first_data_row(uw, eu.SEC_ACTUALS)
        for i, row in enumerate(utility_actuals):
            for c, v in enumerate(row, 1):
                uw.cell(row=r + i, column=c, value=v)
        r = _section_first_data_row(uw, eu.SEC_LINES)
        for i in range(len(eu.LINES)):
            line = uw.cell(row=r + i, column=1).value
            for c, v in enumerate((utility_lines or {}).get(line, ()), 2):
                uw.cell(row=r + i, column=c, value=v)

        ws = wb[es.ROSTER_SHEET]
        r = _section_first_data_row(ws, es.SEC_ROSTER)
        for i, (pos, shift, heads, gross, new_heads, new_gross, code, note) in enumerate(roster):
            for c, v in enumerate((pos, shift, heads, gross, 2026, new_heads, new_gross, code, note), 1):
                ws.cell(row=r + i, column=c, value=v)
        r = _section_first_data_row(ws, es.SEC_DUTY)
        for i in range(len(es.DUTY_CODES)):
            code = ws.cell(row=r + i, column=1).value
            if code in duty:
                for c, v in enumerate(duty[code], 2):
                    ws.cell(row=r + i, column=c, value=v)
        r = _section_first_data_row(ws, es.SEC_LINES)
        for i in range(len(es.STAFF_LINES)):
            line = ws.cell(row=r + i, column=1).value
            for c, v in enumerate(lines[line], 2):     # approved, override[, reason code, reason note]
                ws.cell(row=r + i, column=c, value=v)
        r = _section_first_data_row(ws, es.SEC_ACTUAL)
        for i, row in enumerate(actual):
            for c, v in enumerate(row, 1):
                ws.cell(row=r + i, column=c, value=v)

        sd = wb['Staffing Demand']
        headers = {es.normalise(sd.cell(row=4, column=c).value): c for c in range(1, sd.max_column + 1)}
        code_col = headers['reason code']
        for row in range(5, sd.max_row + 1):
            pos = str(sd.cell(row=row, column=1).value or '')
            for prefix, reason in new_position_reasons.items():
                if pos.startswith(prefix):
                    sd.cell(row=row, column=code_col, value=reason)
        wb.save(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def build(out=OUT):
    return _build(out, NAME, 'II', ROSTER, DUTY, LINES, ACTUAL, NEW_POSITION_REASONS, city='TP. Hồ Chí Minh',
                  utility_actuals=UTILITY_ACTUALS, utility_lines=UTILITY_LINES)


def build_lump(out=OUT_LUMP):
    return _build(out, NAME_LUMP, None, [], {}, LINES_LUMP, [], {},
                  utility_actuals=UTILITY_ACTUALS_LUMP, utility_lines=UTILITY_LINES_LUMP)


if __name__ == '__main__':
    print('Wrote', build())
    print('Wrote', build_lump())
