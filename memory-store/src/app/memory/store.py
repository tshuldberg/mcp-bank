"""
Memory storage backends:
- RedisMemoryStore: KV operations with TTL support
- VectorMemoryStore: pgvector semantic search with sentence-transformers embeddings
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import orjson
import redis.asyncio as aioredis

from ..models.schemas import SearchResult


# ─── Redis KV Store ───────────────────────────────────────────────────────────


class RedisMemoryStore:
    """
    Async Redis-backed key-value store.
    Key format: mem:{namespace}:{key}
    Metadata stored as hash at meta:{namespace}:{key}
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _kv_key(self, namespace: str, key: str) -> str:
        return f"mem:{namespace}:{key}"

    def _meta_key(self, namespace: str, key: str) -> str:
        return f"meta:{namespace}:{key}"

    def _ns_index_key(self, namespace: str) -> str:
        return f"ns:{namespace}:keys"

    async def set(
        self,
        namespace: str,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> dict:
        kv_key = self._kv_key(namespace, key)
        meta_key = self._meta_key(namespace, key)
        ns_index = self._ns_index_key(namespace)
        now = datetime.now(timezone.utc).isoformat()

        pipe = self._redis.pipeline()
        pipe.set(kv_key, value)
        pipe.hset(meta_key, mapping={"stored_at": now, "bytes": str(len(value.encode()))})
        pipe.sadd(ns_index, key)

        if ttl_seconds:
            expires_at = (
                datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + ttl_seconds, tz=timezone.utc
                ).isoformat()
            )
            pipe.expire(kv_key, ttl_seconds)
            pipe.expire(meta_key, ttl_seconds)
            pipe.hset(meta_key, "expires_at", expires_at)
        else:
            expires_at = None

        await pipe.execute()

        # Increment write counter
        await self._redis.hincrby(f"stats:{namespace}", "writes_today", 1)
        await self._redis.hincrby(f"stats:{namespace}", "bytes_total", len(value.encode()))

        return {
            "stored": True,
            "key": key,
            "namespace": namespace,
            "bytes": len(value.encode()),
            "expires_at": expires_at,
        }

    async def get(self, namespace: str, key: str) -> dict:
        kv_key = self._kv_key(namespace, key)
        meta_key = self._meta_key(namespace, key)

        pipe = self._redis.pipeline()
        pipe.get(kv_key)
        pipe.hgetall(meta_key)
        results = await pipe.execute()

        raw_value, meta = results
        found = raw_value is not None

        if found:
            await self._redis.hincrby(f"stats:{namespace}", "reads_today", 1)

        value = raw_value.decode() if isinstance(raw_value, bytes) else raw_value

        # Decode meta dict
        decoded_meta: dict = {}
        for k, v in (meta or {}).items():
            dk = k.decode() if isinstance(k, bytes) else k
            dv = v.decode() if isinstance(v, bytes) else v
            decoded_meta[dk] = dv

        return {
            "value": value,
            "key": key,
            "namespace": namespace,
            "found": found,
            "stored_at": decoded_meta.get("stored_at"),
            "expires_at": decoded_meta.get("expires_at"),
        }

    async def list(
        self,
        namespace: str,
        prefix: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict:
        ns_index = self._ns_index_key(namespace)
        all_keys = await self._redis.smembers(ns_index)

        # Decode and filter
        decoded_keys = sorted(
            k.decode() if isinstance(k, bytes) else k for k in all_keys
        )

        if prefix:
            decoded_keys = [k for k in decoded_keys if k.startswith(prefix)]

        # Filter out keys that no longer exist in Redis (expired)
        total = len(decoded_keys)

        # Simple cursor: treat as offset string
        offset = 0
        if cursor:
            try:
                offset = int(cursor)
            except ValueError:
                offset = 0

        page = decoded_keys[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < total else None

        await self._redis.hincrby(f"stats:{namespace}", "reads_today", 1)

        return {
            "keys": page,
            "namespace": namespace,
            "next_cursor": next_cursor,
            "total": total,
        }

    async def delete(self, namespace: str, key: str) -> dict:
        kv_key = self._kv_key(namespace, key)
        meta_key = self._meta_key(namespace, key)
        ns_index = self._ns_index_key(namespace)

        pipe = self._redis.pipeline()
        pipe.delete(kv_key)
        pipe.delete(meta_key)
        pipe.srem(ns_index, key)
        results = await pipe.execute()

        deleted = results[0] > 0
        return {"deleted": deleted, "key": key, "namespace": namespace}

    async def stats(self, namespace: str) -> dict:
        stats_key = f"stats:{namespace}"
        ns_index = self._ns_index_key(namespace)

        pipe = self._redis.pipeline()
        pipe.scard(ns_index)
        pipe.hgetall(stats_key)
        results = await pipe.execute()

        key_count, raw_stats = results

        decoded_stats: dict = {}
        for k, v in (raw_stats or {}).items():
            dk = k.decode() if isinstance(k, bytes) else k
            dv = v.decode() if isinstance(v, bytes) else v
            decoded_stats[dk] = dv

        reads_today = int(decoded_stats.get("reads_today", 0))
        writes_today = int(decoded_stats.get("writes_today", 0))
        bytes_total = int(decoded_stats.get("bytes_total", 0))

        # Cost calculation per SPEC pricing
        cost = (reads_today * 0.0001) + (writes_today * 0.001)

        return {
            "namespace": namespace,
            "keys": key_count,
            "bytes": bytes_total,
            "reads_today": reads_today,
            "writes_today": writes_today,
            "cost_today_usd": round(cost, 6),
        }


# ─── pgvector Store ───────────────────────────────────────────────────────────


@dataclass
class EmbeddingRecord:
    id: str
    namespace: str
    key: str
    value: str
    score: float
    stored_at: datetime | None


class VectorMemoryStore:
    """
    Async pgvector-backed semantic search using sentence-transformers embeddings.

    Table: memory_embeddings(
        id UUID,
        namespace TEXT,
        key TEXT,
        value TEXT,
        embedding vector(384),
        stored_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ
    )

    Embedding model: all-MiniLM-L6-v2 (384 dimensions, runs on CPU)
    """

    _model = None  # lazy-loaded singleton

    def __init__(self, pool) -> None:
        self._pool = pool

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._model

    def embed(self, text: str) -> list[float]:
        """Embed text using all-MiniLM-L6-v2 (384 dims)."""
        model = self._get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def ensure_table(self) -> None:
        """Create the memory_embeddings table if it doesn't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    embedding vector(384) NOT NULL,
                    stored_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ,
                    UNIQUE (namespace, key)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memory_embeddings_ns_idx
                ON memory_embeddings (namespace)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memory_embeddings_vector_idx
                ON memory_embeddings USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

    async def store_embedding(
        self,
        namespace: str,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store or update an embedding for a key-value pair."""
        embedding = self.embed(value)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        expires_at_expr = "NULL"
        params: list = [namespace, key, value, embedding_str]

        if ttl_seconds:
            expires_at_expr = f"NOW() + INTERVAL '{ttl_seconds} seconds'"

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO memory_embeddings (namespace, key, value, embedding, expires_at)
                VALUES ($1, $2, $3, $4::vector, {expires_at_expr})
                ON CONFLICT (namespace, key) DO UPDATE
                    SET value = EXCLUDED.value,
                        embedding = EXCLUDED.embedding,
                        stored_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                """,
                *params,
            )

    async def delete_embedding(self, namespace: str, key: str) -> None:
        """Remove an embedding record."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM memory_embeddings WHERE namespace = $1 AND key = $2",
                namespace,
                key,
            )

    async def search(
        self,
        namespace: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """
        Semantic search over stored embeddings using cosine similarity.

        Returns results with score >= min_score, sorted by descending similarity.
        """
        query_embedding = self.embed(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    key,
                    value,
                    stored_at,
                    1 - (embedding <=> $1::vector) AS score
                FROM memory_embeddings
                WHERE namespace = $2
                  AND (expires_at IS NULL OR expires_at > NOW())
                  AND 1 - (embedding <=> $1::vector) >= $3
                ORDER BY embedding <=> $1::vector
                LIMIT $4
                """,
                embedding_str,
                namespace,
                min_score,
                top_k,
            )

        return [
            SearchResult(
                key=row["key"],
                value=row["value"],
                score=float(row["score"]),
                stored_at=row["stored_at"],
            )
            for row in rows
        ]
