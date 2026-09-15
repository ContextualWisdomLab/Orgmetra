export const AUTHENTICATED_DEPLOYMENT_EVIDENCE_OWNER = "ContextualWisdomLab/Orgmetra#395";

/**
 * Keep commercial performance acceptance fail closed until the service that
 * actually answered the timed requests is independently bound to the exact
 * source candidate. A caller-authored observed_service_sha or deployment
 * reference can be made internally consistent and later attested as bytes;
 * neither proves which deployed workload served the HTTPS origin.
 */
export function requireAuthenticatedDeploymentEvidence() {
  throw new Error(
    `commercial acceptance requires authenticated deployed-candidate evidence from ${AUTHENTICATED_DEPLOYMENT_EVIDENCE_OWNER}; caller-supplied observed_service_sha and deployment references are structural evidence only`,
  );
}
