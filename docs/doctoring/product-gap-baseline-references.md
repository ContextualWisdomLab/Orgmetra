# Product-gap baseline references and applied boundaries

Retrieved September 1, 2026.

This doctoring note records the external sources re-checked while replacing `docs/product-technical-gap-baseline.md` and repairing its upstream governance assumptions. A citation is evidence for a design constraint, not certification, legal advice, merge authorization, or proof that an implementation satisfies the source.

## Human-resource and selection governance

International Organization for Standardization. (2023). *ISO 30405:2023 Human resource management—Guidelines on recruitment* (2nd ed.). https://www.iso.org/standard/79488.html

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association.

### Applied boundary

Orgmetra keeps recruitment/selection evidence reviewable and attributable, preserves job/evidence provenance, and keeps model output outside autonomous employment-decision authority. Criterion-related or fairness claims require exact predictor/criterion/version linkage and scientific evidence rather than a correlation-only product claim. These sources do not establish that a particular employment decision is lawful or valid.

## Accessibility and customer interaction

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2 is a W3C Recommendation*. https://www.w3.org/WAI/news/2023-10-05/wcag22rec/

### Applied boundary

The P1 role-workspace release gate requires WCAG 2.2 AA-oriented evidence, including keyboard/focus behavior, touch-target and dragging alternatives, accessible authentication where applicable, consistent help/error semantics, exact-value alternatives for charts, responsive screenshots, and Storybook edge states. A design-token or wireframe document alone is not accessibility evidence.

## Security, privacy and AI risk

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53 Rev. 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Autio, C., Schwartz, R., Dunietz, J., Jain, S., Stanley, M., Tabassi, E., Hall, P., & Roberts, K. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.600-1

### Applied boundary

Orgmetra treats tenant/actor/purpose/resource authorization, immutable audit evidence, least privilege, retention/export/delete, recovery, provenance, and separately governed emergency access as executable control boundaries. Generative-AI output is supporting/draft evidence routed through the contextual-orchestrator boundary; it does not obtain authoritative HRIS write or employment-decision authority merely because a model response is structured. These NIST publications inform evidence readiness and risk management; they are not SOC 2, CSAP, or product certification claims.

## GitHub protected-branch and dependency-review semantics

GitHub. (n.d.). *Available rules for rulesets*. GitHub Docs. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

GitHub. (n.d.). *REST API endpoints for dependency review*. GitHub Docs. https://docs.github.com/en/rest/dependency-graph/dependency-review

GitHub. (n.d.). *Dependency graph*. GitHub Docs. https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-graph

### Applied boundary

The current one-human-maintainer governance decision uses the documented ability to set the generic required approving-review count to zero; it also disables latest-push approval because that rule requires approval from someone other than the latest pusher. The repair does **not** manufacture independence through bot/service-account approvals and does not weaken required review-thread resolution or deterministic required workflows.

For Dependency Review, an HTTP failure from the exact dependency comparison is treated as missing authoritative evidence and fails closed. Independent OSV/Trivy/SAST/Scorecard evidence is retained but is not promoted to a semantic substitute for GitHub Dependency Review.

## Traceability rule

When any cited source changes an executable invariant, the owning PR must carry a regression/contract test and the relevant ADR/TRD/API/schema/UI evidence must be updated on the same exact head. If only the prose changes, the result remains documentation evidence rather than implemented product behavior.
