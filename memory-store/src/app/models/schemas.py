"""
Pydantic v2 request/response models for the Memory Store service.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Request Models ───────────────────────────────────────────────────────────


class MemorySetRequest(BaseModel):
    namespace: str = Field(..., description="Scoping prefix — wallet address or logical name")
    key: str = Field(..., description="Unique key within the namespace")
    value: str = Field(..., description="String value to store (JSON-serialized recommended)")
    ttl_seconds: int | None = Field(None, description="Optional TTL. Omit for permanent storage.")


class MemoryGetRequest(BaseModel):
    namespace: str = Field(..., description="Namespace the key belongs to")
    key: str = Field(..., description="Key to retrieve")


class MemorySearchRequest(BaseModel):
    namespace: str = Field(..., description="Namespace to search within")
    query: str = Field(..., description="Natural language query for semantic search")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of results to return")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum cosine similarity score")


class MemoryListRequest(BaseModel):
    namespace: str = Field(..., description="Namespace to list keys from")
    prefix: str | None = Field(None, description="Optional key prefix filter")
    limit: int = Field(100, ge=1, le=1000, description="Maximum keys to return")
    cursor: str | None = Field(None, description="Pagination cursor from previous response")


class MemoryDeleteRequest(BaseModel):
    namespace: str = Field(..., description="Namespace the key belongs to")
    key: str = Field(..., description="Key to delete")


class MemoryStatsRequest(BaseModel):
    namespace: str = Field(..., description="Namespace to retrieve stats for")


# ─── Response Models ──────────────────────────────────────────────────────────


class MemorySetResponse(BaseModel):
    stored: bool
    key: str
    namespace: str
    bytes: int
    expires_at: datetime | None = None


class MemoryGetResponse(BaseModel):
    value: str | None
    key: str
    namespace: str
    stored_at: datetime | None = None
    expires_at: datetime | None = None
    found: bool


class SearchResult(BaseModel):
    key: str
    value: str
    score: float
    stored_at: datetime | None = None


class MemorySearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    namespace: str
    count: int


class MemoryListResponse(BaseModel):
    keys: list[str]
    namespace: str
    next_cursor: str | None = None
    total: int


class MemoryDeleteResponse(BaseModel):
    deleted: bool
    key: str
    namespace: str


class MemoryStatsResponse(BaseModel):
    namespace: str
    keys: int
    bytes: int
    reads_today: int
    writes_today: int
    cost_today_usd: float
