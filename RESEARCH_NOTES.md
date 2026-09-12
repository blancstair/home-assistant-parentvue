# ParentVUE Research Notes

These notes separate behavior verified against the Chesapeake Public Schools
ParentVUE deployment from behavior that remains best-effort or deferred.

## Verified website workflow

Development was initially validated against Chesapeake Public Schools ParentVUE.

### Authentication

The normal website login is an ASP.NET form under
`/PXP2_Login_Parent.aspx?regenerateSessionId=true`. A successful login redirects
to `/Home_PXP2.aspx`.

The integration discovers the actual login field names and ASP.NET hidden fields
at runtime. ParentVUE student selectors are rendered as
`.student-info[data-agu]`. The `AGU` value is treated only as the website's child
context/index.

Raw student identifiers are never exposed as Home Assistant identifiers. Where a
raw student ID is available in the page, it is immediately hashed into a
privacy-preserving key.

### Grade Book

The website Grade Book is `/PXP2_Gradebook.aspx`.

Observed summary structures include:

- `.gb-class-header`
- `.course-title`
- teacher and room metadata
- `.course-markperiod`
- `.mark`
- `.last-update`
- missing-assignment summary text

Version 0.3.0 keeps ParentVUE's letter-grade label separate from any percentage
published in the Grade Book. It never computes a letter grade from the numeric
percentage.

The site also uses structured methods under
`/service/PXP2Communication.asmx/`, including observed
`GradebookFocusClassInfo` and `LoadControl` calls. Detailed assignment/category
normalization remains deferred until stable request/response contracts are
validated.

### Daily schedule

The website uses `/Service/PXP2WebCommonService.asmx/DayContent` with a JSON date
request. Observed response fields include class name, period, teacher, room,
start/end information, and online-course status.

Version 0.3.0 exposes the complete cached schedule plus current/next class and
stable field entities. Current/next state is recalculated locally and does not
increase ParentVUE polling.

### Attendance

The structured method
`/service/PXP2Communication.asmx/AttGetCalendarDay` was observed in website
research, with daily/period attendance structures including reason, course,
teacher, room, period, and attendance reason type.

Version 0.3.0 adds conservative, non-fatal attendance support. It attempts to
normalize current-day event structures and server-rendered school-year totals.
District-specific attendance labels and payload differences may cause those
entities to remain unavailable. Grade Book and schedule data continue working
when attendance cannot be normalized.

Cumulative attendance interpretation should continue to be validated against
additional districts before stronger cross-district guarantees are made.

### Synergy Mail

Captured website traffic confirmed an unread-message count call under
`/st_api/ST.Messaging/GetUnreadMessageCount` using a portal query parameter and
form-encoded request data. The sanitized capture intentionally removed the
portal value and response scalar values.

Version 0.3.0 therefore does not guess the redacted portal value. It exposes an
account-level unread count only when a reliably parseable unread indicator is
present in authenticated website HTML. Message-list and message-detail APIs are
not used, and message content is not retrieved.

### Other observed website interfaces

Observed during website research include:

- `/service/PXP2Communication.asmx/DXDataGridRequest`
- `/Home_PXP2.aspx/LoadCounselorData`
- `/PXP2_PermissionSlips.aspx/GetBadgeData`
- `/StreamCommand.aspx/GetStreamsNotificationData`
- `/api/v1/components/...`

The website also exposes server-rendered pages for report cards, student
information, school information, documents, messages, and other modules.

## Deferred / not inferred

The integration deliberately does not invent unsupported semantics. Remaining
areas include:

- exact individual-assignment missing/late/exempt semantics
- reliable due-today/due-tomorrow/upcoming assignment normalization
- detailed assignment/category data with stable assignment identifiers
- structured report-card document access
- Synergy Mail message list/detail data
- school-calendar event normalization
- GPA meaning/availability across districts
- robust semester/year transition cleanup for dynamic course entities
- persisted grade/assignment/attendance change-detection events

New fields should be added only when their website behavior can be observed and
tested without exposing real student records.
