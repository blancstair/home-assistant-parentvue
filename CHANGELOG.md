# Changelog

All notable changes to the ParentVUE Home Assistant integration are documented
here. Versioning follows Semantic Versioning.

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
