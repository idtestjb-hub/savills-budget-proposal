"""
Tóm tắt kết quả một lượt chạy cho trang web: doanh thu, chi phí, chênh lệch năm đầu; mức dịch vụ; so sánh với
dự án tham chiếu. Chỉ đọc file đã sinh, không chạy lại pipeline.

Nguồn số, và vì sao:
- Thu / chi / chênh lệch: bản ghi run_log (<workdir>/run_log/*.json) mà pipeline viết sau mỗi lượt. run_log.py mở bản
  giao trong Excel, tính lại, và đọc các dòng tổng của '1. Summary'. Bản giao do openpyxl ghi nên các ô công thức
  không có giá trị cache; đọc thẳng bằng openpyxl ra None. Máy không có Excel thì bản ghi có status
  'excel_unavailable' và các số là null: trang nói rõ là chưa đo được, không đoán.
- Mức dịch vụ: sheet 'Service Levels' của bản phân tích, pipeline ghi bằng giá trị.
- So sánh: sheet 'Comparison' của bản phân tích, kể cả tên hai dự án tham chiếu (người dùng yêu cầu 19/10: hiện tên).
- Lượt review (webapp/review_run.py): review_summary.json và review_notes.json mà review.py ghi trong thư mục lượt.
"""
import glob
import json
import os

import openpyxl

RUN_LOG_SOURCE = "Bản ghi run_log của lượt chạy (pipeline đo bằng Excel trên sheet '1. Summary' của bản giao)"
SERVICE_SOURCE = "Sheet 'Service Levels' của bản phân tích nội bộ"
COMPARE_SOURCE = "Sheet 'Comparison' của bản phân tích nội bộ"


def _norm(value):
    return str(value or '').strip().casefold()



# ---- 1. Thu / chi / chênh lệch -----------------------------------------------------------------

def read_run_log(workdir):
    """Bản ghi run_log mới nhất của thư mục chạy, hoặc None."""
    files = glob.glob(os.path.join(workdir, 'run_log', '*.json'))
    if not files:
        return None
    with open(max(files, key=os.path.getmtime), encoding='utf-8') as fh:
        return json.load(fh)


def financials(record):
    """{'revenue','expense','surplus','vat_basis','budget_year','status','note','source'}; số là VND/năm hoặc None."""
    out = dict(revenue=None, expense=None, surplus=None, vat_basis=None, budget_year=None, status=None,
               required_pct=None, note='', source=RUN_LOG_SOURCE)
    if not record:
        out['note'] = 'Chưa có bản ghi run_log cho lượt này: pipeline không ghi được bản ghi, nên chưa đo được số.'
        return out
    out.update(revenue=record.get('revenue_vnd'), expense=record.get('expense_vnd'),
               surplus=record.get('fund_surplus_vnd'), vat_basis=record.get('vat_basis'),
               budget_year=record.get('budget_year'), status=record.get('status'),
               required_pct=record.get('required_pct'))
    if out['surplus'] is None and out['revenue'] is not None and out['expense'] is not None:
        out['surplus'] = out['revenue'] - out['expense']
    if out['revenue'] is None or out['expense'] is None:
        status = str(record.get('status') or '')
        why = ('máy chủ không có Excel để tính lại bản giao' if 'excel_unavailable' in status
               else f'bản ghi run_log báo: {status or "không rõ"}')
        out['note'] = f'Chưa đo được: {why}. Số có trong file bản giao khi mở bằng Excel.'
    return out


# ---- 2. Mức dịch vụ --------------------------------------------------------------------------

_SERVICE_VI = {'cleaning': 'Vệ sinh', 'security': 'Bảo vệ', 'landscape': 'Cảnh quan'}
_UNIT_VI = {'m2 nfa thu phi / nguoi truc moi ngay': 'm² NFA thu phí / người trực mỗi ngày',
            'chot 24h quy doi / 10.000 m2 nfa thu phi': 'chốt 24h quy đổi / 10.000 m² NFA thu phí'}


