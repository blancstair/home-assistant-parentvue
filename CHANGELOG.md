# Changelog

All notable changes to the ParentVUE Home Assistant integration are documented
here. Versioning follows Semantic Versioning.

## 0.3.0 - 2026-09-11

### Added

- Per-child configuration for the bundled ParentVUE dashboard card.
- Visual card editor with grouped controls for student, assignment, schedule,
  course, attendance, and Synergy Mail sections.
- Student name as the default single-child card header, with optional custom
  title override.
- Configurable missing-assignment alert threshold and alert color.
- Full today's-schedule section with optional period, teacher, room, time,
  delivery-mode, and current-class highlighting.
- Separate ParentVUE letter-grade and published-percentage entities.
- Stable per-course entities for course name, grade, percentage, teacher, room,
  period, marking period, missing assignments, delivery mode, and last update.
- Stable current/next-class field entities for period, teacher, room, start/end
  time, and delivery mode.
- Today's attendance collection/count entities and school-year attendance
  summary/count entities when the district response can be normalized.
- Account-level unread Synergy Mail sensor when ParentVUE exposes a recognized
  unread indicator.
- Student-name and complete-today-schedule entities for flexible custom
  dashboards outside the bundled card.

### Changed

- The dashboard is now entity-first: the card reads Home Assistant entities and
  does not have a private data path to ParentVUE.
- Existing course-grade, missing-assignment, current-class, and next-class unique
  IDs are retained for registry continuity.
- Feature-specific attendance failures are non-fatal and do not discard valid
  Grade Book or schedule data.
- Individual attendance events are exposed as structured attributes instead of
  creating high-churn entity-registry entries.
- Schedule and course delivery-mode displays now distinguish Online and In person.

### Privacy

- Synergy Mail content is not retrieved.
- Diagnostics continue to omit student/course names, grades, attendance details,
  identifiers, credentials, cookie values, and raw responses.
- The two-hour minimum ParentVUE network interval remains unchanged.

## 0.2.5 - 2026-09-11

### Fixed

- Fixed a false authentication failure after a successful ParentVUE login.
  Chesapeake returned `/Home_PXP2.aspx` with all expected session cookies, but
  the previous login-page detector could combine unrelated username/password
  controls in the authenticated HTML and incorrectly classify it as a login page.
- Authenticated `.student-info[data-agu]` selectors are now treated as stronger
  evidence of a successful ParentVUE session.
- Login-form fallback detection now requires username and password fields to be
  in the same form.
- ParentVUE browser headers are now attached to each HTTP request. Home
  Assistant intentionally replaces `ClientSession` default headers, so the
  previous session-level browser User-Agent was not guaranteed to reach the
  district server.
- Fixed the Home Assistant warning caused by explicitly closing an
  `async_create_clientsession` session during config-flow validation. The
  temporary session now uses `auto_cleanup=False` and `detach()` as required by
  Home Assistant's session helper.

### Tests

- Added regression coverage for authenticated pages containing password/account
  controls so they cannot be mistaken for the ParentVUE login form.

## 0.2.4 - 2026-09-11

### Fixed

- Changed ParentVUE website sessions to use a browser-compatible request
  fingerprint. The standalone website probe authenticated successfully with a
  browser-style User-Agent, while the Home Assistant client had been using an
  API-style User-Agent.
- Made the ASP.NET login POST more closely match the normal website request by
  including browser-compatible Origin/Referer/form headers.
- Changed authenticated-page HTTP 401/403 handling so it is not automatically
  mislabeled as a bad username/password.

### Diagnostics

- Added debug-only authentication-stage metadata containing only URL paths,
  booleans, and cookie *names*. Credential values, cookie values, HTML, and
  student data are never logged.
- Updated the config-flow authentication message so it describes a rejected or
  returned-to-login result instead of claiming the password is certainly wrong.

### Packaging

- Removed GitHub publishing/update instruction files from the release source.
  Repository-management instructions remain outside release packages.

## 0.2.3 - 2026-09-11

### Fixed

- Fixed a runtime import failure that prevented the Home Assistant config flow
  from loading. `DOMAIN` is now imported before it is used by
  `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`.
- This resolves the Home Assistant UI error:
  `Config flow could not be loaded: {"message":"Invalid handler specified"}`.

### Validation

- Added a Ruff undefined-name/static-error check to GitHub Actions so this class
  of import-time mistake is caught before release.

## 0.2.2 - 2026-09-11

### Fixed

- Sorted `manifest.json` keys in Home Assistant Hassfest order.
- Removed the literal district URL from translatable config-flow text.
- Added `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)` for the
  config-entry-only integration.
- Updated `async_setup` to use Home Assistant's current `ConfigType` annotation.
- Updated ParentVUE HTTP User-Agent strings to use the integration version.

## 0.2.1 - 2026-09-11

### Changed

- Replaced all GitHub-owner placeholders with `blancstair`.
- Removed local publishing/setup helper scripts.
- Added concise GitHub website-only publishing instructions.
- Updated repository URLs and issue links for
  `https://github.com/blancstair/home-assistant-parentvue`.
- Updated documentation to use the v0.2.1 release number.
- Added a version query to the bundled dashboard resource so browser caching does not hide card updates.

### Fixed

- Publication package is ready for direct upload through the GitHub website.

## 0.2.0 - 2026-09-11

### Added

- GitHub/HACS-ready repository structure.
- Bundled `ParentVUE Dashboard` Lovelace card.
- Automatic discovery of ParentVUE devices/entities by the dashboard card.
- Ready-to-paste dedicated dashboard YAML.
- Full user/help guide in `docs/HELP.md`.
- GitHub bug-report and feature-request templates.
- Security and contribution policies focused on protecting student records.
- HACS and Hassfest validation workflow.
- Home Assistant source `strings.json`.

### Changed

- Added Home Assistant frontend/HTTP dependencies so the bundled dashboard card
  can be served directly by the integration.
- Integration version bumped to 0.2.0.

### Security

- Dashboard code reads Home Assistant entity state only; it never contacts
  ParentVUE directly.
- Public issue templates warn users not to upload credentials, raw HAR captures,
  cookies, tokens, or student records.

## 0.1.0 - 2026-09-11

### Added

- Initial Home Assistant custom integration with domain `parentvue`.
- Normal ParentVUE website login/session support.
- Chesapeake Public Schools default district URL.
- UI config flow with connection validation.
- Reauthentication flow.
- Automatic multi-child discovery from ParentVUE's student selector.
- Privacy-preserving hashed student/course unique identifiers.
- One Home Assistant device per child.
- School and grade-level sensors.
- Aggregate missing-assignment sensor using Grade Book summaries.
- Dynamic per-course grade sensors.
- Current-class and next-class sensors from the structured
  `PXP2WebCommonService.asmx/DayContent` endpoint.
- `DataUpdateCoordinator` with a hard minimum two-hour ParentVUE network
  interval.
- Privacy-preserving diagnostics.
- HACS-compatible repository layout.

### Research validated before implementation

- Standard Chesapeake ParentVUE website login successfully authenticates and
  redirects to `Home_PXP2.aspx`.
- Multiple child selectors are present in the authenticated website.
- `PXP2_Gradebook.aspx` exposes Grade Book course/mark summaries.
- Website JavaScript uses structured methods under
  `PXP2Communication.asmx`.
- Daily class schedule data is available as structured JSON through
  `PXP2WebCommonService.asmx/DayContent`.

### Deferred

- Detailed assignments, attendance, calendars, messages, report cards, GPA,
  and change-detection events.
