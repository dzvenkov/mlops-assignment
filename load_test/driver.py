"""Async load driver for the agent endpoint.

Samples questions from load_test/perf_pool.jsonl and fires them at the
agent at the requested RPS for the requested duration, recording per-
request latency and outcome.

Run:
    uv run python load_test/driver.py --rps 8 --duration 300

Writes a JSON file (default results/load_test.json) with summary + raw
per-request data.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import random
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
PERF_POOL = ROOT / "load_test" / "perf_pool.jsonl"
DEFAULT_OUT = ROOT / "results" / "load_test.json"
AGENT_URL_DEFAULT = "http://localhost:8001/answer"


async def fire_one(
    session: aiohttp.ClientSession,
    url: str,
    question: dict,
    results: list[dict],
    launched_at: float,
) -> None:
    payload = {"question": question["question"], "db": question["db_id"]}
    t0 = launched_at
    status = "ok"
    err: str | None = None
    http_status: int | None = None
    response_body: str | None = None
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            http_status = resp.status
            body = await resp.text()
            if resp.status != 200:
                status = "http_error"
                err = f"HTTP {resp.status}"
                response_body = body[:1000]
    except asyncio.TimeoutError:
        status = "timeout"
    except Exception as e:  # noqa: BLE001
        status = "client_error"
        err = f"{type(e).__name__}: {e}"
    results.append({
        "latency_seconds": time.monotonic() - t0,
        "status": status,
        "error": err,
        "http_status": http_status,
        "response_body": response_body,
        "db_id": question["db_id"],
        "launched_at_seconds": launched_at,
        "completed_at_seconds": time.monotonic(),
    })


async def drive(args: argparse.Namespace) -> None:
    if not PERF_POOL.exists():
        raise SystemExit(f"{PERF_POOL} not found - run scripts/load_data.py first")
    questions = [json.loads(line) for line in PERF_POOL.read_text().splitlines() if line.strip()]
    if not questions:
        raise SystemExit(f"{PERF_POOL} is empty")

    rnd = random.Random(0)
    results: list[dict] = []
    interval = 1.0 / args.rps

    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        start = time.monotonic()
        deadline = start + args.duration
        tasks: list[asyncio.Task] = []
        task_started_at: dict[asyncio.Task, float] = {}
        next_fire = start
        while time.monotonic() < deadline:
            q = rnd.choice(questions)
            launched_at = time.monotonic()
            task = asyncio.create_task(fire_one(session, args.agent_url, q, results, launched_at))
            tasks.append(task)
            task_started_at[task] = launched_at
            next_fire += interval
            sleep_for = next_fire - time.monotonic()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
        # let in-flight finish (cap drain at 60s)
        active_end = time.monotonic()
        if tasks:
            await asyncio.wait(tasks, timeout=60.0)
        finished_at = time.monotonic()
        wall = finished_at - start
        pending_after_drain = sum(1 for task in tasks if not task.done())
        pending_ages = [
            finished_at - task_started_at[task]
            for task in tasks
            if not task.done()
        ]

    latencies = sorted(r["latency_seconds"] for r in results if r["status"] == "ok")
    status_counts = Counter(r["status"] for r in results)
    http_status_counts = Counter(
        str(r["http_status"]) for r in results if r.get("http_status") is not None
    )
    error_counts = Counter(r["error"] or "" for r in results if r["status"] != "ok")

    def pct(p: float) -> float:
        if not latencies:
            return float("nan")
        k = int(round(p * (len(latencies) - 1)))
        return latencies[k]

    summary = {
        "requested_rps": args.rps,
        "duration_seconds": args.duration,
        "wall_clock_seconds": wall,
        "active_window_seconds": active_end - start,
        "drain_seconds": wall - (active_end - start),
        "total_requests": len(results),
        "achieved_rps": (len(results) / wall) if wall > 0 else 0.0,
        "scheduled_rps": len(tasks) / args.duration,
        "ok_per_active_second": status_counts["ok"] / args.duration,
        "error_rate": (len(results) - status_counts["ok"]) / len(results) if results else 0.0,
        "ok": status_counts["ok"],
        "timeouts": status_counts["timeout"],
        "http_errors": status_counts["http_error"],
        "client_errors": status_counts["client_error"],
        "pending_after_drain": pending_after_drain,
        "pending_age_max_seconds": max(pending_ages) if pending_ages else 0.0,
        "pending_age_min_seconds": min(pending_ages) if pending_ages else 0.0,
        "http_status_counts": dict(sorted(http_status_counts.items())),
        "error_counts": dict(error_counts.most_common(10)),
        "latency_p50": pct(0.50),
        "latency_p95": pct(0.95),
        "latency_p99": pct(0.99),
        "latency_max": latencies[-1] if latencies else float("nan"),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"Wrote {args.out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rps", type=float, default=8.0, help="target requests/second")
    p.add_argument("--duration", type=int, default=300, help="seconds to drive load")
    p.add_argument("--agent-url", default=AGENT_URL_DEFAULT)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()
    asyncio.run(drive(args))


if __name__ == "__main__":
    main()
