from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    service: str = Field(max_length=256)
    operation: str = Field(max_length=256)
    start_time: int
    end_time: int
    status: str
    tags: dict[str, str] = Field(default_factory=dict, max_length=50)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"ok", "error"}:
            raise ValueError("status must be 'ok' or 'error'")
        return value

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, value: int, info) -> int:
        if "start_time" in info.data and value < info.data["start_time"]:
            raise ValueError("end_time must be greater than or equal to start_time")
        return value


class IngestRequest(BaseModel):
    spans: list[Span] = Field(min_length=1, max_length=500)


class TraceSummary(BaseModel):
    trace_id: str
    root_service: str
    root_operation: str
    span_count: int
    duration_ms: int
    start_time: int
    status: str


class TraceListResponse(BaseModel):
    total: int
    traces: list[TraceSummary]


class TraceDetailResponse(BaseModel):
    trace_id: str
    spans: list[Span]

