"""
Pydantic v2 request/response models for the Structured Extractor service.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    url: str
    schema_: dict = Field(alias="schema")
    render_js: bool = False

    model_config = {"populate_by_name": True}


class ExtractFromHtmlRequest(BaseModel):
    html: str
    schema_: dict = Field(alias="schema")

    model_config = {"populate_by_name": True}


class ExtractFromImageRequest(BaseModel):
    image_url: str
    schema_: dict = Field(alias="schema")

    model_config = {"populate_by_name": True}


class ExtractBatchRequest(BaseModel):
    urls: list[str]
    schema_: dict = Field(alias="schema")
    render_js: bool = False
    max_concurrent: int = Field(default=5, ge=1, le=20)

    model_config = {"populate_by_name": True}


class ExtractionResult(BaseModel):
    data: dict | None
    confidence: float
    method: str
    url: str | None = None
    extracted_at: str
    duration_ms: int
    cached: bool = False


class BatchExtractionResult(BaseModel):
    results: list[ExtractionResult]
    total_urls: int
    successful: int
    failed: int
    total_duration_ms: int
