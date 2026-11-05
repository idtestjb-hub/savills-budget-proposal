"""
Dựng thư mục Python chạy độc lập cho gói site (change site-standalone-package, design D2).

    python build_site_runtime.py --out <thư mục python của gói>

Chép từ chính bản Python 3.14 đang chạy lệnh này: python.exe, pythonw.exe, các DLL, thư viện chuẩn (bỏ test, idlelib,
tkinter, turtledemo, ensurepip, bytecode), và chỉ những gói mà hai generator và trang web import: bao đóng Requires-Dist
từ bảy gói gốc (fastapi, uvicorn, python-multipart, itsdangerous, msal, openpyxl, pywin32), mỗi gói chép từ đúng thư mục
nó được cài (site-packages của máy hoặc của người dùng). Phiên bản phải đúng như requirements.txt và
webapp\\requirements.txt; khác là dừng. Không tải gì từ mạng.

Thư mục ra có python314._pth trỏ tới ..\\app\\Budget_Agent\\source_code (bố cục gói, design D1) và bỏ qua site-packages
của người dùng lẫn PYTHONPATH; pywin32.pth thêm win32, win32\\lib, pythonwin; các DLL của pywin32_system32 nằm cạnh
python.exe để pythoncom nạp được mà không cần bước post-install.
"""
import argparse
import importlib.metadata as md
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = ['fastapi', 'uvicorn', 'python-multipart', 'itsdangerous', 'msal', 'openpyxl', 'pywin32']
PRUNE_LIB = {'test', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip', 'site-packages', 'venv', 'lib2to3',
             'pydoc_data', 'unittest/test'}
PRUNE_DLL_PREFIX = ('_tkinter', 'tcl', 'tk', '_test')
IMPORT_CHECK = 'import openpyxl, fastapi, uvicorn, msal, win32com.client, pythoncom, pydantic_core, itsdangerous'
APP_PATH = os.path.join('..', 'app', 'Budget_Agent', 'source_code')


def pinned_versions():
    """{tên gói thường hoá: phiên bản} từ requirements.txt và webapp\\requirements.txt (dòng name==version)."""
    pins = {}
    for name in ('requirements.txt', os.path.join('webapp', 'requirements.txt')):
        with open(os.path.join(HERE, name), encoding='utf-8') as fh:
            for line in fh:
                m = re.match(r'\s*([A-Za-z0-9_.-]+)\s*==\s*([A-Za-z0-9_.]+)', line)
                if m:
                    pins[_norm(m.group(1))] = m.group(2)
    return pins


def _norm(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def closure(names):
    """Các distribution đi tới được từ `names` qua Requires-Dist (bỏ yêu cầu chỉ thuộc một extra)."""
    seen, todo = [], list(names)
    while todo:
        n = todo.pop(0)
        try:
            dist = md.distribution(n)
        except md.PackageNotFoundError:
            if n in names:
                raise SystemExit(f'Thiếu gói {n!r} trên máy dựng: cài đúng requirements.txt trước.')
            continue        # yêu cầu có điều kiện không áp dụng cho 3.14 (ví dụ exceptiongroup cho Python cũ)
        key = dist.metadata['Name']
        if _norm(key) in {_norm(x.metadata['Name']) for x in seen}:
            continue
        seen.append(dist)
        for req in dist.requires or []:
            if 'extra ==' in req:
                continue
            todo.append(re.split(r'[\s;<>=!\[(]', req, maxsplit=1)[0])
    return seen


def _ignore_lib(lib_root):
    def ignore(d, names):
        rel = os.path.relpath(d, lib_root).replace('\\', '/')
        out = set()
        for n in names:
            p = n if rel == '.' else rel + '/' + n
            if n == '__pycache__' or p in PRUNE_LIB or n.endswith('.pyc'):
                out.add(n)
        return out
    return ignore


def build(out):
    src = os.path.dirname(sys.executable)
    if sys.version_info[:2] != (3, 14):
        raise SystemExit(f'Cần chạy bằng Python 3.14 (đang là {sys.version.split()[0]}).')
    pins = pinned_versions()
    dists = closure(TOP)
    bad = [(d.metadata['Name'], d.version, pins[_norm(d.metadata['Name'])]) for d in dists
           if _norm(d.metadata['Name']) in pins and d.version != pins[_norm(d.metadata['Name'])]]
    if bad:
        raise SystemExit('Phiên bản khác requirements: ' + ', '.join(f'{n} {v} (cần {p})' for n, v, p in bad))
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for f in ('python.exe', 'pythonw.exe', 'python3.dll', 'python314.dll', 'vcruntime140.dll', 'vcruntime140_1.dll',
              'LICENSE.txt'):
        p = os.path.join(src, f)
        if os.path.exists(p):
            shutil.copy2(p, out)
    shutil.copytree(os.path.join(src, 'DLLs'), os.path.join(out, 'DLLs'),
                    ignore=lambda d, n: {x for x in n if x.startswith(PRUNE_DLL_PREFIX)})
    lib_root = os.path.join(src, 'Lib')
    shutil.copytree(lib_root, os.path.join(out, 'Lib'), ignore=_ignore_lib(lib_root))
    sp_out = os.path.join(out, 'Lib', 'site-packages')
    os.makedirs(sp_out, exist_ok=True)
    n_files = 0
    for dist in dists:
        root = str(dist.locate_file(''))
        for f in dist.files or []:
            rel = str(f)
            s = os.path.join(root, rel)
            if not os.path.isfile(s) or rel.endswith('.pyc') or '__pycache__' in rel or rel.startswith('..'):
                continue
            d = os.path.join(sp_out, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n_files += 1
        print(f"  {dist.metadata['Name']:22} {dist.version}")
    sys32 = os.path.join(sp_out, 'pywin32_system32')
    if not os.path.isdir(sys32):
        raise SystemExit('pywin32 không có pywin32_system32: cài lại pywin32.')
    for dll in os.listdir(sys32):
        shutil.copy2(os.path.join(sys32, dll), out)
    with open(os.path.join(sp_out, 'pywin32.pth'), 'w', encoding='ascii') as fh:
        fh.write('win32\nwin32' + chr(92) + 'lib\npythonwin\n')
    with open(os.path.join(out, 'python314._pth'), 'w', encoding='ascii') as fh:
        fh.write('python314.zip\nDLLs\nLib\nLib' + chr(92) + 'site-packages\n' + APP_PATH + '\nimport site\n')
    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(out) for f in fs)
    print(f'{len(dists)} gói, {n_files} file từ site-packages; runtime {total / 1e6:.0f} MB tại {out}')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='Dựng thư mục Python chạy độc lập cho gói site.')
    ap.add_argument('--out', required=True, help='thư mục python\\ của gói (bị xoá và dựng lại)')
    a = ap.parse_args(argv)
    build(os.path.abspath(a.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
