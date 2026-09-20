# Contextual Orchestrator model-routing traceability

## Status

Active PR #51 only. This evidence becomes protected-`develop` governance truth only after the unchanged exact head satisfies fresh gates and integrates through the ordinary protected path.

| Requirement | Orgmetra consumer contract | Owner boundary | Executable evidence |
|---|---|---|---|
| Keep provider credentials out of Orgmetra model guidance | Model-backed paths authenticate through repository-scoped `GITHUB_TOKEN` and the approved gateway token; Orgmetra does not require provider API keys | released `contextual-orchestrator` | `tests/model-routing-governance.test.mjs` rejects direct provider credential names in `AGENTS.md` |
| Route model-backed GitHub Actions through the free orchestrator contract | GitHub Actions use `orchestrator/free` only | released `contextual-orchestrator` | `tests/model-routing-governance.test.mjs` requires the route in AGENTS/CLAUDE/TRD/security/traceability guidance |
| Prevent consumer-side provider/model/group or paid-fallback selection | Orgmetra does not choose provider, model, provider group, or paid fallback | released `contextual-orchestrator` owns routing/capability selection | AGENTS/TRD regression and review |
| Fail closed when the released owner lacks a capability | No local direct-provider escape hatch is permitted | Contextual Orchestrator owner is repaired before Orgmetra consumes the missing capability | AGENTS/CLAUDE/TRD/security guidance plus exact-head Foundation validation |
| Keep termination semantics in one owner | Default model timeout, user cancellation, provider-end, and administrator-timeout semantics are not reimplemented locally | released `contextual-orchestrator` | documentation contract review and absence of local routing implementation |
| Keep LLM output non-authoritative for employment decisions | Model output remains draft/verification evidence until accountable human action | Orgmetra high-impact command boundary | existing human-confirmation and audit/evidence contracts |
