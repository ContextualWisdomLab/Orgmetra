export const PINNED_K6_VERSION = "2.2.0";

export function requirePinnedK6Version(value) {
  if (value !== PINNED_K6_VERSION) {
    throw new Error(`commercial Employment separation performance runs require k6 ${PINNED_K6_VERSION}`);
  }
  return value;
}
