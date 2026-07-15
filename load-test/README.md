# Load testing (k6)

Empirical basis for the Cloud Run scaling settings in
`.github/workflows/cd-deploy.yml` (`--concurrency`, `--max-instances`).

## Why these endpoints

`health-load.js` hits only `/health` and `/ready`:

- **`/health`** does no I/O, so its throughput is the raw request rate a single
  container can serve — this is what caps useful `--concurrency`.
- **`/ready`** adds one Cloud SQL round-trip, showing how much the database
  narrows that ceiling.

The scan/chat endpoints are deliberately excluded: they call Gemini / Vision and
would burn paid quota while measuring the LLM's latency instead of ours.

## Install k6

- Windows: `winget install k6 --source winget` (or `choco install k6`)
- macOS: `brew install k6`
- Docker: `docker run --rm -i grafana/k6 run - <load-test/health-load.js`

## Run

Against a local server (free, recommended — start the app first):

```bash
BASE_URL=http://localhost:8000 k6 run load-test/health-load.js
```

Against the deployed candidate revision (careful — this hammers Cloud SQL):

```bash
BASE_URL=https://candidate---menuscan-api-xxxx-as.a.run.app k6 run load-test/health-load.js
```

On PowerShell, set the variable inline:

```powershell
$env:BASE_URL="http://localhost:8000"; k6 run load-test/health-load.js
```

## Reading the result → tuning Cloud Run

k6 prints per-endpoint `http_req_duration` and `http_reqs` (throughput). Map them
to the deploy flags:

- **`p95` stays flat as VUs climb 20 → 50** → one instance still has headroom;
  `--concurrency` can go higher (toward 80).
- **`p95` bends upward past some VU count** → that VU level is roughly the
  per-instance ceiling. Set `--concurrency` a bit below it so Cloud Run spins up
  a new instance *before* latency degrades, rather than overloading one.
- **`http_req_failed` climbs / 5xx appears** → the instance is saturated (CPU or
  DB connections). Lower `--concurrency`, or raise `--memory`/`--cpu`.
- Multiply the chosen `--concurrency` by `--max-instances` to sanity-check the
  worst-case concurrent-request fan-out against expected real traffic.

Record the numbers you observe here so the scaling settings are defensible:

| Date | Endpoint | VUs | p95 (ms) | req/s | fail rate |
|------|----------|-----|----------|-------|-----------|
| _tbd_ | /health | 50 | | | |
| _tbd_ | /ready | 50 | | | |
