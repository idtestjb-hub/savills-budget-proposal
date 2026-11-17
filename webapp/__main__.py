"""
    cd source_code
    python -m webapp

Biến môi trường (đều có mặc định): BUDGET_WEB_HOST (127.0.0.1), BUDGET_WEB_PORT (8090),
BUDGET_WEB_PREFIX (/budget), BUDGET_WEB_RUNS (..\\reports\\web_runs). Chỉ bind đúng host đó.
Log ra stdout/stderr.

Link ngoài (change budget-web-project-access): đặt BUDGET_WEB_LINK_PORT (ví dụ 8091) để mở thêm cổng thứ hai, cùng host,
chỉ dành cho tunnel Cloudflare. Cần thêm BUDGET_WEB_CF_TEAM, BUDGET_WEB_CF_AUD, BUDGET_WEB_ACCESS_BOOK; thiếu là không
khởi động. Tunnel chỉ được trỏ vào cổng này, không bao giờ vào cổng thường hay cổng của Caddy.
"""
import asyncio
import os
import sys

import uvicorn

from webapp import auth
from webapp.server import ACCESS_BOOK, HOST, LINK_PORT, PORT, PREFIX, RUNS_DIR, access_list, app


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
    missing = auth.missing_link_settings()
    if missing:
        print('Budget web: KHÔNG khởi động, đã đặt BUDGET_WEB_LINK_PORT mà thiếu: ' + ', '.join(missing), flush=True)
        sys.exit(2)
    if LINK_PORT and LINK_PORT == PORT:
        print('Budget web: KHÔNG khởi động, BUDGET_WEB_LINK_PORT phải khác BUDGET_WEB_PORT.', flush=True)
        sys.exit(2)
    os.makedirs(RUNS_DIR, exist_ok=True)
    mode = ('SSO Entra ID, ' + f'{len(auth.allowed_users())} tài khoản được phép, redirect {auth.redirect_uri()}'
            if auth.enabled() else 'KHÔNG đăng nhập (BUDGET_WEB_AUTH=off)')
    print(f'Budget web: http://{HOST}:{PORT}/  (prefix {PREFIX or "/"}; runs: {RUNS_DIR}; {mode})', flush=True)
    if not LINK_PORT:
        uvicorn.run(app, host=HOST, port=PORT, log_level='info')
        return
    acl = access_list()
    print(f'Budget web: link ngoài http://{HOST}:{LINK_PORT}/ (token Cloudflare bắt buộc, team {auth.cf_team_url()}; '
          f'phân quyền {ACCESS_BOOK}: ' + (f'{len(acl.projects)} dự án, {len(acl.people)} email' if acl else
                                           'CHƯA ĐỌC ĐƯỢC, mọi người dùng link bị từ chối') + ')', flush=True)

    async def serve_both():
        servers = [uvicorn.Server(uvicorn.Config(app, host=HOST, port=p, log_level='info')) for p in (PORT, LINK_PORT)]
        await asyncio.gather(*(srv.serve() for srv in servers))

    asyncio.run(serve_both())


if __name__ == '__main__':
    main()
