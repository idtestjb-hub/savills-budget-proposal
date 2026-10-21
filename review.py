"""Budget Review in one command (change add-budget-renewal-mode, design D3, D5, D6, D9, D10):

    python review.py <last year's approved budget .xlsx> [--input form.xlsx] [--facts facts.json] [--workdir DIR]

For a building Savills already runs: read last year's approved budget (review_import.py), fill the Existing-project
form from it, run both generators in an isolated work folder, let Excel recalculate the deliverable, and add a sheet
`Review` at the end of the analysis workbook that sets the approved figure beside the tool's new-year figure, line by
line, with how the tool got each figure. Two ties are printed and the command exits 1 if either fails: the tool
column's R and E totals equal the deliverable's own R and E rows; the approved column's R and E totals equal the
source file's own R and E rows.

Nothing in the live reports/ or sample_output/ is written (verification.isolation redirects every path). Excel is
needed for the Review sheet, as for the run log; without it the command stops after the pipeline and says so.
"""
import argparse
import datetime
import glob
import json
import os
import sys

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import review_import as ri                       # noqa: E402
import utility_tariffs as ut                     # noqa: E402

BUDGET_AGENT = os.path.dirname(HERE)
DEFAULT_WORKDIR = os.path.join(BUDGET_AGENT, 'reports', 'review')
REVIEW_SHEET = 'Review'
TOL = 1.0
TOP = 10

# The deliverable's fund sheets: code, item, annual and the first and last month column (2027 template).
DELIVERABLE_LAYOUT = {
    'MF': dict(sheet='2. Budget-Management Fund', code='Y', name='Z', value='AK', first_month='AQ'),
    'CA': dict(sheet='2.2 Common area Fund', code='Y', name='Z', value='AG', first_month='AL'),
}
SECTION_VI = {'R': 'THU', 'E': 'CHI'}

# "How the tool got its figure" (design D6).
LABEL_LAW = 'Mang sang theo luật'
LABEL_TARIFF = 'Mang sang theo biểu giá'
LABEL_PM = 'PM nhập'
LABEL_ESTIMATE = 'Ước lượng'
LABEL_NO_METHOD = 'Chưa có phương pháp'
LABEL_ZERO = 'Công cụ ra 0'
LABEL_TOOL_ONLY = 'Chỉ công cụ'
LABEL_NOT_ON_FORM = 'Không có trên form 2027'
LAW_CODES = set(ri.es.STAFF_LINES)
TARIFF_CODES = set(ri.eu.LINES)

HEADER_FILL = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
SECTION_FILL = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
TOTAL_FILL = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
HEADER_FONT = Font(color='FFFFFF', bold=True)
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = '#,##0'
PCT = '0.0%'
COLUMNS = ['Mã', 'Hạng mục', 'Duyệt NS {py} (như file)', 'Hệ số VAT', 'Duyệt NS {py} (quy đổi)', 'Công cụ NS {by}',
           'Chênh (công cụ − duyệt)', '%', 'Cách công cụ ra số', 'Ghi chú']
WIDTHS = [10, 46, 20, 9, 20, 20, 20, 8, 34, 50]


class ReviewError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------
# VAT
# ------------------------------------------------------------------------------------------------
_FALLBACK_CUT = [((2022, 2), (2022, 12)), ((2023, 7), (2023, 12)), ((2024, 1), (2024, 6)), ((2024, 7), (2024, 12)),
                 ((2025, 1), (2025, 6)), ((2025, 7), (2026, 12))]


def vat_rate(year, month, rows=None):
    """General VAT rate (percent) of a month: the tariff table (the one place the 8%/10% rule is stated), and for
    months before the table starts the dated reduced-rate periods of the scan store."""
    try:
        return float(ut.vat_rate(year, month, rows=rows))
    except ut.TariffError:
        return 8.0 if any(a <= (year, month) <= b for a, b in _FALLBACK_CUT) else 10.0


