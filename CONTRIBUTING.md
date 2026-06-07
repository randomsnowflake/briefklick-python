# Contributing

Thanks for helping improve `briefklick-python`.

## Development setup

```bash
git clone https://github.com/randomsnowflake/briefklick-python.git
cd briefklick-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The test suite is fully offline. Do not use a real BriefKlick API key in tests.

## Safety model

BriefKlick has no sandbox for `send`.

- `/create` + `/preview` is free and safe.
- `/send` is real mail and chargeable.
- Never add tests, examples, or CI jobs that call the live API.
- Never commit `.env`, API keys, generated letters containing private data, or real recipient details.

## Pull request checklist

Before opening a PR:

- [ ] `pytest` passes locally.
- [ ] New behavior has offline tests using mocked HTTP responses.
- [ ] Public docs are updated when user-facing behavior changes.
- [ ] No secrets or personal data are included in files or fixtures.
- [ ] Send-related code documents ambiguous retry behavior. Blindly retrying `send` can duplicate physical mail.

## Style

- Keep the client small and synchronous.
- Prefer explicit dataclasses/enums over loosely typed dictionaries for public API results.
- Preserve backwards compatibility where practical. If a breaking change is necessary, document it in `CHANGELOG.md`.
- Keep examples copy-pasteable, but use fictional recipients and placeholder filenames.

## Releasing

1. Update the version in `pyproject.toml` and `src/briefklick/__init__.py`.
2. Update `CHANGELOG.md`.
3. Run `pytest`.
4. Build with `python -m build` from a clean checkout.
5. Publish only from a trusted machine after reviewing the source distribution and wheel contents.
