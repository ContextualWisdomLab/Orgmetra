# Orgmetra Job Analysis model-draft boundary

This package is an **active pull-request capability, not protected-main truth**. It governs model-assisted drafting for Job Analysis without giving an LLM, orchestrator, or draft receipt authority to change authoritative Job Analysis records or make employment decisions.

## What the workflow does

The host supplies one exact tenant-qualified Job Analysis snapshot plus a non-empty, canonically ordered set of semantic units covering all three evidence families: **Task**, **FJA**, and **KSAO**. Each semantic unit carries bounded runtime text, an opaque reference, an exact SHA-256 content digest, and an exact source-provenance digest. Raw semantic text is available only for the authorized runtime call and is not copied into the durable receipt.

Execution is deliberately ordered:

1. Revalidate the exact tenant, Job Analysis reference, snapshot digest, purpose, and requesting actor through the injected authoritative scope resolver.
2. Only after authorization succeeds, pass the governed request to an injected model-orchestration adapter. Contextual Orchestrator remains a read-only dedicated-writer dependency; this package does not import its private implementation or query its application tables.
3. Bind the untrusted model draft to its SHA-256 digest, exact reviewed orchestration revision, orchestration-evidence digest, and opaque model-route reference.
4. Require a **different human reviewer** to confirm the draft for later authoritative review or reject it with a controlled reason.
5. Issue value-minimized, tamper-evident durable evidence, including the exact authority-evidence digest used for the scope decision. Raw Task/FJA/KSAO text and raw model output are excluded from the receipt.

A human-confirmed draft is still marked `not_authorized_for_job_analysis_persistence`. The only next action is submission through the authoritative Job Analysis persistence boundary, which must re-resolve the current Job Analysis truth and make its own authorization/audit decision.

## Trust and integrity rules

Trust-bearing strings, integers, tuples, booleans, and datetimes use exact built-in runtime types to prevent caller-defined equality, hashing, ordering, or serialization behavior from changing what was checked versus what is recorded. Packet-owned references use canonical UUIDv4 suffixes; authoritative tenant identity accepts canonical non-sentinel operational UUIDs so it remains compatible with the HRIS tenant contract.

The workflow snapshots request evidence before authority/model/human calls and rejects post-validation mutation. It also snapshots the model provenance before human review. Durable receipts can only be issued by the workflow and are sealed outside writable receipt fields with a process-local weak registry. That seal is defense in depth only; durable distributed uniqueness, authorization, and immutable audit/outbox remain responsibilities of the authoritative host transaction.

## Model orchestration is not decision authority

Fugu, Conductor, and TRINITY show useful patterns for dynamically coordinating heterogeneous models and separating proposal, work, and verification roles. Orgmetra uses those findings only as orchestration design evidence. They do **not** justify autonomous Job Analysis publication, candidate screening, ranking, selection, compensation, performance, or other high-impact employment decisions. Model output remains untrusted draft evidence and accountable human review is mandatory before it can be considered by an authoritative HR boundary.
