# ParentVUE for Home Assistant

A privacy-conscious Home Assistant custom integration for **Edupoint ParentVUE**.

Current version: **0.2.2**

> This project is independent and is not affiliated with Edupoint or any school district.

## Highlights

- normal ParentVUE **website** authentication
- automatic multi-child discovery
- one Home Assistant device per child
- Grade Book course sensors
- missing-assignment summary
- current/next-class sensors
- conservative two-hour server polling floor
- UI config flow and reauthentication
- privacy-preserving diagnostics
- bundled **ParentVUE Dashboard** card
- HACS-ready repository layout

Development was initially validated against Chesapeake Public Schools ParentVUE:

`https://va-cps-psv.edupoint.com`

## Dashboard

Version 0.2.2 ships a frontend card with the integration itself:

`custom:parentvue-dashboard-card`

It automatically discovers ParentVUE devices and entities and displays each
child's school/grade, missing-assignment count, current/next class, and courses.

No separate dashboard-card repository is required.

See [`docs/HELP.md`](docs/HELP.md) for setup instructions.

## Installation

### HACS custom repository

1. Open HACS.
2. Open **Custom repositories**.
3. Add this GitHub repository URL as type **Integration**.
4. Install ParentVUE.
5. Restart Home Assistant.
6. Open **Settings → Devices & services → Add integration**.
7. Search for **ParentVUE**.

### Manual

Copy:

`custom_components/parentvue`

to:

`/config/custom_components/parentvue`

and restart Home Assistant.

## Configuration

Setup is entirely through the Home Assistant UI.

Required fields:

- district/base URL
- ParentVUE username
- ParentVUE password

Credentials must never be put in YAML, source code, screenshots, public issues,
or test fixtures.

## Polling

The integration will not automatically contact ParentVUE more frequently than
once every two hours.

- scheduled interval: 2 hours 1 minute
- hard network minimum: 2 hours
- all entities share one coordinator
- current/next-class state can change locally from cached schedule data without
  a ParentVUE request

## Privacy and security

This project handles children's educational records.

It does not add telemetry and does not send ParentVUE data to an external
service.

Diagnostics intentionally omit student/course details and credentials.

Read [`SECURITY.md`](SECURITY.md) before filing issues involving authentication
or student data.

## Documentation

- [Full help and user guide](docs/HELP.md)
- [GitHub web publishing guide](GITHUB_WEB_PUBLISH.md)
- [Research notes](RESEARCH_NOTES.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Dashboard YAML](dashboard/parentvue_dashboard.yaml)

## Current 0.2.2 entities

Per child:

- School
- Grade level
- Missing assignments
- Current class
- Next class
- One course-grade sensor per discovered Grade Book course

Assignment details, attendance, calendars, messages, report cards, GPA, and
change events remain planned work and will only be added after their website
schemas are validated.

## Versioning

Semantic versioning is used from the beginning.

GitHub releases should use tags such as:

`v0.2.2`

The integration manifest version is:

`0.2.2`

## Development principles

- prefer structured ParentVUE website/API calls over visual HTML scraping
- do not invent endpoints or response structures
- isolate ParentVUE parsing/network logic from Home Assistant entity code
- never log credentials or full ParentVUE responses
- avoid exposing raw student identifiers
- keep ParentVUE polling conservative
- use modern Home Assistant UI configuration and current `action` terminology
