# Orgmetra Compensation Change Review

`orgmetra-compensation-change-review` defines a portable, value-minimized evidence envelope for reviewing a proposed compensation change before any authoritative HRIS mutation or payroll execution.

## What the packet carries

The packet correlates one tenant, Person, Employment, active Assignment/Job/Position scope snapshot, current compensation snapshot, proposed compensation plan, exact compensation policy, pay-equity review, budget authorization, payroll handoff plan, requester, reviewer, business effective date, and evidence version. Trust-bearing artifacts use canonical UUID-backed opaque references; evidence artifacts also carry independent lowercase SHA-256 digests.

The envelope intentionally **does not carry salary, wage, bonus, benefit, equity, protected-attribute, credential, or free-form case/model values**. Opaque Person/Employment and evidence references still create sensitive personal-data correlation, so the packet explicitly reports `contains_personal_data = true` rather than claiming anonymity.

## Human and system boundary

A valid packet is not an approval. It remains:

- `decision_authority = human_review_only`;
- `review_state = requires_human_review`;
- `scope_verification_state = requires_authoritative_resolution`;
- `mutation_state = not_authorized_to_apply`; and
- `external_execution_state = not_authorized_to_execute`.

Immediately before approval, the host must re-resolve every reference in the packet tenant, prove requester/reviewer resolve to distinct authoritative actor identities, prove the Person-to-Employment and active Assignment/Job/Position scope, and verify the exact current/proposed compensation evidence, compensation policy, pay-equity review, budget authorization, effective date, and payroll-handoff provenance. Any authorized HRIS change then goes through Orgmetra's authoritative People boundary. Payroll execution remains behind the payroll owner's published contract.

## Example

```python
from datetime import date, datetime, timezone
from orgmetra_compensation_change_review import build_compensation_change_review_packet

packet = build_compensation_change_review_packet(
    tenant_record_id="11111111-1111-4111-8111-111111111111",
    compensation_review_reference="compensation_change_review:22222222-2222-4222-8222-222222222222",
    person_record_reference="person_record:33333333-3333-4333-8333-333333333333",
    employment_record_reference="employment_record:44444444-4444-4444-8444-444444444444",
    active_assignment_snapshot_reference="active_assignment_snapshot:55555555-5555-4555-8555-555555555555",
    active_assignment_snapshot_digest="a" * 64,
    current_compensation_snapshot_reference="compensation_snapshot:66666666-6666-4666-8666-666666666666",
    current_compensation_snapshot_digest="b" * 64,
    proposed_compensation_plan_reference="compensation_plan:77777777-7777-4777-8777-777777777777",
    proposed_compensation_plan_digest="c" * 64,
    compensation_policy_reference="compensation_policy:88888888-8888-4888-8888-888888888888",
    compensation_policy_digest="d" * 64,
    pay_equity_review_reference="pay_equity_review:99999999-9999-4999-8999-999999999999",
    pay_equity_review_digest="e" * 64,
    budget_authorization_reference="budget_authorization:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    budget_authorization_digest="f" * 64,
    payroll_handoff_plan_reference="payroll_handoff_plan:bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    payroll_handoff_plan_digest="1" * 64,
    requester_reference="actor:cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    reviewer_reference="actor:dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    purpose_code="compensation_change_review",
    reason_code="annual_compensation_review",
    proposed_effective_on=date(2026, 10, 1),
    generated_at=datetime.now(timezone.utc),
)
```

`packet.sha256_digest()` is immutable correlation evidence only. It is not proof that pay is fair, lawful, budgeted, approved, applied in the HRIS, or executed in payroll.
