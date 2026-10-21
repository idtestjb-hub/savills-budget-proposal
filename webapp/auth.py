"""
Đăng nhập SSO bằng tài khoản Microsoft của Savills (Entra ID, OpenID Connect, authorization code + PKCE qua
thư viện MSAL), chỉ cho những tài khoản có trong danh sách.

Biến môi trường:
  BUDGET_WEB_AUTH            'sso' (mặc định) hoặc 'off' (không đăng nhập, chỉ dùng khi chạy thử trên máy cá nhân)
  BUDGET_WEB_TENANT_ID       tenant Entra ID của Savills
  BUDGET_WEB_CLIENT_ID       Application (client) ID của app registration "PM - Budget Agent web"
  BUDGET_WEB_CLIENT_SECRET   client secret của app registration (chỉ nằm trong biến môi trường, không ghi vào file)
  BUDGET_WEB_PUBLIC_URL      địa chỉ người dùng mở, kể cả tiền tố, ví dụ https://host:8443/budget
                             (Entra chỉ nhận redirect URI https, trừ localhost)
  BUDGET_WEB_ALLOWED_USERS   danh sách email được phép, cách nhau bằng dấu phẩy hoặc dấu chấm phẩy; không phân biệt hoa thường.
                             Trống = không ai vào được (đóng mặc định).
  BUDGET_WEB_SESSION_SECRET  khoá ký cookie phiên; trống = sinh ngẫu nhiên mỗi lần khởi động (mọi người phải đăng nhập lại)

Redirect URI phải khai trong app registration: <BUDGET_WEB_PUBLIC_URL>/auth/callback.
Danh tính lấy từ claim `preferred_username` (UPN) của id_token, và `email` nếu có; một trong hai khớp danh sách là được.
"""
import os
import secrets

AUTH_MODE = (os.environ.get('BUDGET_WEB_AUTH') or 'sso').strip().lower()
TENANT_ID = os.environ.get('BUDGET_WEB_TENANT_ID', '').strip()
CLIENT_ID = os.environ.get('BUDGET_WEB_CLIENT_ID', '').strip()
CLIENT_SECRET = os.environ.get('BUDGET_WEB_CLIENT_SECRET', '').strip()
PUBLIC_URL = os.environ.get('BUDGET_WEB_PUBLIC_URL', '').strip().rstrip('/')
SESSION_SECRET = os.environ.get('BUDGET_WEB_SESSION_SECRET', '').strip() or secrets.token_urlsafe(32)
SCOPES = ['User.Read']          # MSAL tự thêm openid, profile, offline_access
SESSION_HOURS = 8


def enabled():
    return AUTH_MODE != 'off'


def allowed_users(raw=None):
    """Tập email được phép, chữ thường, từ BUDGET_WEB_ALLOWED_USERS (hoặc `raw` khi kiểm thử)."""
    text = os.environ.get('BUDGET_WEB_ALLOWED_USERS', '') if raw is None else raw
    return {p.strip().lower() for p in text.replace(';', ',').split(',') if p.strip()}


def identity_of(claims):
    """(email dùng để đối chiếu, tên hiển thị) từ id_token claims; email None khi không có."""
    candidates = [claims.get('preferred_username'), claims.get('email'), claims.get('upn')]
    emails = [str(c).strip().lower() for c in candidates if c and '@' in str(c)]
    name = claims.get('name') or (emails[0] if emails else '')
    return (emails[0] if emails else None), name, emails


def is_allowed(claims, allowed=None):
    allowed = allowed_users() if allowed is None else allowed
    _, _, emails = identity_of(claims)
    return any(e in allowed for e in emails)


def missing_settings():
    """Tên các biến còn thiếu khi bật SSO; rỗng = đủ."""
    if not enabled():
        return []
    needed = {'BUDGET_WEB_TENANT_ID': TENANT_ID, 'BUDGET_WEB_CLIENT_ID': CLIENT_ID,
              'BUDGET_WEB_CLIENT_SECRET': CLIENT_SECRET, 'BUDGET_WEB_PUBLIC_URL': PUBLIC_URL}
    missing = [k for k, v in needed.items() if not v]
    if PUBLIC_URL and not (PUBLIC_URL.startswith('https://') or PUBLIC_URL.startswith('http://localhost')
                           or PUBLIC_URL.startswith('http://127.0.0.1')):
        missing.append('BUDGET_WEB_PUBLIC_URL (Entra chỉ nhận redirect URI https, trừ localhost)')
    if not allowed_users():
        missing.append('BUDGET_WEB_ALLOWED_USERS (trống = không ai vào được)')
    return missing


def redirect_uri():
    return PUBLIC_URL + '/auth/callback'


def authority():
    return f'https://login.microsoftonline.com/{TENANT_ID}'


_client = None


def client():
    """ConfidentialClientApplication dùng chung; MSAL chỉ được import khi SSO bật, để chế độ off không cần gói."""
    global _client
    if _client is None:
        import msal
        _client = msal.ConfidentialClientApplication(CLIENT_ID, authority=authority(),
                                                     client_credential=CLIENT_SECRET)
    return _client


def begin_login():
    """Khởi tạo auth code flow (PKCE, state, nonce). Trả về dict flow để cất vào phiên; flow['auth_uri'] là nơi chuyển tới."""
    return client().initiate_auth_code_flow(SCOPES, redirect_uri=redirect_uri())


def finish_login(flow, query_params):
    """Đổi code lấy token; trả về claims của id_token hoặc ném ValueError với thông báo tiếng Việt."""
    result = client().acquire_token_by_auth_code_flow(flow, dict(query_params))
    if 'error' in result:
        raise ValueError(f"{result.get('error')}: {result.get('error_description', '')}")
    claims = result.get('id_token_claims') or {}
    if not claims:
        raise ValueError('Microsoft không trả về id_token.')
    return claims


def logout_url():
    return f'{authority()}/oauth2/v2.0/logout?post_logout_redirect_uri={PUBLIC_URL}/'
