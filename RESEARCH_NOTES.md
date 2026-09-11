# ParentVUE Research Notes

These notes separate behavior verified against the Chesapeake Public Schools
deployment from behavior that remains reverse-engineered or unimplemented.

## Verified against Chesapeake ParentVUE

Base URL used during development:

`https://va-cps-psv.edupoint.com`

### Service surface

The district exposes:

`/Service/PXPCommunication.asmx`

Its service-description page advertises operations including:

- `AuthenticateUser`
- `GetWidgetData`
- `ProcessWebServiceRequest`
- `ProcessWebServiceRequestMultiWeb`
- `ProcessWebServiceRequestMultiWeb2`
- `ProcessWebServiceRequestMultiWeb3`
- `ValidUser`

The current integration does **not** use these mobile-oriented login methods.

### ParentVUE website authentication

The normal website login page is:

`/PXP2_Login_Parent.aspx?regenerateSessionId=true`

A successful parent login redirects to:

`/Home_PXP2.aspx`

The website uses an ASP.NET form containing ViewState/EventValidation fields and
normal username/password fields. Version 0.1.0 discovers the actual field names
from the form instead of hard-coding them.

### Multiple children

The authenticated website renders one `.student-info[data-agu]` selector per
available child.

The ParentVUE JavaScript `loadStudent()` implementation changes the current
student context with the `AGU` query parameter. Version 0.1.0 follows that
website behavior.

Raw student IDs are not exposed by the integration. They are hashed immediately
and only the privacy-preserving hash is used for Home Assistant device/entity
unique identifiers.

### Grade Book

The website Grade Book is:

`/PXP2_Gradebook.aspx`

Verified summary structures include:

- `.gb-class-header`
- `.course-title`
- teacher and room metadata
- `.course-markperiod`
- `.mark`
- `.last-update`
- missing-assignment summary text

The website also uses structured JSON methods under:

`/service/PXP2Communication.asmx/`

Observed methods include:

- `GradebookFocusClassInfo`
- `LoadControl`

`LoadControl` was observed with the control:

`Gradebook_ClassDetails`

The detailed class response contains Grade Book percentage/category/assignment
grid structures. Version 0.1.0 intentionally does not request those per-course
detail controls yet in order to keep the first release conservative.

### Daily schedule

The website uses:

`/Service/PXP2WebCommonService.asmx/DayContent`

with a JSON date request. The response contains structured school/class data
including:

- class name
- period
- teacher
- room
- start/end date and time
- online-course flag

Version 0.1.0 uses this structured endpoint for cached current/next-class data.

### Attendance

Observed structured method:

`/service/PXP2Communication.asmx/AttGetCalendarDay`

Observed response structures include daily/period summaries, reasons, course,
teacher, room, period, and attendance reason types.

Attendance entities are deferred until the meaning of district-specific reason
types and cumulative-count behavior is validated.

### Other observed website interfaces

Observed during website research:

- `/service/PXP2Communication.asmx/DXDataGridRequest`
- `/Home_PXP2.aspx/LoadCounselorData`
- `/PXP2_PermissionSlips.aspx/GetBadgeData`
- `/StreamCommand.aspx/GetStreamsNotificationData`
- `/api/v1/components/...`

The website also exposes server-rendered pages for report cards, student
information, school information, documents, messages, and other modules.

## Remaining unknowns / deferred reverse engineering

The following are deliberately not guessed in 0.1.0:

- exact individual-assignment missing/late/exempt semantics
- reliable due-today/due-tomorrow/upcoming assignment normalization
- cumulative absence/tardy calculations across grading periods
- overall GPA availability/meaning
- structured report-card document API
- Synergy Mail message-list/message-detail API contract
- school-calendar event normalization
- stable identifiers for assignment-level change detection
- semester/year transition behavior for course entity cleanup

These areas should be added only after real responses have been observed and
sanitized fixtures/tests are available.