def vat_factor(code, months, file_incl, deliverable_incl, rows=None):
    """The factor the approved figure is multiplied by to reach the deliverable's basis (design D3)."""
    if file_incl == deliverable_incl or ri.no_vat(code) or not months:
        return 1.0
    avg = sum(1 + vat_rate(y, m, rows) / 100 for y, m in months) / len(months)
    return avg if deliverable_incl else 1 / avg


# ------------------------------------------------------------------------------------------------
# The tool's figures, from the recalculated deliverable (design D5)
# ------------------------------------------------------------------------------------------------
def recalc_copy(src, dst):
    try:
        import pythoncom
        import win32com.client as w
    except ImportError as exc:
        raise ReviewError(f'Excel cannot be used (pywin32 missing: {exc}); the Review sheet needs it.')
    pythoncom.CoInitialize()
    xl = None
    try:
        try:
            xl = w.DispatchEx('Excel.Application')
        except Exception as exc:
            raise ReviewError(f'Excel cannot be started ({type(exc).__name__}); the Review sheet needs it.')
        xl.Visible = False
        xl.DisplayAlerts = False
        wb = xl.Workbooks.Open(os.path.abspath(src), UpdateLinks=0, ReadOnly=True)
        xl.CalculateFullRebuild()
        wb.SaveCopyAs(os.path.abspath(dst))
        wb.Close(False)
    finally:
        if xl is not None:
            xl.Quit()
        pythoncom.CoUninitialize()


def tool_lines(deliverable, recalced):
    """{fund: dict(lines={code: dict(sec, name, amount)}, totals={'R': v, 'E': v}, incl_vat=bool)}: the leaf rows
    (annual cell = SUM over the month cells; group rows are SUBTOTALs) and the sheet's own R and E rows."""
    wbf = openpyxl.load_workbook(deliverable)
    wbv = openpyxl.load_workbook(recalced, data_only=True)
    out = {}
    for fund, lay in DELIVERABLE_LAYOUT.items():
        if lay['sheet'] not in wbv.sheetnames:
            continue
        wf, wv = wbf[lay['sheet']], wbv[lay['sheet']]
        lines, totals, sec = {}, {}, None
        for r in range(1, wv.max_row + 1):
            code = wv[f"{lay['code']}{r}"].value
            if not isinstance(code, str) or not code.strip():
                continue
            code = code.strip()
            v = wv[f"{lay['value']}{r}"].value
            v = float(v) if isinstance(v, (int, float)) else 0.0
            if code in ('R', 'E'):
                sec, totals[code] = code, v
                continue
            if (code.isalpha() and len(code) == 1) or code.startswith('PL'):
                sec = None            # section D (VAT, CIT) starts at the D row, or at PL1 on a sheet without one
                continue
            f = str(wf[f"{lay['value']}{r}"].value or '').replace(' ', '').upper()
            if sec and f.startswith(f"=SUM({lay['first_month']}"):
                e = lines.setdefault(code, dict(sec=sec, name=' '.join(str(wv[f"{lay['name']}{r}"].value or '').split('\n')[0].split()),
                                                amount=0.0, rows=[]))
                e['amount'] += v
                e['rows'].append(r)
        incl = True
        if fund == 'MF':
            switch = ' '.join(str(wv['F7'].value or '').split()).upper()
            incl = switch != 'KHOÁN'
        out[fund] = dict(lines=lines, totals=totals, incl_vat=incl)
    if 'MF' in out:
        for fund in out:
            out[fund]['incl_vat'] = out['MF']['incl_vat']
    return out


