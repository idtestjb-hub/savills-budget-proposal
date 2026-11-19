"""
Đăng nhập bằng mã gửi qua email trên link ngoài (change add-link-email-code-login).

PM gõ email; email có trong sheet "Nguoi dung" của file phân quyền thì nhận một mã 6 chữ số, hết hạn sau 15 phút,
dùng một lần. Mã được gửi bằng cách ghi một file JSON nhỏ vào thư mục outbox (OneDrive riêng của tài khoản dịch vụ);
một flow Power Automate chuẩn đọc file, gửi mail từ hộp thư của tài khoản đó rồi xoá file.

Lưu trữ (sqlite, một file): chỉ có HMAC của mã (khoá BUDGET_WEB_LINK_SECRET) và SHA-256 của token phiên; không bao giờ
có mã hay token ở dạng rõ, kể cả trong log.

Giới hạn (design D5): mỗi email 3 mã / 15 phút và 6 mã / giờ; mỗi IP 20 lần xin mã và 30 lần nhập mã / giờ; toàn site
100 mã / giờ. Xin mã quá giới hạn hoặc email lạ: cùng một câu trả lời, không ghi file.
"""
import datetime
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time

CODE_MINUTES = 15
CODE_DIGITS = 6
MAX_WRONG = 5
SESSION_HOURS = 12
EMAIL_LIMITS = ((15 * 60, 3), (3600, 6))      # (cửa sổ giây, số mã tối đa)
IP_REQUEST_LIMIT = (3600, 20)
IP_CHECK_LIMIT = (3600, 30)
SITE_LIMIT = (3600, 100)
EVENT_KEEP_S = 2 * 24 * 3600
COOKIE_NAME = 'budget_link_session'

# Kết quả xin mã
SENT, UNKNOWN, LIMITED, SEND_FAILED, INVALID = 'sent', 'unknown', 'limited', 'send-failed', 'invalid'
# Kết quả nhập mã
OK, WRONG, EXPIRED, CHECK_LIMITED = 'ok', 'wrong', 'expired', 'limited'

_SCHEMA = """
CREATE TABLE IF NOT EXISTS codes (email TEXT PRIMARY KEY, code_hash TEXT NOT NULL, created REAL NOT NULL,
                                  expires REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS events (kind TEXT NOT NULL, email TEXT, ip TEXT, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS events_kind_at ON events(kind, at);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, created REAL NOT NULL,
                                     expires REAL NOT NULL, csrf TEXT NOT NULL);
"""


def normal_email(text):
    """Email chữ thường, bỏ khoảng trắng; '' khi không giống email."""
    email = str(text or '').strip().lower()
    if not email or len(email) > 254 or ' ' in email or email.count('@') != 1:
        return ''
    local, domain = email.split('@')
    return email if local and '.' in domain else ''


