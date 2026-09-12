# ParentVUE for Home Assistant — Help & User Guide

This guide applies to **ParentVUE integration 0.3.0**.

## What this integration does

ParentVUE connects Home Assistant directly to a district's Edupoint ParentVUE
website using the normal parent website account. It does not require another
cloud service, does not add telemetry, and does not expose raw student IDs.

## Polling policy

ParentVUE is intentionally treated conservatively.

- scheduled ParentVUE refresh: **2 hours 1 minute**
- hard minimum between ParentVUE network refreshes: **2 hours**
- manual entity refreshes inside the safety window return cached data
- current/next class state is recalculated locally once per minute from the
  cached daily schedule
- local class-state updates do not contact ParentVUE

## Configuration

Add ParentVUE from **Settings → Devices & services → Add integration**. Enter the
district ParentVUE base URL plus the normal ParentVUE website username and
password.

The password is stored in Home Assistant's config entry so the integration can
reauthenticate when the website session expires. It is not exposed as an entity
or diagnostic value.

## ParentVUE Dashboard card

The integration includes **ParentVUE Dashboard**. Add it through a dashboard's
card picker or use a Manual card with:

```yaml
type: custom:parentvue-dashboard-card
```

The card has a visual editor. The **Child** selector can display all children or
one selected ParentVUE child device.

For a single-child card, the default header is the student's device name. Leave
the custom title blank to use that name. A custom title overrides it.

The editor provides grouped switches for school/grade, assignments, current and
next class, today's full schedule, schedule details, course grades and details,
attendance, and unread Synergy Mail.

### Missing-assignment alert

The editor includes:

- **Alert when missing count is greater than** — a configurable integer
- **Alert color** — a color picker

For example, a threshold of `1` highlights the missing-assignment block at `2`
or more. A threshold of `0` highlights any missing assignment.

### Course grades

Letter grade and percentage are separate controls and separate Home Assistant
entities. ParentVUE is authoritative; Home Assistant does not calculate one from
the other.

### Today's schedule

The full schedule uses the same cached schedule already maintained by the
integration. Display options include period, teacher, room, times, delivery mode,
and current-class highlighting. Showing the schedule does not increase
ParentVUE polling.

### Attendance

The card can show both today's attendance and a school-year summary. Attendance
website schemas vary between districts, so attendance entities are available
only when the configured ParentVUE deployment returns a recognized structure.
Attendance failure does not make Grade Book or schedule entities unavailable.

### Synergy Mail

The card can show an account-level unread Synergy Mail count when ParentVUE
publishes a recognized unread indicator. It is account-level rather than
artificially assigned to a child. Message subjects, senders, and bodies are not
retrieved by this version.

## Entity model

Version 0.3.0 exposes stable ParentVUE values as entities so you can use the
bundled card, ordinary Home Assistant cards, templates, and automations.

Per child, available sensors include student name, school, grade level, aggregate
missing assignments, full today's schedule, current/next class and their stable
fields, attendance summaries/counts, and stable per-course fields such as course
name, letter grade, percentage, teacher, room, period, marking period, missing
assignments, delivery mode, and last-updated label.

Individual attendance events are stored in the `Attendance today` sensor's
`events` attribute. This avoids creating transient entity-registry entries for
every event.

## Privacy

Do not post credentials, cookie values, raw HAR files, raw authenticated
HTML/XML/JSON, student IDs, student records, or message contents to a public
issue.

Home Assistant diagnostics intentionally contain only privacy-preserving status
and count metadata.

## Troubleshooting

If the dashboard card is missing after an update, restart Home Assistant and
hard-refresh the browser/app frontend.

If entities are unavailable, check the ParentVUE integration entry first.
Feature-specific attendance or schedule failures are designed to remain
non-fatal where possible.

If authentication fails, confirm the same account works on the district's normal
ParentVUE website. Debug logs must remain metadata-only; never publish
credentials, cookie values, or raw authenticated responses.