# ------------------------------------------------------------------------------------------------
# The Review sheet (design D9)
# ------------------------------------------------------------------------------------------------
def label_of(code, fund, approved, tool_amount, ctx):
    """(label, note) of design D6. `ctx`: existing, rate_codes, parking_codes, methods {code: (method, item_vi)},
    on_form."""
    has_tool = tool_amount is not None and abs(tool_amount) >= 0.5
    has_approved = abs(approved) >= 0.5
    if not ctx.get('on_form', True):
        return LABEL_NOT_ON_FORM, ''
    if ctx.get('existing') and code in LAW_CODES:
        return LABEL_LAW, ''
    if ctx.get('existing') and code in TARIFF_CODES:
        return LABEL_TARIFF, ''
    if code in ctx.get('rate_codes', ()):
        return LABEL_PM, ctx.get('rate_note', '')
    if code in ctx.get('parking_codes', ()) or code in ctx.get('cob_codes', ()):
        return LABEL_PM, ''
    method = (ctx.get('methods') or {}).get(code, ('', ''))[0]
    if has_tool:
        if not has_approved:
            return LABEL_TOOL_ONLY, ri.method_vi(method)
        return f'{LABEL_ESTIMATE}: {ri.method_vi(method)}' if method else LABEL_ESTIMATE, ''
    if has_approved:
        if not method or method in ri.NO_METHOD_KEYS:
            return LABEL_NO_METHOD, ri.method_vi(method)
        return LABEL_ZERO, ri.method_vi(method)
    return '', ''


def _pct(diff, base):
    return (diff / base) if abs(base) >= 0.5 else None