def service_levels(analysis_path):
    """[{service, people, headcount, nfa, measure, unit, level, near_cutoff, percentile, compared}] cho vệ sinh và bảo vệ."""
    out = dict(rows=[], note='', source=SERVICE_SOURCE)
    if not analysis_path or not os.path.exists(analysis_path):
        out['note'] = 'Chưa có bản phân tích.'
        return out
    wb = openpyxl.load_workbook(analysis_path, read_only=True, data_only=True)
    try:
        if 'Service Levels' not in wb.sheetnames:
            out['note'] = "Bản phân tích không có sheet 'Service Levels'."
            return out
        ws = wb['Service Levels']
        header = None
        for row in ws.iter_rows(values_only=True):
            if header is None:
                if _norm(row[0]) == 'service' and 'people' in _norm(row[1]):
                    header = {_norm(h): i for i, h in enumerate(row) if h}
                continue
            name = _norm(row[0])
            if name not in ('cleaning', 'security'):
                if name.startswith('threshold') or name == 'landscape':
                    if name.startswith('threshold'):
                        break
                continue

            def col(prefix):
                for key, i in header.items():
                    if key.startswith(prefix):
                        return row[i] if i < len(row) else None
                return None

            unit = col('unit')
            out['rows'].append(dict(
                service=_SERVICE_VI.get(name, row[0]), people=col('people on duty'), headcount=col('roster headcount'),
                nfa=col('fee-paying nfa'), measure=col('measure'), unit=_UNIT_VI.get(_norm(unit), unit),
                level=col('level'), near_cutoff=col('near cut-off') or '', thresholds=col('thresholds applied'),
                percentile=col('percentile'), compared=col('projects compared')))
        if not out['rows']:
            out['note'] = "Không đọc được bảng mức dịch vụ (không thấy dòng Cleaning / Security)."
    finally:
        wb.close()
    return out


# ---- 3. So sánh với dự án tham chiếu ---------------------------------------------------------

_COMPARE_ROWS = (
    ('total nfa', 'Tổng NFA (m²), cơ sở so sánh'),
    ('apartment units', 'Số căn hộ'),
    ('real apartment rate per comparable', 'Đơn giá phí quản lý căn hộ thực tế (VND/m²/tháng)'),
    ('model-derived apartment rate', 'Đơn giá căn hộ đề xuất cho dự án này (VND/m²/tháng)'),
    ('management fee per apartment', 'Phí quản lý một căn hộ (VND/tháng)'),
)


def comparables(analysis_path):
    """{'columns': ['Dự án này', <tên tham chiếu 1>, ...], 'rows': [{'label', 'values': [...]}], 'note', 'source'}."""
    out = dict(columns=[], rows=[], count=0, note='', source=COMPARE_SOURCE)
    if not analysis_path or not os.path.exists(analysis_path):
        out['note'] = 'Chưa có bản phân tích.'
        return out
    wb = openpyxl.load_workbook(analysis_path, read_only=True, data_only=True)
    try:
        if 'Comparison' not in wb.sheetnames:
            out['note'] = "Bản phân tích không có sheet 'Comparison'."
            return out
        ws = wb['Comparison']
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    header_idx = next((i for i, r in enumerate(rows) if _norm(r[0]) == 'metric'), None)
    if header_idx is None:
        out['note'] = "Không thấy dòng tiêu đề 'Metric' trên sheet Comparison."
        return out
    header = rows[header_idx]
    ncomp = sum(1 for v in header[2:] if v not in (None, ''))
    out['count'] = ncomp
    out['columns'] = ['Dự án này'] + [str(v).strip() for v in header[2:2 + ncomp]]
    for prefix, label in _COMPARE_ROWS:
        for r in rows[header_idx + 1:]:
            if _norm(r[0]).startswith(prefix):
                values = [r[1]] + [r[2 + i] if 2 + i < len(r) else None for i in range(ncomp)]
                out['rows'].append(dict(label=label, values=[_clean(v) for v in values]))
                break
    if not out['rows']:
        out['note'] = 'Không đọc được bảng so sánh.'
    return out


