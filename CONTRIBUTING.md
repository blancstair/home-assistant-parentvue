# Contributing

Contributions are welcome, especially sanitized observations from additional
Edupoint ParentVUE districts.

## Rules for captured ParentVUE data

Do not commit real student data, credentials, cookies, tokens, raw HAR files, or
raw authenticated responses.

Tests and fixtures must use synthetic data.

## Development principles

- website/API interfaces are preferred over rendered-HTML scraping
- endpoint names and schemas must be observed before implementation
- XML/HTML/JSON parsing belongs in `api.py`, not entity classes
- Home Assistant entities consume normalized models
- all ParentVUE entities share the coordinator
- automatic ParentVUE network refresh must remain at least two hours apart
- temporary district outages must not permanently break the config entry
- credentials and full responses must never be logged
- use Home Assistant's current `action` terminology in examples

## Versioning

Semantic versioning is used from the beginning.

Changes should update both `manifest.json` and `CHANGELOG.md`.
