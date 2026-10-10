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


def _build(out, name, region, roster, duty, lines, actual, new_position_reasons):
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
    return _build(out, NAME, 'II', ROSTER, DUTY, LINES, ACTUAL, NEW_POSITION_REASONS)


def build_lump(out=OUT_LUMP):
    return _build(out, NAME_LUMP, None, [], {}, LINES_LUMP, [], {})


if __name__ == '__main__':
    print('Wrote', build())
    print('Wrote', build_lump())
