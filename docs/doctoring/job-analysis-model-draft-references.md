# Job Analysis model-draft references

Reviewed for this active PR on 2026-08-26. These references support orchestration design, Job Analysis evidence discipline, human-accountable use, and reproducible package evidence; they do not establish autonomous employment-decision authority or certification.

## Primary orchestration research

Nielsen, S., Cetin, E., Schwendeman, P., Sun, Q., Xu, J., & Tang, Y. (2025). *Learning to orchestrate agents in natural language with the Conductor*. arXiv. https://arxiv.org/abs/2512.04388

Xu, J., Sun, Q., Schwendeman, P., Nielsen, S., Cetin, E., & Tang, Y. (2025). *TRINITY: An evolved LLM coordinator*. arXiv. https://arxiv.org/abs/2512.04695

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report*. arXiv. https://arxiv.org/abs/2606.21228

The Conductor work shows learned model-to-model communication topologies and targeted instructions. TRINITY separates coordination into dynamic Thinker/Worker/Verifier delegation. Fugu extends adaptive orchestration into a production-oriented family of orchestrator models. Orgmetra uses these as evidence that orchestration should be modular, revisioned, and provenance-bearing; it does not import their coordinator implementations or infer HR decision validity from benchmark performance.

## Personnel-selection and testing standards

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.). Society for Industrial and Organizational Psychology.

These standards support explicit construct/evidence provenance, controlled interpretation, and separation between evidence generation and consequential decision authority. In this package, model output is an untrusted proposal that requires distinct human review and remains non-authoritative until a separate Job Analysis persistence boundary revalidates it.

## Packaging evidence

Python Packaging Authority. (2026, August 8). *setuptools 84.0.0*. Python Package Index. https://pypi.org/project/setuptools/84.0.0/

PyPI reports `setuptools-84.0.0-py3-none-any.whl` with SHA-256 `51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670`. The exact-head quality lane installs that reviewed backend by hash, builds the package wheel from the exact Git checkout with build isolation disabled, computes the resulting local wheel SHA-256, and requires that same hash for the isolated install used as package evidence. Public Python support is bounded to `>=3.14,<3.15` because this lane executes exact CPython 3.14.7 rather than claiming untested future minor versions.

## Engineering interpretation

- Orchestrators may choose models/roles dynamically, but the host must retain exact request/snapshot authorization and durable provenance.
- A verifier or reviewer model is not a substitute for the accountable human reviewer required by this HR boundary.
- Task/FJA/KSAO semantic units are digest/provenance bound so generated prose can be traced back to the reviewed evidence family without storing unrestricted raw HR content in the durable receipt.
- Exact orchestration revision and route evidence are recorded because provider/model pools can change over time.
- No cited orchestration paper is treated as evidence of content validity, criterion validity, fairness, legal compliance, or authorization for an employment decision.
