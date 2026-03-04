from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import orjson

_METRICS_FILE = Path("/tmp/mcp-bank-metrics.jsonl")


async def log_operation(
    service: str,
    operation: str,
    agent_wallet: str | None,
    price_usd: float,
    duration_ms: int,
    cached: bool = False,
) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "operation": operation,
        "agent_wallet": agent_wallet,
        "price_usd": price_usd,
        "duration_ms": duration_ms,
        "cached": cached,
    }

    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # Structured log to stdout for production log aggregation
        print(orjson.dumps(record).decode(), flush=True)
    else:
        with _METRICS_FILE.open("ab") as f:
            f.write(orjson.dumps(record) + b"\n")


async def get_daily_stats(service: str) -> dict:
    if not _METRICS_FILE.exists():
        return {
            "total_calls": 0,
            "total_revenue_usd": 0.0,
            "unique_agents": 0,
            "avg_duration_ms": 0,
        }

    today = datetime.now(timezone.utc).date().isoformat()
    total_calls = 0
    total_revenue = 0.0
    agents: set[str] = set()
    total_duration = 0

    with _METRICS_FILE.open("rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = orjson.loads(line)
            except Exception:
                continue

            if record.get("service") != service:
                continue
            if not record.get("ts", "").startswith(today):
                continue

            total_calls += 1
            total_revenue += record.get("price_usd", 0.0)
            total_duration += record.get("duration_ms", 0)
            wallet = record.get("agent_wallet")
            if wallet:
                agents.add(wallet)

    return {
        "total_calls": total_calls,
        "total_revenue_usd": round(total_revenue, 6),
        "unique_agents": len(agents),
        "avg_duration_ms": round(total_duration / total_calls) if total_calls else 0,
    }
