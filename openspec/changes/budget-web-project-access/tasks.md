## 1. Access list

- [x] 1.1 Create the access workbook template `PM/Project/config/Budget-web-quyen-du-an.xlsx`, with sheets `Du an` (Ma, Ten, Ten khac) and `Nguoi dung` (Email, Ma du an). Fill it with TEST DATA rows only, and keep a dated backup if a file already exists. Verify it opens in Excel COM with no repair prompt.
- [x] 1.2 Write `webapp/project_access.py`: read the workbook (values only), fold emails, split codes on `;`, recognise `ALL`, reject unknown codes, reload on mtime change at most every 60 s, keep the last good list on error, and refuse everyone when no list was ever read. Verify with `tests/test_project_access.py` (one-project person, ALL, unknown email, bad code, broken workbook keeps the previous list, no list at start).
- [x] 1.3 Write a project-name matcher (folded `Ten` + `Ten khac`) shared by library rows and old runs. Verify by unit test on fictional names, including one with Vietnamese accents and one with no match.

## 2. Proving the email on the link

- [x] 2.1 Add Cloudflare Access token verification to `webapp/auth.py`: RS256, keys from the team certs URL cached by `kid` (re-fetched on an unknown `kid`), `aud` = `BUDGET_WEB_CF_AUD`, `iss` = team URL, exp/nbf with 60 s leeway. Pin PyJWT and cryptography in `webapp/requirements.txt` at the installed versions. Verify with tests signing tokens with a local test key: valid, wrong key, wrong aud, expired, header email without token.
- [x] 2.2 Let `python -m webapp` listen on `BUDGET_WEB_LINK_PORT` as well as the current port (both on 127.0.0.1), and tag each request with the port it came in on. On the link port, require a valid token and ignore `X-Hub-*`; on the Hub port ignore Cloudflare headers. Verify with a test client on both ports: no token gives 401, and the Hub port behaves exactly as before.

## 3. One access decision on every route

- [x] 3.1 Add the `scope` dependency (`office`, `viewer`, `project`, `none`) and `_run_for(scope, run_id)`, which returns 404 for another project's run and 403 for kind `none`. Switch every data route to it. Verify with a test that enumerates the router's routes and fails on any route that neither takes `scope` nor is on the short allow-list.
- [x] 3.2 Filter `api/history`, `api/library` and `api/library/{id}/facts` by the person's codes. Make `api/library/overview` answer 404 for project users. Verify with route tests: a P012 user sees only P012 rows.
- [x] 3.3 Record `project_code` in `web_meta.json` from the form in `start_run` and `start_review`. Refuse with 403 a code outside the person's codes, and refuse a `source_run` of another project with 404, in both cases before any run folder is made. Verify with route tests that check that no folder was created.
- [x] 3.4 Add `api/me` (kind, codes with display names, email). Verify by test for each kind.

## 4. Hiding reference projects

- [x] 4.1 Find every place where the generators and `review.py` build `data\` paths. Make them honour `BUDGET_AGENT_DATA_DIR`, or choose the code-mirror fallback (design D5). Record the choice and its reason in design.md. Verify that the full test suite still passes with the variable unset.
- [x] 4.2 Write `build_scoped_data.py --code`, which uses `site_data.build` with the project's own names into `scoped-data\<code>\<data stamp>\data`, plus a prune of old stamps. Verify on a fictional project: `find_leaks` over the built folder finds nothing except the own names.
- [x] 4.3 Start project users' runs and Reviews on the masked set (build it on first use). Verify by measurement: one standard sample and one Review fixture, run on office data and on masked data, give 0 figure and formula differences on the deliverable, and the before/after table is saved in the session folder.
- [x] 4.4 Add a `project` role to `visible_outputs`, `may_download` and `visible_log` (deliverable, PDF A4/A3, roster; viewer log filter). Verify by test: the analysis is neither listed nor downloadable, for a new run and for an old run.
- [x] 4.5 Add the release scan: before a file or log lines go to a project user, run `find_leaks` with the cached word list for that code. On a hit, return 409 and log it. Verify by test with a fictional deliverable that contains a reference name.

## 5. Page

- [x] 5.1 In `index.html`, read `api/me`. For project users, hide the library tab and the analysis link, and replace the project name box with a picker of their codes. Office users get the picker plus "Dự án mới". Verify in the browser preview as each kind (office, project, none), on desktop and at phone width.

## 6. Old runs

- [x] 6.1 Write `webapp/map_run_codes.py`. `--propose` writes a CSV (run id, project text, proposed code, how matched). `--apply <csv>` backs up and updates `web_meta.json`. Verify on a copy of local test runs; the CSV for the server is produced on the server by [Hub] and approved by the user.

## 7. Acceptance and release

- [x] 7.1 Acceptance check on the client: run the link port with a test key and a test workbook. A P012 user calls every route with run ids, file names and library ids of P020, and every call returns 403 or 404. `find_leaks` over everything that user received finds nothing.
- [x] 7.2 `python verification/verify.py` passes, and the full test suite passes.
- [x] 7.3 Update `RUNNING.md` and the webapp section of `README.md` (variables, link port, workbook format, old-run mapping). Update `docs/project-status.md`.
- [x] 7.4 Commit (submodule first, then outer repo) on the user's request. Write the release note `releases\YYYY-MM-DD-budget-web-quyen-du-an.txt` stacked after the pending 16/11 and 17/11 notes, listing the four server variables, the tunnel rule (point it at the link port only, never at 8080/8090), the mapping step and the rollback. Report "Sẵn sàng deploy: budget-web <hash>".
