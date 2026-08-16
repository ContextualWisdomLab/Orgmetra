# AGENTS.md

## Mission

Build Orgmetra as a commercial-grade, evidence-centered HRIS and HCM platform that connects job analysis, selection, employment, performance outcomes, and validation evidence across the employment lifecycle.

## Hard rules

- Never bypass branch protection, required checks, independent review, OpenCode, Noema, Strix, SAST, or Security Scan gates.
- Never self-approve or manufacture approval evidence.
- Never use `COPILOT_GITHUB_TOKEN` as a development model credential. Use `NVIDIA_NIM_API_KEY` for model-backed tests and OpenCode development paths.
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
