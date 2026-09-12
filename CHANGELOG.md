# Changelog

All notable changes to the ParentVUE Home Assistant integration are documented
here. Versioning follows Semantic Versioning.

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
