# ADR-0023: Governed TEPP analysis-request boundary

**Status:** Proposed on active PR
**Decision owner:** Orgmetra
**Foreign owner:** TEPP (read-only dependency)

## Context

Orgmetra needs temporal/event analytical evidence for workforce validation without duplicating TEPP kernels or violating dedicated-writer ownership. TEPP protected revision `7c29e7c971d7940e1fb3def1ed3aae2d1bc8ad4a` exposes `AnalysisRunRequest` contract v1 in `tepp_api`, with immutable snapshot identity, knowledge cutoff, model contract, output profile, and idempotency key. The same TEPP revision documents that protected main is not yet a production HTTP service.

A direct HTTP client in Orgmetra would therefore overstate foreign runtime maturity. Conversely, copying TEPP's analytical implementation would create split scientific authority and an acquisition-grade integration liability.

## Decision

Orgmetra owns a small pre-transport adapter that:

1. emits exactly the seven fields accepted by TEPP `AnalysisRunRequest` v1;
2. pins the reviewed TEPP protected revision and contract version as evidence, not as permission to mutate TEPP;
3. binds the request to an Orgmetra tenant, validation study, accountable actor, immutable snapshot digest, evidence version, and deterministic request digest;
4. detaches the knowledge cutoff and generation instant to exact UTC datetimes, canonicalizes them to RFC 3339 UTC, and rejects naive or unusable instants;
5. distinguishes exact same-key retries from same-key semantic conflicts;
6. treats opaque correlations as linkable personal/governance data while refusing direct identity values, source text, and credentials at this boundary;
7. performs no network transport until the host proves a compatible executable TEPP service contract is published and authorized; and
8. treats returned TEPP/LLM output as untrusted analytical evidence requiring accountable human scientific review before any high-impact employment use.

Orgmetra does not read TEPP application tables, mutate TEPP source/configuration, or reimplement TEPP's temporal/event/statistical kernels.

## Consequences

The integration can be unit-tested and audited now without manufacturing runtime evidence. Future transport can be added behind the same adapter only after TEPP publishes an executable service contract; that future change must add consumer/provider compatibility, timeout/deadline, authentication, retry, observability, privacy, and failure-mode tests against the then-current foreign contract.

The adapter deliberately requires host re-resolution of tenant/workspace/snapshot/model/output authority. Syntax validation alone never proves tenant membership, artifact existence, policy applicability, or scientific suitability.
