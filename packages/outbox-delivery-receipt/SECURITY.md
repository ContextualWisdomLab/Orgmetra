# Security and privacy boundary

External transport receipts are attacker-controlled input until reconciled by Orgmetra.

The contract therefore:

- treats transport evidence as `untrusted_transport_evidence`;
- binds it to one tenant/outbox/audit/target/attempt coordinate;
- stores only a host-normalized opaque reference and SHA-256 digest, not raw provider
  response bodies;
- excludes HR payloads, destinations, credentials, free-form text, compensation, ratings,
  assessment outcomes, and model output;
- rejects noncanonical/sentinel UUID identities, malformed governance codes, non-UUIDv4
  normalized receipt references, invalid digests, unbounded attempt/version values, and
  impossible observation chronology;
- issues a sealed non-tuple value only after validation, retaining fields in a
  closure-private identity registry instead of a readable or replaceable object slot, so
  raw object allocation, seal cloning, and tuple reconstruction cannot expose forged
  public receipt fields;
- revalidates one immutable field snapshot on canonical export, preventing a stateful
  replacement from switching values between validation and serialization; and
- never grants authority to mutate `outbox_delivery_record`.

A consumer must not interpret a provider-reported receipt as proof that the intended human
or system actually consumed the message. It is evidence that the configured transport
reported delivery for the correlated attempt. Downstream business semantics need their
own explicit acknowledgement contract.

No secret, provider token, destination address, or raw transport payload belongs in this
evidence packet or routine logs.

This boundary does not claim cryptographic secrecy against code with arbitrary
same-process reflection, bytecode rewriting, debugger access, or native-memory access.
Hosts must isolate such untrusted code at the process/runtime boundary.
