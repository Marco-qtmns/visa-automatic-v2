# Commercial-message synthetic fixtures — Visa Automatic V2

These are entirely fictional commercial-intake messages written in Brazilian Portuguese. The provided `Commercial_message.txt` was used only as a **format/style reference**; no real applicant identity is included.

## Intended use
- Import each `.txt` separately into a disposable synthetic Case.
- Use paste mode for `plain` messages; use WhatsApp text export mode for `android` and `ios` examples; `mixed` is intentionally nonuniform.
- Verify full text preservation, candidate parsing, source provenance, warnings and safe review behavior.
- `cases.json` provides scenario IDs, expected sponsor/host state and message format.
- `expected-results.md` specifies requirements and important limits.
- A case with multiple people is NOT permission to create multiple applicants automatically.

## Crucial extraction limitation
The currently inspected V2 `backend/app/services/fact_catalog.py` allows **only** `sponsor.exists`, `host.exists`, and `trip.payer` for automated fact extraction. These fixture descriptions are **human-expected semantics**; names, kinship, guardianship, age, organization identity, travel details etc. must NOT be expected as automatic extracted fact keys without a separately approved extension.

All names and organizations in fixtures are invented; `Northern Example Institute` is fictional.
