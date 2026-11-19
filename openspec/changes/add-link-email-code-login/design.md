## Context

Today the link port (`BUDGET_WEB_LINK_PORT`, 8091) accepts a request only when it carries a valid Cloudflare Access
token (`server.link_email`, `auth.verify_cf_token`). Every request reaches the app from 127.0.0.1, because the tunnel
or `tailscale serve` sits in front of it, so the source IP proves nothing. The app keeps the `/budget` prefix on this
port.

Rules approved by the user on 2026-11-19, in session:
- keep Cloudflare for people outside the office;
- people in the office log in with a mailed code;
- the app accepts either way;
- mail goes out from the service account's mailbox;
- the outbox is in that account's own OneDrive, and the code may sit in the request file;
- codes last 15 minutes;
- sessions last 12 hours, with no extension.

## Goals / Non-Goals

**Goals:**
- An office PM on the access workbook can log in on the link with no Cloudflare step.
- An outside PM keeps logging in through Cloudflare Access.

**Non-goals:**
- No change to the Hub port (8090).
- No change to Entra SSO.
- No change to Cloudflare or the tunnel; the infra session does those after deploy.
- No Premium connector.

## Decisions

**D1. Who the caller is on the link port.** The mode comes from `BUDGET_WEB_LINK_AUTH`: `cf` (the default, today's
behaviour), `otp`, or `cf+otp`. The app checks, in order:
1. If the mode includes `cf` and the request carries a valid Access token, the email comes from the token.
2. Otherwise, if the mode includes `otp` and the `budget_link_session` cookie matches a live session, the email comes
   from the session.
3. Otherwise the caller is anonymous:
   - `GET /` shows the code login page (status 200 for heartbeat; 401 in mode `cf`, as today);
   - every API answers 401.

An invalid token does not refuse the request by itself; the cookie is still checked, then the anonymous rule applies.
The access workbook is consulted on every request, exactly as today, so a person removed from it loses access at once.

**D2. Store.** One sqlite file (`BUDGET_WEB_LINK_DB`, by default `link_login.sqlite` beside the runs folder). WAL mode,
one connection per call, and a module lock around writes. Tables:
- `codes`: one row per email (`email`, `code_hash`, `created`, `expires`, `attempts`);
- `events`: `kind`, `email`, `ip`, `at`, used for the limits, kept 2 days;
- `sessions`: `token_hash`, `email`, `created`, `expires`, `csrf`.

A restart keeps codes and sessions. The file holds no code and no token in clear.

**D3. Secrets and hashes.** `BUDGET_WEB_LINK_SECRET` (environment only, at least 32 characters) is required in the
modes with `otp`.
- Code hash: `HMAC-SHA256(secret, email + '|' + code)`. A 6-digit code hashed without a key could be brute-forced
  from the file.
- Session token: `secrets.token_urlsafe(32)` in the cookie, stored as its SHA-256.
- Every comparison uses `hmac.compare_digest`.

**D4. Code rules.**
- The code is 6 digits from `secrets.randbelow(10**6)`, zero-padded, and lasts 15 minutes.
- A new request replaces the email's previous code.
- A correct code deletes the row: one use only.
- The 5th wrong attempt deletes the row.
- An expired code is deleted when it is read.

**D5. Limits** (constants in `link_login.py`). Requests:
- per email: 3 in 15 minutes and 6 in 1 hour;
- per IP: 20 code requests and 30 code checks in 1 hour;
- whole site: 100 codes sent in 1 hour.

The IP comes from `CF-Connecting-IP`, else `X-Forwarded-For`'s first entry, else the socket. It is best effort, because
any tailnet member can set the header. The site-wide cap is the real guard for the mailbox and the flow quota.
- A request over a limit, or for an email not on the workbook, gets exactly the same 200 answer as a request that
  sent a code, and nothing is written to the outbox.
- A code check over the IP limit gets 429 with a plain message.

**D6. Outbox file.** The file is named `otp-<16 hex>.json`, with no email in the name. Its content is JSON: `to`,
`code`, `minutes`, `valid_until` (local time HH:MM, for the mail text), `sent_by` = "Budget web".
- The app writes `~$otp-<id>.tmp` in the same folder, then renames it with `os.replace` (atomic, same volume).
  OneDrive skips `~$` files.
- The flow's trigger filters on the `.json` ending.
- If the write fails, the person still gets the same answer, and the log records `send-failed` for the office to
  see.

**D7. Cookie.**
- `budget_link_session`: `HttpOnly`, `Secure` always (the browser is on https at Cloudflare even though 8091 is plain
  http), `SameSite=Lax`, `Path` = the prefix (`/budget`), `Max-Age` = 12 h.
- The cookie is set only on the link port and read only on the link port.
- Starlette's signed `budget_web_session` stays as it is, for the Hub's Entra mode.

**D8. CSRF.**
- Every POST on the link port must carry an `Origin` equal to `BUDGET_WEB_LINK_PUBLIC_URL`'s origin. A missing or
  other Origin gets 403.
- Every POST except the two login steps must also carry `X-CSRF-Token`:
  - for a session login it is the session's `csrf` value;
  - for a token login it is `HMAC(secret, 'csrf|' + email)`.
- The page receives the value in `GET /api/me` and adds it to every POST (fetch wrapper in `index.html`).
- The two login steps have no session yet. For them the Origin check and the identical answer stand in for the token.
- The check runs as a middleware on the link port, so no route can skip it.

**D9. Login log.** One line per step through the app's `_log`: `link-login <kind> email=<email> ip=<ip>`. The kinds are
`requested`, `sent`, `unknown`, `limited`, `send-failed`, `ok`, `wrong`, `expired`, `logout`. It never contains a code,
a token or a hash.

**D10. Pages.**
- `static/login_code.html` has two steps in one page: email, then code. Both are plain Vietnamese. The page tells the
  person the mail can take a few minutes, gives the sender's name, and offers "Gửi lại mã".
- The Entra routes `/auth/login`, `/auth/callback` and `/auth/logout` answer 404 on the link port.
- Logout: `POST /auth/code/logout` deletes the session and clears the cookie. A person who logged in through
  Cloudflare is sent to `/cdn-cgi/access/logout`.

## Risks / Trade-offs

- **Mail delay.** The OneDrive trigger polls about every 5 minutes on the Office 365 plan, plus sync and mail time.
  This is the reason for the 15-minute codes, and the page says so.
- **Code at rest.** Deleted outbox files stay in the OneDrive recycle bin. Mitigations:
  - the folder belongs to the service account only;
  - a code is dead after 15 minutes or one use.
- **Cloudflare seats.** Outside users stay on the 50-seat free plan. Office users never touch Access once the bypass
  rule exists.
- **IP limit can be spoofed** inside the tailnet. The site-wide cap and the per-email limits do not depend on the IP.
