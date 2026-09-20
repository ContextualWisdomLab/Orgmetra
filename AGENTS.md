# AGENTS.md

## Mission

Build Orgmetra as a commercial-grade, evidence-centered HRIS and HCM platform that connects job analysis, selection, employment, performance outcomes, and validation evidence across the employment lifecycle.

## Hard rules

- Never bypass branch protection, required checks, independent review, OpenCode, Noema, Strix, SAST, or Security Scan gates.
- Never self-approve or manufacture approval evidence.
- Model-backed product and GitHub Actions behavior must consume a released `contextual-orchestrator` contract. GitHub Actions use `orchestrator/free` through the approved gateway token; Orgmetra does not require direct provider credentials, hard-code provider/model/group selection, or select a paid fallback. Repository-scoped `GITHUB_TOKEN` and an approved gateway token are consumer authentication material, not provider-routing authority.
- If a required model capability is unavailable through the released Contextual Orchestrator contract, fail closed and repair the capability in the Contextual Orchestrator owner. Provider-key discovery, routing, timeout defaults, user cancellation, provider-end, and administrator-timeout semantics remain Contextual Orchestrator responsibilities and are not reimplemented in Orgmetra.
- Never make LLM output an autonomous high-impact employment decision.
- Never copy another CWL product into Orgmetra when an adapter/package/API/event boundary is sufficient.
- Never directly query another service's application database.
- Never store raw credentials or passkeys in Orgmetra person records.
- Never blanket-mask PII in ways that make HR work unusable; use purpose-bound authorization, least privilege, encryption, retention, audit, export controls, and field-level access decisions.

## Database rules

- Owned database objects use descriptive two-or-more-word `snake_case` names.
- 3NF is the default for HRIS facts.
- Bitemporal facts keep effective time and system-recorded time separately.
- Person, employment, organization, job, position, and assignment are separate concepts.

## Documentation rules

Keep README, PRD, TRD, ARCHITECTURE, DATA_MODEL, ERD, UML, API_CONTRACT, SECURITY, THREAT_MODEL, TEST_STRATEGY, OPERABILITY, TRACEABILITY, ADRs, doctoring references, AGENTS, CLAUDE, and CHANGELOG current with code. Distinguish shipped protected default branch truth from active PRs, accepted architecture, planned work, research-only work, superseded work, and out-of-scope work.

## Quality rules

- Production code requires beginner-readable public docstrings.
- Owned production statement and branch coverage targets are 100% where tooling exposes them.
- Mathematical and psychometric production compute is Rust-first with CPU multithreading and GPU parity where material.
- Psychometric tests must include true-parameter recovery, bias/MAE/RMSE/coverage/convergence, and temporal/multilevel/multiple-membership evidence when relevant.
