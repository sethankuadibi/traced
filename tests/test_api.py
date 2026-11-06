from fastapi.testclient import TestClient

from traced.api import create_app
from traced.store import TraceStore


def make_span(trace_id, span_id, start, parent=None):
    value = {
        "trace_id": trace_id,
        "span_id": span_id,
        "service": "checkout",
        "operation": span_id,
        "start_time": start,
        "end_time": start + 100_000_000,
        "status": "ok",
    }
    if parent:
        value["parent_span_id"] = parent
    return value


def test_contract_endpoints():
    now = 1_000_000_000_000
    client = TestClient(create_app(TraceStore(clock=lambda: now)))
    trace_id = "550e8400-e29b-41d4-a716-446655440000"

    response = client.post("/spans", json={"spans": [make_span(trace_id, "child", now, "root")]})
    assert response.status_code == 202
    assert client.get("/traces").json()["total"] == 0
    client.post("/spans", json={"spans": [make_span(trace_id, "root", now)]})

    listing = client.get("/traces").json()
    detail = client.get(f"/traces/{trace_id}").json()
    assert listing["traces"][0]["span_count"] == 2
    assert len(detail["spans"]) == 2


def test_invalid_trace_and_time_range_are_rejected():
    client = TestClient(create_app(TraceStore()))
    assert client.get("/traces/not-a-uuid").status_code == 400
    assert client.get("/traces?after=10&before=10").status_code == 400

