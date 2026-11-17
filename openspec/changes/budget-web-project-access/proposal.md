## Why

The Budget web on the Hub is about to be reachable from a Cloudflare link, so site PMs outside the office can open it.
Today the web assumes everyone who reaches it is office staff:
- every user sees every run of every project;
- users can see the approved-budget library of 48 projects;
- users can see the internal analysis, which names the reference projects.

On the Hub the web runs with its own login switched off and trusts the Hub's login gate in front of it. A request that
arrives without the Hub's role header gets full access. A Cloudflare tunnel connects from the server itself, and the
Hub's gate does not ask local callers to log in, so a tunnel pointed at the web would open everything.

Rule decided 2026-11-17:
- a person whose email belongs to a project sees only that project's data;
- every other project that the tool uses as a reference shows without its name.

## What Changes

- **Login for the link.** The web reads the person's email from the Cloudflare Access token and checks the token's
  signature itself. The link reaches the web on a separate port, and that port refuses any request without a valid
  token. The office route through the Hub (Windows login) works as before.
- **Email-to-project list.** An Excel workbook on SharePoint holds two lists:
  - the projects: code, display name, and the other names the project goes by;
  - the people: email, then the project codes they may see, or `ALL`.

  The web re-reads the workbook every few minutes. A person not on the list, or on it with no project, sees nothing.
- **Every run carries a project code.** On the form, the free-text project name becomes a choice from the project list:
  - a project user can choose only their own projects;
  - office users can still enter a new name.

  Runs made before this change get their code once, from a mapping table the user approves. A run with no code is
  visible to `ALL` users only.
- **Each screen and download checks the project.** A project user sees only their own projects' runs in the history,
  only their own projects' approved budgets in the Review list, and no library overview. The check is made on the run
  itself, so opening or downloading another project's run by its address is refused.
- **Reference projects are hidden in two ways:**
  - a project user's runs use a data set in which every other project's name reads "Dự án tham chiếu NN" (the site
    package mechanism; figures unchanged);
  - a project user gets only the client deliverable (Excel and PDF) and the roster, never the internal analysis, and
    sees the run log filtered as a viewer's.
- **Name scan before release.** Before a file is handed to a project user, the web scans it for other projects' names.
  When it finds one, it holds the file back and logs the finding.
- Office users, and the Hub viewer role, see no change in what they get. Figures on the deliverable do not move.

## Capabilities

### New Capabilities
- `budget-web-project-access`: who may see which project's runs, approved budgets and files on the Budget web; how the
  email is proven, where the email-to-project list lives, how a run is tied to a project, and how reference projects
  are hidden from project users.

### Modified Capabilities
<!-- none: budget-site-package keeps its requirements; this change reuses its masking and name scan unchanged -->

## Impact

- Code:
  - `webapp/server.py`: identity, a project filter on every run, file and library route, and the tunnel port;
  - `webapp/auth.py`: verifying the Cloudflare Access token;
  - new `webapp/project_access.py`: reading the workbook and deciding access;
  - `webapp/history.py`: the project code in `web_meta.json`;
  - `webapp/library.py`: library rows carry a project code;
  - `webapp/static/index.html`: the project picker, plus tabs hidden for project users;
  - new `build_scoped_data.py`: builds a masked data set per project, reusing `site_data.py`.
- Server (via the [Hub] session only):
  - a second listening port for the tunnel;
  - environment variables for the Cloudflare team domain, the AUD tag and the workbook path;
  - a one-time project-code mapping for the runs already on the server.

  The tunnel must not be opened to the Budget web before this change is deployed.
- Dependency: a library to verify the RS256 token (`PyJWT` with `cryptography`, pinned in `webapp/requirements.txt`).
- No figure on any deliverable changes, and no recorded baseline moves.
