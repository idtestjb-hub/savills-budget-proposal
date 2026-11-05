"""
Trang kết quả tĩnh `ket-qua.html` của một lượt review chạy một lần (change site-standalone-package, design D6).

render(workdir) đọc review_summary.json + review_notes.json qua results.review_summary() và ghi một file HTML tự đứng,
cùng các mục và cách gọi như tab Review của trang web: duyệt so với công cụ theo quỹ, đối chiếu tổng, 10 dòng lệch lớn
nhất, ghi chú nhập, link tới ba file kết quả (đường dẫn tương đối trong thư mục lượt). Arial, token màu Savills, không
logo, không tên người. Lượt dừng (không có review_summary.json) thì trang ghi dòng STOPPED từ run.log.
"""
import html
import os

from webapp import history, results

FILE_NAME = 'ket-qua.html'
FUND_VI = {'MF': 'Quỹ quản lý vận hành', 'CA': 'Quỹ khai thác khu vực chung'}
CSS = """
:root { --bg:#FFFFFF; --text:#000000; --muted:#595959; --rule:#D9D9D9; --yellow:#FFDF00; --navy:#25273A;
  --total:#E4E6E8; --warm:#EEE8E3; --neg:#CE181E; --ok:#008493; }
@media (prefers-color-scheme: dark) { :root { --bg:#25273A; --text:#FFFFFF; --muted:#BEBFC4; --rule:#696975;
  --total:#303244; --warm:#36384A; --neg:#D95F65; } }
body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 Arial, Helvetica, sans-serif; }
.edge { position:fixed; top:0; right:0; width:7px; height:100vh; background:var(--yellow); }
.page { max-width:1200px; margin:0 auto; padding:28px 36px 60px; }
.eyebrow { display:inline-block; background:var(--yellow); color:#000; padding:3px 8px; font-weight:700; font-size:13px; }
h1 { font-size:26px; margin:14px 0 6px; } h1 b { background:var(--yellow); color:#000; padding:0 4px; }
h2 { font-size:18px; margin:26px 0 8px; } .src { color:var(--muted); font-size:13px; }
table { border-collapse:collapse; width:100%; margin:6px 0 10px; }
th, td { padding:6px 8px; border-bottom:1px solid var(--rule); text-align:left; vertical-align:top; }
th { background:var(--yellow); color:#000; font-size:13px; }
td.num, th.num { text-align:right; white-space:nowrap; } td.neg { color:var(--neg); }
tr.fund td { background:var(--total); font-weight:700; }
.ok { color:var(--ok); font-weight:700; } .bad { color:var(--neg); font-weight:700; }
.stop { border:1px solid var(--neg); padding:12px 14px; margin:12px 0; }
a { color:var(--navy); font-weight:700; } @media (prefers-color-scheme: dark) { a { color:var(--yellow); } }
"""


def _e(v):
    return html.escape('' if v is None else str(v))


def _mil(v):
    return '—' if v is None else f'{v / 1e6:,.1f}'


def _pct(v):
    return '—' if v is None else f'{"+" if v > 0 else ""}{round(v * 100)}%'


def _num_td(v, cls='num'):
    return f'<td class="{cls}{" neg" if isinstance(v, (int, float)) and v < 0 else ""}">{_mil(v)}</td>'


def _pct_td(v):
    return f'<td class="num{" neg" if isinstance(v, (int, float)) and v < 0 else ""}">{_pct(v)}</td>'


def _summary_table(s):
    rows = []
    for fund in ('MF', 'CA'):
        f = (s.get('summary') or {}).get(fund)
        if not f:
            continue
        rows.append(f'<tr class="fund"><td colspan="5">{FUND_VI[fund]}</td></tr>')
        for key, lab in (('R', 'Tổng thu'), ('E', 'Tổng chi'), ('S', 'Thặng dư')):
            t = f.get(key) or {}
            rows.append(f'<tr><td>{lab}</td>{_num_td(t.get("converted"))}{_num_td(t.get("tool"))}'
                        f'{_num_td(t.get("diff"))}{_pct_td(t.get("pct"))}</tr>')
    m = s.get('meta') or {}
    py, by = m.get('prior_year') or '', m.get('budget_year') or ''
    head = (f'<tr><th>Quỹ / mục</th><th class="num">Duyệt NS {_e(py)} (quy đổi)</th><th class="num">Công cụ NS {_e(by)}</th>'
            f'<th class="num">Chênh (công cụ − duyệt)</th><th class="num">%</th></tr>')
    return f'<table>{head}{"".join(rows) or "<tr><td colspan=5>Chưa có số tóm tắt.</td></tr>"}</table>'


def _ties(s):
    items = []
    for t in s.get('ties') or []:
        items.append(f'<li>{_e(t.get("kind"))}, {FUND_VI.get(t.get("fund"), _e(t.get("fund")))} {_e(t.get("section"))}: '
                     f'{round(t.get("left") or 0):,} / {round(t.get("right") or 0):,}, lệch {round(t.get("diff") or 0):,} → '
                     f'<b class="{"ok" if t.get("ok") else "bad"}">{"KHỚP" if t.get("ok") else "LỆCH"}</b></li>')
    for t in s.get('measure_ties') or []:
        items.append(f'<li class="src">{_e(t.get("kind"))}, {FUND_VI.get(t.get("fund"), _e(t.get("fund")))} {_e(t.get("section"))}: '
                     f'lệch {round(t.get("diff") or 0):,} → {"KHỚP" if t.get("ok") else "LỆCH"} (không tính vào kết quả)</li>')
    return '<ul>' + (''.join(items) or '<li>Chưa có phép đối chiếu.</li>') + '</ul>'


