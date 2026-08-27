# HR Workspace document retrieval accessibility references

Status: primary-source design references for active PR #132. These sources support interaction semantics only; they do not grant HR authorization, legal entitlement, export authority, or employment-decision authority.

## References (APA 7)

World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

## Applied interpretation

- Progress messages that do not require immediate intervention use a polite `status` live region.
- Permission denial, expired authorization, and retrieval/audit failure use an assertive `alert` because the user's requested protected action cannot continue.
- `aria-busy=true` is bound only to authorizing, reading, and auditing states; duplicate submission is disabled while those phases are active.
- Completion is explicitly read-only and tells the HR user what to do next without implying export or employment-decision authority.
- Visible keyboard focus uses the existing Orgmetra `--orgmetra-focus-ring` token and `:focus-visible` contract inherited from the parent protected-read interaction slice.

Primary references were rechecked on 2026-08-28. WCAG 2.2 remains the final W3C Recommendation used here; ongoing WCAG 2.x errata/editorial work is not treated as a new conformance version.
