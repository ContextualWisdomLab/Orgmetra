const PERFORMANCE_PROFILES = new Set(["first_commit", "replay", "rejection", "contention"]);
const HTTPS_ORIGIN_PREFIX = "https://";
const DNS_OR_IPV4_HOST_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$/;
const BRACKETED_IP_LITERAL_PATTERN = /^\[[0-9A-Fa-f:.]+\]$/;

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function invalidHttpsOrigin() {
  throw new Error("ORGMETRA_PERFORMANCE_BASE_URL must be an authenticated HTTPS origin");
}

function requireValidPort(value) {
  if (!/^\d{1,5}$/.test(value)) invalidHttpsOrigin();
  const port = Number(value);
  if (!Number.isSafeInteger(port) || port < 1 || port > 65535) invalidHttpsOrigin();
}

export function requireGovernedSeparationHttpsOrigin(value) {
  if (typeof value !== "string" || value === "" || value !== value.trim()) invalidHttpsOrigin();
  if (!value.startsWith(HTTPS_ORIGIN_PREFIX)) invalidHttpsOrigin();

  let authority = value.slice(HTTPS_ORIGIN_PREFIX.length);
  const slash = authority.indexOf("/");
  if (slash !== -1) {
    if (slash !== authority.length - 1 || authority.lastIndexOf("/") !== slash) invalidHttpsOrigin();
    authority = authority.slice(0, -1);
  }
  if (
    authority === ""
    || authority.includes("@")
    || authority.includes("?")
    || authority.includes("#")
    || /[\u0000-\u0020\u007f]/.test(authority)
  ) invalidHttpsOrigin();

  if (authority.startsWith("[")) {
    const closingBracket = authority.indexOf("]");
    if (closingBracket < 2) invalidHttpsOrigin();
    const host = authority.slice(0, closingBracket + 1);
    if (!BRACKETED_IP_LITERAL_PATTERN.test(host) || !host.includes(":")) invalidHttpsOrigin();
    const suffix = authority.slice(closingBracket + 1);
    if (suffix !== "") {
      if (!suffix.startsWith(":")) invalidHttpsOrigin();
      requireValidPort(suffix.slice(1));
    }
  } else {
    const colon = authority.lastIndexOf(":");
    if (colon !== authority.indexOf(":")) invalidHttpsOrigin();
    const host = colon === -1 ? authority : authority.slice(0, colon);
    if (!DNS_OR_IPV4_HOST_PATTERN.test(host) || host.includes("..")) invalidHttpsOrigin();
    if (colon !== -1) requireValidPort(authority.slice(colon + 1));
  }

  return `${HTTPS_ORIGIN_PREFIX}${authority}`;
}

export function governedSeparationRequestParams(headers, profile) {
  if (!isPlainObject(headers)) {
    throw new Error("Employment-separation request headers must be a plain object");
  }
  if (!PERFORMANCE_PROFILES.has(profile)) {
    throw new Error(`unsupported Employment-separation performance profile: ${profile}`);
  }
  return {
    headers,
    redirects: 0,
    tags: { profile },
  };
}