def assemble(prior_lines, anchors, tool, meta, ctx, template=None):
    """Everything the sheet, the summary and the ties need, from plain data (no Excel): rows per fund and
    section, totals, ties. `prior_lines`: dicts (fund, section, code, item, approved, incl_vat, flags, on_form,
    remark). `anchors`: {fund: {'R': v, 'E': v}} of the source file. `tool`: tool_lines() output."""
    tcodes = template if template is not None else ri.template_codes()
    vat_rows = ut.load_rows()
    d_incl = bool(meta.get('deliverable_incl', True))
    months = meta.get('period') or []
    rows_by = {}
    for fund in ri.FUNDS:
        if fund not in anchors and fund not in tool:
            continue
        for sec in ri.SECTIONS_COMPARED:
            agg = {}
            for l in prior_lines:
                if l['fund'] != fund or l['section'] != sec:
                    continue
                e = agg.setdefault(l['code'], dict(code=l['code'], item=l['item'], approved=0.0, incl=l['incl_vat'],
                                                   flags=[], on_form=l.get('on_form', True), remark=''))
                e['approved'] += l['approved']
                for f in l.get('flags', []):
                    if f not in e['flags']:
                        e['flags'].append(f)
                if l.get('remark') and not e['remark']:
                    e['remark'] = l['remark']
            tl = (tool.get(fund) or {}).get('lines', {})
            for code, t in tl.items():
                if t['sec'] != sec:
                    continue
                e = agg.setdefault(code, dict(code=code, item=t['name'], approved=0.0, incl=d_incl, flags=[],
                                              on_form=True, remark=''))
                e['tool'] = t['amount']
                if not e['item']:
                    e['item'] = t['name']
            rows = []
            for code, e in agg.items():
                tool_amt = e.get('tool')
                if abs(e['approved']) < 0.5 and (tool_amt is None or abs(tool_amt) < 0.5):
                    continue
                factor = vat_factor(code, months, e['incl'], d_incl, vat_rows)
                conv = e['approved'] * factor
                label, note = label_of(code, fund, e['approved'], tool_amt, dict(ctx, on_form=e['on_form']))
                t_show = (tool_amt or 0.0) if e['on_form'] else None      # approved only: 0, never the approved figure
                t_num = tool_amt or 0.0
                item_vi = (ctx.get('methods') or {}).get(code, ('', ''))[1]
                remark = '; '.join(x for x in (note, *e['flags'], e['remark'][:120] if e['remark'] else '') if x)
                rows.append(dict(code=code, item=item_vi or e['item'], approved=e['approved'], factor=factor,
                                 converted=conv, tool=t_show, tool_num=t_num, diff=t_num - conv,
                                 pct=_pct(t_num - conv, conv), label=label, remark=remark, on_form=e['on_form'],
                                 order=(0 if e['on_form'] else 1, tcodes.get(fund, {}).get(code, 10 ** 6), code)))
            rows.sort(key=lambda x: x['order'])
            tot = dict(approved=sum(x['approved'] for x in rows), converted=sum(x['converted'] for x in rows),
                       tool=sum(x['tool_num'] for x in rows))
            tot['diff'] = tot['tool'] - tot['converted']
            tot['pct'] = _pct(tot['diff'], tot['converted'])
            rows_by[(fund, sec)] = dict(rows=rows, total=tot)
    ties = []
    for fund in ri.FUNDS:
        for sec in ri.SECTIONS_COMPARED:
            if (fund, sec) not in rows_by:
                continue
            tot = rows_by[(fund, sec)]['total']
            t_anchor = (tool.get(fund) or {}).get('totals', {}).get(sec)
            if t_anchor is not None:
                ties.append(dict(kind='công cụ = bản giao', fund=fund, section=sec, left=tot['tool'], right=t_anchor,
                                 diff=tot['tool'] - t_anchor, ok=abs(tot['tool'] - t_anchor) <= TOL))
            a_anchor = (anchors.get(fund) or {}).get(sec)
            if a_anchor is not None:
                ties.append(dict(kind='duyệt = file nguồn', fund=fund, section=sec, left=tot['approved'], right=a_anchor,
                                 diff=tot['approved'] - a_anchor, ok=abs(tot['approved'] - a_anchor) <= TOL))
    summary = {}
    for fund in ri.FUNDS:
        if (fund, 'R') in rows_by and (fund, 'E') in rows_by:
            r, e = rows_by[(fund, 'R')]['total'], rows_by[(fund, 'E')]['total']
            summary[fund] = dict(R=r, E=e, S=dict(converted=r['converted'] - e['converted'], tool=r['tool'] - e['tool'],
                                                 approved=r['approved'] - e['approved']))
            summary[fund]['S']['diff'] = summary[fund]['S']['tool'] - summary[fund]['S']['converted']
            summary[fund]['S']['pct'] = _pct(summary[fund]['S']['diff'], summary[fund]['S']['converted'])
    all_rows = [dict(x, fund=f, section=s) for (f, s), b in rows_by.items() for x in b['rows']]
    counts = dict(lines=len(all_rows), both=sum(abs(x['approved']) >= 0.5 and abs(x['tool_num']) >= 0.5 for x in all_rows),
                  only_approved=sum(abs(x['approved']) >= 0.5 and abs(x['tool_num']) < 0.5 for x in all_rows),
                  only_tool=sum(abs(x['approved']) < 0.5 and abs(x['tool_num']) >= 0.5 for x in all_rows),
                  not_on_form=sum(not x['on_form'] for x in all_rows),
                  no_method=sum(x['label'] == LABEL_NO_METHOD for x in all_rows),
                  tool_zero=sum(x['label'] == LABEL_ZERO for x in all_rows))
    top = sorted(all_rows, key=lambda x: -abs(x['diff']))[:TOP]
    return dict(rows_by=rows_by, ties=ties, summary=summary, counts=counts, top=top)


