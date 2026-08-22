# Contextual Orchestrator draft-evidence references

Retrieved 2026-08-22. These sources inform orchestration architecture only; they do not establish personnel-selection validity, fairness, or legal compliance.

## Official technical contract

ContextualWisdomLab. (2026). *Contextual Orchestrator OpenAPI contract* (Version 0.1.0, revision e226e1197bdfc890c9d8e5b9b648c78857d7e465) [Source code]. GitHub. https://github.com/ContextualWisdomLab/contextual-orchestrator/blob/e226e1197bdfc890c9d8e5b9b648c78857d7e465/contextual_orchestrator/api_contract.py

The reviewed contract exposes authenticated `POST /v1/responses` and requires `model` plus `input`. Orgmetra records that exact dependency revision and route instead of copying the foreign service.

## Primary research

Nielsen, S., Cetin, E., Schwendeman, P., Sun, Q., Xu, J., & Tang, Y. (2026). *Learning to orchestrate agents in natural language with the Conductor*. International Conference on Learning Representations. https://openreview.net/pdf?id=U23A2BUKYt

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* (arXiv:2606.21228). arXiv. https://arxiv.org/abs/2606.21228

Xu, J., Sun, Q., Schwendeman, P., Nielsen, S., Cetin, E., & Tang, Y. (2026). *TRINITY: An evolved LLM coordinator*. International Conference on Learning Representations. https://openreview.net/pdf?id=5HaRjXai12

## Design interpretation

TRINITY demonstrates learned turn-by-turn role assignment among heterogeneous LLMs; Conductor demonstrates learned communication topology and worker instruction; Fugu extends these ideas into dynamically generated agentic scaffolds. These results support preserving exact orchestration provenance because the effective computation can span multiple models and coordination steps. They do **not** justify treating the resulting text as an authoritative HR fact or decision. Accordingly, Orgmetra binds request/response/provenance digests and human-review state while withholding employment-decision authority from model output.
