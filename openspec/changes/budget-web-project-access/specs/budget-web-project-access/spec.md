## Purpose

Decides who may see which project's runs, approved budgets and files on the Budget web, so a site PM who opens the web
from the outside link sees only their own project and never another project's name, while office users keep full
access.

## ADDED Requirements

### Requirement: The outside link proves the person's email
The web SHALL serve the outside link on a port of its own. Every request on that port SHALL carry a Cloudflare Access
token, and the web SHALL check that token's signature against the Cloudflare team's published keys, its audience (the
AUD tag of the Access application), its issuer and its expiry before reading the email from it. A request without a
token, or with a token that fails any check, SHALL get 401 and no data. An email header sent without a valid token
SHALL be ignored. The office route through the Hub's login gate SHALL keep working as before and SHALL never accept a
Cloudflare token in place of the Hub login.

#### Scenario: Valid token
- **WHEN** a request on the link port carries a token signed by the team's key, for the right audience, not expired,
  for `pm.a@example.com`
- **THEN** the web treats the request as `pm.a@example.com`

#### Scenario: Forged email header
- **WHEN** a request on the link port carries `Cf-Access-Authenticated-User-Email: boss@example.com` and no token, or
  a token signed by another key
- **THEN** the web answers 401 and returns no project data

#### Scenario: Office route unchanged
- **WHEN** an office user opens the web through the Hub with their Windows login
- **THEN** they see every project's runs, the library and the analysis exactly as before this change

### Requirement: An email-to-project workbook decides access, closed by default
The web SHALL read an Excel workbook, whose path is set on the server, with a sheet of projects (code, display name,
other names) and a sheet of people (email, project codes, or `ALL`). Emails SHALL match without regard to case or
surrounding spaces. A person on the link who is not in the workbook, or is in it with no valid project code, SHALL see a
page saying they have no project and SHALL get no data from any route. `ALL` SHALL give the office view. The web SHALL
re-read the workbook when it changes, at most a few minutes later, without a restart. When the workbook cannot be read
or a row is malformed, the web SHALL keep the last list it read successfully, SHALL log the problem, and SHALL never
widen anyone's access because of the error; when no list was ever read, every link user SHALL be refused.

#### Scenario: Person with one project
- **WHEN** the people sheet has `pm.a@example.com` with code `P012`
- **THEN** that person sees only project `P012`

#### Scenario: Unknown person
- **WHEN** `someone@example.com` passes the Cloudflare login but is not in the workbook
- **THEN** every data route answers 403 and the page says they have no project yet

#### Scenario: Workbook broken mid-day
- **WHEN** the workbook is saved with the people sheet missing
- **THEN** the web keeps the previous list, logs that the workbook could not be read, and nobody gains access

### Requirement: Every run belongs to one project code
Each run SHALL record one project code from the projects sheet. On the form a project user SHALL choose the project from
their own codes only; an office user SHALL choose any code or enter a new project. A run started by a project user for a
code they do not hold SHALL be refused with 403. Runs made before this change SHALL get their code once from a mapping
table that the user approves; a run with no code SHALL be visible to `ALL` and office users only.

#### Scenario: Project user starts a run
- **WHEN** `pm.a@example.com` (code `P012`) starts a new-project run or a Review
- **THEN** the run is recorded with `P012` and the project picker offered only `P012`

#### Scenario: Tampered request
- **WHEN** the same person sends a run request with code `P020`
- **THEN** the web answers 403 and no run folder is created

#### Scenario: Old run without a code
- **WHEN** a run from before this change is not in the approved mapping
- **THEN** it does not appear for any project user, and office users still see it

### Requirement: A project user reaches only their own projects' data on every route
For a project user, the web SHALL apply the project check to the run itself on every route that names a run, not only
to lists:
- the run status and log;
- the run's input values (Clone);
- file download and PDF print;
- the adjustment table and its save;
- Review from an earlier run.

A run of another project SHALL answer 404, the same as a run that does not exist. The history list SHALL hold only the
person's projects' runs. The approved-budget list for Review, and the facts prefilled from it, SHALL hold only files of
the person's projects. The library overview SHALL not be available to project users.

#### Scenario: Guessing another project's run
- **WHEN** `pm.a@example.com` (code `P012`) opens the status, input, a file, the print or the adjustment of a run of
  `P020` by its address
- **THEN** each answers 404 and returns nothing of that run

#### Scenario: Review list
- **WHEN** the same person opens the Review tab
- **THEN** the approved-budget list shows only files mapped to `P012`, and asking for the facts of another file answers
  404

#### Scenario: Gen budget from another project's run
- **WHEN** the person sends a Review that names a run of `P020` as its source
- **THEN** the web answers 404 and starts nothing

### Requirement: Project users never see reference projects' names
A run started by a project user SHALL use a data set in which every project name other than that user's own project
reads "Dự án tham chiếu NN". Codes and figures in that data set SHALL be unchanged, so the run gives the same figures as
the same input on the office data.

A project user SHALL get only:
- the client deliverable (Excel and its PDF prints);
- the roster;
- the run log filtered as the Hub viewer's is.

The internal analysis SHALL be neither listed nor downloadable, for new and old runs alike.

Before any file or log is returned to a project user, the web SHALL scan it for other projects' names. The scan SHALL
use the same word list as the site-package check. Names that already stand in the standard budget template are left
out, as that check reports them apart. A file with a hit SHALL be held back, with a message to ask the office, and the
hit SHALL be logged on the server. A log line with a hit SHALL be left out of what the project user sees.

#### Scenario: Same figures, masked names
- **WHEN** a project user and an office user run the same input for `P012`
- **THEN** both deliverables give the same totals and lines, and the project user's run data names other projects only
  as "Dự án tham chiếu NN"

#### Scenario: Analysis hidden
- **WHEN** a project user opens a finished run of their project
- **THEN** the file list shows the deliverable, its PDFs and the roster only, and asking for the analysis by name
  answers 404

#### Scenario: Name found in an old deliverable
- **WHEN** a deliverable of an old run, made on full data, contains "Tháp Mây Xanh" and a project user asks for it
- **THEN** the download is refused with a message to ask the office, and the server log names the run and the hit
