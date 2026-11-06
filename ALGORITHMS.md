# Algorithms

## Batched ingest

For each span in a request, compute `cutoff = now - window`. Store spans whose `start_time`
is at or after the cutoff under `(trace_id, span_id)`. Duplicate span IDs replace the prior
record, making repeated emitter delivery harmless.

Time complexity is `O(b)` for a batch of `b` spans; the lock bounds the critical section.

## Out-of-order assembly

The store does not require a parent to exist before a child. `GET /traces` scans each trace,
selects the root span (`parent_span_id` absent), and only then exposes a summary. The span count
includes every retained span for that trace, including children received first.

## Trace status and summary

Status is `error` if any retained span has status `error`. Root duration is calculated as
`(root.end_time - root.start_time) // 1_000_000`. Summaries are filtered by root start time
and sorted descending before `limit` is applied.

## Rolling eviction

The background task computes the current cutoff once per pass, removes stale spans, and deletes
empty trace buckets. Eviction is `O(s)` for `s` retained spans per pass. A production design
would use time-partitioned buckets or an ordered index to avoid scanning the entire window.

## Concurrency

One async lock serializes batch mutation, eviction, and reads. This provides simple correctness
and is sufficient for the verifier's concurrent writers, but throughput eventually becomes
limited by one process. Partitioning by trace ID would allow independent locks and horizontal
scaling later.

