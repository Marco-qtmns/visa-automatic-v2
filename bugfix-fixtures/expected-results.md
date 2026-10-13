# Visa Automatic V2 — Bug Fix Acceptance Specification

**Target branch:** `integrate-new-changes`  
**Purpose:** Define exact expected behavior for bugs discovered during Raspberry Pi testing.  
**Scope:** CSV imports, canonical intake, address normalization, citizenship, IMM5257 purpose, commercial messages, and fact extraction.

## 1. Global implementation requirements

1. Work exclusively on `integrate-new-changes`. Do not merge into `main`.
2. Preserve the existing V2 database architecture, migration history, canonical data model, audit trail, and provenance system.
3. Reuse existing parsing, normalization, import preview, and canonical decision services.
4. Never silently overwrite confirmed canonical information.
5. Do not infer information that is not supported by the source.
6. Preserve original source values even when a normalized value is proposed.
7. Changes originating from imported data must remain reviewable.
8. Do not reset databases or modify real applicant data.
9. Do not automatically deploy, commit, push, or merge.
10. Implement regression tests for every acceptance case below.

A fix is complete only when the specified behavior works through the relevant backend API and, where applicable, the employee frontend.

---

## 2. CSV Import

### CSV-01 — Existing verified CSV format

**Given:** A CSV using the currently supported verified Google Forms header layout with exactly one applicant response.

**When:** An employee uploads the CSV.

**Expected:**
- The file is accepted.
- Exactly one applicant response is parsed.
- Import preview displays all supported mapped information.
- Existing canonical values remain protected by review and conflict rules.
- Header names, duplicate headers, and column order are preserved.
- Raw source information and provenance remain available.

**Must not:**
- Break existing verified formats.
- Shift columns.
- Drop unknown source values.
- Automatically confirm ambiguous information.

**Pass:** Existing CSV import regression tests continue to pass.

## CSV-02 — Google Forms `Nome de usuário` field

**Problem:** The second CSV column has the header `Nome de usuário`. Google Forms uses this column to store the respondent's email address. The current importer does not interpret it correctly and may reject the CSV or incorrectly treat the value as a name.

**Input example:**

- Column position: 2 (zero-based index 1)
- Header: `Nome de usuário`
- Value: `applicant@example.com`

**Expected behavior:**

1. Recognize `Nome de usuário` as a Google Forms respondent email field when its value is a valid email address.
2. Map the value to the applicant's contact email (`contact.email`), following the existing canonical import and review workflow.
3. Never map this value to `identity.family_name`, `identity.given_names`, or any other name field.
4. Obtain the applicant's name exclusively from the actual applicant name fields in the CSV.
5. Preserve the original column header and value for provenance.
6. If the CSV also contains a separate applicant email field:
   - If identical, use the email without creating a conflict.
   - If different, preserve both sources and require employee review.
7. Recognize this Google Forms export layout as a supported CSV variant without weakening the validation of other columns.
8. Do not change the meaning or position of unrelated CSV fields.

**Acceptance test:**

Given a CSV containing:

- `Nome de usuário` = `applicant@example.com`
- Applicant's actual name = `Maria Silva`

After import preview:

- Applicant email = `applicant@example.com`
- Applicant name = `Maria Silva`
- Email must not appear in any name field.
- No `CSV_SCHEMA_MISMATCH` error solely because of the recognized `Nome de usuário` header.

## CSV-03 — `Nome de usuário` does not contain an email

**Input examples:**

- `Nome de usuário` = `user123`
- `Nome de usuário` = empty string

**Expected behavior:**

1. Do not interpret non-email values as an applicant email address.
2. Never interpret them as the applicant's name.
3. Preserve the original value as source metadata.
4. Keep the applicant's email unresolved if no valid email is available elsewhere.
5. Do not reject an otherwise supported CSV solely because this value is empty or not an email.

**Acceptance test:** The CSV is parsed without fabricating an email or name.

## CSV-04 — Google Forms CSV layout compatibility

**Problem:** The current strict CSV header validation does not accept the Google Forms layout containing the second-column header `Nome de usuário`.

**Expected behavior:**

1. Support the exact Google Forms layout containing this column.
2. Update the appropriate verified header mapping or register this layout as an additional supported schema profile.
3. Preserve support for previously verified CSV exports.
4. Keep all other field mappings unchanged unless an actual schema difference requires a separately verified mapping.
5. Continue rejecting genuinely unsupported or ambiguous header layouts.
6. Do not remove header validation or replace it with unrestricted positional guessing.

