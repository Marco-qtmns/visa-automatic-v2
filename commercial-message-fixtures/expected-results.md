# Expected results — synthetic commercial messages

## Safety invariants (all CM-01..CM-25)

1. Store and allow retrieval of the exact supplied source text (except documented line-ending normalization). Do not drop unsupported lines or claim text was verified WhatsApp metadata.
2. Never fabricate senders, timestamps, identities, sponsor/host names, family relationships or citizenship. Messages with `@Equipe` are internal handoffs; they do not imply the named consultant is a sponsor or host.
3. All statements are source evidence, not confirmed canonical facts. If a supported configured extractor produces candidates, they remain reviewable; do not auto-confirm. A disabled extractor must not run and must not block message import.
4. Sponsor and host are separate concepts: financial support is not necessarily hosting; accommodation is not necessarily financial sponsorship. Partial funding must remain qualified.
5. Uncertain language (`talvez`, `pode ser`, `ainda não sabemos`) => unknown, not `false` or `true`. Conflicts => review, not silent selection of one assertion.
6. For minors, identify that staff must verify age, parents/guardians, accompanying adult and any required consent/guardianship documents; do not assume a legal conclusion or fabricate consent.
7. Multiple people in a message do not authorize creation/mutation of multiple Cases or cross-applicant assignment.
8. Do not broaden the automated fact catalog without explicit approval. Currently audited catalog keys: `sponsor.exists`, `host.exists`, `trip.payer` only.

## Expected classifications / review notes

| ID | Sponsor | Host | Key requirement |
| --- | --- | --- | --- |
| CM-01 | no | no | Adult self-funded traveler staying in hotel |
| CM-02 | yes | no | Financial sponsor in Brazil; hotel, no Canadian host |
| CM-03 | no | yes | Canadian host offers accommodation but not financial sponsorship |
| CM-04 | yes | yes | Same person is sponsor and host |
| CM-05 | yes | yes | Separate sponsor and host |
| CM-06 | yes | no | Minor accompanied by both parents; parents pay |
| CM-07 | yes | no | Minor accompanied by mother; father funds |
| CM-08 | yes | yes | Minor traveling without parents; parental support and Canadian grandparent host |
| CM-09 | yes | yes | Minor traveling with one parent; separate sponsor and host |
| CM-10 | unknown | unknown | Minor with unresolved legal guardianship and arrangements |
| CM-11 | unknown | unknown | Referral linking mother to prior child case; do not reuse child identity |
| CM-12 | mixed | no | Two applicants in message; payer shared; separate applicants |
| CM-13 | no | yes | Accommodation-only host; do not treat as full sponsor |
| CM-14 | yes | yes | Partial support; sponsor scope must be reviewed |
| CM-15 | unknown | unknown | Tentative arrangements are unknown, not confirmed yes/no |
| CM-16 | conflict | no | Conflicting and later updated funding information; require review |
| CM-17 | no | conflict | Host changed from hotel to friend; preserve change |
| CM-18 | no | no | Visa representative is neither sponsor nor host |
| CM-19 | yes | yes | Organization may be host and partial payer; travel purpose requires review |
| CM-20 | unknown | unknown | Do not invent host identity or sponsor |
| CM-21 | mixed | mixed | Multiple applicants; avoid cross-case contamination |
| CM-22 | yes | no | Valid Android WhatsApp export |
| CM-23 | no | yes | Valid iOS WhatsApp export |
| CM-24 | unknown | unknown | Minor school group, guardian and payer unknown |
| CM-25 | unknown | unknown | Third-party referral; uncertainty and no invented applicant facts |

`yes`/`no`/`unknown` above indicate the message's express or uncertain claims for **reviewable suggestions**, never automatic authoritative values. `mixed` means separate people have separate funding roles; `conflict` means the text contains contradictory or changed information. The term `sponsor` means financial support rather than necessarily a formal IRCC sponsor category.

## Format-specific expectations

- CM-22: Android WhatsApp messages with 3 timestamps, speakers and bodies.
- CM-23: iOS WhatsApp messages with 3 timestamps, speakers and bodies.
- CM-16, CM-17: mixed WhatsApp plus narrative text; preserve both; warnings permitted if metadata cannot be verified.
- All other `.txt`: commercial/plain-text handoffs. Missing WhatsApp headers must not reject raw text. Sender and time may remain null unless reliably parsed.

## Regression checks

- Content digest and text preserved on import and readback.
- Reimport of an identical file into the same synthetic Case: existing deduplication behavior remains intact; do not create duplicate copies.
- Disabled fact extraction: import successful, no new extraction-run row, manual review possible.
- Enabled supported extractor: proposed candidates only for supported keys, no unsourced certainty, conflicts visible.
- Different synthetic Cases: source data never crosses Cases.
