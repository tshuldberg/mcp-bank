"""
Transform Agent route handlers — 9 operations + GET /capabilities.
All handlers: check cache → run transform → cache result → return with timing.
"""

import time
import orjson
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import ORJSONResponse

from src.app.models.schemas import (
    TransformRequest, TransformResponse,
    ValidateRequest, ValidateResponse, ValidationError,
    InferSchemaRequest, InferSchemaResponse,
    ReshapeRequest, ReshapeResponse,
    DiffRequest, DiffResponse, DiffEntry,
    MergeRequest, MergeResponse,
    FilterRequest, FilterResponse,
    SampleRequest, SampleResponse,
    CapabilitiesResponse, CapabilityInfo,
)
from src.app.transforms.registry import get_handler, list_capabilities
from src.app.transforms import schema_ops
from src.app.middleware.cache import make_cache_key, cache_get, cache_set

router = APIRouter()

OPERATION_PRICES = {
    "validate":     0.0005,
    "infer_schema": 0.0005,
    "reshape":      0.002,
    "diff":         0.001,
    "merge":        0.001,
    "filter":       0.001,
    "sample":       0.0005,
}


# ─── POST /transform ──────────────────────────────────────────────────────────

@router.post("/transform", response_class=ORJSONResponse)
async def transform(req: TransformRequest) -> dict:
    src, tgt = req.source_format.lower(), req.target_format.lower()

    handler = get_handler(src, tgt)
    if handler is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported conversion: {src} → {tgt}",
        )

    cache_key = make_cache_key(src, tgt, req.data)
    t0 = time.monotonic()

    cached_result = await cache_get(cache_key)
    if cached_result is not None:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "result": cached_result,
            "source_format": src,
            "target_format": tgt,
            "bytes_in": len(req.data.encode()),
            "bytes_out": len(cached_result.encode()),
            "cached": True,
            "duration_ms": duration_ms,
        }

    try:
        result = handler(req.data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    duration_ms = int((time.monotonic() - t0) * 1000)
    await cache_set(cache_key, result)

    return {
        "result": result,
        "source_format": src,
        "target_format": tgt,
        "bytes_in": len(req.data.encode()),
        "bytes_out": len(result.encode()),
        "cached": False,
        "duration_ms": duration_ms,
    }


# ─── POST /validate ───────────────────────────────────────────────────────────

@router.post("/validate", response_class=ORJSONResponse)
async def validate(req: ValidateRequest) -> dict:
    t0 = time.monotonic()
    try:
        result = schema_ops.validate_data(req.data, req.schema_)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── POST /infer_schema ───────────────────────────────────────────────────────

@router.post("/infer_schema", response_class=ORJSONResponse)
async def infer_schema(req: InferSchemaRequest) -> dict:
    cache_key = make_cache_key("infer_schema", req.strictness, req.data)
    t0 = time.monotonic()

    cached = await cache_get(cache_key)
    if cached:
        duration_ms = int((time.monotonic() - t0) * 1000)
        result = orjson.loads(cached)
        return {**result, "duration_ms": duration_ms, "cached": True}

    try:
        result = schema_ops.infer_schema(req.data, req.data_format, req.strictness)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    duration_ms = int((time.monotonic() - t0) * 1000)
    await cache_set(cache_key, orjson.dumps(result).decode())
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── POST /reshape ────────────────────────────────────────────────────────────

@router.post("/reshape", response_class=ORJSONResponse)
async def reshape(req: ReshapeRequest) -> dict:
    t0 = time.monotonic()
    try:
        result = schema_ops.reshape_json(req.data, req.mapping)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── POST /diff ───────────────────────────────────────────────────────────────

@router.post("/diff", response_class=ORJSONResponse)
async def diff(req: DiffRequest) -> dict:
    t0 = time.monotonic()
    try:
        result = schema_ops.diff_data(req.before, req.after, req.key_field)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── POST /merge ──────────────────────────────────────────────────────────────

@router.post("/merge", response_class=ORJSONResponse)
async def merge(req: MergeRequest) -> dict:
    t0 = time.monotonic()
    try:
        result = schema_ops.merge_data(req.left, req.right, req.on, req.how)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── POST /filter ─────────────────────────────────────────────────────────────

@router.post("/filter", response_class=ORJSONResponse)
async def filter_rows(req: FilterRequest) -> dict:
    t0 = time.monotonic()
    try:
        result = schema_ops.filter_data(req.data, req.where)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── POST /sample ─────────────────────────────────────────────────────────────

@router.post("/sample", response_class=ORJSONResponse)
async def sample(req: SampleRequest) -> dict:
    cache_key = make_cache_key("sample", str(req.n), req.data + str(req.seed))
    t0 = time.monotonic()

    cached = await cache_get(cache_key)
    if cached:
        duration_ms = int((time.monotonic() - t0) * 1000)
        result = orjson.loads(cached)
        return {**result, "duration_ms": duration_ms, "cached": True}

    try:
        result = schema_ops.sample_data(req.data, req.n, req.seed)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    duration_ms = int((time.monotonic() - t0) * 1000)
    await cache_set(cache_key, orjson.dumps(result).decode())
    return {**result, "duration_ms": duration_ms, "cached": False}


# ─── GET /capabilities ────────────────────────────────────────────────────────

@router.get("/capabilities", response_class=ORJSONResponse)
async def capabilities() -> dict:
    conversions = list_capabilities()
    return {
        "conversions": conversions,
        "operations": OPERATION_PRICES,
        "total_conversions": len(conversions),
    }
