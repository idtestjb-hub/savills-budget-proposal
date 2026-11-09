"""
Đóng một gói chạy độc lập cho một site (change site-standalone-package, design D1, D3, D7, D8).

    python build_site_package.py --site "<tên dự án>" --prior <file .xlsx đã duyệt> --city "Hồ Chí Minh"
                                 --runtime <thư mục python đã dựng bằng build_site_runtime.py>
                                 --out <thư mục chứa gói> [--library-id <id kho>] [--facts <json>] [--zip] [--check]

Gói ra: <out>\\BudgetAgent-<site>\\ với python\\ (chép từ --runtime), app\\Budget_Agent\\source_code (không tests, legacy,
openspec, docs, bytecode), app\\Budget_Agent\\data, app\\Budget_Agent\\reports\\Project_Budget_Input.xlsx,
app\\input\\template\\<form 2027>, site\\site.json + file đã duyệt, runs\\, tmp\\, launcher .cmd, HUONG-DAN.txt,
và trang sơ đồ hệ thống (docs\\so-do-he-thong-budget-agent.html của repo ngoài, tự chứa) khi file đó có.
Dữ kiện mục 2: --facts (JSON {city, district, tower_count, ...}) hoặc điền sẵn từ kho khi có --library-id (lượt trước
cùng dự án, sheet 0. Info, danh sách master); --city ghi đè / bổ sung Tỉnh / thành phố (bắt buộc để chạy).
--check: python trong gói import đủ module, đọc được file đã duyệt bằng review_import, quét gói không chứa tên
người dùng, tên máy, đường dẫn máy dựng hay tên công cụ AI. --zip: nén gói thành <out>\\BudgetAgent-<site>.zip;
--zip luôn chạy bước kiểm của --check và không nén khi kiểm không đạt.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import site_data  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(HERE)
BASE = os.path.dirname(BUDGET_AGENT)
TEMPLATE = os.path.join(BASE, 'input', 'template', '2027 Resi Budget Form (IT team).xlsx')
INPUT_FORM = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx')
# Trang sơ đồ hệ thống (kiến trúc, dữ liệu, luồng chạy), tự chứa, mở bằng trình duyệt; đi kèm gói (người dùng 09/11/2026).
DIAGRAM = os.path.join(BASE, 'docs', 'so-do-he-thong-budget-agent.html')
DIAGRAM_NAME = 'So do he thong Budget Agent.html'
# Không mang sang site: test, mã cũ, OpenSpec, tài liệu (.md có đường dẫn máy văn phòng), bytecode, và chính hai script
# dựng gói (chỉ chạy ở máy văn phòng).
SOURCE_IGNORE = shutil.ignore_patterns('tests', 'legacy', 'openspec', 'docs', '__pycache__', '*.pyc', '.git*',
                                       '.pytest_cache', '*.log', '*.md', 'build_site_*.py',
                                       # Script dựng dữ liệu / nghiên cứu: chỉ chạy ở máy văn phòng, có tên dự án
                                       # thật trong chú thích (change site-data-isolation).
                                       'build_master_rate_card.py', 'build_project_plan_v2.py', 'build_real_budget_ranges.py',
                                       'build_service_levels.py', 'build_prior_coverage.py', 'build_roster_input_form.py',
                                       'rescan_*.py', 'etl_*.py', 'derive_*.py', 'study_*.py', 'transform_*.py',
                                       'extract_info_sheets.py', 'method_coverage.py',
                                       # Change reference-projects-by-key: the registry builder and the one-off
                                       # migration spell the names on purpose; the end-to-end demo is office-only.
                                       'migrate_*.py', 'build_reference_registry.py', 'generate_from_real_project.py',
                                       # Change widen-utility-and-capex-sources: the usage-table builder reads the store.
                                       'build_utility_usage.py')
DATA_IGNORE = shutil.ignore_patterns('__pycache__', '*.backup-*', '*.bak')
IMPORT_CHECK = 'import openpyxl, fastapi, uvicorn, msal, win32com.client, pythoncom, pydantic_core, itsdangerous'
TEXT_EXT = {'.py', '.txt', '.md', '.json', '.html', '.cmd', '.csv', '.pth', '._pth'}
AI_WORDS = ('claude', 'anthropic')

LAUNCH_WEB = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONNOUSERSITE=1
set PYTHONDONTWRITEBYTECODE=1
title Budget Agent - {site}
echo Dang khoi dong trang Budget Agent cho du an {site} ...
"%~dp0python\\python.exe" -s "%~dp0app\\Budget_Agent\\source_code\\webapp\\start_site.py"
echo.
echo Trang da tat. Nhan phim bat ky de dong cua so.
pause >nul
"""

