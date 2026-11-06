# Architecture

```text
Emitter -> POST /spans -> FastAPI validation -> TraceStore
                                             |
Dashboard <- GET /traces -------------------+
                                             |
                            background eviction loop
```

The HTTP layer validates the contract and delegates all storage behavior to `TraceStore`.
The store keeps a map of trace IDs to span IDs. This deliberately stores child spans even when
their parent or root has not arrived yet; visibility is decided at query time by the presence
of a root.

Every ingest batch is applied under one async lock. This makes a batch appear atomically to
readers and prevents races between writes, queries, and eviction. The background task wakes
once per second and removes spans older than the rolling cutoff, so an idle service does not
retain expired data.

The service is stateless between restarts. For the learning workload this keeps the correctness
rules easy to inspect. A production collector would replace the store with a partitioned,
durable backend such as ClickHouse, PostgreSQL, or a purpose-built time-series store and use
sharded locks or single-writer partitions.