**Acceptance tests:**

- Original verified CSV layout: accepted.
- Google Forms CSV with `Nome de usuário` in column 2: accepted.
- Valid email in `Nome de usuário`: mapped to applicant email, not name.
- Other applicant fields: mapped exactly as intended.
- Unsupported CSV layouts: safely rejected.

### CSV-05 — Useful schema mismatch errors

**Given:** An unsupported CSV layout.

**Expected:**
- Reject the import safely.
- Display a useful error identifying:
  - Missing required headers.
  - Unexpected headers.
  - Duplicated or ambiguous headers.
  - Relevant column-count problems.
- No application or canonical data is written.
- The employee receives an actionable explanation.

**Pass:** Errors are more specific than the current generic `CSV_SCHEMA_MISMATCH: unknown, missing or reordered Canada headers`.

---

## 3. Multiple applicant responses

### CSV-06 — Multiple responses in one CSV

**Given:** A CSV with three valid applicant responses.

**When:** The file is uploaded.

**Expected:**
1. Parse the file into three independent response candidates.
2. Show a response-selection interface before applying the import.
3. Display a safe identifier for each response:
   - Response number.
   - Applicant name, if available.
   - Applicant email, if available.
   - Submission timestamp, if available.
4. Permit selection of exactly one response.
5. Show the normal import preview for that response only.
6. Apply the import only after explicit employee confirmation.
7. Do not create or modify records from unselected responses.

**Pass:** Selecting response 2 imports only response 2.

### CSV-07 — No response selected

**Given:** Several responses exist but no selection has been made.

**Expected:**
- Import confirmation is disabled.
- The interface asks the employee to select an applicant.
- No database changes occur.

**Pass:** Import cannot proceed without selection.

### CSV-08 — Single response

**Given:** A CSV containing exactly one applicant response.

**Expected:**
- Automatically select the sole response for preview.
- Continue using the existing review workflow.
- Do not add an unnecessary selection step.

**Pass:** Existing single-response workflow remains convenient and functional.

### CSV-09 — Invalid or duplicate responses

**Expected:**
- Blank rows are ignored.
- Malformed responses are identified by response number.
- One invalid row must not be silently substituted with another.
- A selection must be tied to the exact source file and response identity.
- If the file changes after preview, require a new preview before confirmation.
- Import retry and deduplication protections remain operational.

---

## 4. Residential address

### ADDR-01 — Street name and number imported

**Given:** CSV field `Endereço completo` contains:

`Rua das Flores, 25, Centro, Brasília - DF, 70000-000`

**Expected proposed values:**

| Canonical field | Value |
|---|---|
| `applicant.residential_address.street_name` | `Rua das Flores` |
| `applicant.residential_address.street_number` | `25` |
| `applicant.residential_address.postal_code` | `70000-000` |
| `applicant.residential_address.city` | `Brasília` only if unambiguously identified |
| `applicant.residential_address.state_province` | `DF` only if unambiguously identified |

The complete original address is retained in `unstructured_source_text`.

If individual parts cannot be identified reliably, preserve them as unresolved source text.

**Pass:** The canonical intake interface displays `Rua das Flores` and `25` as reviewable values.

### ADDR-02 — Alternative address formats

| Input | Expected street name | Expected number |
|---|---|---|
| `Rua das Flores 25` | `Rua das Flores` | `25` |
| `25 Rua das Flores` | `Rua das Flores` | `25` |
| `Av. Paulista, 1578` | `Av. Paulista` | `1578` |
| `Rua das Flores, 25, Apto 302` | `Rua das Flores` | `25` |

For the last example, propose unit `302` when recognized confidently.

**Pass:** Each address is parsed into the expected fields without losing the original text.

### ADDR-03 — Ambiguous address

**Given:** `Centro, Brasília, próximo ao shopping`.

**Expected:**
- Retain the complete text.
- Do not fabricate a street name or street number.
- Mark unresolved components for employee review.
- Do not block preservation of the original source.

**Pass:** No invented address components are stored.

### ADDR-04 — Canonical synchronization

**Given:** An imported address has valid parsed street information.

**Expected:**
- Import preview shows the source address and proposed components.
- Accepted components populate the appropriate canonical address entity.
- Canonical Intake displays the persisted values after refreshing.
- Existing confirmed values are not overwritten without a review decision.
- The employee can manually correct all address components.

**Pass:** The values remain visible after saving, refreshing, and reopening the Case.

---

