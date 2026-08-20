# ADR 0002: Federated CWL integration boundaries

## Status

Status: Accepted

## Context

CWL already has specialist products for identity, communication, psychometrics, temporal analysis, semantic catalogs, document viewing, data migration, retrieval fusion, authoring, and diagrams. Copying them into Orgmetra would create a monolith and duplicate ownership.

The intended modular service architecture is separately deployable leaves that still compose: Orgmetra is the employment-truth leaf; Keyverse is the identity leaf; Naruon is a composition hub for mail, calendar, and file control-plane intents. Sibling products remain linked through published adapters. Orgmetra does not absorb their application tables, and it does not treat a published protocol as a transfer of product ownership.

Buyers and operators need a stable way to ask another product for identity, an assessment snapshot, an ontology handle, a calendar intent, or a migration batch without granting Orgmetra a SQL login to that product's database. OpenAPI Specification v3.2.0 is the published HTTP contract language Orgmetra uses for versioned command and query APIs. OpenID Connect Core 1.0 incorporating errata set 2 is the published identity-layer contract Keyverse presents; Orgmetra consumes tokens and scopes through that contract and does not become the identity provider.

## Decision

Orgmetra integrates CWL products through explicit package, API, event, or adapter boundaries. No direct cross-service application-table SQL is allowed.

Each integration names an owner, a versioned contract, and a failure mode:

- Keyverse publishes OpenID Connect authentication and scope evidence. Orgmetra binds an opaque subject to a person and evaluates employment-policy authorization. Orgmetra does not store passwords, passkeys, or raw tokens, and it does not query Keyverse application tables.
- Naruon and other composition hubs receive versioned intents and emit delivery or calendar evidence. They do not become a second employment ledger.
- Psychometrics Commons, fast-mlsirm, TEPP, Semantic Data Portal, Contextual Orchestrator, Clearfolio, NewsDOM, MHTML ETL Gateway, and mightyETL remain specialists behind package, API, event, or adapter contracts. Orgmetra stores opaque references and immutable snapshots where the owning contract requires them.
- Cross-boundary HTTP uses generated OpenAPI clients. Asynchronous propagation uses versioned event envelopes. Physical co-location of databases is an operations choice, not permission to join another service's application schema.

Contracts are versioned and tested. A breaking change requires a new major contract identity. Adapter failures stay visible to the operator so the next action is retry, correct the mapping, request evidence, or escalate, not silent table-level repair in a sibling database.

## Consequences

- Services remain independently deployable and can be extracted without rewriting employment-truth ownership.
- Orgmetra keeps employment truth centralized while still composing with Keyverse, Naruon, and the other published CWL specialists.
- Adapter failures are isolated and visible; a specialist outage cannot be papered over by reading that specialist's tables.
- Contracts must be versioned and tested. OpenAPI and OpenID Connect are the published wire contracts, not a claim that Orgmetra owns identity or that a sibling owns employment facts.
- Operators can compare contract versions, export adapter evidence, and escalate a failed handoff without crossing into another product's application database.

## References

The APA 7th bibliography is maintained in `docs/doctoring/REFERENCES.md`. This ADR uses:

Cloud Native Computing Foundation. (2022). *CloudEvents specification v1.0.2*. https://github.com/cloudevents/spec/tree/ce@v1.0.2

OpenAPI Initiative. (2025, September 19). *OpenAPI Specification v3.2.0*. https://spec.openapis.org/oas/v3.2.0.html

OpenID Foundation. (2014, February 25). *OpenID Connect Core 1.0 incorporating errata set 2*. https://openid.net/specs/openid-connect-core-1_0.html
