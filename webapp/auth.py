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

Link ngoài qua Cloudflare Access (change budget-web-project-access), chỉ trên cổng BUDGET_WEB_LINK_PORT:
  BUDGET_WEB_CF_TEAM         team domain của Cloudflare Zero Trust, ví dụ "savillsvn" hoặc "savillsvn.cloudflareaccess.com"
  BUDGET_WEB_CF_AUD          AUD tag của Access application trỏ vào link này
Web tự kiểm token Cf-Access-Jwt-Assertion: chữ ký RS256 theo khoá công khai của team (tải từ
https://<team>.cloudflareaccess.com/cdn-cgi/access/certs, nhớ theo kid), aud, iss, hạn dùng. Tiêu đề email trần
(Cf-Access-Authenticated-User-Email) không bao giờ được tin.

Đăng nhập bằng mã qua email trên cổng link (change add-link-email-code-login, webapp/link_login.py):
  BUDGET_WEB_LINK_AUTH       cf (mặc định) | otp | cf+otp
  BUDGET_WEB_LINK_SECRET     khoá HMAC của mã và CSRF, ít nhất 32 ký tự, chỉ nằm trong biến môi trường
  BUDGET_WEB_OTP_OUTBOX      thư mục outbox (OneDrive riêng của tài khoản dịch vụ) mà flow gửi mail theo dõi
  BUDGET_WEB_LINK_PUBLIC_URL địa chỉ người dùng mở link, ví dụ https://power.savills-hub.com.vn (để kiểm Origin)
  BUDGET_WEB_LINK_DB         file sqlite lưu mã / phiên (mặc định link_login.sqlite cạnh thư mục runs)
"""
import os
import secrets
import threading

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


# ---- Cloudflare Access (link ngoài) ---------------------------------------------------------------------------------

CF_TOKEN_HEADER = 'Cf-Access-Jwt-Assertion'
CF_LEEWAY_S = 60


def cf_team_url(raw=None):
    """https://<team>.cloudflareaccess.com từ BUDGET_WEB_CF_TEAM (tên team, tên miền, hoặc URL đầy đủ); '' khi chưa đặt."""
    text = (os.environ.get('BUDGET_WEB_CF_TEAM', '') if raw is None else raw).strip().rstrip('/')
    if not text:
        return ''
    text = text.removeprefix('https://').removeprefix('http://')
    if '.' not in text:
        text += '.cloudflareaccess.com'
    return 'https://' + text


def cf_audience():
    return os.environ.get('BUDGET_WEB_CF_AUD', '').strip()


class CfTokenError(ValueError):
    """Token Cloudflare Access thiếu hoặc không hợp lệ (nội dung chỉ để ghi log, không trả cho trình duyệt)."""


_jwk = {'client': None, 'url': None}
_jwk_lock = threading.Lock()


def _cf_key(token):
    """Khoá công khai đúng kid của token, từ bộ khoá của team (PyJWKClient tự nhớ và tải lại khi gặp kid lạ)."""
    import jwt
    url = cf_team_url() + '/cdn-cgi/access/certs'
    with _jwk_lock:
        if _jwk['client'] is None or _jwk['url'] != url:
            _jwk['client'], _jwk['url'] = jwt.PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=10), url
        client = _jwk['client']
    return client.get_signing_key_from_jwt(token).key


def verify_cf_token(token, get_key=None, team_url=None, audience=None):
    """Email (chữ thường) trong token Cloudflare Access sau khi kiểm chữ ký RS256, aud, iss, exp/nbf. Mọi lỗi ->
    CfTokenError. `get_key`, `team_url`, `audience` chỉ để kiểm thử."""
    import jwt
    team_url = cf_team_url() if team_url is None else team_url
    audience = cf_audience() if audience is None else audience
    if not team_url or not audience:
        raise CfTokenError('BUDGET_WEB_CF_TEAM / BUDGET_WEB_CF_AUD chưa đặt')
    if not token:
        raise CfTokenError('thiếu token Cf-Access-Jwt-Assertion')
    try:
        key = (get_key or _cf_key)(token)
        claims = jwt.decode(token, key=key, algorithms=['RS256'], audience=audience, issuer=team_url,
                            leeway=CF_LEEWAY_S, options={'require': ['exp', 'iat', 'iss', 'aud']})
    except Exception as exc:  # noqa: BLE001 - chữ ký, hạn, aud, iss sai, hoặc không tải được khoá: đều từ chối
        raise CfTokenError(f'{type(exc).__name__}: {exc}') from exc
    email = str(claims.get('email') or '').strip().lower()
    if '@' not in email:
        raise CfTokenError('token không có email (token dịch vụ?)')
    return email


LINK_MODES = ('cf', 'otp', 'cf+otp')


def link_mode(raw=None):
    """Cách đăng nhập trên cổng link (BUDGET_WEB_LINK_AUTH): 'cf' (mặc định, chỉ token Cloudflare Access), 'otp'
    (chỉ mã qua email) hoặc 'cf+otp' (một trong hai). Giá trị lạ -> '' (không khởi động)."""
    text = (os.environ.get('BUDGET_WEB_LINK_AUTH', '') if raw is None else raw).strip().lower().replace(' ', '')
    text = text or 'cf'
    if text == 'otp+cf':
        text = 'cf+otp'
    return text if text in LINK_MODES else ''


def link_uses_cf(mode=None):
    return 'cf' in (link_mode() if mode is None else mode)


def link_uses_otp(mode=None):
    return 'otp' in (link_mode() if mode is None else mode)


def link_public_origin(raw=None):
    """scheme://host[:port] của BUDGET_WEB_LINK_PUBLIC_URL (địa chỉ người dùng mở link); '' khi chưa đặt."""
    from urllib.parse import urlsplit
    text = (os.environ.get('BUDGET_WEB_LINK_PUBLIC_URL', '') if raw is None else raw).strip()
    if not text:
        return ''
    parts = urlsplit(text)
    return f'{parts.scheme}://{parts.netloc}'.lower() if parts.scheme and parts.netloc else ''


def missing_link_settings():
    """Biến còn thiếu khi bật cổng link ngoài (BUDGET_WEB_LINK_PORT); rỗng = đủ."""
    if not os.environ.get('BUDGET_WEB_LINK_PORT', '').strip():
        return []
    mode = link_mode()
    if not mode:
        return ['BUDGET_WEB_LINK_AUTH (chỉ nhận cf, otp hoặc cf+otp)']
    needed = {'BUDGET_WEB_ACCESS_BOOK': os.environ.get('BUDGET_WEB_ACCESS_BOOK', '').strip()}
    if link_uses_cf(mode):
        needed.update({'BUDGET_WEB_CF_TEAM': cf_team_url(), 'BUDGET_WEB_CF_AUD': cf_audience()})
    if link_uses_otp(mode):
        needed.update({'BUDGET_WEB_OTP_OUTBOX': os.environ.get('BUDGET_WEB_OTP_OUTBOX', '').strip(),
                       'BUDGET_WEB_LINK_PUBLIC_URL': link_public_origin()})
        if len(os.environ.get('BUDGET_WEB_LINK_SECRET', '').strip()) < 32:
            needed['BUDGET_WEB_LINK_SECRET (ít nhất 32 ký tự)'] = ''
    return [k for k, v in needed.items() if not v]
