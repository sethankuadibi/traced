from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable

from .models import Span, TraceDetailResponse, TraceListResponse, TraceSummary


class TraceStore:
    """In-memory trace store with atomic async batches and a continuously evicted window."""

    def __init__(self, window_minutes: int = 30, clock: Callable[[], int] | None = None):
        if window_minutes <= 0:
            raise ValueError("window_minutes must be positive")
        self.window_ns = window_minutes * 60 * 1_000_000_000
        self._clock = clock or time.time_ns
        self._traces: dict[str, dict[str, Span]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def ingest(self, spans: list[Span]) -> int:
        cutoff = self._clock() - self.window_ns
        accepted = 0
        async with self._lock:
            for span in spans:
                if span.start_time < cutoff:
                    continue
                self._traces[span.trace_id][span.span_id] = span
                accepted += 1
            self._evict_locked(cutoff)
        return accepted

    async def evict(self) -> int:
        async with self._lock:
            return self._evict_locked(self._clock() - self.window_ns)

    async def list_traces(self, limit: int = 20, after: int | None = None, before: int | None = None) -> TraceListResponse:
        async with self._lock:
            summaries = self._summaries_locked(after, before)
            summaries.sort(key=lambda item: item.start_time, reverse=True)
            return TraceListResponse(total=len(summaries), traces=summaries[:limit])

    async def get_trace(self, trace_id: str) -> TraceDetailResponse | None:
        async with self._lock:
            spans = list(self._traces.get(trace_id, {}).values())
            if not any(span.parent_span_id is None for span in spans):
                return None
            spans.sort(key=lambda span: span.start_time)
            return TraceDetailResponse(trace_id=trace_id, spans=spans)

    def _summaries_locked(self, after: int | None, before: int | None) -> list[TraceSummary]:
        summaries = []
        for trace_id, spans_by_id in self._traces.items():
            spans = list(spans_by_id.values())
            roots = [span for span in spans if span.parent_span_id is None]
            if not roots:
                continue
            root = min(roots, key=lambda span: span.start_time)
            if after is not None and root.start_time < after:
                continue
            if before is not None and root.start_time >= before:
                continue
            summaries.append(
                TraceSummary(
                    trace_id=trace_id,
                    root_service=root.service,
                    root_operation=root.operation,
                    span_count=len(spans),
                    duration_ms=(root.end_time - root.start_time) // 1_000_000,
                    start_time=root.start_time,
                    status="error" if any(span.status == "error" for span in spans) else "ok",
                )
            )
        return summaries

    def _evict_locked(self, cutoff: int) -> int:
        removed = 0
        for trace_id in list(self._traces):
            spans = self._traces[trace_id]
            for span_id, span in list(spans.items()):
                if span.start_time < cutoff:
                    del spans[span_id]
                    removed += 1
            if not spans:
                del self._traces[trace_id]
        return removed