def _sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class Store:
    """Mã, phiên và giới hạn của đăng nhập bằng mã. `clock` chỉ đổi khi kiểm thử."""

    def __init__(self, path, secret, outbox, clock=time.time, log=print):
        if not secret or len(secret) < 32:
            raise ValueError('BUDGET_WEB_LINK_SECRET phải dài ít nhất 32 ký tự.')
        self.path, self.outbox, self.clock, self.log = path, outbox, clock, log
        self._key = secret.encode('utf-8')
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self._db() as db:
            db.executescript(_SCHEMA)

    # ---- nền -----------------------------------------------------------------------------------------------------
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.execute('PRAGMA journal_mode=WAL')
        return _Conn(db)

    def _hmac(self, text):
        return hmac.new(self._key, text.encode('utf-8'), hashlib.sha256).hexdigest()

    def _code_hash(self, email, code):
        return self._hmac(f'code|{email}|{code}')

    def _count(self, db, kind, since, email=None, ip=None):
        sql, args = 'SELECT COUNT(*) FROM events WHERE kind = ? AND at > ?', [kind, since]
        if email is not None:
            sql, args = sql + ' AND email = ?', args + [email]
        if ip is not None:
            sql, args = sql + ' AND ip = ?', args + [ip]
        return db.execute(sql, args).fetchone()[0]

    def _event(self, db, kind, email, ip, now):
        db.execute('INSERT INTO events (kind, email, ip, at) VALUES (?, ?, ?, ?)', (kind, email, ip, now))

    def _say(self, kind, email, ip):
        # Không bao giờ ghi mã, token hay hash vào log.
        self.log(f'link-login {kind} email={email or "-"} ip={ip or "-"}')

    # ---- xin mã --------------------------------------------------------------------------------------------------
    def request_code(self, email, ip, is_listed):
        """Một trong SENT / UNKNOWN / LIMITED / SEND_FAILED / INVALID. Người gọi luôn trả cùng một câu cho mọi kết quả."""
        email = normal_email(email)
        ip = ip or ''
        now = self.clock()
        with self._lock, self._db() as db:
            db.execute('DELETE FROM events WHERE at < ?', (now - EVENT_KEEP_S,))
            if not email:
                self._say(INVALID, '', ip)
                return INVALID
            window, cap = IP_REQUEST_LIMIT
            if ip and self._count(db, 'request', now - window, ip=ip) >= cap:
                self._say(LIMITED, email, ip)
                return LIMITED
            self._event(db, 'request', email, ip, now)
            self._say('requested', email, ip)
            if not is_listed(email):
                self._say(UNKNOWN, email, ip)
                return UNKNOWN
            if any(self._count(db, 'sent', now - w, email=email) >= c for w, c in EMAIL_LIMITS) \
                    or self._count(db, 'sent', now - SITE_LIMIT[0]) >= SITE_LIMIT[1]:
                self._say(LIMITED, email, ip)
                return LIMITED
            code = f'{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}'
            expires = now + CODE_MINUTES * 60
            db.execute('INSERT OR REPLACE INTO codes (email, code_hash, created, expires, attempts) '
                       'VALUES (?, ?, ?, ?, 0)', (email, self._code_hash(email, code), now, expires))
            self._event(db, 'sent', email, ip, now)
        try:
            self._drop(email, code, expires)
        except OSError as exc:
            self.log(f'link-login send-failed email={email} ip={ip or "-"}: {type(exc).__name__}: {exc}')
            return SEND_FAILED
        self._say(SENT, email, ip)
        return SENT

    def _drop(self, email, code, expires):
        """Ghi file yêu cầu gửi mail: tên tạm `~$...tmp` (OneDrive không đồng bộ) rồi đổi tên một lần sang .json."""
        os.makedirs(self.outbox, exist_ok=True)
        name = f'otp-{secrets.token_hex(8)}'
        tmp, final = os.path.join(self.outbox, f'~${name}.tmp'), os.path.join(self.outbox, f'{name}.json')
        body = dict(to=email, code=code, minutes=CODE_MINUTES,
                    valid_until=datetime.datetime.fromtimestamp(expires).strftime('%H:%M'), sent_by='Budget web')
        try:
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(body, fh, ensure_ascii=False)
            os.replace(tmp, final)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return final

    # ---- nhập mã -------------------------------------------------------------------------------------------------
    def verify_code(self, email, code, ip):
        """OK / WRONG / EXPIRED / CHECK_LIMITED. EXPIRED cũng dùng cho mã đã dùng, đã bị huỷ hoặc chưa từng có."""
        email = normal_email(email)
        code = ''.join(ch for ch in str(code or '') if not ch.isspace())
        ip = ip or ''
        now = self.clock()
        with self._lock, self._db() as db:
            window, cap = IP_CHECK_LIMIT
            if ip and self._count(db, 'check', now - window, ip=ip) >= cap:
                self._say('check-limited', email, ip)
                return CHECK_LIMITED
            self._event(db, 'check', email, ip, now)
            row = db.execute('SELECT code_hash, expires, attempts FROM codes WHERE email = ?',
                             (email,)).fetchone() if email else None
            if row is None:
                self._say(EXPIRED, email, ip)
                return EXPIRED
            code_hash, expires, attempts = row
            if now >= expires:
                db.execute('DELETE FROM codes WHERE email = ?', (email,))
                self._say(EXPIRED, email, ip)
                return EXPIRED
            if hmac.compare_digest(code_hash, self._code_hash(email, code)):
                db.execute('DELETE FROM codes WHERE email = ?', (email,))
                self._say(OK, email, ip)
                return OK
            attempts += 1
            if attempts >= MAX_WRONG:
                db.execute('DELETE FROM codes WHERE email = ?', (email,))
            else:
                db.execute('UPDATE codes SET attempts = ? WHERE email = ?', (attempts, email))
            self._say(WRONG, email, ip)
            return WRONG

    # ---- phiên ---------------------------------------------------------------------------------------------------
    def create_session(self, email):
        """(token cho cookie, giá trị CSRF, số giây sống). Token chỉ được lưu dưới dạng SHA-256."""
        email = normal_email(email)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        now = self.clock()
        with self._lock, self._db() as db:
            db.execute('DELETE FROM sessions WHERE expires <= ?', (now,))
            db.execute('INSERT INTO sessions (token_hash, email, created, expires, csrf) VALUES (?, ?, ?, ?, ?)',
                       (_sha256(token), email, now, now + SESSION_HOURS * 3600, csrf))
        return token, csrf, SESSION_HOURS * 3600

    def session(self, token):
        """dict(email, csrf, expires) của phiên còn sống, hoặc None."""
        if not token:
            return None
        with self._db() as db:
            row = db.execute('SELECT email, csrf, expires FROM sessions WHERE token_hash = ?',
                             (_sha256(token),)).fetchone()
        if row is None or self.clock() >= row[2]:
            return None
        return dict(email=row[0], csrf=row[1], expires=row[2])

    def logout(self, token):
        if not token:
            return
        with self._lock, self._db() as db:
            db.execute('DELETE FROM sessions WHERE token_hash = ?', (_sha256(token),))

    def cf_csrf(self, email):
        """Giá trị CSRF cho người đăng nhập qua Cloudflare (không có phiên phía server)."""
        return self._hmac(f'csrf|{normal_email(email)}')


class _Conn:
    """sqlite3.Connection dùng trong `with`, đóng khi ra khỏi khối (kết nối gốc chỉ commit, không đóng)."""

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, *exc):
        self.db.close()
        return False
