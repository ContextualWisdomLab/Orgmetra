# ADR 0007: Govern candidate-to-worker conversion lineage

- Status: Accepted on active PR #24; not protected-main truth
- Date: 2026-08-17
- Owners: Orgmetra employment-truth boundary

## Context

The foundation schema contains a legacy `candidate_worker_link` that can associate a candidate directly with a person using only tenant, candidate, person, and link timestamp. That shape cannot prove which employment relationship resulted from the conversion, which human-confirmed hiring decision authorized it, which versioned evidence supported that decision, or what business-effective and system-recorded intervals were known later.

A candidate becoming a worker is a high-impact employment transition. Orgmetra therefore needs a durable fact that preserves hiring provenance without copying assessment payloads or necessary PII into a shadow record.

## Decision

New writes to `candidate_worker_link` are closed. Historical rows remain readable and append-only for compatibility, but are explicitly legacy evidence until migrated through a governed process that can establish real provenance without inventing facts.

New conversions use `candidate_worker_conversion_record`. Each record is tenant-scoped and binds exactly one candidate profile to the resulting person, employment, and selection decision. The employment/person composite foreign key proves that the employment belongs to the worker. The selection decision must:

1. belong to the same tenant and candidate;
2. have `decision_code = 'hire'`;
3. preserve non-empty actor, purpose, reason, and human-confirmation references;
4. consume a versioned evidence set sealed by that exact decision; and
5. contain at least one versioned evidence member.

The conversion cannot be recorded before the hiring decision or become business-effective before the decision date. Conversion history preserves both effective/business time and recorded/system time. Overlapping simultaneously visible conversions for one candidate are rejected using a bitemporal exclusion constraint. Corrections may only close an open recorded interval before a replacement fact is inserted; in-place business mutation and deletion fail closed.

The new relation forces tenant row-level security and uses opaque UUID identities. It stores references to authoritative decision/evidence facts rather than duplicating candidate assessment or personal data.

## Consequences

- Buyers can reconstruct who was converted, into which employment, under which confirmed hiring decision, based on which versioned evidence, at both business and knowledge coordinates.
- Legacy candidate links cannot silently create new employment lineage.
- Historical legacy rows are not assigned synthetic actors, decisions, confirmations, or evidence. Migration must either establish genuine source provenance or retain them as explicitly legacy records.
- The API/service layer can apply finer purpose-bound authorization without changing this persistence contract.
- This decision changes only Orgmetra-owned persistence. Keyverse and other CWL dedicated-writer repositories remain read-only dependencies.

## Evidence and standards basis

NIST SP 800-162 defines attribute-based access-control decisions in terms of subject, object, requested operation, and relevant environment attributes; Orgmetra keeps the durable actor/purpose/evidence facts needed for that authorization boundary rather than collapsing them into an opaque link. NIST Privacy Framework 1.0 informs the minimization and accountability posture: the conversion record keeps opaque references and governance metadata while authoritative PII remains in its owning HRIS facts.

Executable acceptance evidence is `tests/test_bitemporal_postgres.sh`, including rejection of the legacy direct-link path, successful human-confirmed hire conversion, non-hire denial, bitemporal conflict denial, immutable-history enforcement, and forced tenant RLS. APA 7 references are recorded in `docs/doctoring/CANDIDATE_WORKER_CONVERSION_REFERENCES.md`.