READ_CHECK = """
import os, shutil, sys
sys.path.insert(0, os.path.join('app', 'Budget_Agent', 'source_code'))
import json
import review_import as ri
info = json.load(open(os.path.join('site', 'site.json'), encoding='utf-8'))
tmp = os.path.join('tmp', 'check')
os.makedirs(tmp, exist_ok=True)
try:
    p = ri.read_prior_budget(os.path.join('site', info['prior_file']), workdir=tmp)
    print('Đọc được: dự án %r, năm %s, ' % (p.project_name, p.budget_year)
          + ', '.join('%s %d dòng' % (f, len(fr.lines)) for f, fr in p.funds.items()))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
"""

GUIDE = """BUDGET AGENT - GÓI CHẠY RIÊNG CHO DỰ ÁN {site}
Bản mã {code} · đóng gói {built}

Gói này lập ngân sách năm mới cho dự án từ ngân sách đã duyệt năm ngoái (file trong thư mục site\\). Máy cần có
Microsoft Excel. Không cần cài Python hay phần mềm nào khác.

1. Giải nén cả thư mục này ra ổ C, ví dụ C:\\BudgetAgent\\ (không chạy trong file zip, không đặt trong OneDrive).
2. Bấm đúp "Chay Budget Agent.cmd". Một cửa sổ đen mở ra, rồi trình duyệt mở trang Review của dự án.
   - Kiểm tra mục 2 (dữ kiện file ngân sách không có), rồi bấm "Tạo ngân sách năm mới". Khoảng 1-2 phút.
   - Kết quả, bảng điều chỉnh và nút tải file hiện ngay bên dưới. Tab "Dự án đã tạo" giữ các lượt đã chạy.
   - Đóng cửa sổ đen là tắt trang. Bấm đúp lại để mở tiếp.
3. Mọi lượt nằm trong runs\\<ngày-giờ>_review-<dự án>\\run\\. Trên trang tải bản giao khách và lịch trực.
4. Có file duyệt mới hơn: trên trang chọn "Tải file lên" và chọn file .xlsx đó.
5. Sơ đồ hệ thống, dữ liệu và luồng chạy: bấm đúp "So do he thong Budget Agent.html" (mở bằng trình duyệt, không cần mạng).

Khi Windows hỏi có chạy file không: chọn Run / Chạy. Nếu máy chặn hẳn, nhờ IT cho phép thư mục C:\\BudgetAgent\\.
Lỗi thì gửi về văn phòng thư mục runs\\<lượt>\\ (file run.log, review_error.txt nếu có) kèm bản mã ở trên.
"""


def _safe(name, fallback='site'):
    return (re.sub(r'[^A-Za-z0-9]+', '-', str(name)).strip('-') or fallback)[:40]


def git_hash():
    try:
        return subprocess.run(['git', '-C', HERE, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                              timeout=10).stdout.strip() or 'n/a'
    except (OSError, subprocess.SubprocessError):
        return 'n/a'


def facts_for(library_id, facts_file, city):
    """Dữ kiện mục 2 (khoá của trang: city, district, tower_count, ...): từ kho (library_id) rồi file JSON rồi --city."""
    raw = {}
    if library_id:
        from webapp import facts_prefill, history, library
        e = library.find(library_id)
        if e is None:
            raise SystemExit(f'Không có dòng {library_id!r} trong kho (BUDGET_WEB_LIBRARY_STORE).')
        pf = facts_prefill.prefill(dict(e, path=library.long_path(e['path']) if e.get('selectable') else ''),
                                   history.scan(os.path.join(BUDGET_AGENT, 'reports', 'web_runs')))
        raw = {k: v.get('value') for k, v in pf['fields'].items() if v.get('value') not in (None, '')}
    if facts_file:
        with open(facts_file, encoding='utf-8') as fh:
            raw.update({k: v for k, v in json.load(fh).items() if v not in (None, '')})
    if city:
        raw['city'] = city
    return raw


def copy_tree(src, dst, ignore=None):
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)


