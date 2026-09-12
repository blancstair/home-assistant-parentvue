# ParentVUE for Home Assistant

A privacy-conscious Home Assistant custom integration for **Edupoint ParentVUE**.

Current version: **0.3.0**

> This project is independent and is not affiliated with Edupoint or any school district.

## Highlights

- normal ParentVUE **website** authentication
- automatic multi-child discovery
- one Home Assistant device per child
- configurable per-child ParentVUE dashboard card with visual editor
- ParentVUE letter grades and published percentages as separate entities
- aggregate and per-course missing-assignment sensors
- current class, next class, and full today's schedule
- best-effort current-day and school-year attendance
- account-level unread Synergy Mail count when ParentVUE exposes it
- conservative two-hour server polling floor
- UI config flow and reauthentication
- privacy-preserving diagnostics
- HACS-ready repository layout

Development was initially validated against Chesapeake Public Schools ParentVUE.

## Dashboard card

The integration ships the custom card:

`custom:parentvue-dashboard-card`

The card reads Home Assistant entities only. It never contacts ParentVUE directly.

The visual card editor can select **All children** or one child and can independently
show or hide student, assignment, schedule, course, attendance, and Synergy Mail
sections. When one child is selected, the default card header is that student's
Home Assistant device name. A custom title can override it.

The missing-assignment alert threshold is a configurable non-negative integer.
The alert activates when the missing count is **greater than** the configured
threshold. Its alert color is also configurable.

## Entities

Stable values are exposed as Home Assistant sensor entities so dashboards and
automations do not depend on the bundled card.

Per child, the integration can expose:

- student name, school, and grade level
- aggregate missing-assignment count
- today's schedule collection
- current and next class
- current/next period, teacher, room, start time, end time, and delivery mode
- today's attendance collection and numeric attendance counts
- school-year attendance summary and numeric attendance totals
- for each stable course: course name, ParentVUE letter grade, ParentVUE
  percentage, teacher, room, period, marking period, missing assignments,
  delivery mode, and last-updated label

An unread Synergy Mail count is exposed as an **account-level** sensor when the
website publishes a reliably parseable unread indicator. It is intentionally not
assigned to an individual child.

Repeating/high-churn records such as individual attendance events are retained as
attributes on collection entities rather than creating large numbers of stale
entity-registry entries.

## Grade handling

ParentVUE remains the authority for both grade values. The integration does not
calculate a letter grade from a percentage. If ParentVUE publishes only one of
the two values, only that value is exposed.

## Attendance and mail status

Attendance and Synergy Mail vary across ParentVUE deployments. These features are
best-effort and non-fatal: if a district does not expose a recognized response,
the related entities remain unavailable while Grade Book and schedule data
continue to update.

Message contents are never retrieved or exposed by the current integration.

## Installation

### HACS custom repository

Add this repository to HACS as an **Integration**, install ParentVUE, restart
Home Assistant, then open **Settings → Devices & services → Add integration**
and search for **ParentVUE**.

### Manual

Copy `custom_components/parentvue` to
`/config/custom_components/parentvue`, restart Home Assistant, then add the
integration from the Home Assistant UI.

## Configuration

Setup is entirely through the Home Assistant UI. Enter the district/base URL and
your normal ParentVUE website username and password.

Credentials must never be put in YAML, source code, screenshots, public issues,
or test fixtures.

## Polling

The integration will not automatically contact ParentVUE more frequently than
once every two hours.

- scheduled interval: **2 hours 1 minute**
- hard network minimum: **2 hours**
- all entities share one coordinator
- current/next-class state is recalculated locally from cached schedule data
- local class-state updates do not contact ParentVUE

## Privacy and security

ParentVUE handles children's educational records. This integration adds no
telemetry and sends ParentVUE data only between Home Assistant and the configured
district website.

Diagnostics intentionally omit credentials, cookie values, student/course
details, grades, assignment content, attendance details, mail content, and raw
ParentVUE responses.

Read [`SECURITY.md`](SECURITY.md) before reporting authentication or student-data
issues.

## Documentation

- [Full help and user guide](docs/HELP.md)
- [Research notes](RESEARCH_NOTES.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Dashboard YAML](dashboard/parentvue_dashboard.yaml)

## Development principles

- prefer structured ParentVUE website interfaces over rendered-HTML parsing
- do not infer educational values ParentVUE does not publish
- isolate ParentVUE network/parsing logic from Home Assistant entity code
- never log credentials, cookie values, or raw ParentVUE responses
- avoid exposing raw student identifiers
- keep ParentVUE polling conservative
- use current Home Assistant `action` terminology in examples
