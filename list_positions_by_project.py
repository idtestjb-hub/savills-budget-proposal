# -*- coding: utf-8 -*-
import os, glob, re, zipfile, tempfile
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from collections import defaultdict
from common_utils_v2 import norm

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FINAL_OUT = os.path.join(BASE, 'output', 'simple_reports', 'Project_Detail_Lists.xlsx')
LOCAL_TMP = tempfile.gettempdir()
OUT = os.path.join(LOCAL_TMP, 'Project_Detail_Lists.xlsx')  # save locally first, move into place after


def repair_workbook(filepath):
    """Repairs into LOCAL temp, not the OneDrive-synced input folder -- avoids the recurring
    sync-lock collision common_utils_v2.repair_workbook hits when writing its cache file
    alongside the source in a synced folder."""
    try:
        openpyxl.load_workbook(filepath, read_only=True)
        return filepath
    except Exception:
        pass
    repaired_path = os.path.join(LOCAL_TMP, os.path.basename(filepath).replace('.xlsx', '__local_repaired.xlsx'))
    with zipfile.ZipFile(filepath, 'r') as zin:
        wbxml = zin.read('xl/workbook.xml').decode('utf-8')
        cleaned = re.sub(r'<definedNames>.*?</definedNames>', '', wbxml, flags=re.DOTALL)
        with zipfile.ZipFile(repaired_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                data = zin.read(item)
                if item == 'xl/workbook.xml':
                    data = cleaned.encode('utf-8')
                zout.writestr(item, data)
    return repaired_path

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
SECTION_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
SECTION_FONT = Font(bold=True)
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center', wrap_text=True)
MONEY_FMT = '#,##0'

wb_out = openpyxl.Workbook()

# ============ Sheet 1: Staff positions, listed per project ============
staff_src = os.path.join(BASE, 'input', 'staff_cost', '2026 Staff Cost Data (Master Data) update.xlsx')
wb_staff = openpyxl.load_workbook(staff_src, data_only=True)
ws_staff = wb_staff['DS Staff cost (KT - 2025)']
rows = list(ws_staff.iter_rows(min_row=11, max_row=ws_staff.max_row, values_only=True))
data = [r for r in rows if r[2] is not None and r[3] is not None and isinstance(r[4], (int, float))]

by_proj_pos = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'gross_total': 0.0}))
proj_code = {}
for r in data:
    code, _, proj, pos, gross = r[0], r[1], r[2], r[3], r[4]
    proj_code[proj] = code
    d = by_proj_pos[proj][pos]
    d['count'] += 1
    d['gross_total'] += gross or 0

ws1 = wb_out.active
ws1.title = 'Staff Positions by Project'
ws1['A1'] = 'Staff — distinct positions listed per project (89 operating properties)'
ws1['A1'].font = TITLE_FONT
ws1.merge_cells('A1:E1')
ws1['A2'] = 'One row per (project, position). Sorted by project (highest headcount first), then by position headcount within it.'
ws1['A2'].font = SUBTITLE_FONT
ws1.merge_cells('A2:E2')
headers = ['Project Code', 'Project Name', 'Position', 'Headcount', 'Avg Gross Salary (VND)']
r = 4
for c, h in enumerate(headers, start=1):
    cell = ws1.cell(row=r, column=c, value=h)
    cell.fill = HEADER_FILL
    cell.font = HEADER_FONT
    cell.alignment = CENTER
    cell.border = BORDER
r += 1

proj_totals = {p: sum(d['count'] for d in positions.values()) for p, positions in by_proj_pos.items()}
for proj in sorted(by_proj_pos.keys(), key=lambda p: -proj_totals[p]):
    positions = by_proj_pos[proj]
    for pos in sorted(positions.keys(), key=lambda p: -positions[p]['count']):
        d = positions[pos]
        ws1.cell(row=r, column=1, value=proj_code[proj]).border = BORDER
        ws1.cell(row=r, column=2, value=proj).border = BORDER
        ws1.cell(row=r, column=2).alignment = LEFT
        ws1.cell(row=r, column=3, value=pos).border = BORDER
        ws1.cell(row=r, column=3).alignment = LEFT
        ws1.cell(row=r, column=4, value=d['count']).border = BORDER
        c5 = ws1.cell(row=r, column=5, value=round(d['gross_total'] / d['count']))
        c5.number_format = MONEY_FMT
        c5.border = BORDER
        r += 1
for col, w in {'A': 16, 'B': 30, 'C': 40, 'D': 12, 'E': 22}.items():
    ws1.column_dimensions[col].width = w
ws1.freeze_panes = 'A5'
print('Staff Positions by Project rows:', r - 5)

