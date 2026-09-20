# CLAUDE.md

Orgmetra is an evidence-centered HRIS/HCM system of record. Its primary responsibility is employment truth: people, employment, organizations, jobs, positions, assignments, candidate-worker linkage, performance criteria, compensation, and validated decisions.

Do not treat Orgmetra as a resume parser, ATS-only system, psychometric engine, or AI hiring bot. Those are specialist capabilities behind explicit boundaries.

## Core boundaries

- Orgmetra owns HRIS facts and employment lifecycle state.
- Keyverse owns identity and credentials.
- Psychometrics Commons owns assessment operations and immutable assessment result snapshots.
- fast-mlsirm owns psychometric numerical kernels.
- TEPP owns temporal/event/multilevel analysis artifacts.
- Semantic Data Portal owns occupation/skill/ability ontology and semantic catalog.
- Naruon owns mail/calendar/file control-plane integrations.
- Contextual Orchestrator owns model routing, provider-key discovery, capability selection, timeout/cancellation/provider-end semantics, and bounded LLM orchestration traces.

## Model-backed automation

Consume only a released `contextual-orchestrator` API/client/schema. Model-backed GitHub Actions use `orchestrator/free` through the approved gateway token; Orgmetra must not hard-code provider/model/group routing, require direct provider API keys, or choose a paid fallback. If the released orchestrator cannot provide the required capability, fail closed and repair the Contextual Orchestrator owner rather than adding local provider logic. Repository-scoped `GITHUB_TOKEN` and an approved gateway token may authenticate the consumer path but do not confer provider-routing authority.

## Writing guidance

Customer-facing copy must help the next action: approve, review, correct, request evidence, compare, export, or escalate. Avoid vague AI claims. Every high-stakes recommendation must show evidence, uncertainty, and a human decision path.
