# ParentVUE for Home Assistant — Help & User Guide

This guide applies to **ParentVUE integration 0.2.2**.

## What this integration does

ParentVUE connects Home Assistant directly to your school district's Edupoint
ParentVUE website. It uses the same normal ParentVUE website account that a
parent uses in a browser.

The integration does **not** require Nabu Casa, does not send school records to
another cloud service, and does not add telemetry.

## Current data

Version 0.2.2 currently exposes:

- one Home Assistant device per discovered child
- school
- grade level
- aggregate missing-assignment count
- course-grade sensors
- current class
- next class
- cached daily schedule data used by the class sensors

Detailed assignment lists, attendance totals, calendars, messages, report cards,
GPA, and change-detection events are planned but intentionally deferred until
their website schemas have been validated.

## Polling policy

ParentVUE is intentionally treated conservatively.

- scheduled ParentVUE refresh: **2 hours 1 minute**
- hard minimum between ParentVUE network refreshes: **2 hours**
- manual entity refreshes inside the safety window return cached data
- current/next class state is recalculated locally from cached schedule data
- local class-state updates do not contact ParentVUE

## Installation with HACS

After this repository is published at `https://github.com/blancstair/home-assistant-parentvue`:

1. Open HACS in Home Assistant.
2. Open the three-dot menu.
3. Select **Custom repositories**.
4. Paste the GitHub repository URL.
5. Select **Integration**.
6. Install **ParentVUE**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**.
9. Search for **ParentVUE**.

HACS installs custom integrations under `custom_components/`. A public GitHub
repository with the standard HACS integration layout is required for normal HACS
distribution.

## Manual installation

Copy:

`custom_components/parentvue`

to:

`/config/custom_components/parentvue`

Restart Home Assistant, then add ParentVUE from **Settings → Devices & services**.

## Configuration

The UI setup asks for:

- ParentVUE district URL
- ParentVUE username
- ParentVUE password

For Chesapeake Public Schools:

`https://va-cps-psv.edupoint.com`

Use the base district URL, not a particular Grade Book or login-page URL.

The password is stored in Home Assistant's config entry so the integration can
reauthenticate after the ParentVUE website session expires. It is not exposed as
an entity or diagnostic value.

## ParentVUE Dashboard

Version 0.2.2 bundles a custom card named:

**ParentVUE Dashboard**

The JavaScript is shipped inside the integration and loaded by Home Assistant.
There is no second HACS frontend repository to install.

### Create a dedicated dashboard

1. Go to **Settings → Dashboards**.
2. Create a new dashboard named **ParentVUE**.
3. Open it and enter edit mode.
4. Add a card.
5. Search for **ParentVUE Dashboard** under custom/community cards.
6. Add it.

The card automatically discovers ParentVUE entities from Home Assistant's entity
and device registries. You do not need to type your children's entity IDs.

A ready-to-paste raw dashboard example is also included at:

`dashboard/parentvue_dashboard.yaml`

### Dashboard contents

For each ParentVUE child device, the card displays:

- child/device name
- school and grade level
- missing-assignment count
- current class
- next class
- discovered course grades

Clicking a metric or course opens Home Assistant's normal More Info dialog.

The dashboard card never contacts ParentVUE itself. It only reads entities
already maintained by the backend integration.

## Updating

When installed through HACS, use HACS to install newer GitHub releases.

The project uses semantic versioning:

- patch: bug fixes, e.g. `0.2.2`
- minor: backward-compatible features, e.g. `0.3.0`
- major: breaking changes, e.g. `1.0.0`

## Diagnostics

Open:

**Settings → Devices & services → ParentVUE → three-dot menu → Download diagnostics**

Diagnostics intentionally exclude:

- username
- password
- raw ParentVUE cookies
- raw HTML/API responses
- student names
- raw student identifiers
- course names
- grades
- assignment contents

Useful diagnostics include only counts, update state, and polling-policy status.

## Troubleshooting

### ParentVUE does not appear after installation

Restart Home Assistant after installing or updating the custom integration.
If installed through HACS and it still does not appear, hard-refresh the browser.

### Invalid username or password

Confirm the same credentials work on the district's normal ParentVUE website.
Do not test against StudentVUE credentials or a student's SSO account.

### Server unavailable

ParentVUE districts periodically perform maintenance. A temporary outage should
not require deleting/recreating the integration. Home Assistant will retry on a
later coordinator refresh.

### Entities are unavailable

Check the ParentVUE integration entry first. If the coordinator cannot update,
all dependent entities may be unavailable until a later successful refresh.

A class-schedule endpoint failure can make current/next-class sensors unavailable
without discarding otherwise valid Grade Book data.

### Grade says Unknown

A teacher/course may not publish a current mark, especially early in a grading
period. ParentVUE itself can display `N/A`; this integration does not invent a
grade where ParentVUE does not provide one.

### Dashboard card is missing

After updating from a version before 0.2.2:

1. restart Home Assistant
2. perform a hard browser refresh
3. reopen the dashboard card picker

The card is served from the integration itself at a local Home Assistant path.

### Need debug logs?

Do not post credentials, cookies, HAR files, raw ParentVUE responses, or
unredacted student records to a public GitHub issue.

If additional logging is added during development, it must remain metadata-only
by default.

## Reporting a bug

Before opening a GitHub issue:

1. confirm the district ParentVUE website itself is working
2. note your Home Assistant version
3. note the ParentVUE integration version
4. download ParentVUE diagnostics
5. remove any personal/school information you added manually
6. include the exact Home Assistant traceback if there is one

Never include:

- ParentVUE password
- session cookies
- authentication tokens
- raw HAR captures
- student IDs
- report-card documents
- message contents

## Development status

This is an independent custom integration and is not affiliated with Edupoint or
the school district.

The current implementation is based on verified behavior of Chesapeake Public
Schools' ParentVUE website plus documented observations in `RESEARCH_NOTES.md`.
Unverified endpoints are not invented or silently assumed.
