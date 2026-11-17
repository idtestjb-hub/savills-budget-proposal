## Context

- **The web on the Hub.**
  - `webapp/server.py` runs with `BUDGET_WEB_AUTH=off` (setup-budget-web.ps1) behind Caddy and hub-auth.
  - Hub-auth logs people in with Windows Negotiate and passes `X-Hub-User` and `X-Hub-Role` to the web.
  - `role_of()` returns `viewer` only when that header says so. Anything else, including no header, is the full office
    view.
  - Caddy does not run hub-auth for 127.0.0.1, and cloudflared connects from 127.0.0.1. So the tunnel must never point
    at Caddy :8080 or at the web's current port 8090 (see the Hub notes on the earlier Cloudflare attempt).
- **Runs.**
  - Runs live in `C:\Savills-Automation-Hub\data\budget-web\runs\<timestamp>_<tag>`, with `web_meta.json` (kind,
    project, user, status).
  - The project is free text typed on the form. Run IDs are predictable.
- **Library.** The library is the scan store `final_v4` (87 files, 48 project names in `project_map.csv`). The master
  lists (`Dim_Property_Residential/Commercial.csv`) have no project code.
- **Existing masking.** `site_data.py` already builds a masked data folder: `KEEP` files, the `MASK` rules, one
  pseudonym per name grouped by registry key, the project's own names kept. It also has the name scan (`leak_words`,
  `find_leaks`). The City Garden and Sunrise Riverside packages showed that figures equal the office run.
- **Token library.** PyJWT 2.15 and cryptography 50 are already installed as dependencies of `msal`, which
  `webapp/requirements.txt` pins and the site runtime bundles.

## Goals / Non-Goals

**Goals:**
- Closed by default on the link: no valid token, unknown email, or broken list all mean no data.
- One access decision function used by every route, so a new route cannot forget the check.
- Office route and Hub viewer role behave exactly as today.

**Non-Goals:**
- Changing the Cloudflare tunnel, Access policy or hub-access.json. Those are [Hub] session work, on the server.
- Masking inside office users' runs, or rebuilding old runs.
- Per-person audit reports. The server log line per refused request is enough for now.
- Other Hub pages (FTown, Cadena, Billing). This change covers the Budget web only.

## Decisions

### D1. A second listener for the link, token mandatory
`python -m webapp` starts uvicorn on two ports when `BUDGET_WEB_LINK_PORT` is set: the current port (Hub route) and
the link port, both bound to 127.0.0.1. Uvicorn runs both in one process; a small middleware tags each request by
its server port.
- **On the link port:** every request needs a valid `Cf-Access-Jwt-Assertion`. The token is checked for an RS256
  signature (keys from `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`, cached, refreshed when a `kid` is
  unknown), `aud` equal to `BUDGET_WEB_CF_AUD`, `iss` equal to the team URL, and `exp`/`nbf` with a 60-second leeway.
  `X-Hub-*` headers are ignored there.
- **On the Hub port:** the current behaviour is unchanged, and Cloudflare headers are ignored.

*Why not one port that decides by header:* Caddy and cloudflared both arrive from 127.0.0.1. A request that loses
or drops the Cloudflare header would then fall through to the full office view. A separate port fails closed by
construction.
*Why not trust `Cf-Access-Authenticated-User-Email`:* it is a plain header. Cloudflare's own documentation says to
validate the JWT.
*Why not cloudflared's own `access` check alone:* the server session may enable it as well (defence in depth). The
web still checks for itself, so a mistake in the tunnel config does not open data.

### D2. Access list from an Excel workbook on SharePoint (user's choice)
New `webapp/project_access.py` reads the workbook named by `BUDGET_WEB_ACCESS_BOOK` with openpyxl, read-only, values
only. It has two sheets:
- `Du an`: `Ma` (code, for example P012), `Ten` (display), `Ten khac` (other names separated by `;`, used to match
  library `project_name` and old runs);
- `Nguoi dung`: `Email`, `Ma du an` (codes separated by `;`, or `ALL`).

The reader:
- re-reads when the file's mtime changes, checked at most every 60 seconds;
- on any error keeps the last good list and logs the error;
- at start-up with no good list, refuses every link user;
- rejects unknown codes on a person's row, and does not count them as `ALL`.

The default file location is `PM/Project/config/Budget-web-quyen-du-an.xlsx` in the synced library, which the server
reads through its OneDrive sync. The user can still change the path ([Hub] sets the variable).

*Why a workbook, not JSON:* the user's choice, 2026-11-17. PM admins can edit it without the server.
*Trade-off:* OneDrive sync delay, and a half-synced file. The mtime check plus "keep last good" covers both.

### D3. One decision point
`project_access.scope(request) -> Scope(kind, codes, email)`, where kind is `office`, `viewer`, `project` or `none`.
- Every route resolves `scope` through a FastAPI dependency in place of `require_user`.
- Every route that names a run calls `_run_for(scope, run_id)`. It loads the run and returns 404 when
  `scope.kind == 'project'` and the run's code is not in `scope.codes`. Code `none` gets 403 on every data route.
- Lists (history, library) filter through the same predicate.

Tests enumerate the router's routes and assert that each one either takes `scope` or is on a short allow-list
(`/`, the login pages, static files). A route added later without the check fails the test.

### D4. Project code on runs and library rows
- `web_meta.json` gains `project_code`. `start_run` and `start_review` take `project_code` from the form; for a
  project user it must be in `scope.codes`.
