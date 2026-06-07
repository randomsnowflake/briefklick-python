# Changelog

All notable changes to this project will be documented here.

This project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic versioning once releases are published.

## [Unreleased]

### Added

- Public contributor documentation.
- Public security policy.
- Public repository readiness checklist.
- GitHub Actions CI for the offline test suite.

## [0.1.0] - 2026-04-18

### Added

- Initial synchronous Python client for the BriefKlick v2 API.
- Typed models for recipients, uploaded documents, orders, previews, and status responses.
- `preview_letter()` helper for free `/create` + `/preview` workflows.
- `send_letter()` helper for one-shot `/create` + `/send` workflows.
- Offline unit tests using mocked HTTP calls.
- LLM-facing `briefklick-send-letter` skill.
