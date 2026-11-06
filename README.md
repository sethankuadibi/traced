# Traced

A concurrent span-ingestion API that assembles distributed traces, accepts children before
their parents, evicts data continuously from a rolling window, and serves accurate summaries
to a dashboard.

## What it demonstrates

- Atomic batched writes protected by an async lock.
- Out-of-order span storage and root-aware trace visibility.
- Continuous background eviction independent of ingest traffic.
- Error status derived from every span, not only the root.
- Contract-first FastAPI endpoints with validation and query filters.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
WINDOW_MINUTES=30 uvicorn traced.api:app --host 0.0.0.0 --port 8080
```

Open <http://localhost:8080/docs>. The API contract is in `spec/openapi.yaml`.

## API examples

Ingest a batch:

```bash
curl -X POST http://localhost:8080/spans \
  -H 'Content-Type: application/json' \
  -d '{"spans":[{"trace_id":"550e8400-e29b-41d4-a716-446655440000","span_id":"root","service":"checkout","operation":"place_order","start_time":1713484800000000000,"end_time":1713484800150000000,"status":"ok"}]}'
```

Query recent traces:

```bash
curl 'http://localhost:8080/traces?limit=20'
curl http://localhost:8080/traces/550e8400-e29b-41d4-a716-446655440000
```

## Development

```bash
make install
make check
make run
```

The tests cover out-of-order assembly, rolling eviction, concurrent writes, error propagation,
time filters, and the HTTP contract. See [ARCHITECTURE.md](ARCHITECTURE.md),
[ALGORITHMS.md](ALGORITHMS.md), and [TRADEOFFS.md](TRADEOFFS.md).

