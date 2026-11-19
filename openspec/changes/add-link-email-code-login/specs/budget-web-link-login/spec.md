## Purpose

Lets a site PM in the office log in on the Budget web's outside link with a one-time code mailed from the company's
service mailbox, while people outside the office keep logging in through Cloudflare Access.

## ADDED Requirements

### Requirement: The link port accepts a Cloudflare token or an email-code session
In mode `cf+otp`, the link port SHALL accept a request when it carries a valid Cloudflare Access token, or when it
carries a live email-code session. A request with neither SHALL get the code login page on `/`, and 401 with no data on
every other route. In mode `cf` the link port SHALL behave exactly as before this change. The Hub port SHALL not change
in any mode. The Entra login routes SHALL answer 404 on the link port.

#### Scenario: Outside user with a Cloudflare token
- **WHEN** a request on the link port carries a valid token for `pm.a@example.com` and no session cookie
- **THEN** the web treats the request as `pm.a@example.com`

#### Scenario: Office user with no token
- **WHEN** a request for `/api/history` on the link port carries no token and no session cookie
- **THEN** the web answers 401 and returns no project data, and `/` shows the code login page

### Requirement: A code is sent only to an email on the access workbook, with one answer for all
The web SHALL send a code only to an email listed on the access workbook's `Nguoi dung` sheet, matched without regard
to case or spaces. It SHALL send the code to that listed address only. The answer to a code request SHALL be the same in
text and status whether the email is listed, unknown, or over a limit.

#### Scenario: Unknown email
- **WHEN** someone requests a code for `stranger@example.com`, which is not on the workbook
- **THEN** they see the same "code sent" answer as a listed person, and no request file is written

### Requirement: A code has 6 digits, lasts 15 minutes, works once and is stored only as a keyed hash
A code SHALL be 6 random digits and SHALL expire 15 minutes after it is issued. It SHALL work for one login only, and a
new code SHALL replace the email's previous one. The 5th wrong attempt SHALL void it. The server SHALL keep only an HMAC
of the code under a server secret, and SHALL never write the code to its log.

#### Scenario: Expired code
- **WHEN** the right code is entered 16 minutes after it was issued
- **THEN** the login is refused and the person is asked for a new code

#### Scenario: Reused code
- **WHEN** a code that already logged someone in is entered again
- **THEN** the login is refused

#### Scenario: Wrong attempts
- **WHEN** a wrong code is entered 5 times
- **THEN** the right code no longer works

### Requirement: Code requests are limited per email, per IP and for the whole site
The web SHALL send at most 3 codes per email in 15 minutes and 6 in one hour. It SHALL accept at most 20 code requests
and 30 code checks per client IP in one hour. It SHALL send at most 100 codes in one hour across the whole site. A
request over a limit SHALL send nothing and SHALL be logged.

#### Scenario: Fourth request in 15 minutes
- **WHEN** a listed person requests a 4th code within 15 minutes
- **THEN** they see the usual answer and no request file is written

### Requirement: The session cookie is server-side, protected and ends at logout
A login SHALL create a server-side session that lasts 12 hours, with no extension. Its cookie SHALL be HttpOnly, Secure
and SameSite=Lax, with the path set to the web's prefix. Only a hash of the cookie's token SHALL be stored. Logout SHALL
delete the session, so the same cookie no longer works.

#### Scenario: Cookie flags
- **WHEN** a correct code is entered
- **THEN** the response sets `budget_link_session` with HttpOnly, Secure, SameSite=Lax and Max-Age of 12 hours

#### Scenario: Logout
- **WHEN** the person logs out and the old cookie is sent again
- **THEN** the web answers 401

### Requirement: Every POST on the link port is protected against cross-site requests
Every POST on the link port SHALL carry an `Origin` equal to the link's public address. Every POST other than the two
login steps SHALL also carry the CSRF token the page received for the person. A POST that fails either check SHALL get
403 and SHALL change nothing.

#### Scenario: POST without the CSRF token
- **WHEN** a logged-in person's browser sends a POST to start a run without `X-CSRF-Token`
- **THEN** the web answers 403 and no run folder is made

### Requirement: The mail goes out through a request file and a standard flow
The web SHALL write each code to a new JSON file in the outbox folder. The file name SHALL carry no email, and the file
SHALL be written whole before it appears under its final name. A standard Power Automate flow on the service account
SHALL send the mail from the service mailbox and then delete the file.

#### Scenario: Request file
- **WHEN** a listed person requests a code
- **THEN** one `otp-<id>.json` file appears in the outbox holding the address and the code, and its name contains no
  part of the email
