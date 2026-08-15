# Operability

## SLO candidates

- HRIS core read availability: 99.9% for production deployments.
- High-impact command audit append success: 99.99% within accepted maintenance windows.
- Integration adapter error visibility: every failed outbound command produces an operator-safe event.

## Degraded modes

- Keyverse unavailable: existing sessions may continue until policy expiry; new identity provisioning is paused.
- Psychometrics Commons unavailable: assessment result fetches show unavailable state, not invented scores.
- Contextual Orchestrator unavailable: AI drafting disabled; manual workflows continue.
- Semantic Data Portal unavailable: ontology enrichment disabled; approved job profiles continue.

## Backups

- HRIS PostgreSQL requires encrypted backups and restore rehearsals.
- Audit/provenance records require immutability and tamper evidence.
- Object-store artifacts require retention and deletion policy.

## Incident classes

- authorization failure
- evidence integrity failure
- integration outage
- bitemporal corruption
- LLM draft hallucination detected
- validation study discrepancy
- migration reconciliation failure
