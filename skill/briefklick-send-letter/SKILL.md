---
name: briefklick-send-letter
description: Use when previewing or sending physical letters via BriefKlick, including German registered mail, postal status, tracking, pricing or balance. Not email.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# BriefKlick letters

BriefKlick prints and posts real physical mail. **Every send is real and billed; there is no send sandbox.** Preview is the default, using `/create` + `/preview`: not billed or dispatched and works without balance, but it uploads private letter content and addresses to BriefKlick. A local-only preview/test request does not authorize that upload; explain the disclosure and obtain permission or keep rendering local. An explicit BriefKlick preview request authorizes that preview, not dispatch.

## Canonical preview → confirm → send → status flow

1. Preserve exact supplied sender/recipient spelling, street, city, country and postal-code strings (including leading zeros). Never silently correct a mismatch; ask if it prevents reliable delivery. Preflight the PDF: at most 20 MB and 90 pages. Confirm supported countries through `/countries` when not known. Use `BriefKlickClient.from_env()` / `BRIEFKLICK_API_KEY`, never hardcoded or printed secrets.
2. With upload authorization, call `preview_letter()` or `create_document()` + `preview()`. Save and show the final rendered PDF. Preview is not sent. Inspect generated pages rather than assuming rendering succeeded.
3. Before sending, show the exact recipient, service, pages and current price from `get_pricing()`, and check `get_balance()` (Eurocents). Obtain explicit confirmation for this final preview and these dispatch details. A prior general “send a letter” request is not confirmation of unseen generated content or inferred details. If anything changes, preview/show and confirm again. Low balance (<1000 cents) warrants a warning; insufficient balance blocks sending, not previewing.
4. After confirmation, send once with `send(doc.id, einschreiben=...)`, reusing the preview document ID. Do not use the convenience `send_letter()` to bypass the preview gate.
5. Read back `get_status(order.id)` and report order ID, charged price and actual state: `NEW` is queued, `SENT` is dispatched (not proof of delivery), `ERROR` is failure. Include tracking when available. Use bounded polling only if needed; do not promise arrival from an API acknowledgement.

On ambiguous send timeout/server failure, reconcile with order status/account evidence before any retry. If no order ID is known and reconciliation is unavailable, report uncertain dispatch and ask for account/support verification; never resend blindly or claim it failed safely.

## Service mapping

| Request | Service |
|---|---|
| Normal/unspecified letter | `Einschreiben.NORMAL` (0) |
| Einwurf-Einschreiben | `Einschreiben.EINWURF` (1) |
| Einschreiben / registered / signature required | `Einschreiben.STANDARD` (2) |
| Rückschein / return receipt | Unsupported; ask whether STANDARD or another provider is acceptable. Never silently substitute. |

The default service must still be shown in the pre-send confirmation. A preview-only request stops after the preview; it never proceeds to confirmation/send automatically.

For SDK installation, the two-stage code recipe, pricing/status and exception types, load `references/api-workflow.md`. No external send or preview upload is a safe maintenance test; use mocked transport tests.