## 5. Other citizenship

### CIT-01 — Portuguese negative answer

**Given:** The CSV answers `Não` to whether the applicant has another citizenship.

**Expected:**
- Normalize the answer to Boolean `false`.
- Store or propose `person_biographies.has_other_citizenship = false`.
- Do not create a secondary citizenship record.
- Do not require an ISO-3 country code for a negative answer.
- Keep the applicant's primary citizenship unchanged.
- Preserve the original Portuguese value.

**Pass:** `Não` is represented as *No other citizenship* without requesting `BRA`, `CAN`, or another country.

### CIT-02 — Equivalent negative answers

**Inputs:** `Nao`, `Não`, `No`, `False`.

**Expected:** All normalize to Boolean `false` in this specific yes/no question context.

**Pass:** No secondary citizenship is created.

### CIT-03 — Positive answer without country

**Given:** `Sim`, with no secondary country specified.

**Expected:**
- Normalize to Boolean `true`.
- Mark the secondary citizenship country as unresolved.
- Request employee input for the country.
- Do not invent an ISO-3 code.

**Pass:** The system records the positive answer while keeping the missing country unresolved.

### CIT-04 — Positive answer with country

**Given:** The applicant explicitly identifies Canada as an additional citizenship.

**Expected:**
- `has_other_citizenship = true`.
- Propose `CAN` as the ISO-3166 alpha-3 code.
- Require the existing appropriate review before confirmation.
- Preserve the original country text.

**Pass:** A valid country can be represented without confusing the Boolean answer with the country code.

### CIT-05 — Primary citizenship protection

**Given:** Primary citizenship is `BRA`.

**When:** The CSV states `Não` for additional citizenship.

**Expected:**
- Primary citizenship remains `BRA`.
- Secondary citizenship is absent.
- `has_other_citizenship` becomes `false`.

**Must not:** Convert `Não` to `BRA`, replace the primary citizenship, or create a second `BRA` record.

---

## 6. IMM5257 purpose of visit

### PURPOSE-01 — Explain the field

**Current issue:** The field `IMM5257 purpose code` has no explanation.

**Expected UI:**
- Label: `Purpose of visit to Canada (IMM5257)`.
- Short help text: `Select the purpose category used on the official Canadian visitor visa application. This is separate from your detailed travel-purpose description.`
- A dropdown or equivalent controlled selection rather than an unexplained free-text field.

### PURPOSE-02 — Supported values

**Expected:**
- Derive available categories and their exact stored codes from the versioned official IMM5257 template or generator mapping.
- Show understandable category names to employees.
- Store only values supported by the existing generator.
- Do not invent codes or assume that the displayed label is the stored code.
- Include `Unresolved / not selected` until the employee makes a selection.

**Pass:** The selected value is accepted by the backend and maps correctly to the generated IMM5257 field.

### PURPOSE-03 — Travel description remains separate

**Given:**
- Travel description: `Visiting family in Toronto for two weeks`.
- Employee selects the appropriate official purpose category.

**Expected:**
- Preserve the full free-text description.
- Store the official category separately in `trip.imm5257_purpose_code`.
- Do not derive or confirm the official code automatically from the description.

**Pass:** Both values remain distinct and survive refresh.

### PURPOSE-04 — Invalid code

**Given:** An unsupported purpose code is submitted through the API.

**Expected:**
- Reject the unsupported value with a clear validation error.
- Do not persist or mark it confirmed.
- Preserve the previously confirmed value, if one exists.

---

## 7. Commercial messages and WhatsApp parsing

### MSG-01 — Standard WhatsApp export

**Given:** A standard WhatsApp conversation export with supported timestamps and sender headers.

**Expected:**
- Parse messages into structured records.
- Preserve each original message body.
- Extract timestamp and sender only when present and valid.
- Continue supporting existing accepted WhatsApp formats.

**Pass:** Existing WhatsApp parser regression tests remain successful.

### MSG-02 — Plain commercial conversation

**Given:**

Customer: Hello, I want to apply for a Canadian visitor visa.

Agent: Do you already have a passport?

Customer: Yes, it expires in 2029.

**Expected:**
- Accept the content as unstructured conversation text.
- Preserve the complete original text.
- Do not reject the entire input because it lacks WhatsApp timestamp headers.
- Do not fabricate message timestamps or authenticated sender identities.
- Display the content for employee review.
- Do not automatically create confirmed canonical facts.

**Pass:** The text is stored and can be reviewed without a `Line did not match a supported WhatsApp header` rejection.