def build_review_sheet(wb, data, meta):
    """Write the Review sheet from assemble()'s output. Returns the worksheet."""
    if REVIEW_SHEET in wb.sheetnames:
        del wb[REVIEW_SHEET]
    ws = wb.create_sheet(REVIEW_SHEET)
    py, by = meta['prior_year'], meta['budget_year']
    ws['A1'] = f'Review — ngân sách đã duyệt {py} so với ngân sách {by} do công cụ sinh'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = (f"Nguồn: {meta.get('file_name', '')}; sheet {', '.join(meta.get('sheets', {}).values())}; kỳ "
                f"{meta.get('period_text', '')}; file {'gồm' if meta.get('file_incl') else 'chưa gồm'} VAT, bản giao "
                f"{'gồm' if meta.get('deliverable_incl', True) else 'chưa gồm'} VAT. Số duyệt quy về cơ sở bản giao theo "
                f"từng dòng (lương, thuế phí, phí và lãi ngân hàng không VAT; 8% kỳ giảm, 10% còn lại). "
                f"Công cụ = dòng lá bản giao sau khi Excel tính lại.")
    ws['A2'].font = Font(italic=True, size=9, color='7F7F7F')
    ws['A2'].alignment = Alignment(wrap_text=True, vertical='top')
    ws.merge_cells('A2:J2')
    ws.row_dimensions[2].height = 42
    c = data['counts']
    ws['A3'] = (f"Dòng so sánh: {c['lines']} (cả hai có số {c['both']}, chỉ file duyệt {c['only_approved']}, chỉ công cụ "
                f"{c['only_tool']}); mã không có trên form 2027: {c['not_on_form']}; chưa có phương pháp: {c['no_method']}; "
                f"công cụ ra 0: {c['tool_zero']}. Phần D (VAT, CIT) không so.")
    ws['A3'].font = Font(size=9)
    ws.merge_cells('A3:J3')

    r = 5
    ws.cell(row=r, column=1, value='TÓM TẮT (Quỹ quản lý vận hành)').font = Font(bold=True)
    r += 1
    for col, h in enumerate(['', f'Duyệt NS {py} (quy đổi)', f'Công cụ NS {by}', 'Chênh', '%'], start=1):
        cell = ws.cell(row=r, column=col, value=h)
        cell.fill, cell.font, cell.border = HEADER_FILL, HEADER_FONT, BORDER
    r += 1
    s = data['summary'].get('MF')
    if s:
        for key, lab in (('R', 'Tổng thu'), ('E', 'Tổng chi'), ('S', 'Thặng dư')):
            t = s[key]
            vals = [lab, t['converted'], t['tool'], t['diff'], t['pct']]
            for col, v in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=col, value=v)
                cell.border = BORDER
                if col in (2, 3, 4):
                    cell.number_format = MONEY
                if col == 5:
                    cell.number_format = PCT
            ws.cell(row=r, column=1).font = Font(bold=True)
            r += 1
    r += 1
    ws.cell(row=r, column=1, value='ĐỐI CHIẾU TỔNG').font = Font(bold=True)
    r += 1
    for t in data['ties']:
        text = (f"{t['kind']} — {ri.FUND_VI[t['fund']]} {t['section']}: {t['left']:,.0f} so với {t['right']:,.0f}, "
                f"lệch {t['diff']:,.0f} → {'KHỚP' if t['ok'] else 'LỆCH'}")
        ws.cell(row=r, column=1, value=text).font = Font(size=9, color='006100' if t['ok'] else 'C00000')
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=10)
        r += 1

    r += 1
    headers = [h.format(py=py, by=by) for h in COLUMNS]
    for fund in ri.FUNDS:
        if not any((fund, s_) in data['rows_by'] for s_ in ri.SECTIONS_COMPARED):
            continue
        ws.cell(row=r, column=1, value=f"{ri.FUND_VI[fund]} ({meta.get('sheets', {}).get(fund, fund)})").font = Font(bold=True, size=12)
        r += 1
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=r, column=col, value=h)
            cell.fill, cell.font, cell.border = HEADER_FILL, HEADER_FONT, BORDER
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[r].height = 30
        r += 1
        for sec in ri.SECTIONS_COMPARED:
            block = data['rows_by'].get((fund, sec))
            if block is None:
                continue
            cell = ws.cell(row=r, column=1, value=f'{sec} — {SECTION_VI[sec]}')
            cell.font, cell.fill = Font(bold=True), SECTION_FILL
            for col in range(2, 11):
                ws.cell(row=r, column=col).fill = SECTION_FILL
            r += 1
            shown_off_form = False
            for x in block['rows']:
                if not x['on_form'] and not shown_off_form:
                    ws.cell(row=r, column=1, value=LABEL_NOT_ON_FORM + ' (vẫn tính vào tổng duyệt)').font = Font(italic=True)
                    r += 1
                    shown_off_form = True
                vals = [x['code'], x['item'], x['approved'], x['factor'], x['converted'], x['tool'], x['diff'], x['pct'],
                        x['label'], x['remark']]
                for col, v in enumerate(vals, start=1):
                    cell = ws.cell(row=r, column=col, value=v)
                    cell.border = BORDER
                    if col in (3, 5, 6, 7):
                        cell.number_format = MONEY
                    elif col == 4:
                        cell.number_format = '0.00'
                    elif col == 8:
                        cell.number_format = PCT
                    if col in (2, 9, 10):
                        cell.alignment = Alignment(wrap_text=False, vertical='top')
                r += 1
            tot = block['total']
            vals = [f'Tổng {sec}', '', tot['approved'], '', tot['converted'], tot['tool'], tot['diff'], tot['pct'], '', '']
            for col, v in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=col, value=v if v != '' else None)
                cell.fill, cell.border, cell.font = TOTAL_FILL, BORDER, Font(bold=True)
                if col in (3, 5, 6, 7):
                    cell.number_format = MONEY
                elif col == 8:
                    cell.number_format = PCT
            r += 1
        s = data['summary'].get(fund)
        if s:
            vals = ['Thặng dư (R − E)', '', s['S']['approved'], '', s['S']['converted'], s['S']['tool'], s['S']['diff'], s['S']['pct'], '', '']
            for col, v in enumerate(vals, start=1):
                cell = ws.cell(row=r, column=col, value=v if v != '' else None)
                cell.fill, cell.border, cell.font = TOTAL_FILL, BORDER, Font(bold=True)
                if col in (3, 5, 6, 7):
                    cell.number_format = MONEY
                elif col == 8:
                    cell.number_format = PCT
            r += 1
        r += 1
    for i, w in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A5'
    return ws


