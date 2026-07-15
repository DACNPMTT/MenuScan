// k6 load test for MenuScan — infrastructure scaling baseline.
//
// This intentionally hits only cheap endpoints:
//   /health  — pure framework overhead (no I/O)  → raw req/s a single instance
//              can serve, i.e. the per-instance concurrency ceiling.
//   /ready   — adds one Cloud SQL round-trip      → DB-bound capacity.
//
// It does NOT exercise the scan/chat pipeline on purpose: those call Gemini /
// Vision and would burn paid quota while measuring THEIR latency, not ours.
// We size Cloud Run (--concurrency / --max-instances) from the framework and
// DB limits measured here.
//
// Run against a local server (recommended, free):
//   BASE_URL=http://localhost:8000 k6 run load-test/health-load.js
// Or against the deployed candidate URL (careful: hammers Cloud SQL):
//   BASE_URL=https://candidate---menuscan-api-xxxx-as.a.run.app k6 run load-test/health-load.js

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 20 }, // warm up
        { duration: '1m', target: 20 }, // hold — read steady-state p95
        { duration: '30s', target: 50 }, // step up — watch where latency bends
        { duration: '1m', target: 50 }, // hold at the higher level
        { duration: '30s', target: 0 }, // ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    // <1% of requests may fail across the whole run.
    http_req_failed: ['rate<0.01'],
    // Overall p95 budget.
    http_req_duration: ['p(95)<500'],
    // /health is pure overhead — hold it to a tight budget so a regression in
    // framework/startup cost is caught, not hidden behind the DB call.
    'http_req_duration{endpoint:health}': ['p(95)<150'],
  },
};

export default function () {
  const health = http.get(`${BASE_URL}/health`, { tags: { endpoint: 'health' } });
  check(health, { 'health is 200': (r) => r.status === 200 });

  const ready = http.get(`${BASE_URL}/ready`, { tags: { endpoint: 'ready' } });
  check(ready, { 'ready is 200': (r) => r.status === 200 });

  sleep(1);
}
