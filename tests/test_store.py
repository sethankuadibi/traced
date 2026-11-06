import asyncio

from traced.models import Span
from traced.store import TraceStore


def span(trace, span_id, start, parent=None, status="ok", end=None):
    return Span(
        trace_id=trace,
        span_id=span_id,
        parent_span_id=parent,
        service="checkout",
        operation=span_id,
        start_time=start,
        end_time=end or start + 150_000_000,
        status=status,
    )


async def test_out_of_order_children_are_assembled_when_root_arrives():
    now = 1_000_000_000_000
    store = TraceStore(window_minutes=30, clock=lambda: now)
    trace_id = "550e8400-e29b-41d4-a716-446655440000"
    child = span(trace_id, "child", now - 1_000_000, parent="root", status="error")
    root = span(trace_id, "root", now, end=now + 300_000_000)

    await store.ingest([child])
    assert (await store.list_traces()).total == 0
    await store.ingest([root])

    result = await store.list_traces()
    assert result.total == 1
    assert result.traces[0].span_count == 2
    assert result.traces[0].status == "error"
    assert [item.span_id for item in (await store.get_trace(trace_id)).spans] == ["child", "root"]


async def test_eviction_removes_old_spans_without_new_ingest():
    current = [1_000_000_000_000]
    store = TraceStore(window_minutes=1, clock=lambda: current[0])
    trace_id = "550e8400-e29b-41d4-a716-446655440000"
    await store.ingest([span(trace_id, "root", current[0] - 30_000_000_000)])
    assert (await store.list_traces()).total == 1

    current[0] += 90_000_000_000
    assert await store.evict() == 1
    assert (await store.list_traces()).total == 0


async def test_time_filters_and_descending_order():
    now = 1_000_000_000_000
    store = TraceStore(clock=lambda: now)
    first = "550e8400-e29b-41d4-a716-446655440000"
    second = "550e8400-e29b-41d4-a716-446655440001"
    await store.ingest([span(first, "root-a", now - 20_000_000)])
    await store.ingest([span(second, "root-b", now - 10_000_000)])

    result = await store.list_traces(after=now - 15_000_000, before=now)
    assert result.total == 1
    assert result.traces[0].trace_id == second


async def test_concurrent_batches_remain_consistent():
    now = 1_000_000_000_000
    store = TraceStore(clock=lambda: now)
    trace_id = "550e8400-e29b-41d4-a716-446655440000"
    await asyncio.gather(
        *(store.ingest([span(trace_id, f"child-{i}", now, parent="root")]) for i in range(100))
    )
    await store.ingest([span(trace_id, "root", now)])

    assert (await store.list_traces()).traces[0].span_count == 101
