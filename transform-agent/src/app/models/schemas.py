"""Pydantic v2 request and response models for the Transform Agent."""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ─── Transform ────────────────────────────────────────────────────────────────

class TransformRequest(BaseModel):
    source_format: str = Field(..., description="Input format (json, csv, xml, yaml, toml, html, markdown, pdf, xlsx, docx, base64, hex, url, text)")
    target_format: str = Field(..., description="Output format")
    data: str = Field(..., description="Input data as string (binary formats must be base64-encoded)")
    async_mode: bool = Field(False, alias="async", description="Force async processing")
    webhook_url: str | None = Field(None, description="Webhook called on async completion")

    model_config = {"populate_by_name": True}


class TransformResponse(BaseModel):
    result: str
    source_format: str
    target_format: str
    bytes_in: int
    bytes_out: int
    cached: bool
    duration_ms: int


class AsyncJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "complete", "failed"]
    poll_url: str
    estimated_seconds: int


# ─── Validate ─────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    data: str = Field(..., description="Data to validate (JSON string)")
    schema_: str = Field(..., alias="schema", description="JSON Schema as a JSON string")
    data_format: str = Field("json", description="Format of data field")

    model_config = {"populate_by_name": True}


class ValidationError(BaseModel):
    path: str
    message: str
    value: Any = None


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[ValidationError] = []


# ─── Infer Schema ─────────────────────────────────────────────────────────────

class InferSchemaRequest(BaseModel):
    data: str = Field(..., description="Sample data to infer schema from")
    data_format: str = Field("json", description="Format of data field")
    strictness: Literal["strict", "relaxed"] = Field("relaxed", description="How strictly to mark fields as required")


class InferSchemaResponse(BaseModel):
    schema_: dict = Field(..., alias="schema")
    confidence: float

    model_config = {"populate_by_name": True}


# ─── Reshape ──────────────────────────────────────────────────────────────────

class ReshapeRequest(BaseModel):
    data: Any = Field(..., description="JSON data to reshape (object or array)")
    mapping: dict[str, str] = Field(..., description="Output field → dot-notation source path")


class ReshapeResponse(BaseModel):
    result: Any
    fields_mapped: int
    fields_missing: list[str] = []


# ─── Diff ─────────────────────────────────────────────────────────────────────

class DiffRequest(BaseModel):
    before: str = Field(..., description="Original dataset (JSON string)")
    after: str = Field(..., description="Updated dataset (JSON string)")
    data_format: str = Field("json")
    key_field: str = Field(..., description="Field to use as unique row identifier")


class DiffEntry(BaseModel):
    id: Any
    field: str
    before: Any
    after: Any


class DiffResponse(BaseModel):
    added: list[dict] = []
    removed: list[dict] = []
    modified: list[DiffEntry] = []
    unchanged: int = 0


# ─── Merge ────────────────────────────────────────────────────────────────────

class MergeRequest(BaseModel):
    left: str = Field(..., description="Left dataset (JSON string)")
    right: str = Field(..., description="Right dataset (JSON string)")
    on: str = Field(..., description="Join key field name")
    how: Literal["inner", "left", "right", "full"] = Field("inner", description="Join type")
    data_format: str = Field("json")


class MergeResponse(BaseModel):
    result: str
    rows_in_left: int
    rows_in_right: int
    rows_out: int


# ─── Filter ───────────────────────────────────────────────────────────────────

class FilterRequest(BaseModel):
    data: str = Field(..., description="Tabular data (JSON string)")
    where: str = Field(..., description="Filter expression e.g. 'age >= 18' or 'status == active'")
    data_format: str = Field("json")


class FilterResponse(BaseModel):
    result: str
    rows_in: int
    rows_out: int


# ─── Sample ───────────────────────────────────────────────────────────────────

class SampleRequest(BaseModel):
    data: str = Field(..., description="Tabular data (JSON string)")
    n: int = Field(10, description="Number of rows to sample", ge=1, le=10000)
    seed: int | None = Field(None, description="Random seed for reproducibility")
    data_format: str = Field("json")


class SampleResponse(BaseModel):
    result: str
    rows_in: int
    rows_out: int


# ─── Capabilities ─────────────────────────────────────────────────────────────

class CapabilityInfo(BaseModel):
    source_format: str
    target_format: str
    price_usdc: float
    category: str


class CapabilitiesResponse(BaseModel):
    conversions: list[CapabilityInfo]
    operations: dict[str, float]
    total_conversions: int
