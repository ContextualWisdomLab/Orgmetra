# Employee profile assignment-history read — primary references

## Current authoritative references

National Institute of Standards and Technology. (2020). *Zero trust architecture* (NIST Special Publication 800-207). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-207

National Institute of Standards and Technology. (2023). *A zero trust architecture model for access control in cloud-native applications in multi-cloud environments* (NIST Special Publication 800-207A). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-207A

## Why these sources matter to PR #142

NIST SP 800-207 treats authentication and authorization as resource-access decisions rather than implicit consequences of network location. SP 800-207A extends granular identity-based policy enforcement to application/service boundaries. PR #142 applies that principle narrowly: the People API authorizes the exact tenant, person, purpose, operation, and requested fields before the protected assignment-history port is called.

These references support the **authorization boundary**, not a claim of NIST certification or compliance. Orgmetra's bitemporal representation remains governed by its own accepted ADR 0003 and authoritative Assignment model. The references do not justify deriving employment decisions, ratings, compensation actions, or inferred worker characteristics from history records.

## Review date

Rechecked against official NIST publication pages on 2026-08-28. Re-review these references if NIST publishes a superseding final revision that materially changes application-level authorization guidance.
