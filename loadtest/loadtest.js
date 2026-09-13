/**
 * Stress / load test for the rate-limiting reverse proxy.
 *
 * Usage:
 *   k6 run loadtest.js
 *
 * Override target/host/path via env vars, e.g.:
 *   k6 run -e BASE_URL=http://localhost:8000 -e TARGET_HOST=api.myapp.com -e TARGET_PATH=/login loadtest.js
 *
 * Produces:
 *   - report.json   (raw k6 summary data)
 *   - report.html   (human-readable report: RPS, latency, status breakdown, thresholds)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TARGET_HOST = __ENV.TARGET_HOST || 'localhost';
const TARGET_PATH = __ENV.TARGET_PATH || '/health';

// Custom metrics so the report can break down pass/reject/error explicitly,
// not just rely on k6's generic http_req metrics.
const allowedCount = new Counter('rl_allowed_200');
const rejectedCount = new Counter('rl_rejected_429');
const serverErrorCount = new Counter('rl_server_error_5xx');
const unexpectedCount = new Counter('rl_unexpected_status');
const rateLimitedLatency = new Trend('rl_latency_ms', true);

export const options = {
  // By default k6 only includes avg/min/med/max/p(90)/p(95) in summary
  // 'values' output — p(99) is still used for thresholds either way, but
  // won't show up in report.json/report.html unless listed here.
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
  scenarios: {
    // Stage 1: gentle ramp to find the knee in the latency curve.
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '20s', target: 20 },
        { duration: '20s', target: 50 },
        { duration: '20s', target: 100 },
        { duration: '20s', target: 200 },
        { duration: '20s', target: 0 },
      ],
      gracefulRampDown: '5s',
      exec: 'rampScenario',
    },
    // Stage 2: sustained burst at the same instant, to catch race conditions
    // right at the rate-limit boundary (many concurrent requests, same bucket).
    boundary_burst: {
      executor: 'per-vu-iterations',
      vus: 20,
      iterations: 5,
      startTime: '2m10s', // starts after ramp_up finishes
      exec: 'burstScenario',
    },
  },
  thresholds: {
    // Fail the whole test run if these aren't met - turns this into a real
    // pass/fail gate rather than just numbers to eyeball.
    http_req_duration: ['p(95)<1000', 'p(99)<3000'],
    rl_server_error_5xx: ['count==0'], // zero unhandled 5xxs allowed
    checks: ['rate>0.99'], // >99% of our own check() assertions should pass
  },
};

function classify(res) {
  if (res.status === 200) {
    allowedCount.add(1);
  } else if (res.status === 429) {
    rejectedCount.add(1);
  } else if (res.status >= 500) {
    serverErrorCount.add(1);
  } else {
    unexpectedCount.add(1);
  }
  rateLimitedLatency.add(res.timings.duration);
}

export function rampScenario() {
  const res = http.get(`${BASE_URL}${TARGET_PATH}`, {
    headers: {
      Host: TARGET_HOST,
        'X-API-Key': 'test-key-do-not-use-in-prod',
    },
  });

  classify(res);

  check(res, {
    'status is 200, 429, or a clean 5xx (no crash)': (r) =>
      r.status === 200 || r.status === 429 || r.status === 502 || r.status === 504,
    'rate limit headers present when not exempt path': (r) =>
      TARGET_PATH === '/health' || r.headers['X-Ratelimit-Limit'] !== undefined || r.status === 429,
  });

  sleep(0.1);
}

export function burstScenario() {
  const res = http.get(`${BASE_URL}${TARGET_PATH}`, {
    headers: {
      Host: TARGET_HOST,
      'X-API-Key': 'sk_live_abc123',
    },
  });

  classify(res);

  check(res, {
    'boundary burst: status is 200 or 429 only': (r) => r.status === 200 || r.status === 429,
  });
}

export function handleSummary(data) {
  return {
    'report.json': JSON.stringify(data, null, 2),
    'report.html': htmlReport(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function metricVal(data, name, stat, fallback) {
  const m = data.metrics[name];
  if (!m || !m.values || m.values[stat] === undefined) return fallback;
  return m.values[stat];
}

function htmlReport(data) {
  const totalReqs = metricVal(data, 'http_reqs', 'count', 0);
  const allowed = metricVal(data, 'rl_allowed_200', 'count', 0);
  const rejected = metricVal(data, 'rl_rejected_429', 'count', 0);
  const serverErrors = metricVal(data, 'rl_server_error_5xx', 'count', 0);
  const unexpected = metricVal(data, 'rl_unexpected_status', 'count', 0);

  const p50 = metricVal(data, 'http_req_duration', 'med', 0).toFixed(1);
  const p95 = metricVal(data, 'http_req_duration', 'p(95)', 0).toFixed(1);
  const p99 = metricVal(data, 'http_req_duration', 'p(99)', 0).toFixed(1);
  const maxLat = metricVal(data, 'http_req_duration', 'max', 0).toFixed(1);
  const rps = metricVal(data, 'http_reqs', 'rate', 0).toFixed(2);

  const checksPassed = metricVal(data, 'checks', 'passes', 0);
  const checksFailed = metricVal(data, 'checks', 'fails', 0);
  const checkTotal = checksPassed + checksFailed;
  const checkRate = checkTotal > 0 ? ((checksPassed / checkTotal) * 100).toFixed(2) : '100.00';

  const thresholdRows = Object.entries(data.metrics)
    .filter(([, m]) => m.thresholds)
    .flatMap(([name, m]) =>
      Object.entries(m.thresholds).map(([expr, result]) => ({
        name,
        expr,
        ok: result.ok,
      }))
    );

  const overallPass = thresholdRows.every((t) => t.ok);

  const thresholdHtml = thresholdRows
    .map(
      (t) => `
      <tr>
        <td>${t.name}</td>
        <td><code>${t.expr}</code></td>
        <td class="${t.ok ? 'pass' : 'fail'}">${t.ok ? 'PASS' : 'FAIL'}</td>
      </tr>`
    )
    .join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Rate Limiter Load Test Report</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; color: #1a1a1a; background: #fafafa; }
  h1 { margin-bottom: 0.2rem; }
  .subtitle { color: #666; margin-top: 0; margin-bottom: 2rem; }
  .verdict { display: inline-block; padding: 0.4rem 1rem; border-radius: 6px; font-weight: 600; margin-bottom: 1.5rem; }
  .verdict.pass { background: #d1f5d3; color: #1a7431; }
  .verdict.fail { background: #fbdada; color: #9b1c1c; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
  .card { background: white; border: 1px solid #e5e5e5; border-radius: 8px; padding: 1rem; }
  .card .label { font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.03em; }
  .card .value { font-size: 1.6rem; font-weight: 700; margin-top: 0.2rem; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; background: white; }
  th, td { text-align: left; padding: 0.6rem 0.8rem; border-bottom: 1px solid #eee; }
  th { background: #f0f0f0; font-size: 0.85rem; text-transform: uppercase; }
  .pass { color: #1a7431; font-weight: 600; }
  .fail { color: #9b1c1c; font-weight: 600; }
  code { background: #f0f0f0; padding: 0.1rem 0.3rem; border-radius: 3px; }
</style>
</head>
<body>
  <h1>Rate Limiter — Load Test Report</h1>
  <p class="subtitle">Generated ${new Date().toISOString()}</p>

  <div class="verdict ${overallPass ? 'pass' : 'fail'}">
    Overall: ${overallPass ? 'ALL THRESHOLDS PASSED' : 'ONE OR MORE THRESHOLDS FAILED'}
  </div>

  <div class="grid">
    <div class="card"><div class="label">Total Requests</div><div class="value">${totalReqs}</div></div>
    <div class="card"><div class="label">Requests/sec</div><div class="value">${rps}</div></div>
    <div class="card"><div class="label">200 Allowed</div><div class="value">${allowed}</div></div>
    <div class="card"><div class="label">429 Rejected</div><div class="value">${rejected}</div></div>
    <div class="card"><div class="label">5xx Errors</div><div class="value">${serverErrors}</div></div>
    <div class="card"><div class="label">Unexpected Status</div><div class="value">${unexpected}</div></div>
    <div class="card"><div class="label">p50 Latency</div><div class="value">${p50} ms</div></div>
    <div class="card"><div class="label">p95 Latency</div><div class="value">${p95} ms</div></div>
    <div class="card"><div class="label">p99 Latency</div><div class="value">${p99} ms</div></div>
    <div class="card"><div class="label">Max Latency</div><div class="value">${maxLat} ms</div></div>
    <div class="card"><div class="label">Check Pass Rate</div><div class="value">${checkRate}%</div></div>
  </div>

  <h2>Thresholds</h2>
  <table>
    <thead><tr><th>Metric</th><th>Condition</th><th>Result</th></tr></thead>
    <tbody>${thresholdHtml || '<tr><td colspan="3">No thresholds recorded</td></tr>'}</tbody>
  </table>

  <h2>What to look for</h2>
  <ul>
    <li><strong>5xx Errors should be 0</strong> — anything above zero means an unhandled exception surfaced under load rather than a clean error response.</li>
    <li><strong>p95/p99 latency</strong> should stay well below your SLA even as VUs ramp up in the <code>ramp_up</code> scenario — a sudden knee indicates the proxy's saturation point.</li>
    <li><strong>200 + 429 should account for ~all requests</strong> — a large "Unexpected Status" count suggests something is returning codes outside the expected 200/429/502/504 range.</li>
    <li>Check <code>report.json</code> for the full raw metrics if you need to dig into a specific scenario or percentile not shown here.</li>
  </ul>
</body>
</html>`;
}