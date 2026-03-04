"""
Memory Store route handlers.

All billable endpoints are protected by x402 middleware configured in main.py.
Handlers are thin — all business logic lives in memory/store.py.
"""

from fastapi import APIRouter, Request

from ..memory.store import RedisMemoryStore, VectorMemoryStore
from ..models.schemas import (
    MemoryDeleteRequest,
    MemoryDeleteResponse,
    MemoryGetRequest,
    MemoryGetResponse,
    MemoryListRequest,
    MemoryListResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySetRequest,
    MemorySetResponse,
    MemoryStatsRequest,
    MemoryStatsResponse,
)

router = APIRouter(prefix="/memory")


def _get_stores(request: Request) -> tuple[RedisMemoryStore, VectorMemoryStore]:
    return request.app.state.redis_store, request.app.state.vector_store


@router.post("/set", response_model=MemorySetResponse)
async def memory_set(body: MemorySetRequest, request: Request) -> MemorySetResponse:
    """Store a value in persistent memory. Price: $0.001/call."""
    redis_store, vector_store = _get_stores(request)

    result = await redis_store.set(
        namespace=body.namespace,
        key=body.key,
        value=body.value,
        ttl_seconds=body.ttl_seconds,
    )

    # Fire-and-forget embedding (don't block on vector store errors)
    try:
        await vector_store.store_embedding(
            namespace=body.namespace,
            key=body.key,
            value=body.value,
            ttl_seconds=body.ttl_seconds,
        )
    except Exception:
        pass  # KV write succeeded; vector store failure is non-fatal

    return MemorySetResponse(**result)


@router.post("/get", response_model=MemoryGetResponse)
async def memory_get(body: MemoryGetRequest, request: Request) -> MemoryGetResponse:
    """Retrieve a stored value by exact key. Price: $0.0001/call."""
    redis_store, _ = _get_stores(request)
    result = await redis_store.get(namespace=body.namespace, key=body.key)
    return MemoryGetResponse(**result)


@router.post("/search", response_model=MemorySearchResponse)
async def memory_search(body: MemorySearchRequest, request: Request) -> MemorySearchResponse:
    """Semantic search over stored values using vector similarity. Price: $0.01/call."""
    _, vector_store = _get_stores(request)

    results = await vector_store.search(
        namespace=body.namespace,
        query=body.query,
        top_k=body.top_k,
        min_score=body.min_score,
    )

    return MemorySearchResponse(
        results=results,
        query=body.query,
        namespace=body.namespace,
        count=len(results),
    )


@router.post("/list", response_model=MemoryListResponse)
async def memory_list(body: MemoryListRequest, request: Request) -> MemoryListResponse:
    """Enumerate keys in a namespace. Price: $0.0001/call."""
    redis_store, _ = _get_stores(request)

    result = await redis_store.list(
        namespace=body.namespace,
        prefix=body.prefix,
        limit=body.limit,
        cursor=body.cursor,
    )

    return MemoryListResponse(**result)


@router.post("/delete", response_model=MemoryDeleteResponse)
async def memory_delete(body: MemoryDeleteRequest, request: Request) -> MemoryDeleteResponse:
    """Remove a key from memory. Price: $0.0001/call."""
    redis_store, vector_store = _get_stores(request)

    result = await redis_store.delete(namespace=body.namespace, key=body.key)

    try:
        await vector_store.delete_embedding(namespace=body.namespace, key=body.key)
    except Exception:
        pass  # KV delete succeeded; vector cleanup failure is non-fatal

    return MemoryDeleteResponse(**result)


@router.get("/stats", response_model=MemoryStatsResponse)
async def memory_stats(namespace: str, request: Request) -> MemoryStatsResponse:
    """Usage and cost information for a namespace. Price: free."""
    redis_store, _ = _get_stores(request)
    result = await redis_store.stats(namespace=namespace)
    return MemoryStatsResponse(**result)
