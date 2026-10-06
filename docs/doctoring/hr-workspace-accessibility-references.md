# HR Workspace accessibility references

## Scope

These references support the protected-read interaction-state proof in the active stacked UI PR. They do not claim certification or default-branch integration.

## APA 7 references

World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

## Applied decision

The Storybook proof uses a status region for ordinary progress/completion, alert semantics for denial/error, `aria-busy` while protected work is in flight, a native disabled control to prevent a duplicate submission in the loading state, and visible keyboard focus using the existing Orgmetra focus token. Customer-facing failure copy always names the next action instead of exposing an internal transport or storage mechanism.
