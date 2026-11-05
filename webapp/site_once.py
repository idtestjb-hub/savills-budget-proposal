"""
Chạy một lượt Review của gói site không cần trang web (change site-standalone-package, design D6).

    python\\python.exe -s app\\Budget_Agent\\source_code\\webapp\\site_once.py [--package <gói>] [--dry-run] [--no-open]

Tạo runs\\<yyyymmdd-hhmmss>_review-<dự án>\\, chép file ngân sách đã duyệt của gói vào prior\\, ghi facts.json từ
site.json, ghi web_meta.json như server (tab Dự án đã tạo của trang web đọc được), chạy review_run.py trong tiến trình
con với log ra run.log, rồi dựng ket-qua.html (static_report) và mở bằng trình duyệt mặc định. --dry-run: chỉ đọc file
ngân sách của gói bằng review_import (không cần Excel, không tạo lượt), dùng cho bước kiểm của build_site_package.py.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(HERE)
DEFAULT_PACKAGE = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)


def _env(pkg):
    tmp = os.path.join(pkg, 'tmp')
    os.makedirs(tmp, exist_ok=True)
    os.environ.update(BUDGET_WEB_AUTH='off', BUDGET_WEB_SITE=os.path.join(pkg, 'site'), TEMP=tmp, TMP=tmp,
                      PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTHONIOENCODING='utf-8')
    os.environ.pop('BUDGET_WEB_LIBRARY_STORE', None)


def read_site(pkg):
    with open(os.path.join(pkg, 'site', 'site.json'), encoding='utf-8') as fh:
        info = json.load(fh)
    prior = os.path.join(pkg, 'site', str(info.get('prior_file') or ''))
    if not info.get('prior_file') or not os.path.isfile(prior):
        raise SystemExit(f"Gói thiếu file ngân sách đã duyệt: {info.get('prior_file')!r} trong {os.path.join(pkg, 'site')}")
    return info, prior


def dry_run(pkg):
    info, prior = read_site(pkg)
    import review_import as ri
    tmp = os.path.join(pkg, 'tmp', 'dry-run')
    os.makedirs(tmp, exist_ok=True)
    try:
        p = ri.read_prior_budget(prior, workdir=tmp)
        print(f"Đọc được: dự án {p.project_name!r}, năm {p.budget_year}, "
              + ', '.join(f"{f} {len(fr.lines)} dòng" for f, fr in p.funds.items()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


def run_once(pkg, open_page=True):
    from webapp import history, server, static_report
    info, prior = read_site(pkg)
    project = str(info.get('project') or os.path.splitext(info['prior_file'])[0])
    run_id = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '_review-' + server._safe(project, 'du-an')
    workdir = os.path.join(pkg, 'runs', run_id)
    os.makedirs(os.path.join(workdir, 'prior'))
    prior_src = os.path.join(workdir, 'prior', server._safe(os.path.splitext(info['prior_file'])[0], 'approved') + '.xlsx')
    shutil.copy2(prior, prior_src)
    facts_path = os.path.join(workdir, 'facts.json')
    with open(facts_path, 'w', encoding='utf-8') as fh:
        json.dump(server._facts_from_form(info.get('facts') or {}), fh, ensure_ascii=False, indent=1)
    started = datetime.datetime.now().isoformat(timespec='seconds')
    source = f"ngân sách đã duyệt của dự án {project} ({info['prior_file']})"
    history.write_meta(workdir, kind='review', project=project, user='chạy một lần', started=started,
                       status='running', source=source, facts=info.get('facts') or {})
    cmd = [sys.executable, '-X', 'utf8', os.path.join(HERE, 'review_run.py'),
           '--prior', prior_src, '--facts', facts_path, '--workdir', workdir]
    print(f'Thư mục chạy: {workdir}')
    print(f'Ngân sách năm ngoái: {source}')
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    with open(os.path.join(workdir, 'run.log'), 'w', encoding='utf-8') as log:
        log.write(f'Thư mục chạy: {workdir}\nNgân sách năm ngoái: {source}\n')
        proc = subprocess.Popen(cmd, cwd=SOURCE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.decode('utf-8', errors='replace').rstrip('\r\n')
            print(line)
            log.write(line + '\n')
        rc = proc.wait()
    outputs = history.outputs_of(workdir)
    summary = server.results.summarize_run(workdir, 'review')
    meta = summary.get('meta') or {}
    ok = rc in (0, 1) and len(outputs) == len(history.OUTPUT_KINDS) and bool(summary.get('summary'))
    history.write_meta(workdir, status='done' if ok else 'failed', rc=rc,
                       finished=datetime.datetime.now().isoformat(timespec='seconds'),
                       project=meta.get('project') or project, budget_year=meta.get('budget_year'),
                       prior_year=meta.get('prior_year'))
    page = static_report.render(workdir, project=meta.get('project') or project)
    print(f'Kết quả: {page} ({"xong" if ok else "chưa ra kết quả, xem run.log"})')
    if open_page:
        os.startfile(page)  # type: ignore[attr-defined]
    return 0 if ok else 2


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', default=DEFAULT_PACKAGE)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-open', action='store_true')
    a = ap.parse_args(argv)
    pkg = os.path.abspath(a.package)
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    _env(pkg)
    os.chdir(SOURCE_DIR)
    if a.dry_run:
        return dry_run(pkg)
    return run_once(pkg, open_page=not a.no_open)


if __name__ == '__main__':
    sys.exit(main())
