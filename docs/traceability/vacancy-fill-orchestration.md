# Vacancy fill orchestration traceability

## State

- Protected-main truth: authoritative purpose-bound Assignment creation already exists on `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`.
- Active-PR truth: `feat/vacancy-fill-orchestration` adds fresh vacancy re-resolution before that mutation path.
- Planned: Position freeze/correction remains outside this slice and must use its own authoritative bitemporal mutation contract.

## Requirement mapping

| Requirement | Implementation | Regression evidence |
|---|---|---|
| Do not trust cached vacancy/UI state | `VacancyFillAuthority.verify_vacancy_fill()` is invoked for every fill after pre-authorization | happy-path authority-call assertion; mismatch/capacity drift cases |
| No protected staffing oracle for unauthorized callers | exact Assignment target is purpose-authorized before the vacancy resolver runs | wrong-purpose test proves resolver and mutation port remain untouched |
| Preserve Job/Position/Assignment separation | fill delegates only to existing `AssignmentMutationCommand` / `create_assignment_record()` | mutation port records Assignment only; Employment/Position methods are forbidden in fixture |
| Preserve effective time | verification `effective_on` must equal command `effective_from` | effective-date drift regression |
| Preserve tenant/worker/Position scope | verification tenant, Employment, Person, and Position must match the command exactly | independent mismatch regressions |
| Preserve human review evidence | confirmation reference and evidence version must match exact reviewed command | confirmation/evidence-version drift regressions |
| Prevent seat overfill | fresh available allocation must be at least the requested allocation; persistence retains authoritative seat-capacity checks | insufficient-allocation regression plus existing Assignment mutation boundary |
| Prevent runtime-type forgery | trust-bearing command and verification primitives use exact built-in runtime types before equality/comparison | hostile `str`/`Decimal` and post-construction command mutation regressions |
| Minimize evidence | verification contains opaque IDs, effective date, staffable status, allocation capacity, confirmation/version, and review state only | redacted repr regression; no PII/value fields in contract |
| Keep final mutation authoritative/auditable | orchestration delegates unchanged command to `create_assignment_record()` after fresh verification | happy-path persistence assertion; existing mutation contract owns audit/outbox/idempotency |

## Buyer behavior

An authorized workforce operator can request one Assignment fill against a reviewed vacancy. Orgmetra authorizes the exact target, re-resolves authoritative staffing truth, rejects stale or insufficient vacancy evidence, and only then crosses the existing Assignment mutation boundary. The verification itself never grants hire, compensation, or employment-decision authority.
