# Security Policy

## Supported versions

Security fixes are accepted for the current `main` branch. Released package versions will be listed in `CHANGELOG.md` once distribution begins.

## Reporting a vulnerability

Please report security issues privately instead of opening a public issue.

Preferred route:

- Open a private GitHub security advisory for this repository, if available.
- If advisories are not available, contact the maintainer through the GitHub profile listed on the repository.

Include:

- A concise description of the issue.
- A minimal reproduction that does not use real API keys or private letter contents.
- Affected version or commit.
- Any relevant logs with secrets redacted.

## Secret handling

`briefklick-python` authenticates with the `apikey` HTTP header. Treat `BRIEFKLICK_API_KEY` like a password.

- Store it in environment variables or a local `.env` file.
- Never commit `.env` files, live keys, generated private letters, or real recipient data.
- Rotate the BriefKlick API key immediately if it is exposed.

## Operational safety

`send()` and `send_letter()` create real, chargeable physical mail. A timeout or 5xx during a send is ambiguous: the order may or may not have been accepted by BriefKlick. Do not automatically retry send operations without reconciling the account/dashboard first.
