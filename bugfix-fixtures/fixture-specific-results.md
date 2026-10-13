# Synthetic fixture expectations — Visa Automatic V2

All rows contain **invented data**. The CSV header row is copied verbatim from the supplied `CANADA-TURISMO.csv` export: **235 columns**. The second column (index 1) is `Nome de usuário`, and this version's SHA-256 header fingerprint is **`b6e8522a93caa32ab790fdc605f6f4f419018dfd2fe5e45247d569ca6f97241e`** (UTF-8 JSON, no spaces, `ensure_ascii=False`). The original uploaded applicant responses are **not** included.

## Expected mapping and behavior

| Fixture | Expectation |
| --- | --- |
| `csv-google-forms.csv` | Exactly one synthetic applicant: Maria Silva; `Nome de usuário` = `maria.silva@example.com`; applicant email, **not** applicant name; verify import and canonical review. |
| `csv-with-username-email.csv` | Valid second-column username email should fill applicant email if ordinary `E-mail` is blank. |
| `csv-without-username-email.csv` | Blank `Nome de usuário` is accepted, email stays unresolved if no other source supplies it. |
| `csv-username-not-email.csv` | `user12345` is preserved as metadata; never assigned to applicant email or name. |
| `csv-conflicting-emails.csv` | Username email `maria.login@example.com`, applicant `E-mail` `maria.contact@example.com`; preserve both, applicant `E-mail` takes priority for the proposed contact email, and expose source mismatch for review. |
| `csv-multiple-applicants.csv` | Three synthetics: Maria Silva, João Costa, Ana Pereira. List 3, select exactly one, import ONLY selection. No silent import of others. |
| `csv-other-citizenship-no.csv` | `Não` => `has_other_citizenship=false`, no other-citizenship country and no second record. Primary citizenship is Brazil (`BRA`) from **separate** nationality value. |
| `csv-other-citizenship-nao.csv` | Unaccented `Nao` => false as above. |
| `csv-other-citizenship-yes.csv` | `Sim` => true, secondary country unresolved, request review; never fabricate a country. |
| `csv-other-citizenship-canada.csv` | Explicit `Canadá` as secondary country => true, secondary country `CAN`, subject to review. |
| `csv-address-trailing-number.csv` | Propose street `Rua das Flores`, number `25`; preserve original address. |
| `csv-address-leading-number.csv` | Propose street `Rua das Flores`, number `25`; preserve original address. |
| `csv-address-unit.csv` | Propose street `Rua das Flores`, number `25`, unit `302`; preserve original address. |
| `csv-address-ambiguous.csv` | Preserve raw text and mark uncertain street/number unresolved; do not invent. |
| `csv-unsupported-header.csv` | Deliberately modified second header, reject with actionable schema error; don't map by guessed position. |
| `csv-malformed-row.csv` | Intentionally 234 values against 235 headers; reject/report malformed response, never silently shift/truncate. |
| `messages-whatsapp.txt` | Parse 3 timestamped WhatsApp messages with sender/timestamp/body; preserve raw text. |
| `messages-commercial.txt` | Accept as unstructured text with appropriate warning; never invent timestamps or confirmed facts. |
| `messages-mixed.txt` | Preserve all raw text, identify parseable timestamped messages, retain nonstructured content with warnings. |

### What these files DO NOT prove

- The exact header from the uploaded 235-column Google export differs from the older **234-column** verified header mapping. Supporting it requires the **new schema profile** to map fields correctly, not generic positional offset assumptions.
- The fabricated content intentionally exercises only a subset of 235 fields. Blank values are **not** evidence that the corresponding CSV field is unsupported.
- These fixtures specify acceptance criteria; they are **not** evidence that the application currently passes these tests. Run the parser, backend persistence, and browser UI tests.
- Some fixtures intentionally fail or require review; that is expected.

### Safety

Use these files in isolated tests or synthetic staging only. They include fake passport numbers and example.com emails; no real customer records. Do not include the original customer CSV in Git, test logs, or agent input.