- Office users may leave it blank for a brand-new project. The run then shows to office and `ALL` only.
- Library rows get their code by matching the folded `project_name` against `Ten` and `Ten khac`. Rows with no match
  have no code and are hidden from project users.
- Old runs: a one-off script `webapp/map_run_codes.py --propose` writes a CSV (run id, project text, proposed code,
  how matched) for the user to approve. `--apply <csv>` writes `project_code` into each `web_meta.json`, after a backup
  of the meta files. It runs on the server via [Hub].

### D5. Masked data per project for project users' runs (decided at apply: code mirror)
`build_scoped_data.ensure(code, names, root)` lays out one mirror per code and stamp under `BUDGET_WEB_SCOPED_ROOT`
(default `<runs>\..\scoped\<code>\<stamp>`). The layout is the same as a site package: `app\Budget_Agent\source_code`,
`data` and `reports`, plus `app\input\template`.
- `data` is `site_data.build(..., own_names=<Ten + Ten khac>)`.
- The stamp is a hash of the source files, the `KEEP` data files, the template, the input form and the own names.
  When the code or the data changes, the next run builds a fresh mirror, and older stamps of that code are pruned.

The web's worker builds the mirror (only on the first run of that code) before it starts the subprocess. It then runs
the same script (`run_budget.py`, `review_run.py`) from inside the mirror, with the mirror as cwd.

*Why not `BUDGET_AGENT_DATA_DIR`:* about 20 modules build `data\` paths from `BUDGET_AGENT` or `HERE\..`. Changing
all of them is wide and easy to miss one. The mirror is the layout the site packages already proved gives the office
figures. It costs about 3 MB of code plus the masked data per code.

### D6. What a project user receives
- `visible_outputs` gains a `project` role equal to the viewer's file set (deliverable, PDF A4/A3) plus the roster.
- `visible_log` uses the viewer filter.
- Before `FileResponse`, and before returning log lines, `leak_check(path or text, scope)` runs `site_data.find_leaks`
  with the word list from `leak_words(own_names=<project names>)`.
  - The word list is built once per code and data stamp, and cached.
  - Excel files are scanned once per file and the result is cached by path and mtime.
  - A hit returns 409 with "File này cần văn phòng kiểm tra trước khi tải" and logs the run, file and words.
- Names that already stand in the standard 2027 template are left out of the word list. This is the same exemption as
  the site-package check, where the template notes are reported apart. The template is Savills' own form, every PM has
  it, and every deliverable is built on it, so counting those notes would block every download. Measured on
  2026-11-17: 4 of the 169 words are in the template.
- Log lines with a hit are dropped from what a project user sees, and the server log records it.

### D7. Front end
- `index.html` reads `api/me`, which returns kind, codes with display names, and email. Not part of the spec, the page
  needs it.
- For project users the page:
  - hides the Kho ngân sách tab;
  - replaces the project name box with a picker of their codes;
  - hides the analysis link.

  Office users get the picker plus a "Dự án mới" free-text option.

## Risks / Trade-offs

- [Hub route still trusts headers from 127.0.0.1] → Unchanged by this change, and out of scope. It is recorded in the
  release note so [Hub] keeps the web bound to 127.0.0.1 and never points the tunnel at it.
- [Workbook typo locks a PM out] → The log says which row was rejected, and the page tells the person to contact the
  office.
- [Library names that match no project] → Hidden from project users (fail closed). The mapping report lists them so the
  user can add `Ten khac`.
- [Masked run differs from office run] → Verify task: same input, office versus masked, 0 figure differences, as for
  the packages.
- [Leak scan false positives on short or common words] → The same word list as the package check (≥4 characters, own
  names removed). A hit blocks the download but never alters the file.
- [Cloudflare key fetch needs outbound HTTPS from the server] → The keys are cached. If the fetch fails, the link is
  refused (fail closed), and the Hub route is unaffected.

- [Measured 2026-11-17 on the City Garden Review, with the name typed in lower case]
  - The fund sheets are identical and `review_summary` is equal.
  - 50 cells differ, all of them text or layout:
    - the own project's street address on `0. Info`: the masked data blanks addresses, as in a site package;
    - the `Comparison` sheet: the reference names are pseudonyms, and one row is shifted.

  → Mitigation: the Review page prefills the street from the master for the user's own project. The master spelling
  of the own name is kept (`own_names_for`), and a run whose name matches no master row says so in its log.

## Migration Plan

1. Build and verify on the client: unit tests, the route-coverage test, the masked-equals-office run, and the
   acceptance check (a P012 user against every route with P020 ids gets 404/403, and the leak scan finds nothing in
   what that user sees).
2. User fills the access workbook (projects + people) and approves the old-run code mapping.
3. Release note stacked after the pending budget-web notes of 16/11 and 17/11. [Hub] deploys it, sets
   `BUDGET_WEB_LINK_PORT`, `BUDGET_WEB_CF_TEAM`, `BUDGET_WEB_CF_AUD` and `BUDGET_WEB_ACCESS_BOOK`, runs
   `map_run_codes.py --apply`, then points the tunnel at the link port only.
4. Rollback: unset `BUDGET_WEB_LINK_PORT` (the link port closes, the Hub route is as before) and redeploy the previous
   release. The `project_code` field in `web_meta.json` is ignored by older code.

## Open Questions

- The exact Cloudflare team domain and AUD tag come from the server session. They are settings only.
- Whether the server already sees `PM/Project/config/` through OneDrive. [Hub] checks this at deploy; the path is a
  setting.