def _top(s):
    rows = []
    for i, x in enumerate(s.get('top') or [], 1):
        rows.append(f'<tr><td>{i}</td><td>{_e(x.get("fund"))}</td><td>{_e(x.get("code"))}</td><td>{_e(x.get("item"))}</td>'
                    f'{_num_td(x.get("converted"))}{_num_td(x.get("tool_num"))}{_num_td(x.get("diff"))}{_pct_td(x.get("pct"))}'
                    f'<td>{_e(x.get("label"))}{(" <small class=src>" + _e(x.get("remark")) + "</small>") if x.get("remark") else ""}</td></tr>')
    head = ('<tr><th>#</th><th>Quỹ</th><th>Mã</th><th>Hạng mục</th><th class="num">Duyệt (quy đổi)</th><th class="num">Công cụ</th>'
            '<th class="num">Chênh</th><th class="num">%</th><th>Cách công cụ ra số</th></tr>')
    return f'<table>{head}{"".join(rows) or "<tr><td colspan=9>Chưa có dòng.</td></tr>"}</table>'


def _notes(s):
    notes = s.get('notes') or []
    fl = s.get('filled') or {}
    parts = []
    if fl.get('blank'):
        parts.append('Để trống, PM điền: ' + ', '.join(map(str, fl['blank'])) + '.')
    if fl.get('facts'):
        parts.append('Từ dữ kiện trong gói: ' + ', '.join(map(str, fl['facts'])) + '.')
    rows = ''.join(f'<tr><td>{_e(n.get("kind"))}</td><td>{_e(n.get("where"))}</td><td>{_e(n.get("text"))}</td></tr>' for n in notes)
    table = f'<table><tr><th>Loại</th><th>Mã / trường</th><th>Ghi chú</th></tr>{rows}</table>' if notes else ''
    return f'<p class="src">{_e(" ".join(parts)) or "Không có ghi chú nhập."}</p>{table}'


def _files(workdir):
    items = []
    for o in history.outputs_of(workdir):
        rel = os.path.relpath(o['path'], workdir).replace(os.sep, '/')
        items.append(f'<li><a href="{_e(rel)}">{_e(o["title"])}</a> <span class="src">{_e(o["name"])}, {o["size"] / 1e6:.1f} MB</span></li>')
    return '<ul>' + (''.join(items) or '<li>Chưa có file kết quả.</li>') + '</ul>'


def _stop_lines(workdir):
    try:
        with open(os.path.join(workdir, 'run.log'), encoding='utf-8', errors='replace') as fh:
            lines = [ln.rstrip() for ln in fh]
    except OSError:
        return []
    out = []
    for i, ln in enumerate(lines):
        if ln.startswith('STOPPED'):
            out = lines[i:i + 3]
            break
    return out


def render(workdir, project=''):
    """Ghi <workdir>/ket-qua.html từ kết quả của lượt; trả về đường dẫn file."""
    s = results.review_summary(workdir)
    m = s.get('meta') or {}
    name = project or m.get('project') or os.path.basename(workdir)
    py, by = m.get('prior_year') or '', m.get('budget_year') or ''
    stop = _stop_lines(workdir) if s.get('note') else []
    counts = s.get('counts') or {}
    parts = [f'<div class="edge"></div><div class="page"><span class="eyebrow">Budget Agent · gói dự án</span>',
             f'<h1>Ngân sách năm mới cho dự án <b>{_e(name)}</b></h1>',
             f'<p class="src">Lượt {_e(os.path.basename(workdir))}' + (f' · {_e(m.get("ran_at"))}' if m.get('ran_at') else '') +
             f' · nguồn: {_e(m.get("file_name") or "")} · kỳ {_e(m.get("period_text") or "")}. Đơn vị: triệu VND/năm.</p>']
    if s.get('note'):
        parts.append(f'<div class="stop"><b>Lượt chưa ra kết quả.</b> {_e(s["note"])}' +
                     (('<br>' + '<br>'.join(_e(x) for x in stop)) if stop else '') + '</div>')
    parts.append(f'<h2>Ngân sách đã duyệt {_e(py)} so với ngân sách {_e(by)} do công cụ sinh</h2>' + _summary_table(s))
    if counts.get('lines') is not None:
        parts.append(f'<p class="src">Dòng so sánh: {counts.get("lines")} (cả hai có số {counts.get("both")}, chỉ file duyệt '
                     f'{counts.get("only_approved")}, chỉ công cụ {counts.get("only_tool")}); mã không có trên form: '
                     f'{counts.get("not_on_form")}; chưa có phương pháp: {counts.get("no_method")}; công cụ ra 0: {counts.get("tool_zero")}.</p>')
    parts.append('<h2>Đối chiếu tổng</h2>' + _ties(s))
    parts.append('<h2>10 dòng lệch lớn nhất</h2>' + _top(s) +
                 '<p class="src">Toàn bộ các dòng, từng mã, nằm ở sheet "Review" cuối bản phân tích nội bộ.</p>')
    parts.append('<h2>Ghi chú nhập</h2>' + _notes(s))
    parts.append('<h2>File kết quả</h2>' + _files(workdir) +
                 '<p class="src">Điều chỉnh trước khi giao: mở bản giao khách, sheet "4. Điều chỉnh", chọn loại điều chỉnh ở dòng '
                 'tổng của mã rồi sửa ô vàng; dòng tổng, sheet quỹ và 1. Summary tính lại theo công thức.</p></div>')
    doc = (f'<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>Kết quả review · {_e(name)}</title><style>{CSS}</style></head><body>{"".join(parts)}</body></html>')
    path = os.path.join(workdir, FILE_NAME)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(doc)
    return path
