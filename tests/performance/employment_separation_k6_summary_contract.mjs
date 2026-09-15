const SUPPORTED_TREND_STATS = Object.freeze(["p(50)", "p(95)", "p(99)", "max", "count"]);

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

function exactStringArray(value, expected, label) {
  if (!Array.isArray(value) || value.length !== expected.length) {
    fail(`${label} must equal ${expected.join(", ")}`);
  }
  for (let index = 0; index < expected.length; index += 1) {
    if (value[index] !== expected[index]) fail(`${label} must equal ${expected.join(", ")}`);
  }
}

function requireMetric(metrics, name, type) {
  const metric = plainObject(metrics[name], `k6 summary.metrics.${name}`);
  if (metric.type !== type) fail(`k6 summary.metrics.${name}.type must be ${type}`);
  return plainObject(metric.values, `k6 summary.metrics.${name}.values`);
}

function counterValue(metrics, name) {
  return nonNegativeInteger(requireMetric(metrics, name, "counter").count, `k6 summary.metrics.${name}.values.count`);
}

function rateValue(metrics, name) {
  const values = requireMetric(metrics, name, "rate");
  const passes = nonNegativeInteger(values.passes, `k6 summary.metrics.${name}.values.passes`);
  const fails = nonNegativeInteger(values.fails, `k6 summary.metrics.${name}.values.fails`);
  const total = passes + fails;
  if (!Number.isSafeInteger(total)) fail(`k6 summary.metrics.${name} sample total must be a safe integer`);
  const rate = finiteNumber(values.rate, `k6 summary.metrics.${name}.values.rate`, { maximum: 1 });
  const expectedRate = total === 0 ? 0 : passes / total;
  if (Math.abs(rate - expectedRate) > Number.EPSILON * 8) {
    fail(`k6 summary.metrics.${name}.values.rate must equal passes / total`);
  }
  return Object.freeze({ passes, fails, rate });
}

function trendValue(metrics, name) {
  const values = requireMetric(metrics, name, "trend");
  return Object.freeze({
    "p(50)": finiteNumber(values["p(50)"], `k6 summary.metrics.${name}.values.p(50)`),
    "p(95)": finiteNumber(values["p(95)"], `k6 summary.metrics.${name}.values.p(95)`),
    "p(99)": finiteNumber(values["p(99)"], `k6 summary.metrics.${name}.values.p(99)`),
    max: finiteNumber(values.max, `k6 summary.metrics.${name}.values.max`),
    count: nonNegativeInteger(values.count, `k6 summary.metrics.${name}.values.count`),
  });
}

export function normalizeEmploymentSeparationK6Summary(summary, { expectedK6Version, trendName }) {
  const document = plainObject(summary, "k6 summary");
  if (Object.prototype.hasOwnProperty.call(document, "version")) {
    fail("pinned k6 2.2 machine-readable summary cannot supply required p(99) and trend count evidence");
  }
  const options = plainObject(document.options, "k6 summary.options");
  exactStringArray(options.summaryTrendStats, SUPPORTED_TREND_STATS, "k6 summary.options.summaryTrendStats");
  const requiredK6Version = nonEmptyString(expectedK6Version, "expectedK6Version");
  const requiredTrendName = nonEmptyString(trendName, "trendName");
  const metrics = plainObject(document.metrics, "k6 summary.metrics");

  const iterations = counterValue(metrics, "iterations");
  const latencySamples = counterValue(metrics, "employment_separation_latency_samples");
  const unexpected = rateValue(metrics, "employment_separation_unexpected_response");
  const checks = rateValue(metrics, "checks");
  const trend = trendValue(metrics, requiredTrendName);

  return Object.freeze({
    summary_contract: "k6-legacy-handle-summary",
    summary_k6_version: requiredK6Version,
    metrics: Object.freeze({
      iterations: Object.freeze({ values: Object.freeze({ count: iterations }) }),
      checks: Object.freeze({ values: checks }),
      employment_separation_unexpected_response: Object.freeze({ values: unexpected }),
      employment_separation_latency_samples: Object.freeze({ values: Object.freeze({ count: latencySamples }) }),
      [requiredTrendName]: Object.freeze({ values: trend }),
    }),
  });
}
