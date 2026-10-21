"""
    cd source_code
    python -m webapp

Biến môi trường (đều có mặc định): BUDGET_WEB_HOST (127.0.0.1), BUDGET_WEB_PORT (8090),
BUDGET_WEB_PREFIX (/budget), BUDGET_WEB_RUNS (..\\reports\\web_runs). Chỉ bind đúng host đó.
Log ra stdout/stderr.
"""
import os
import sys

import uvicorn

from webapp import auth
from webapp.server import HOST, PORT, PREFIX, RUNS_DIR, app


def main():
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    missing = auth.missing_settings()
    if missing:
        print('Budget web: KHÔNG khởi động, SSO đang bật (BUDGET_WEB_AUTH=sso) mà thiếu: ' + ', '.join(missing)
              + '. Đặt các biến đó, hoặc BUDGET_WEB_AUTH=off để chạy thử trên máy cá nhân không cần đăng nhập.',
              flush=True)
        sys.exit(2)
    if auth.enabled():
        try:
            auth.client()      # tải cấu hình OpenID của tenant ngay bây giờ: tenant sai thì dừng ở đây, không đợi người dùng bấm
        except Exception as exc:
            print(f'Budget web: KHÔNG khởi động, không tải được cấu hình đăng nhập của tenant '
                  f'{auth.TENANT_ID!r}: {type(exc).__name__}: {exc}', flush=True)
            sys.exit(2)
    os.makedirs(RUNS_DIR, exist_ok=True)
    mode = ('SSO Entra ID, ' + f'{len(auth.allowed_users())} tài khoản được phép, redirect {auth.redirect_uri()}'
            if auth.enabled() else 'KHÔNG đăng nhập (BUDGET_WEB_AUTH=off)')
    print(f'Budget web: http://{HOST}:{PORT}/  (prefix {PREFIX or "/"}; runs: {RUNS_DIR}; {mode})', flush=True)
    uvicorn.run(app, host=HOST, port=PORT, log_level='info')


if __name__ == '__main__':
    main()
