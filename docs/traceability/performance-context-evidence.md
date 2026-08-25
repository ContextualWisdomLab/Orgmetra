# Performance context evidence traceability

## Truth boundary

- **Protected-`develop` truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has performance cycles and criterion observations but no governed performance-context evidence packet.
- **Active PR truth:** PR #93 adds `PerformanceContextEvidencePacket` and its exact-head quality gate.
- **Accepted architecture:** Orgmetra remains the authoritative HRIS owner; context evidence is value-minimized provenance, not a cross-service database join and not a numerical estimation kernel.
- **Planned after integration:** authoritative persistence/audit binding for durable distributed uniqueness; governed statistical use in validity/workforce analysis with scientifically relevant multilevel, cross-classified, multiple-membership, and temporal structure.
- **Out of scope:** automated rating adjustment, causal attribution to manager/context, compensation or employment decisions, raw manager identity, raw performance scores, and writes to dedicated-writer dependency repositories.

## Requirement mapping

| Requirement | Evidence | Verification |
| --- | --- | --- |
| Preserve opportunity-to-perform provenance | `opportunity_to_perform_digest` | SHA-256 format and canonical-evidence tests |
| Preserve multiple-membership context | bounded sorted Assignment/Organization tuples plus `membership_weight_digest` | deterministic collection and adversarial runtime tests |
| Preserve business time separately from system time | half-open exact-date context window plus timezone-aware `generated_at` | chronology and timestamp canonicalization tests |
| Minimize sensitive evidence | fixed `contains_performance_rating=false`, `contains_manager_identity=false`, `contains_hr_values=false` | direct-construction and canonical-document tests |
| Require accountable human review | distinct requester/reviewer plus fixed purpose/reason | separation and fixed-governance tests |
| Prevent automated high-impact decisions | fixed context-only/review/authority states and governed `next_action` | direct-construction tests |
| Fail closed on runtime polymorphism | exact built-in strings, ints, dates, datetimes, tuples | hostile subclass and collection-subclass tests |
| Detect evidence rewriting | process-local creation digest | post-issuance mutation tests |
| Preserve one live reference binding across idempotent duplicates | shared weak live-binding object retained by every live duplicate | conflicting reissuance plus duplicate-garbage-collection regression |
| Exact owned production coverage | package quality workflow | hash-bound installed-wheel pytest with 100% statement/branch gate |

## Buyer-visible next action

A validation or workforce analyst must re-resolve the referenced HRIS scope and source snapshots under current authorization, verify the four digests, and explicitly choose how context is represented in the governed analysis. The packet must never be used to silently overwrite an individual criterion, rating, or employment outcome.
