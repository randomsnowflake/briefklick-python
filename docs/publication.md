# Public repository readiness

This checklist documents what must be true before making the repository public.

## Required files

- [x] `README.md` with project purpose, warning about chargeable sends, installation, configuration, quickstart, testing, docs, and license.
- [x] `LICENSE` with MIT terms.
- [x] `.env.example` with placeholders only.
- [x] `.gitignore` excluding `.env`, virtualenvs, build output, caches, and local scratch files.
- [x] `CONTRIBUTING.md` with setup, PR checklist, and no-live-API testing rule.
- [x] `SECURITY.md` with private reporting guidance and API-key handling.
- [x] `CHANGELOG.md` with initial release notes.
- [x] `.github/workflows/ci.yml` running the offline test suite.

## Safety requirements

- [x] Examples use fictional recipients and placeholder document names.
- [x] Tests are offline and use mocked HTTP responses only.
- [x] Docs clearly state that `send()` / `send_letter()` are chargeable and not idempotent.
- [x] Docs recommend preview-first workflows by default.
- [x] No live API key is required for tests or examples.

## Final checks before flipping visibility

Run from a clean checkout:

```bash
git status --short
pytest
python -m build
```

Then audit:

```bash
# Current tree, excluding intentional placeholder docs/tests
git grep -n -I -E '(BEGIN (RSA|OPENSSH|PRIVATE) KEY|Bear[e]r [A-Za-z0-9._-]+|Authori[z]ation:|pass[word]=|sec[ret]=)' -- . || true

# History smoke test for accidentally committed credentials
git log --all -p -- . ':(exclude).env.example' \
  | grep -En '(BEGIN (RSA|OPENSSH|PRIVATE) KEY|Bear[e]r [A-Za-z0-9._-]+|Authori[z]ation:|pass[word]=|sec[ret]=)' \
  | head -50 || true

# Large blobs that may be generated/private artifacts
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $3>1048576 {print $3, $4}' \
  | sort -nr
```

If any finding is a real secret or private document, rotate/revoke the credential and rewrite history before making the repository public. Do not rely on deletion in a later commit.

## Repository visibility

This PR prepares the content for public visibility. The actual GitHub visibility change should be done separately by a maintainer after reviewing the PR and confirming there are no private forks, branch protections, or release automation assumptions that depend on the repository being private.