# ------------------------------------------------------------------------------------------------
# Summary text
# ------------------------------------------------------------------------------------------------
def _m(v):
    return '' if v is None else f'{v / 1e6:,.1f}'


def _p(v):
    return '' if v is None else f'{v:+.0%}'


def summary_md(data, meta):
    py, by = meta['prior_year'], meta['budget_year']
    md = [f"# Budget Review: NS duyệt {py} so với NS {by} do công cụ sinh\n",
          f"Nguồn: `{meta.get('file_name', '')}`; kỳ {meta.get('period_text', '')}; cơ sở so: "
          f"{'gồm' if meta.get('deliverable_incl', True) else 'chưa gồm'} VAT (cơ sở bản giao). Đơn vị: triệu VND/năm.\n"]
    s = data['summary'].get('MF')
    if s:
        md.append('| Quỹ quản lý vận hành | Duyệt (quy đổi) | Công cụ | Chênh | % |\n|---|---:|---:|---:|---:|')
        for key, lab in (('R', 'Tổng thu'), ('E', 'Tổng chi'), ('S', 'Thặng dư')):
            t = s[key]
            md.append(f"| {lab} | {_m(t['converted'])} | {_m(t['tool'])} | {_m(t['diff'])} | {_p(t['pct'])} |")
    c = data['counts']
    md.append(f"\nDòng so sánh: {c['lines']} (cả hai có số {c['both']}, chỉ file duyệt {c['only_approved']}, chỉ công cụ "
              f"{c['only_tool']}); mã không có trên form 2027: {c['not_on_form']}; chưa có phương pháp: {c['no_method']}; "
              f"công cụ ra 0: {c['tool_zero']}.\n")
    md.append('Đối chiếu tổng:')
    for t in data['ties']:
        md.append(f"- {t['kind']}, {ri.FUND_VI[t['fund']]} {t['section']}: {t['left']:,.0f} / {t['right']:,.0f}, lệch "
                  f"{t['diff']:,.0f} → {'KHỚP' if t['ok'] else 'LỆCH'}")
    md.append(f'\nTop {TOP} theo |chênh lệch|:\n')
    md.append('| # | Quỹ | Mã | Hạng mục | Duyệt (quy đổi) | Công cụ | Chênh | % | Cách ra số |\n|---:|---|---|---|---:|---:|---:|---:|---|')
    for i, x in enumerate(data['top'], 1):
        md.append(f"| {i} | {x['fund']} | {x['code']} | {x['item'][:44].replace('|', '/')} | {_m(x['converted'])} | "
                  f"{_m(x['tool_num'])} | {_m(x['diff'])} | {_p(x['pct'])} | {x['label']} |")
    return '\n'.join(md) + '\n'


