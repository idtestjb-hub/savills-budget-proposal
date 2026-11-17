"""
Bản chạy ẩn danh cho người dùng dự án trên link ngoài (change budget-web-project-access, design D5).

    python build_scoped_data.py --code P012 --name "Tên dự án" [--name "Tên khác"] [--root <thư mục>] [--prune]

Lượt chạy của người dùng dự án không đọc thư mục data\\ của văn phòng. Nó chạy trên một bản sao của mã nguồn, cùng bố
cục với gói site (app\\Budget_Agent\\source_code, data, reports, app\\input\\template), trong đó data\\ chỉ gồm các file
lượt chạy đọc và mọi tên dự án khác đã thành "Dự án tham chiếu NN" (site_data.build, giữ tên của chính dự án). Số liệu
không đổi nên bản giao giống hệt lượt văn phòng.

Mỗi bản nằm ở <root>\\<mã>\\<dấu>\\, với <dấu> là băm của mã nguồn và các file dữ liệu nguồn: đổi code hay dữ liệu thì
lần chạy sau tự dựng bản mới; `--prune` (và `prune()`) xoá các dấu cũ của mã đó.
"""
import argparse
import hashlib
import os
import shutil
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(HERE)
BASE = os.path.dirname(BUDGET_AGENT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import site_data  # noqa: E402

DATA_DIR = os.path.join(BUDGET_AGENT, 'data')
TEMPLATE = os.path.join(BASE, 'input', 'template', '2027 Resi Budget Form (IT team).xlsx')
INPUT_FORM = os.path.join(BUDGET_AGENT, 'reports', 'Project_Budget_Input.xlsx')
READY = '_ready.txt'
_IGNORE_DIRS = {'tests', 'legacy', 'openspec', 'docs', '__pycache__', '.git', '.pytest_cache'}
_IGNORE = shutil.ignore_patterns(*_IGNORE_DIRS, '*.pyc', '.git*', '*.log', '*.md')
_lock = threading.Lock()


def _source_files():
    for root, dirs, files in os.walk(HERE):
        dirs[:] = sorted(d for d in dirs if d not in _IGNORE_DIRS and not d.startswith('.'))
        for f in sorted(files):
            if f.endswith('.py') or f.endswith('.html') or f.endswith('.txt'):
                yield os.path.join(root, f)


def stamp(code_names=()):
    """Băm 16 ký tự của mã nguồn (đường dẫn, cỡ, mtime), các file data KEEP, mẫu, form nhập và tên của chính dự án."""
    h = hashlib.sha1()
    paths = list(_source_files()) + [os.path.join(DATA_DIR, *rel.split('/')) for rel in site_data.KEEP] + [TEMPLATE, INPUT_FORM]
    for p in paths:
        try:
            st = os.stat(p)
            h.update(f'{os.path.relpath(p, BASE)}|{st.st_size}|{st.st_mtime_ns}\n'.encode('utf-8'))
        except OSError:
            h.update(f'{os.path.relpath(p, BASE)}|missing\n'.encode('utf-8'))
    for n in sorted(code_names):
        h.update(('name:' + n + '\n').encode('utf-8'))
    return h.hexdigest()[:16]


def source_dir(mirror):
    """Thư mục source_code bên trong một bản (nơi chạy run_budget.py / review_run.py)."""
    return os.path.join(mirror, 'app', 'Budget_Agent', 'source_code')


MASTER_LISTS = ('master_list_verified/Dim_Property_Residential.csv', 'master_list_verified/Dim_Property_Commercial.csv')


def master_names(names):
    """Tên trong hai danh sách master trùng với một trong `names` sau khi gấp chữ (bỏ dấu, hoa thường, dấu câu). Các
    tên này được giữ nguyên khi ẩn danh, để dòng master của chính dự án không bị đổi tên dù file phân quyền viết khác
    cách viết trong danh sách master. Không bao giờ thêm tên người dùng gõ trên form."""
    from webapp.project_access import fold
    keys = {fold(n) for n in names if fold(n)}
    found = set()
    for rel in MASTER_LISTS:
        path = os.path.join(DATA_DIR, *rel.split('/'))
        if not os.path.isfile(path):
            continue
        _, header, rows = site_data._read_csv(path)
        if 'Name' in header:
            i = header.index('Name')
            found |= {r[i].strip() for r in rows if i < len(r) and r[i].strip() and fold(r[i]) in keys}
    return sorted(found)


def own_names_for(names):
    """Tên được giữ khi ẩn danh: tên trong file phân quyền + cách viết khớp trong danh sách master."""
    return sorted(set(names) | set(master_names(names)))


def ensure(code, own_names, root, log=print):
    """Đường dẫn bản ẩn danh hiện hành của mã `code` (dựng nếu chưa có). Một lần dựng tại một thời điểm."""
    if not own_names:
        raise ValueError(f'Mã {code!r} không có tên dự án; không dựng được dữ liệu ẩn danh.')
    own_names = own_names_for(own_names)
    mirror = os.path.join(root, code, stamp(own_names))
    with _lock:
        if os.path.isfile(os.path.join(mirror, READY)):
            return mirror
        if os.path.exists(mirror):
            shutil.rmtree(mirror)
        tmp = mirror + '.building'
        if os.path.exists(tmp):
            shutil.rmtree(tmp)
        app = os.path.join(tmp, 'app', 'Budget_Agent')
        shutil.copytree(HERE, os.path.join(app, 'source_code'), ignore=_IGNORE)
        info = site_data.build(DATA_DIR, os.path.join(app, 'data'), own_names=list(own_names))
        os.makedirs(os.path.join(app, 'reports'))
        shutil.copy2(INPUT_FORM, os.path.join(app, 'reports'))
        os.makedirs(os.path.join(tmp, 'app', 'input', 'template'))
        shutil.copy2(TEMPLATE, os.path.join(tmp, 'app', 'input', 'template'))
        with open(os.path.join(tmp, READY), 'w', encoding='utf-8') as fh:
            fh.write(f"{code}\n{len(info['copied'])} files, {len(info['pseudonyms'])} names masked\n")
        os.replace(tmp, mirror)
        log(f'scoped data for {code}: {len(info["copied"])} files, {len(info["pseudonyms"])} other names masked -> {mirror}')
        return mirror


def prune(code, root, keep):
    """Xoá các bản cũ của mã `code`, giữ `keep` (đường dẫn bản hiện hành). Trả về danh sách đã xoá."""
    base = os.path.join(root, code)
    gone = []
    if not os.path.isdir(base):
        return gone
    for name in os.listdir(base):
        path = os.path.join(base, name)
        if os.path.normcase(path) != os.path.normcase(keep) and os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
            gone.append(path)
    return gone


_words = {}


def leak_words_for(code, own_names):
    """Danh sách từ để quét lộ tên (như kiểm tra gói site), nhớ theo mã + dấu dữ liệu."""
    key = (code, stamp(own_names))
    if key not in _words:
        _words.clear()
        _words[key] = site_data.leak_words(DATA_DIR, own_names=list(own_names))
    return _words[key]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', required=True)
    ap.add_argument('--name', action='append', required=True, help='tên của chính dự án (lặp lại cho mỗi tên khác)')
    ap.add_argument('--root', default=os.path.join(BUDGET_AGENT, 'reports', 'scoped'))
    ap.add_argument('--prune', action='store_true')
    args = ap.parse_args(argv)
    mirror = ensure(args.code, args.name, args.root)
    if args.prune:
        for p in prune(args.code, args.root, mirror):
            print('đã xoá bản cũ', p)
    print(mirror)


if __name__ == '__main__':
    main()
