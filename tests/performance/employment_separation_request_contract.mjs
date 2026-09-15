const PERFORMANCE_PROFILES = new Set(["first_commit", "replay", "rejection", "contention"]);

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
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
