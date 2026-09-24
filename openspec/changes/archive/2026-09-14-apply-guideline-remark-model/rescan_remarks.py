# Re-scan: for every sheet where the AI Guideline workbook carries an "AI GUIDELINE" column, pull
# (a) the guideline instruction and (b) the WORKED SAMPLE workbook's actual Remark/Ghi chu text for
# the same code/row, side by side. Read-only; writes one report file.
import sys, os, warnings
warnings.simplefilter('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl
from openpyxl.utils import get_column_letter as L

SOURCE_CODE = r"C:\Users\CDangQuang\Savills Asia Pacific\VN, IT Collab - Data\PM\Project_Clone2_NewData\Budget_Agent\source_code"
sys.path.insert(0, SOURCE_CODE)
from common_utils_v2 import find_sheet_exact  # NFC/NFD-safe sheet lookup — some sheet names here are
                                                # a mixed Unicode form that fails a literal dict lookup

DOCS = r"C:\Users\CDangQuang\Savills Asia Pacific\VN, IT Collab - Data\PM\Project_Clone2_NewData\docs"
GUIDE = os.path.join(DOCS, "AI Guideline - 2027 Resi Budget Form (IT team) __repaired.xlsx")
SAMPLE = os.path.join(DOCS, "Ngân sách mẫu  dự án mới sẽ Operation năm 1 + năm 2 có giai đoạn tiền khai trương__repaired.xlsx")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remark_rescan_report.txt")

gwb = openpyxl.load_workbook(GUIDE, data_only=False)
swb = openpyxl.load_workbook(SAMPLE, data_only=False)


def sheet(wb, name):
    resolved = find_sheet_exact(wb, name)
    if resolved is None:
        raise KeyError(f"no sheet matching {name!r} in {[s for s in wb.sheetnames][:3]}...")
    return wb[resolved]

# (guide sheet, guide code_col, guide item_col, guide AI-GUIDELINE col, guide header_row,
#  sample sheet, sample code_col-or-None, sample item_col, sample remark_col, sample header_row)
# Column letters verified 2026-09-11 against both workbooks' actual header rows (not guessed).
PAIRS = [
    dict(gname='0. Info', gcode=None, gitem='B', gguide='L', ghrow=6,
         sname='Info', scode=None, sitem='B', sremark='G', shrow=10),
    dict(gname='1. Summary', gcode='B', gitem='F', gguide='L', ghrow=8,
         sname='1. Summary năm 1 + năm 2', scode='B', sitem='F', sremark='S', shrow=8),
    dict(gname='2. Budget-Management Fund', gcode='Y', gitem='Z', gguide='W', ghrow=9,
         sname='2a.Budget-MF 12 months (year 1)', scode='Z', sitem='AA', sremark='AS', shrow=9),
    dict(gname='A2. Bảo vệ - Security', gcode=None, gitem='D', gguide='V', ghrow=5,
         sname='4. Bảo vệ - Security', scode=None, sitem='D', sremark='I', shrow=5),
    dict(gname='A3. Vệ sinh - Cleaning', gcode=None, gitem='D', gguide='Y', ghrow=5,
         sname='5. Vệ sinh - Cleaning', scode=None, sitem='D', sremark='L', shrow=5),
    dict(gname='B2.6 Rác sinh hoạt (QD67)', gcode=None, gitem='A', gguide='H', ghrow=3,
         sname='17. Rác sinh hoạt (QD67)', scode=None, sitem='A', sremark='G', shrow=3),
]


def col_idx(letter):
    return openpyxl.utils.column_index_from_string(letter)


def dump_rows(ws, code_col, item_col, extra_col, header_row, label):
    """Yield (row, code_or_None, item_text, extra_text) for every row below header_row that has
    a non-empty item OR extra text."""
    out = []
    item_c = col_idx(item_col)
    extra_c = col_idx(extra_col)
    code_c = col_idx(code_col) if code_col else None
    for r in range(header_row + 1, ws.max_row + 1):
        item = ws.cell(row=r, column=item_c).value
        extra = ws.cell(row=r, column=extra_c).value
        code = ws.cell(row=r, column=code_c).value if code_c else None
        item_s = str(item).replace('\n', ' ').strip() if item else ''
        extra_s = str(extra).replace('\n', ' | ').strip() if extra else ''
        code_s = str(code).strip() if code else None
        if item_s or extra_s:
            out.append((r, code_s, item_s, extra_s))
    return out


lines = []
lines.append("REMARK RE-SCAN — AI Guideline instruction vs the worked sample's actual Remark text")
lines.append("Guide:  " + os.path.basename(GUIDE))
lines.append("Sample: " + os.path.basename(SAMPLE))
lines.append("=" * 110)

for p in PAIRS:
    gws = sheet(gwb, p['gname'])
    sws = sheet(swb, p['sname'])
    g_rows = dump_rows(gws, p['gcode'], p['gitem'], p['gguide'], p['ghrow'], 'guide')
    s_rows = dump_rows(sws, p['scode'], p['sitem'], p['sremark'], p['shrow'], 'sample')

    lines.append("")
    lines.append("#" * 110)
    lines.append(f"GUIDE SHEET: [{p['gname']}]  ({len(g_rows)} rows with item/guideline text)")
    lines.append(f"SAMPLE SHEET: [{p['sname']}]  ({len(s_rows)} rows with item/remark text)")
    lines.append("#" * 110)

    # index sample rows by code (if codes exist) else by normalised item text
    def norm(s):
        return ''.join(ch for ch in s.lower() if ch.isalnum())

    s_by_code = {c: (r, c, it, ex) for r, c, it, ex in s_rows if c}
    s_by_item = {}
    for r, c, it, ex in s_rows:
        s_by_item.setdefault(norm(it), []).append((r, c, it, ex))

    matched_sample_rows = set()
    for r, code, item, guide_text in g_rows:
        if not guide_text:
            continue
        match = None
        if code and code in s_by_code:
            match = s_by_code[code]
        else:
            cands = s_by_item.get(norm(item))
            if cands:
                match = cands[0]
        lines.append("")
        lines.append(f"[{code or '-'}] {item}  (guide row {r})")
        lines.append(f"  AI GUIDELINE : {guide_text}")
        if match:
            mr, mc, mit, mex = match
            matched_sample_rows.add(mr)
            lines.append(f"  SAMPLE REMARK (row {mr}, item {mit!r}): {mex or '(blank)'}")
        else:
            lines.append("  SAMPLE REMARK: NO MATCHING ROW FOUND in sample sheet")

    unmatched = [(r, c, it, ex) for r, c, it, ex in s_rows if ex and r not in matched_sample_rows]
    if unmatched:
        lines.append("")
        lines.append(f"  -- sample rows with a Remark but NOT matched to any guide row ({len(unmatched)}) --")
        for r, c, it, ex in unmatched[:40]:
            lines.append(f"     row {r} [{c or '-'}] {it}: {ex}")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('wrote', OUT, len(lines), 'lines')
