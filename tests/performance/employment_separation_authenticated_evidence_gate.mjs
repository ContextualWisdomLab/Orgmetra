const AUTHENTICATED_EVIDENCE_OWNER = "ContextualWisdomLab/.github#2162";

/**
 * Block commercial acceptance while exact performance evidence has no
 * organization-owned authenticated attestation path. Local byte/digest
 * consistency is useful structural evidence, but it is not an authority
 * boundary because the same caller can replace both bytes and self-asserted
 * digests. The gate is removed only after the released central owner contract
 * is consumed and verified at the acceptance entry point.
 */
export function requireAuthenticatedPerformanceEvidence() {
  throw new Error(
    `commercial acceptance requires authenticated performance-evidence attestation from ${AUTHENTICATED_EVIDENCE_OWNER}; local result/runtime/fixture bytes and caller-supplied digests are structural evidence only`,
  );
}

export { AUTHENTICATED_EVIDENCE_OWNER };
