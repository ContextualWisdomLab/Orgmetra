const SUPPORTED_SUMMARY_VERSION = "1.0.0";

function fail(message) {
  throw new Error(message);
}

function plainObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail(`${label} must be an object`);
  }
  return value;
}

function nonEmptyString(value, label) {
  if (typeof value !== "string" || value.trim() === "") fail(`${label} must be a non-empty string`);
  return value;
}

function nonNegativeInteger(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) fail(`${label} must be a non-negative safe integer`);
  return value;
}

function finiteNumber(value, label, { minimum = 0, maximum = Number.POSITIVE_INFINITY } = {}) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < minimum || value > maximum) {
    fail(`${label} must be a finite number between ${minimum} and ${maximum}`);
  }
  return value;
}

function indexMetrics(entries, label, occupiedNames = new Set()) {
  if (!Array.isArray(entries)) fail(`${label} must be an array`);
  const index = new Map();
  for (const [position, entry] of entries.entries()) {
    const metric = plainObject(entry, `${label}[${position}]`);
    const name = nonEmptyString(metric.name, `${label}[${position}].name`);
    if (occupiedNames.has(name) || index.has(name)) fail(`${label} contains duplicate metric ${name}`);
    index.set(name, metric);
  }
  return index;
}

function requireMetric(index, name, type, label) {
  const metric = index.get(name);
  if (!metric) fail(`${label} must contain metric ${name}`);
  if (metric.type !== type) fail(`${label}.${name}.type must be ${type}`);
  return plainObject(metric.values, `${label}.${name}.values`);
}

function counterValue(index, name, label) {
  const values = requireMetric(index, name, "counter", label);
  return nonNegativeInteger(values.count, `${label}.${name}.values.count`);
}

function rateValue(index, name, label) {
  const values = requireMetric(index, name, "rate", label);
  const matches = nonNegativeInteger(values.matches, `${label}.${name}.values.matches`);
  const total = nonNegativeInteger(values.total, `${label}.${name}.values.total`);
  if (matches > total) fail(`${label}.${name}.values.matches cannot exceed total`);
  const rate = finiteNumber(values.rate, `${label}.${name}.values.rate`, { maximum: 1 });
  const expectedRate = total === 0 ? 0 : matches / total;
  if (Math.abs(rate - expectedRate) > Number.EPSILON * 8) {
    fail(`${label}.${name}.values.rate must equal matches / total`);
  }
  return Object.freeze({ matches, total, rate });
}

function trendValue(index, name, label) {
  const values = requireMetric(index, name, "trend", label);
  return Object.freeze({
    "p(50)": finiteNumber(values["p(50)"], `${label}.${name}.values.p(50)`),
    "p(95)": finiteNumber(values["p(95)"], `${label}.${name}.values.p(95)`),
    "p(99)": finiteNumber(values["p(99)"], `${label}.${name}.values.p(99)`),
    max: finiteNumber(values.max, `${label}.${name}.values.max`),
    count: nonNegativeInteger(values.count, `${label}.${name}.values.count`),
  });
}

export function normalizeEmploymentSeparationK6V2Summary(summary, { expectedK6Version, trendName }) {
  const document = plainObject(summary, "k6 summary");
  if (document.version !== SUPPORTED_SUMMARY_VERSION) {
    fail(`k6 summary version must be ${SUPPORTED_SUMMARY_VERSION}`);
  }
  const metadata = plainObject(document.metadata, "k6 summary.metadata");
  const declaredK6Version = nonEmptyString(metadata.k6Version, "k6 summary.metadata.k6Version");
  const requiredK6Version = nonEmptyString(expectedK6Version, "expectedK6Version");
  if (declaredK6Version !== requiredK6Version) {
    fail(`k6 summary k6 version must equal ${requiredK6Version}`);
  }
  const requiredTrendName = nonEmptyString(trendName, "trendName");

  const results = plainObject(document.results, "k6 summary.results");
  const ordinaryMetrics = indexMetrics(results.metrics, "k6 summary.results.metrics");
  const checks = plainObject(results.checks, "k6 summary.results.checks");
  const checkMetrics = indexMetrics(
    checks.metrics,
    "k6 summary.results.checks.metrics",
    new Set(ordinaryMetrics.keys()),
  );

  const iterations = counterValue(ordinaryMetrics, "iterations", "k6 summary.results.metrics");
  const latencySamples = counterValue(
    ordinaryMetrics,
    "employment_separation_latency_samples",
    "k6 summary.results.metrics",
  );
  const unexpected = rateValue(
    ordinaryMetrics,
    "employment_separation_unexpected_response",
    "k6 summary.results.metrics",
  );
  const trend = trendValue(ordinaryMetrics, requiredTrendName, "k6 summary.results.metrics");

  const checksTotal = counterValue(checkMetrics, "checks_total", "k6 summary.results.checks.metrics");
  const checksSucceeded = rateValue(checkMetrics, "checks_succeeded", "k6 summary.results.checks.metrics");
  const checksFailed = rateValue(checkMetrics, "checks_failed", "k6 summary.results.checks.metrics");
  if (
    checksSucceeded.total !== checksTotal
    || checksFailed.total !== checksTotal
    || checksSucceeded.matches + checksFailed.matches !== checksTotal
  ) {
    fail("k6 check aggregate metrics must describe the same complete check population");
  }

  return Object.freeze({
    summary_version: SUPPORTED_SUMMARY_VERSION,
    summary_k6_version: declaredK6Version,
    metrics: Object.freeze({
      iterations: Object.freeze({ values: Object.freeze({ count: iterations }) }),
      checks: Object.freeze({
        values: Object.freeze({
          rate: checksSucceeded.rate,
          passes: checksSucceeded.matches,
          fails: checksFailed.matches,
        }),
      }),
      employment_separation_unexpected_response: Object.freeze({
        values: Object.freeze({
          rate: unexpected.rate,
          passes: unexpected.matches,
          fails: unexpected.total - unexpected.matches,
        }),
      }),
      employment_separation_latency_samples: Object.freeze({
        values: Object.freeze({ count: latencySamples }),
      }),
      [requiredTrendName]: Object.freeze({ values: trend }),
    }),
  });
}