# ============ Sheets 2-4: Security / Cleaning / Landscape position NAMES per budget_planning project ============
CATS = {
    'Security': (['bảo vệ', 'security'], 'Security Positions by Project'),
    'Cleaning': (['vệ sinh', 'cleaning'], 'Cleaning Positions by Project'),
    'Landscape': (['cây xanh', 'landscape'], 'Landscape Positions by Project'),
}

files = sorted(glob.glob(os.path.join(BASE, 'input', 'budget_planning', '*.xlsx')))
files = [f for f in files if '__' not in os.path.basename(f) and not any(
    x in os.path.basename(f) for x in ['MasterData', 'Budget_Workbook', 'Sheet_Index', 'PowerBI', 'SAMPLE', 'GENERATED'])]

FRIENDLY_NAMES = {
    '20232710': '11D Thi Sách',
    '20251006': 'A&K Tower',
    'Lumi Prestige': 'Lumi Prestige & Elite',
    'Lumi Signature': 'Lumi Signature',
    'Parking Building': 'Parking Building',
    'Green Skyline': 'Green Skyline',
    '202604': 'Fiato Airport — F Zone G2',
    '202605': 'Fiato Airport — F Zone MF Pre/Y1/Y2',
}

def friendly_name(filename):
    for key, name in FRIENDLY_NAMES.items():
        if key in filename:
            return name
    return filename

def find_sheets(wb, keywords):
    out = []
    for sn in wb.sheetnames:
        s = norm(sn).lower()
        if any(k in s for k in keywords) and 'quảng cáo' not in s and 'adv' not in s:
            out.append(sn)
    return out

HEADER_NOISE = [norm(s).lower() for s in [
    'đơn giá', 'vận hành', 'số giờ làm việc', 'vị trí / position', 'vị trí/ position',
    'ký hiệu', 'ghi chú', 'diện tích', 'dự án', 'stt', 'rút gọn', 'lưu ý', 'giá trị',
    'bố trí của dự án', 'phần phân bổ', 'nội bộ', 'so sánh', 'combine',
]]


def list_positions(ws):
    names = []
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 100), values_only=True):
        d = row[3] if len(row) > 3 else None
        if isinstance(d, str) and len(d.strip()) > 3 and not d.strip().isupper():
            label = d.strip().split('\n')[0]
            label_norm = norm(label).lower()
            if any(noise in label_norm for noise in HEADER_NOISE):
                continue
            if len(label) <= 2:  # bare section letters like 'A', 'B'
                continue
            names.append(label)
    return names

# Pre-load repaired workbooks once
loaded = {}
for f in files:
    repaired = repair_workbook(f)
    loaded[f] = openpyxl.load_workbook(repaired, data_only=True)
    print('loaded', os.path.basename(f))

for cat, (keywords, sheet_title) in CATS.items():
    ws = wb_out.create_sheet(sheet_title)
    ws['A1'] = f'{cat} — position names listed per project (from each project\'s own file)'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:B1')
    ws['A2'] = 'Approximate extraction (row-scan heuristic) — spot-check before treating as exact.'
    ws['A2'].font = SUBTITLE_FONT
    ws.merge_cells('A2:B2')
    r = 4
    for f in files:
        wb = loaded[f]
        name = friendly_name(os.path.basename(f))
        sheets = find_sheets(wb, keywords)
        all_positions = []
        for sn in sheets:
            all_positions.extend(list_positions(wb[sn]))
        # de-duplicate, keep order
        seen = set()
        deduped = []
        for p in all_positions:
            if p not in seen:
                seen.add(p)
                deduped.append(p)

        ws.cell(row=r, column=1, value=name).font = SECTION_FONT
        ws.cell(row=r, column=1).fill = SECTION_FILL
        ws.cell(row=r, column=2).fill = SECTION_FILL
        ws.cell(row=r, column=1).border = BORDER
        ws.cell(row=r, column=2).border = BORDER
        r += 1
        if not deduped:
            ws.cell(row=r, column=1, value='(no sheet found)').font = Font(italic=True, color='C00000')
            ws.cell(row=r, column=1).border = BORDER
            ws.cell(row=r, column=2).border = BORDER
            r += 1
        for p in deduped:
            ws.cell(row=r, column=2, value=p).border = BORDER
            ws.cell(row=r, column=2).alignment = LEFT
            ws.cell(row=r, column=1).border = BORDER
            r += 1
        r += 1
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 60
    print(f'{cat}: sheet built')

wb_out.save(OUT)
print('Saved locally:', OUT)

import shutil
try:
    os.makedirs(os.path.dirname(FINAL_OUT), exist_ok=True)
    shutil.copyfile(OUT, FINAL_OUT)
    print('Copied into place:', FINAL_OUT)
except PermissionError as e:
    print('Could not copy into place yet (still locked):', e)
    print('Local copy remains valid at:', OUT)
