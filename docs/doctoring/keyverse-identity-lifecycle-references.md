# Keyverse identity lifecycle references

Reviewed: 2026-08-22 UTC.

## Primary technical sources

Hunt, P., Grizzle, K., Wahlstroem, E., & Mortimore, C. (2015). *System for Cross-domain Identity Management: Protocol* (RFC 7644). Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc7644

Hunt, P., Grizzle, K., Wahlstroem, E., & Mortimore, C. (2015). *System for Cross-domain Identity Management: Core Schema* (RFC 7643). Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc7643

ContextualWisdomLab. (2026). *Keyverse SCIM v2 account-unification server shim* (Revision `ce207dfd42975db61c82a5963e206fc1db14ac2b`, `services/account_unification/app/scim.py`). GitHub.

## Decision use

RFC 7644/7643 establish the SCIM protocol and User resource model. The pinned Keyverse source is the authoritative implementation evidence for the foreign owner behavior Orgmetra currently reviews: the `/scim/v2/Users/{user_id}` PATCH path accepts an `active` change and deactivates the account when false, while DELETE is implemented as soft deactivation. Orgmetra records only the reviewed revision and operation descriptor; it does not copy Keyverse source, credentials, user values, or identity tables.

Because identity deactivation can materially affect a worker's access, the Orgmetra packet is deliberately non-executing and non-authorizing. Human review plus fresh authoritative Employment and identity-binding resolution remain required before any host may invoke the owner contract.