def _rmtree(path, tries=5):
    """Xoá thư mục; bỏ cờ chỉ đọc (file chép từ SharePoint hay mang cờ đó) và thử lại vài lần vì phần mềm quét /
    Explorer có thể giữ một thư mục con trong giây lát."""
    import stat
    import time

    def onexc(func, p, exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    for i in range(tries):
        try:
            shutil.rmtree(path, onexc=onexc)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(1.5)


def build(site, prior, runtime, out, facts, store_id='', library_id=''):
    pkg = os.path.join(out, 'BudgetAgent-' + _safe(site))
    if os.path.exists(pkg):
        _rmtree(pkg)
    os.makedirs(pkg)
    print(f'Gói: {pkg}')
    copy_tree(runtime, os.path.join(pkg, 'python'))
    app = os.path.join(pkg, 'app', 'Budget_Agent')
    copy_tree(HERE, os.path.join(app, 'source_code'), SOURCE_IGNORE)
    # Dữ liệu: chỉ các file lượt Review đọc, tên dự án khác ẩn danh (site_data, change site-data-isolation).
    sd = site_data.build(os.path.join(BUDGET_AGENT, 'data'), os.path.join(app, 'data'), own_names=[site])
    print(f"dữ liệu: {len(sd['copied'])} file, {len(sd['pseudonyms'])} tên dự án khác đã ẩn danh, "
          f"cột văn bản xoá ở {len(sd['masked'])} file")
    os.makedirs(os.path.join(app, 'reports'))
    shutil.copy2(INPUT_FORM, os.path.join(app, 'reports'))
    os.makedirs(os.path.join(pkg, 'app', 'input', 'template'))
    shutil.copy2(TEMPLATE, os.path.join(pkg, 'app', 'input', 'template'))
    site_dir = os.path.join(pkg, 'site')
    os.makedirs(site_dir)
    prior_name = os.path.basename(prior)
    shutil.copy2(prior, os.path.join(site_dir, prior_name))
    code = git_hash()
    built = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(os.path.join(site_dir, 'site.json'), 'w', encoding='utf-8') as fh:
        json.dump(dict(project=site, prior_file=prior_name, facts=facts, store_id=store_id or library_id or '',
                       built_at=built, code=code), fh, ensure_ascii=False, indent=1)
    for d in ('runs', 'tmp'):
        os.makedirs(os.path.join(pkg, d))
    with open(os.path.join(pkg, 'Chay Budget Agent.cmd'), 'w', encoding='utf-8') as fh:
        fh.write(LAUNCH_WEB.format(site=_safe(site)))
    with open(os.path.join(pkg, 'HUONG-DAN.txt'), 'w', encoding='utf-8-sig') as fh:
        fh.write(GUIDE.format(site=site, code=code, built=built))
    if os.path.isfile(DIAGRAM):
        shutil.copy2(DIAGRAM, os.path.join(pkg, DIAGRAM_NAME))
    else:
        print(f'Chú ý: không có trang sơ đồ {DIAGRAM}; gói không kèm sơ đồ.')
    return pkg


def _size(path):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(path) for f in fs)


def scan_text(pkg, extra_words=()):
    """Những file văn bản của gói chứa tên người dùng, tên máy, đường dẫn máy dựng hoặc tên công cụ AI."""
    words = [w for w in (os.environ.get('USERNAME', ''), os.environ.get('COMPUTERNAME', ''), BASE) if w]
    words += list(extra_words)
    hits = []
    for d, dirs, files in os.walk(pkg):
        if os.path.basename(d) in ('python', 'Lib', 'DLLs') and os.path.relpath(d, pkg).startswith('python'):
            dirs[:] = []          # runtime: thư viện chuẩn và gói pip, không quét
            continue
        for f in files:
            p = os.path.join(d, f)
            if os.path.splitext(f)[1].lower() not in TEXT_EXT:
                continue
            try:
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    text = fh.read()
            except OSError:
                continue
            low = text.lower()
            found = [w for w in words if w.lower() in low] + [w for w in AI_WORDS if w in low]
            if found:
                hits.append((os.path.relpath(p, pkg), sorted(set(found))))
    return hits


def check(pkg, leak_words=None):
    py = os.path.join(pkg, 'python', 'python.exe')
    env = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    r = subprocess.run([py, '-s', '-c', IMPORT_CHECK], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env, cwd=pkg)
    print('import:', 'OK' if r.returncode == 0 else 'LỖI ' + (r.stderr or r.stdout)[-400:])
    r2 = subprocess.run([py, '-s', '-X', 'utf8', '-c', READ_CHECK], capture_output=True, text=True,
                        encoding='utf-8', errors='replace', env=env, cwd=pkg)
    print('đọc file đã duyệt:', 'OK ' + r2.stdout.strip() if r2.returncode == 0 else 'LỖI ' + (r2.stderr or r2.stdout)[-400:])
    hits = scan_text(pkg)
    print('quét văn bản:', 'sạch' if not hits else 'CÓ ' + '; '.join(f'{p}: {w}' for p, w in hits[:10]))
    found = site_data.find_leaks(pkg, leak_words) if leak_words else []
    # Form chuẩn 2027 là biểu mẫu của đội PM (mọi PM đều có); ghi chú trong đó nhắc vài dự án: báo riêng, không tính là rò rỉ.
    tpl = os.path.join('app', 'input', 'template')
    leaks = [h for h in found if not h[0].startswith(tpl)]
    in_tpl = [h for h in found if h[0].startswith(tpl)]
    print(f'quét tên dự án khác ({len(leak_words or [])} tên):', 'sạch' if not leaks else
          'CÓ ' + '; '.join(f'{p}: {w}' for p, w in leaks[:40]))
    if in_tpl:
        print('  ghi chú sẵn trong form chuẩn (không tính):', '; '.join(f'{p}: {w}' for p, w in in_tpl))
    for d in ('python', 'app', 'site'):
        print(f'  {d:7} {_size(os.path.join(pkg, d)) / 1e6:7.1f} MB')
    print(f'  {"tổng":7} {_size(pkg) / 1e6:7.1f} MB')
    return r.returncode == 0 and r2.returncode == 0 and not hits and not leaks