def _clean(value):
    if value is None or value == '—':
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, float):
        return round(value, 1)
    return value


# ---- 4. Lượt review: ngân sách đã duyệt năm ngoái so với công cụ ----------------------------

REVIEW_SOURCE = ("review_summary.json của lượt review: sheet 'Review' cuối bản phân tích nội bộ; số công cụ đo bằng Excel "
                 "trên bản giao, số duyệt đọc từ file ngân sách đã duyệt và quy đổi về cơ sở VAT của bản giao")
_REVIEW_META_KEYS = ('prior_year', 'budget_year', 'deliverable_incl', 'file_incl', 'file_name', 'period_text',
                     'project', 'ran_at')


def review_summary(workdir):
    """{'kind': 'review', 'meta', 'summary' {MF/CA: {R, E, S}}, 'counts', 'ties', 'top', 'notes', 'filled', 'note',
    'source'}: review_summary.json và review_notes.json của lượt review. Thiếu file thì có note, không đoán."""
    out = dict(kind='review', meta={}, summary={}, counts={}, ties=[], top=[], notes=[], filled={}, note='',
               source=REVIEW_SOURCE)
    path = os.path.join(workdir, 'review_summary.json')
    if not os.path.exists(path):
        out['note'] = 'Chưa có review_summary.json: lượt review dừng trước khi ghi sheet Review (xem log).'
    else:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        meta = data.get('meta') or {}
        out['meta'] = {k: meta.get(k) for k in _REVIEW_META_KEYS}
        out['summary'] = data.get('summary') or {}
        out['counts'] = data.get('counts') or {}
        out['ties'] = data.get('ties') or []
        out['top'] = data.get('top') or []
    notes_path = os.path.join(workdir, 'review_notes.json')
    if os.path.exists(notes_path):
        with open(notes_path, encoding='utf-8') as fh:
            notes = json.load(fh)
        out['notes'] = notes.get('notes') or []
        out['filled'] = notes.get('filled') or {}
    return out


# ---- Tổng hợp --------------------------------------------------------------------------------

def summarize(workdir, analysis_path=None):
    """Một dict JSON cho trang: finance, service, compare. Lỗi ở phần nào thì phần đó có note, phần khác vẫn trả."""
    analysis_path = analysis_path or os.path.join(workdir, 'Project_Budget_Output.xlsx')
    summary = {}
    for key, fn in (('finance', lambda: financials(read_run_log(workdir))),
                    ('service', lambda: service_levels(analysis_path)),
                    ('compare', lambda: comparables(analysis_path))):
        try:
            summary[key] = fn()
        except Exception as exc:  # trang vẫn hiện các phần còn lại
            summary[key] = dict(note=f'Không đọc được: {type(exc).__name__}: {exc}')
    return summary


def adjust_result(workdir):
    """adjust_result.json của lần lưu điều chỉnh gần nhất trong thư mục lượt (webapp/adjust_run.py), hoặc {}."""
    path = os.path.join(workdir, 'adjust_result.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as fh:
        return json.load(fh) or {}


def summarize_run(workdir, kind='new'):
    """Tóm tắt theo loại lượt: 'review' đọc review_summary.json; 'adjust' đọc adjust_result.json; 'new' như summarize()."""
    if kind == 'adjust':
        try:
            data = adjust_result(workdir)
            return dict(kind='adjust', **data) if data else dict(kind='adjust', note='Chưa có kết quả lưu điều chỉnh (xem log).')
        except Exception as exc:
            return dict(kind='adjust', note=f'Không đọc được: {type(exc).__name__}: {exc}')
    if kind == 'review':
        try:
            return review_summary(workdir)
        except Exception as exc:
            return dict(kind='review', note=f'Không đọc được: {type(exc).__name__}: {exc}')
    return summarize(workdir)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    kind = sys.argv[2] if len(sys.argv) > 2 else 'new'
    print(json.dumps(summarize_run(sys.argv[1], kind), ensure_ascii=False, indent=1, default=str))
