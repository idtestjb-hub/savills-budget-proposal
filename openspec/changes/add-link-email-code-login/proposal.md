## Why

The Budget web's outside link (`power.savills-hub.com.vn/budget/`) logs people in only through Cloudflare Access with
an email PIN. Site PMs in the office cannot use it:
- the PIN mail comes from an outside sender and passes through the mail filter;
- it often arrives after its 10 minutes are up, or the Cloudflare login step is blocked on the office network.

Windows login does not work through the tunnel. Entra sign-in was set aside. The user decided on 2026-11-19 to
keep Cloudflare for people outside the office. Office users instead get a one-time code by email, sent from the
company's service mailbox through a standard Power Automate flow.

## What Changes

- **Two ways in on the link port.** A request with a valid Cloudflare Access token works as today. A request without
  one, for example from the office network once Access bypasses the office's public IP range, gets a code login page
  instead of a 401. A switch `BUDGET_WEB_LINK_AUTH` (`cf`, `otp`, `cf+otp`) chooses the mode. The default `cf` keeps
  today's behaviour. The Hub port (8090) does not change.
- **Email code login.**
  - The person types their email. Only emails on the access workbook's `Nguoi dung` sheet get a code. Everyone sees
    the same "code sent" answer.
  - The code has 6 digits, lasts 15 minutes and works once. Only its keyed hash is stored.
  - Limits apply per code, per email, per IP (best effort) and for the whole site.
- **Mail by file drop.** The web writes a small request file (email + code) into a folder in the service account's
  own OneDrive. A flow with the standard OneDrive trigger sends the mail from the service mailbox, then deletes the
  file.
- **Server-side sessions.**
  - The session lasts 12 hours, with no extension.
  - The cookie (`budget_link_session`) is HttpOnly, Secure and SameSite=Lax.
  - Sessions are stored as hashes in a small sqlite file, so a restart keeps people logged in.
  - Logout deletes the session on the server.
- **CSRF and Origin checks** on every POST made through the link port, whichever way the person logged in.
- **Login log** of each step (requested, sent, accepted, wrong, expired, limited, logout). It never holds a code or a
  token.

## Capabilities

### New Capabilities
- `budget-web-link-login`: the email-code login on the outside link, alongside Cloudflare Access.

### Modified Capabilities
- None in `openspec/specs/`. Change `budget-web-project-access` is applied but not yet archived. Its requirement "The
  outside link proves the person's email" says a request without a token gets 401. In mode `cf+otp` or `otp` it gets
  the code login page instead, and the new capability states this. When that change is archived, its requirement
  gets one sentence pointing at `budget-web-link-login`.

## Impact

- Code: `webapp/auth.py`, new `webapp/link_login.py`, `webapp/server.py`, `webapp/__main__.py`,
  `webapp/static/login_code.html` (new), `webapp/static/index.html` (CSRF header and logout on the link), tests.
- Server settings (set by [Hub]):
  - `BUDGET_WEB_LINK_AUTH=cf+otp`;
  - `BUDGET_WEB_LINK_SECRET` (random, environment variable only);
  - `BUDGET_WEB_OTP_OUTBOX` (the service account's OneDrive folder);
  - `BUDGET_WEB_LINK_PUBLIC_URL=https://power.savills-hub.com.vn`.
- Power Automate: one flow under the service account, using standard connectors only (OneDrive for Business, Office
  365 Outlook).
- Cloudflare (infra session, after deploy): an Access policy that bypasses the office's public IP range for this
  application. External users stay under Access and its 50-seat free limit.