def summary_json(data, meta):
    return dict(meta=meta, summary=data['summary'], counts=data['counts'], ties=data['ties'],
                top=[{k: v for k, v in x.items() if k != 'order'} for x in data['top']])


# ------------------------------------------------------------------------------------------------
# The command
# ------------------------------------------------------------------------------------------------
def run(prior_path, base_form=None, facts_path=None, workdir=None, quiet=True, now=None):
    """The whole review. Returns (exit_code, result dict)."""
    from verification.run_workflow import run_workflow

    now = now or datetime.datetime.now()
    workdir = os.path.abspath(workdir or os.path.join(DEFAULT_WORKDIR, now.strftime('%Y%m%d-%H%M%S')))
    os.makedirs(workdir, exist_ok=True)
    log = []

    def say(text):
        log.append(text)
        if not quiet:
            print(text)

    say(f'[1/4] Đọc file ngân sách đã duyệt: {prior_path}')
    prior = ri.read_prior_budget(prior_path, workdir=workdir)
    wb, _ = ri.open_workbook(prior_path, workdir)
    try:
        info = ri.read_info(wb)
    finally:
        wb.close()
    facts = ri.load_facts(facts_path) if facts_path else {}
    for fund in ri.FUNDS:
        fr = prior.funds.get(fund)
        if fr:
            say(f"    {fr.sheet}: R {fr.section_total('R'):,.0f} (sheet {fr.anchors['R']:,.0f}), "
                f"E {fr.section_total('E'):,.0f} (sheet {fr.anchors['E']:,.0f}), {len(fr.lines)} dòng, "
                f"{'chưa' if fr.vat_basis == 'excl' else 'gồm'} VAT, cột năm {fr.value_how}")
    say(f'    dự án {prior.project_name!r}, năm {prior.budget_year}, {len(prior.notes)} ghi chú nhập')

    say('[2/4] Đổ form Existing project')
    form_dir = os.path.join(workdir, 'input')
    form, notes, filled = ri.write_form(prior, info, facts, form_dir, base_form=base_form, now=now)
    say(f"    form: {form}")
    say(f"    đơn giá PM nhập: {', '.join(f'{k} {v[0]:,.0f}' for k, v in filled['rates'].items()) or 'không'}; "
        f"doanh thu xe: {filled['parking'] or 'không'}; để trống: {', '.join(filled['blank']) or 'không'}; "
        f"từ file dữ kiện: {', '.join(filled['facts']) or 'không'}")

    say('[3/4] Chạy hai generator (cô lập)')
    run_dir = os.path.join(workdir, 'run')
    os.makedirs(run_dir, exist_ok=True)
    outputs, _, _ = run_workflow(sample=form, workdir=run_dir, quiet=True)
    deliverables = glob.glob(os.path.join(outputs['deliverable_dir'], '*Consulting Budget*.xlsx'))
    if len(deliverables) != 1:
        raise ReviewError(f'expected one deliverable in {outputs["deliverable_dir"]}, found {deliverables}')
    deliverable, analysis = deliverables[0], outputs['analysis']
    say(f'    bản giao: {deliverable}')
    say(f'    phân tích: {analysis}')

    say('[4/4] Excel tính lại bản giao, ghi sheet Review')
    recalced = os.path.join(workdir, 'deliverable_recalc.xlsx')
    recalc_copy(deliverable, recalced)
    tool = tool_lines(deliverable, recalced)
    mf = prior.funds['MF']
    prior_lines = [dict(fund=l.fund, section=l.section, code=l.code, item=l.item, approved=l.annual,
                        incl_vat=prior.funds[l.fund].vat_basis == 'incl', flags=l.flags, on_form=l.on_form,
                        remark=l.remark) for l in prior.lines()]
    anchors = {f: fr.anchors for f, fr in prior.funds.items()}
    rate_bases = {v[1] for v in filled['rates'].values()}
    d_incl = tool.get('MF', {}).get('incl_vat', True)
    rate_note = ''
    if rate_bases and rate_bases != {ri.oi.VAT_INCL if d_incl else ri.oi.VAT_EXCL}:
        rate_note = (f"đơn giá nhập {', '.join(sorted(rate_bases))}, bản giao {'gồm' if d_incl else 'chưa gồm'} VAT: "
                     f"công cụ không quy đổi đơn giá đã nhập (quy tắc hiện có của ô Actual Rate)")
    ctx = dict(existing=True, rate_codes={ri.PRODUCT_CODES[p] for p in filled['rates']}, rate_note=rate_note,
               parking_codes={c for c, k in (('RP2', 'car'), ('RP1', 'moto')) if k in filled['parking']},
               cob_codes=set(filled.get('cob', {})) | {ri.oi.cob_pairing().get(c, '') for c in filled.get('cob', {})},
               methods=ri.catalogue_methods())
    meta = dict(prior_year=prior.budget_year, budget_year=prior.budget_year + 1,
                deliverable_incl=tool.get('MF', {}).get('incl_vat', True), file_incl=mf.vat_basis == 'incl',
                file_name=os.path.basename(prior_path), sheets={f: fr.sheet for f, fr in prior.funds.items()},
                period=prior.period, period_text=f'{prior.period[0][1]:02d}/{prior.period[0][0]}–{prior.period[-1][1]:02d}/{prior.period[-1][0]}',
                project=prior.project_name, form=form, deliverable=deliverable, analysis=analysis, workdir=workdir,
                ran_at=now.isoformat(timespec='seconds'))
    data = assemble(prior_lines, anchors, tool, meta, ctx)
    awb = openpyxl.load_workbook(analysis)
    build_review_sheet(awb, data, meta)
    awb.save(analysis)
    md = summary_md(data, meta)
    open(os.path.join(workdir, 'review_summary.md'), 'w', encoding='utf-8').write(md)
    json.dump(summary_json(data, meta), open(os.path.join(workdir, 'review_summary.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1, default=str)
    say(md)
    bad = [t for t in data['ties'] if not t['ok']]
    for t in bad:
        say(f"LỆCH: {t['kind']}, {ri.FUND_VI[t['fund']]} {t['section']}: {t['left']:,.0f} so với {t['right']:,.0f} "
            f"(lệch {t['diff']:,.0f})")
    say(f"Sheet '{REVIEW_SHEET}' đã ghi vào {analysis}")
    return (1 if bad else 0), dict(prior=prior, info=info, form=form, notes=notes, filled=filled, tool=tool,
                                   data=data, meta=meta, analysis=analysis, deliverable=deliverable, log=log)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Budget Review: last year's approved budget -> this year's budget + Review sheet.")
    ap.add_argument('prior', help="last year's approved budget workbook (.xlsx on the Savills form)")
    ap.add_argument('--input', help='a filled input form to start from (a dated copy is used; the original is not changed)')
    ap.add_argument('--facts', help='JSON of Project Info label -> value for facts the file does not carry')
    ap.add_argument('--workdir', help=f'work folder (default: {DEFAULT_WORKDIR}\\<timestamp>)')
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    try:
        code, _ = run(a.prior, base_form=a.input, facts_path=a.facts, workdir=a.workdir, quiet=False)
    except (ri.PriorBudgetError, ReviewError, ValueError, LookupError, RuntimeError) as exc:
        print(f'STOPPED: {exc}')
        return 2
    return code


if __name__ == '__main__':
    sys.exit(main())
