# Naruon calendar intent traceability

## Status

Active-PR only. This evidence does not describe protected-`develop` product truth until the owning PR integrates.

| Requirement | Decision / contract | Production implementation | Executable evidence |
|---|---|---|---|
| Preserve service ownership; no cross-service table access or copied calendar implementation | ADR 0010; Naruon contract revision `ddd05c5aaf3e170aa2bdc4412647b43b95d5a6b9` | `packages/naruon-adapter/src/orgmetra_naruon_adapter/calendar.py` is transport-neutral and emits only the published `/api/calendar/writeback-intent` request shape | `test_builds_confirmed_intent_without_pii_or_provider_execution` |
| Require actor, purpose, reason, evidence version, tenant context, exact HR resource and explicit human confirmation before an external calendar intent | ADR 0010 | `CalendarIntentContext` and `_validate_context` | malformed-context, human-confirmation, action-kind and UUID/reference regressions |
| Do not leak HR identifiers or free-form PII into calendar summary text | ADR 0010 | fixed `_ACTION_SUMMARIES`; audit context is kept separate from request body | `test_builds_confirmed_intent_without_pii_or_provider_execution` |
| Do not mutate a provider while the current foreign create-execution contract is defective | Naruon owner handoff in `ContextualWisdomLab/naruon#1350`; ADR 0010 | request body always sets `execute_provider=false`; response validator rejects any reported provider execution or execution metadata | response-drift parameter matrix |
| Fail closed on Naruon contract/provenance drift | ADR 0010 | `validate_calendar_intent_response` requires exact response/provenance keys, CalDAV/customer-owned mode, create semantics, target consistency, intent-only status and bounded metadata | response-drift parameter matrix plus auto-selected-target regression |
| Keep local adapter evidence exact and independently reproducible | Orgmetra quality rules | `.github/workflows/foundation-ci.yml` checks exact candidate SHA, reviewed hashed test dependencies, compilation, 100% statement/branch coverage and clean checkout | hosted exact-head Foundation CI run plus local RED/GREEN development evidence |
| Use current authoritative calendar/HTTP references without duplicating provider protocol logic | ADR 0010 | no CalDAV/iCalendar implementation in Orgmetra | `docs/doctoring/naruon-calendar-intent-references.md` |

## Foreign-owner revalidation gate

Provider-executed create is not part of this slice. After the Naruon owner repairs the exact create/If-Match defect, Orgmetra must refetch the protected Naruon contract, add a new RED acceptance case for the published execution behavior, and prove a fresh exact-head GREEN path before any Orgmetra API may claim provider writeback succeeded. Pre-repair owner comments, predecessor SHAs, or intent-only success do not satisfy that gate.
