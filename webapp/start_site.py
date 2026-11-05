"""
Khởi động trang web cục bộ của một gói site (change site-standalone-package, design D5).

    python\\python.exe -s app\\Budget_Agent\\source_code\\webapp\\start_site.py [--package <thư mục gói>] [--no-browser]

Thư mục gói mặc định là bốn cấp trên file này (gói\\app\\Budget_Agent\\source_code\\webapp). Đặt biến môi trường cho
server (không đăng nhập, tiền tố /budget, thư mục runs và tmp của gói, BUDGET_WEB_SITE = gói\\site), chọn cổng trống từ
8090, ghi tmp\\port.txt. Nếu một server của chính gói này đang trả lời trên cổng đó thì chỉ mở trình duyệt. Không
thì chạy uvicorn ngay trong tiến trình này và mở trình duyệt khi trang trả lời lần đầu. Đóng cửa sổ console là tắt.
"""
import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PACKAGE = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
PREFIX = '/budget'
FIRST_PORT = 8090


def free_port(start=FIRST_PORT, tries=50):
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise SystemExit(f'Không tìm được cổng trống từ {start} tới {start + tries}.')


def site_answers(port, site_dir, timeout=2):
    """True khi một server của chính gói này (cùng thư mục site) đang trả lời trên `port`."""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{PREFIX}/api/site', timeout=timeout) as r:
            return r.status == 200 and os.environ.get('BUDGET_WEB_SITE') == site_dir
    except Exception:
        return False


def read_port(pkg):
    try:
        with open(os.path.join(pkg, 'tmp', 'port.txt'), encoding='ascii') as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def set_env(pkg):
    site = os.path.join(pkg, 'site')
    tmp = os.path.join(pkg, 'tmp')
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(os.path.join(pkg, 'runs'), exist_ok=True)
    os.environ.update(BUDGET_WEB_AUTH='off', BUDGET_WEB_PREFIX=PREFIX, BUDGET_WEB_HOST='127.0.0.1',
                      BUDGET_WEB_RUNS=os.path.join(pkg, 'runs'), BUDGET_WEB_SITE=site, TEMP=tmp, TMP=tmp,
                      PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTHONIOENCODING='utf-8')
    os.environ.pop('BUDGET_WEB_LIBRARY_STORE', None)
    os.environ.pop('BUDGET_WEB_LIBRARY_ROOT', None)
    return site


def open_when_ready(url, timeout=60):
    for _ in range(timeout * 2):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    webbrowser.open(url)
                    return True
        except Exception:
            continue
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', default=DEFAULT_PACKAGE)
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args(argv)
    pkg = os.path.abspath(a.package)
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    site = set_env(pkg)
    if not os.path.isfile(os.path.join(site, 'site.json')):
        print(f'Gói thiếu site\\site.json tại {site}.')
        return 2
    old = read_port(pkg)
    if old and site_answers(old, site):
        url = f'http://127.0.0.1:{old}{PREFIX}/'
        print(f'Trang đã chạy sẵn: {url}')
        if not a.no_browser:
            webbrowser.open(url)
        return 0
    port = free_port()
    os.environ['BUDGET_WEB_PORT'] = str(port)
    with open(os.path.join(pkg, 'tmp', 'port.txt'), 'w', encoding='ascii') as fh:
        fh.write(str(port))
    url = f'http://127.0.0.1:{port}{PREFIX}/'
    print(f'Budget Agent cho dự án này: {url}')
    print('Đóng cửa sổ này để tắt trang.')
    if not a.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    import uvicorn
    from webapp.server import app     # đọc biến môi trường lúc import: phải đặt trước
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')
    return 0


if __name__ == '__main__':
    sys.exit(main())
