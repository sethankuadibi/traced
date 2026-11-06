# Engineering trade-offs

## Storage design

I chose an in-memory dictionary keyed by trace ID and span ID. It makes the parent-before-child
case explicit, has predictable behavior for the verifier, and avoids hiding the core problem
behind a database. It is not durable; a production collector should use a durable, horizontally
scalable store and partition data by trace ID.

## Eviction

A one-second background loop evicts spans whose start time is older than the configured window.
This meets the requirement that idle services still expire data. The current implementation
scans retained spans, which is clear but becomes the first bottleneck as the window grows. Time
 buckets or an ordered min-heap would reduce that cost.

## Concurrency

One async lock protects all store operations. It guarantees that a batch is visible atomically
and that readers never observe a half-applied batch. Under 10x the default emitter load, the
single lock and full scans are likely to limit throughput before the HTTP layer does. Sharded
locks by trace ID and partitioned eviction are the next improvements.

## What I would change

I would add bounded memory accounting, metrics for accepted/stale spans, OpenTelemetry
instrumentation, durable storage, and a retention policy based on event-time buckets. I would
also add a separate reconciliation path for late spans that arrive after a trace has expired.

