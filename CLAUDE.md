# CLAUDE.md

Orgmetra is an evidence-centered HRIS/HCM system of record. Its primary responsibility is employment truth: people, employment, organizations, jobs, positions, assignments, candidate-worker linkage, performance criteria, compensation, and validated decisions.

Do not treat Orgmetra as a resume parser, ATS-only system, psychometric engine, or AI hiring bot. Those are specialist capabilities behind explicit boundaries.

## Core boundaries

- Orgmetra owns HRIS facts and employment lifecycle state.
- Keyverse owns identity and credentials.
- Psychometrics Commons owns assessment operations and immutable assessment result snapshots.
- fast-mlsirm owns psychometric numerical kernels.
- TEPP owns temporal/event/multilevel analysis artifacts.
- ConceptWeave owns ontology and semantic-layer observe/discover/propose/align/validate/review/publish workflows and immutable semantic releases.
- semantic-data-portal owns catalog, governance, search, serving, and consumption of released semantic resources; it does not author Orgmetra domain truth.
- Naruon owns mail/calendar/file control-plane integrations.
- contextual-orchestrator owns bounded LLM orchestration traces, provider discovery, capability-aware routing, and gateway contracts; Orgmetra consumes only released APIs and schemas.

## Writing guidance

Customer-facing copy must help the next action: approve, review, correct, request evidence, compare, export, or escalate. Avoid vague AI claims. Every high-stakes recommendation must show evidence, uncertainty, and a human decision path.
