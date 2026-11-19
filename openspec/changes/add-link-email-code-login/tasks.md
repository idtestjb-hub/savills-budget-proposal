## 1. Code store and rules

- [x] 1.1 Write `webapp/link_login.py`. Scope:
  - the sqlite store (codes, events, sessions);
  - code issue and check (6 digits, 15 min, one use, 5 wrong attempts, keyed hash);
  - the limits (per email, per IP, whole site);
  - sessions (12 h, hash of the token, CSRF value, logout);
  - the outbox writer (`~$` temp name, then `os.replace` to `otp-<id>.json`).

  Verify with `tests/test_link_login.py`, using an injected clock:
  - expiry at 15 minutes;
  - reuse refused;
  - the 5th wrong attempt voids the code;
  - a new code replaces the old one;
  - each limit;
  - the store holds no clear code or token;
  - the outbox file name holds no email.

## 2. Link port

- [x] 2.1 `auth.py`: add `link_mode()` (`cf`, `otp`, `cf+otp`) and the settings check in `missing_link_settings()`:
  - the CF settings only when the mode includes `cf`;
  - when it includes `otp`: the secret (≥ 32 characters), the outbox and the public URL.

  Verify by unit test for each mode.
- [x] 2.2 `server.py`:
  - the identity order of D1;
  - routes `auth/code/request`, `auth/code/verify`, `auth/code/logout`;
  - the Entra routes return 404 on the link port;
  - the Origin and CSRF middleware on link-port POSTs;
  - `api/me` returns the CSRF value and how the person logged in.

  Verify with route tests on both ports:
  - unknown email gives the same answer;
  - the cookie flags;
  - a POST with no CSRF token or the wrong Origin gets 403 and makes no run folder;
  - logout makes the old cookie fail;
  - a person removed from the workbook is refused;
  - mode `cf` behaves as before (the existing 31 tests still pass);
  - the Hub port is unchanged.
- [ ] 2.3 Pages:
  - `static/login_code.html` (email step, code step, "Gửi lại mã", plain Vietnamese);
  - `index.html` fetch wrapper adding `X-CSRF-Token` on POST;
  - a logout link on the link port.

  Verify by opening both pages in a browser on the client. (Code done 2026-11-19; browser check is part of 4.1.)

## 3. Mail flow

- [ ] 3.1 Build the flow (standard connectors). Steps:
  1. OneDrive for Business "When a file is created" on the outbox folder;
  2. trigger condition: the name ends with `.json`;
  3. read the content, parse the JSON;
  4. "Send an email (V2)" with the subject and body in plain Vietnamese;
  5. delete the file.

  Draft: `webapp/flow/send_code_flow.json` (folder id `__FOLDER_ID__` filled when built). Environment: VN - SVL - IT -
  Vietnam AI, owner and connections = the service account (decided 2026-11-19). Run `preflight_flow`, then one controlled run on a fake address after the user approves it. Read the run history.
- [ ] 3.2 Write the flow's export and set-up steps for the service account into the release note (the flow must run
  on the service account's OneDrive and Outlook connections).

## 4. Hand-over

- [ ] 4.1 End-to-end test on the client with TEST DATA: local outbox, the user requests a code, reads the mail or the
  file, logs in, starts nothing real, logs out.
- [x] 4.2 `python verification/verify.py` and the full test suite pass. (2026-11-19: 1662 passed, 1 xfailed; verify PASS.)
- [ ] 4.3 Commit. Fill `Savills-Automation-Hub-Setup\releases\2026-11-19-budget-web-otp.txt` (settings, flow, order:
  deploy, then the infra session adds the Access bypass for the office IP range).