def make_zip(pkg):
    zpath = pkg + '.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for d, _, files in os.walk(pkg):
            for f in files:
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, os.path.dirname(pkg)))
    print(f'Zip: {zpath} ({os.path.getsize(zpath) / 1e6:.0f} MB)')
    return zpath


DEFAULT_STORE = os.path.join(os.environ.get('USERPROFILE', ''), 'Savills-local', 'budget-agent', 'scan-2026-10-07', 'final_v4')


def _leak_words(site, store):
    """Tên không được có trong gói (site_data.leak_words): danh sách master + tên file kho quét, trừ chính dự án."""
    return site_data.leak_words(os.path.join(BUDGET_AGENT, 'data'), own_names=[site] if site else (),
                                store_dir=store if store and os.path.isdir(store) else None)


def _site_name(pkg):
    try:
        with open(os.path.join(pkg, 'site', 'site.json'), encoding='utf-8') as fh:
            return json.load(fh).get('project', '')
    except (OSError, ValueError):
        return ''


def main(argv=None):
    ap = argparse.ArgumentParser(description='Đóng một gói chạy độc lập cho một site.')
    ap.add_argument('--site', help='tên dự án (hiện trên trang và trong tên gói)')
    ap.add_argument('--prior', help='file .xlsx ngân sách đã duyệt năm ngoái của dự án')
    ap.add_argument('--runtime', help='thư mục python đã dựng bằng build_site_runtime.py')
    ap.add_argument('--out', help='thư mục chứa gói (ngoài SharePoint)')
    ap.add_argument('--check-only', default='', help='chỉ kiểm một gói đã dựng (đường dẫn gói)')
    ap.add_argument('--city', default='', help='Tỉnh / thành phố (bắt buộc để chạy; ghi đè dữ kiện khác)')
    ap.add_argument('--library-id', default='', help='id dòng kho để điền sẵn dữ kiện')
    ap.add_argument('--facts', default='', help='file JSON dữ kiện {city, district, tower_count, ...}')
    ap.add_argument('--store', default=DEFAULT_STORE, help='thư mục kho quét (dim_file.csv) để lấy tên file cho bước quét rò rỉ')
    ap.add_argument('--zip', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    if a.check_only:
        pkg = os.path.abspath(a.check_only)
        return 0 if check(pkg, _leak_words(_site_name(pkg), a.store)) else 1
    if not all((a.site, a.prior, a.runtime, a.out)):
        raise SystemExit('Cần --site, --prior, --runtime và --out (hoặc --check-only <gói>).')
    if not os.path.isfile(a.prior) or not a.prior.lower().endswith('.xlsx'):
        raise SystemExit(f'--prior phải là file .xlsx có thật: {a.prior}')
    if not os.path.isfile(os.path.join(a.runtime, 'python.exe')):
        raise SystemExit(f'--runtime không có python.exe: {a.runtime}')
    facts = facts_for(a.library_id, a.facts, a.city)
    if not facts.get('city'):
        print('Chú ý: chưa có Tỉnh / thành phố; PM phải chọn trên trang trước khi chạy.')
    pkg = build(a.site, os.path.abspath(a.prior), os.path.abspath(a.runtime), os.path.abspath(a.out), facts,
                library_id=a.library_id)
    # --zip luôn kiểm trước (kể cả khi quên --check); kiểm không đạt thì không nén, để gói rò rỉ không ra được file gửi đi.
    ok = check(pkg, _leak_words(a.site, a.store)) if (a.check or a.zip) else True
    if a.zip:
        if ok:
            make_zip(pkg)
        else:
            zpath = pkg + '.zip'
            print('KHÔNG nén: bước kiểm không đạt (xem các dòng LỖI / CÓ ở trên). Sửa rồi dựng lại.')
            if os.path.exists(zpath):
                print(f'Chú ý: {zpath} là file zip của lần dựng trước, không phải gói vừa dựng.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
