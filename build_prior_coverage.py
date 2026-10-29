"""Độ phủ cột năm trước (N-1) của kho ngân sách thật, đo bằng chính bộ đọc của Review (change
add-prior-coverage-to-library-tab).

Đọc mọi file chọn được của kho (webapp.library) bằng review_import.read_prior_budget, với tên dự án của kho như khi web
chạy Review (webapp.review_run.store_names), rồi ghi prior_coverage.csv vào thư mục kho. Mỗi file một dòng: mã file,
năm ngân sách của kho, đọc được hay không, và với từng loại cột của quỹ quản lý vận hành (Duyệt, Thực tế, Dự kiến)
có giữ cột không, có khớp tổng không, kỳ. Không ghi số tiền, tên dự án, tên file hay nội dung lỗi (chỉ tên lớp lỗi).

Chạy từ Budget_Agent/source_code:
    python -B build_prior_coverage.py [--store <thư mục kho>] [--workdir <thư mục tạm>]
"""
import argparse
import csv
import datetime
import gc
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import review_import as ri  # noqa: E402
import review_measures as rm  # noqa: E402
from webapp import library, review_run  # noqa: E402

FILE_NAME = 'prior_coverage.csv'
FUND = 'MF'
COLUMNS = (['file_id', 'budget_year', 'status', 'error_kind', 'n_year'] +
           [f'{k}_{f}' for k in rm.KINDS for f in ('kept', 'tie', 'period')] + ['built_at', 'code_commit'])


def _commit():
    try:
        return subprocess.run(['git', '-C', HERE, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def coverage_row(entry, workdir, other_names):
    """Một dòng của prior_coverage.csv cho một file chọn được (đọc bản chép trong workdir, xoá ngay sau khi đọc)."""
    row = dict(file_id=entry['id'], budget_year=entry['year'] or '', status='ok', error_kind='', n_year='')
    for k in rm.KINDS:
        row.update({f'{k}_kept': 0, f'{k}_tie': 0, f'{k}_period': ''})
    dst = os.path.join(workdir, entry['id'] + '.xlsx')
    try:
        shutil.copy2(library.long_path(entry['path']), dst)
        pr = ri.read_prior_budget(dst, workdir=workdir, other_names=other_names)
        row['n_year'] = pr.n_year or ''
        for k, c in pr.measures.get(FUND, {}).items():
            if k in rm.KINDS and c:
                row.update({f'{k}_kept': 1, f'{k}_tie': int(bool(c.get('tie_ok'))), f'{k}_period': rm.period_text(c)})
    except Exception as exc:  # noqa: BLE001  một file lỗi không dừng cả lượt; chỉ ghi tên lớp lỗi
        row.update(status='error', error_kind=exc.__class__.__name__)
    finally:
        gc.collect()
        for f in os.listdir(workdir):
            fp = os.path.join(workdir, f)
            if os.path.isfile(fp) and not os.path.islink(fp):
                try:
                    os.remove(fp)
                except OSError:
                    pass
    return row


def build(store=None, workdir=None, entries=None, other_names=None, now=None, commit=None):
    """Ghi prior_coverage.csv vào thư mục kho; trả về (đường dẫn, các dòng)."""
    store = store or library.store_dir()
    entries = [e for e in (entries if entries is not None else library.load(coverage=False)) if e['selectable']]
    other_names = review_run.store_names() if other_names is None else other_names
    built_at = (now or datetime.datetime.now()).strftime('%Y-%m-%d %H:%M')
    commit = _commit() if commit is None else commit
    own_tmp = workdir is None
    workdir = workdir or tempfile.mkdtemp(prefix='prior_cov_')
    os.makedirs(workdir, exist_ok=True)
    rows = []
    try:
        for e in entries:
            r = coverage_row(e, workdir, other_names)
            r.update(built_at=built_at, code_commit=commit)
            rows.append(r)
            print(e['id'], r['status'], r['error_kind'], *(r[f'{k}_period'] or '-' for k in rm.KINDS), flush=True)
    finally:
        if own_tmp:
            shutil.rmtree(workdir, ignore_errors=True)
    path = os.path.join(store, FILE_NAME)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
    return path, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--store', default=None, help='thư mục kho (mặc định: BUDGET_WEB_LIBRARY_STORE hoặc final_v4)')
    ap.add_argument('--workdir', default=None, help='thư mục chép tạm từng file (mặc định: thư mục tạm của hệ thống)')
    a = ap.parse_args(argv)
    if a.store:
        os.environ['BUDGET_WEB_LIBRARY_STORE'] = a.store
    path, rows = build(store=a.store, workdir=a.workdir)
    ok = [r for r in rows if r['status'] == 'ok']
    print(f'\n{path}\nfile chọn được: {len(rows)} | đọc được: {len(ok)}')
    for k in rm.KINDS:
        print(f'{k}: {sum(r[f"{k}_kept"] for r in ok)} (khớp tổng {sum(r[f"{k}_tie"] for r in ok)})')
    print('đủ ba cột:', sum(all(r[f'{k}_kept'] for k in rm.KINDS) for r in ok))
    return 0


if __name__ == '__main__':
    sys.exit(main())