### MSG-03 — Unsupported structured format

**Given:** A file claims to be a standard WhatsApp export, but its headers are malformed.

**Expected:**
- Return an actionable parsing warning or error.
- Preserve the distinction between verified WhatsApp messages and unstructured text.
- Allow explicitly choosing a plain-text import mode when appropriate.
- Do not silently label unstructured text as a verified WhatsApp export.

**Pass:** The employee understands the problem and can select the correct import mode.

### MSG-04 — Mixed text

**Given:** A commercial conversation contains headings, plain text, and some timestamped messages.

**Expected:**
- Preserve all original source text.
- Parse only identifiable structured messages.
- Retain unsupported portions for manual review.
- Clearly report unparsed portions.
- Do not silently discard information.

**Pass:** No source text is lost.

---

## 8. Fact extraction

### EXT-01 — Extraction provider disabled

**Given:** A conversation has been successfully stored, but `FACT_EXTRACTION_PROVIDER=disabled`.

**Expected:**
- Display: `Automatic fact extraction is disabled. The conversation was saved and is available for manual review.`
- Do not treat disabled extraction as a conversation-import failure.
- Do not automatically start an extraction run that is known to be disabled.
- Provide a clear manual-review workflow.

**Pass:** Successfully stored source text remains available even though automatic extraction is disabled.

### EXT-02 — Manual fact review

**Expected:**
- Employees can read the imported conversation.
- Employees can manually add or confirm supported canonical information through existing review functionality.
- Manual decisions retain source references and appropriate audit information.
- No LLM is required to complete manual review.

**Pass:** A fact from the conversation can be manually reviewed and saved using existing authorized workflows.

### EXT-03 — Enabled provider

**Given:** A supported extraction provider is explicitly configured.

**Expected:**
- Extraction can create reviewable candidate facts.
- Candidate facts are not automatically confirmed.
- Raw conversation content and candidate provenance remain accessible.
- Provider failures do not delete or corrupt the original conversation.

**Must not:** Enable external AI automatically, introduce a new external AI dependency, or send applicant data to a third-party provider without explicit configuration.

---

## 9. Regression and integration tests

Implement focused automated tests for all identifiers:

- `CSV-01` through `CSV-09`
- `ADDR-01` through `ADDR-04`
- `CIT-01` through `CIT-05`
- `PURPOSE-01` through `PURPOSE-04`
- `MSG-01` through `MSG-04`
- `EXT-01` through `EXT-03`

Use synthetic fixture data.

Where useful, extend the existing tests rather than create duplicate test modules.

Backend coverage must verify parsing, normalized values, provenance, persistence, conflict handling, and validation.

Frontend coverage must verify response selection, user-facing errors, address fields, purpose selection, and extraction-disabled messaging.

### Required final checks

1. All newly added regression tests pass.
2. Previously passing affected tests remain passing.
3. Frontend builds successfully.
4. No unintended schema or Alembic migration changes.
5. Existing source imports remain backward compatible.
6. No source record is silently discarded, reassigned to another applicant, or automatically confirmed without authorization.
7. Relevant changes persist correctly after database readback and UI refresh.

---

## 10. Implementation boundaries

Prefer modifying existing relevant modules, particularly:

- `canada/source_readers.py`
- `canada/verified_intake.py`
- `backend/app/services/canada_imports.py`
- `backend/app/services/address_normalization.py`
- `backend/app/services/country_normalization.py`
- `backend/app/config/canada_import_mapping.py`
- `frontend/src/components/CanonicalIntakeSection.tsx`
- `frontend/src/components/CanadaImportSection.tsx`

Locate conversation parsing and extraction modules using a targeted repository search.

Do not refactor unrelated modules.

Do not replace the V2 canonical data model.

Do not remove source provenance, conflict detection, or review requirements to make tests pass.

Avoid broad repository analysis unless a test demonstrates a cross-module dependency.

If the official IMM5257 template does not establish a safe code mapping, leave that mapping unresolved and report the exact missing information instead of inventing it.

---

## 11. Completion report

Return a concise report containing:

**Implemented:** Fixes completed, referencing their test IDs.

**Tests:** Passing and failing counts for backend and frontend.

**Compatibility:** Confirmation of preserved database architecture and existing import formats.

**Unresolved:** Only genuinely unresolved issues, with the exact reason.

**Deployment:** Not performed.

**Git:** No automatic commit, push, or merge.

The branch remains `integrate-new-changes` until explicitly instructed otherwise.