"""
Gắn mã dự án cho các lượt chạy có từ trước change budget-web-project-access (chạy một lần trên server).

    python webapp/map_run_codes.py --runs <thư mục runs> --book <file phân quyền .xlsx> --propose <bang-ma.csv>
    python webapp/map_run_codes.py --runs <thư mục runs> --apply <bang-ma.csv>

--propose: ghi bảng CSV (run_id, project, current_code, proposed_code, how) cho mọi lượt chưa có mã: đề xuất mã khi tên
dự án của lượt khớp đúng một dự án (tên hoặc tên khác) trong file phân quyền. Người dùng sửa / duyệt cột proposed_code.
--apply: sao lưu mọi web_meta.json sẽ đổi (thư mục _backup-map-<giờ> cạnh thư mục runs, ngoài runs để không bị coi là
lượt), rồi ghi project_code = proposed_code. Dòng proposed_code trống thì bỏ qua (lượt đó chỉ văn phòng thấy).
Không đổi lượt đã có mã. Không xoá gì.
"""
import argparse
import csv
import datetime
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(HERE)
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from webapp import history, project_access  # noqa: E402

FIELDS = ['run_id', 'project', 'current_code', 'proposed_code', 'how']


def propose(runs_dir, book, out_csv):
    acl = project_access.load(book)
    rows = []
    for e in history.scan(runs_dir):
        current = e.get('project_code') or ''
        if current:
            continue
        code = acl.match(e['project'])
        rows.append(dict(run_id=e['id'], project=e['project'], current_code='', proposed_code=code or '',
                         how='khớp tên' if code else 'không khớp: để trống = chỉ văn phòng thấy'))
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    matched = sum(1 for r in rows if r['proposed_code'])
    print(f'{len(rows)} lượt chưa có mã, đề xuất được {matched}, {len(rows) - matched} để trống -> {out_csv}')
    return rows


def apply(runs_dir, in_csv, book=None):
    acl = project_access.load(book) if book else None
    with open(in_csv, encoding='utf-8-sig', newline='') as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get('proposed_code') or '').strip()]
    backup = os.path.join(os.path.dirname(os.path.abspath(runs_dir)),
                          f'_backup-map-{datetime.datetime.now():%Y%m%d-%H%M%S}')
    done, skipped = 0, []
    for r in rows:
        rid, code = r['run_id'].strip(), r['proposed_code'].strip()
        workdir = os.path.join(runs_dir, rid)
        if not history.RUN_ID_RE.match(rid) or not os.path.isdir(workdir):
            skipped.append(f'{rid}: không có thư mục lượt')
            continue
        if acl is not None and code not in acl.projects:
            skipped.append(f'{rid}: mã {code} không có trong file phân quyền')
            continue
        meta = history.read_meta(workdir)
        if meta.get('project_code'):
            skipped.append(f'{rid}: đã có mã {meta["project_code"]}')
            continue
        src = os.path.join(workdir, history.META_FILE)
        if os.path.isfile(src):
            os.makedirs(os.path.join(backup, rid), exist_ok=True)
            shutil.copy2(src, os.path.join(backup, rid, history.META_FILE))
        history.write_meta(workdir, project_code=code)
        done += 1
    print(f'Đã gắn mã {done} lượt; bỏ qua {len(skipped)}; sao lưu web_meta.json ở {backup if done else "(không cần)"}')
    for s in skipped:
        print('  bỏ qua', s)
    return done, skipped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', required=True)
    ap.add_argument('--book')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--propose')
    g.add_argument('--apply')
    args = ap.parse_args(argv)
    if args.propose:
        if not args.book:
            ap.error('--propose cần --book')
        propose(args.runs, args.book, args.propose)
    else:
        apply(args.runs, args.apply, args.book)


if __name__ == '__main__':
    main()
