from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from .models import IngestRequest, TraceDetailResponse, TraceListResponse
from .store import TraceStore


def create_app(store: TraceStore | None = None) -> FastAPI:
    trace_store = store or TraceStore(int(os.environ.get("WINDOW_MINUTES", "30")))
    eviction_task: asyncio.Task | None = None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal eviction_task

        async def evict_forever():
            while True:
                await asyncio.sleep(1)
                await trace_store.evict()

        eviction_task = asyncio.create_task(evict_forever())
        yield
        eviction_task.cancel()
        try:
            await eviction_task
        except asyncio.CancelledError:
            pass

    app = FastAPI(title="Traced", version="1.0.0", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/spans", status_code=202)
    async def ingest(request: IngestRequest):
        await trace_store.ingest(request.spans)
        return {"status": "ok"}

    @app.get("/traces", response_model=TraceListResponse)
    async def list_traces(
        limit: int = Query(default=20, ge=1, le=1000),
        after: int | None = Query(default=None, ge=0),
        before: int | None = Query(default=None, ge=0),
    ):
        if after is not None and before is not None and after >= before:
            raise HTTPException(status_code=400, detail="after must be less than before")
        return await trace_store.list_traces(limit, after, before)

    @app.get("/traces/{trace_id}", response_model=TraceDetailResponse)
    async def get_trace(trace_id: str):
        try:
            uuid.UUID(trace_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="trace_id must be a valid UUID") from exc
        trace = await trace_store.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="trace not found")
        return trace

    return app


app = create_app()

