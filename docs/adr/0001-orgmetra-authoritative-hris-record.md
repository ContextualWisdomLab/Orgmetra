# ADR 0001: Orgmetra owns authoritative HRIS records

## Status

Status: Accepted

## Context

Orgmetra must become a full HRIS/HCM platform, not merely a resume screening tool. Selection validity requires post-hire outcome evidence, and outcome evidence requires durable people, employment, job, assignment, performance, and decision records.

A hiring workflow may also need to prepare reviewed evidence for an accountable human before the authoritative selection decision is recorded. That pre-decision material must not become a shadow decision store, duplicate candidate PII, or make model output authoritative merely because it was presented to a reviewer.

## Decision

Orgmetra owns the authoritative record for people, employment, organization, jobs, positions, assignments, candidate-worker linkage, performance criteria, criterion observations, compensation, employment transitions, selection decisions, and validity studies.

Pre-decision selection-review packets are non-authoritative evidence views. They may carry only opaque resource/provenance references and governance metadata needed to identify the candidate, Job, exact sealed evidence set, accountable reviewer, purpose, reason, and evidence version. They must require an explicit human decision and must not contain candidate PII, assessment values, recommendation scores, or free-form model output. When model-backed material is referenced, its draft and provenance references travel together and remain explicitly untrusted draft evidence.

## Consequences

- External services may provide evidence, identity, assessment snapshots, document rendering, or analysis artifacts.
- External services do not own employment truth.
- Orgmetra must provide strong audit, retention, and purpose-bound access.
- Human-review packets cannot finalize hiring, promotion, termination, compensation, or another high-impact employment action; final authority remains the governed Orgmetra decision mutation and immutable audit boundary.
