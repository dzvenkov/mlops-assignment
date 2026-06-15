"""Continuous load generator for the agent endpoint.

Samples questions from load_test/perf_pool.jsonl and keeps firing them at the
agent until interrupted. Useful for driving Grafana panels while you explore
serving behavior manually.

Run:
    uv run python load_test/continuous.py --rps 2

Stop with Ctrl+C. A short summary is printed on exit.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import signal
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
PERF_POOL = ROOT / "load_test" / "perf_pool.jsonl"
AGENT_URL_DEFAULT = "http://localhost:8001/answer"


async def fire_one(
    session: aiohttp.ClientSession,
    url: str,
    question: dict,
    results: list[dict],
    tags: dict[str, str],
) -> None:
    payload = {
        "question": question["question"],
        "db": question["db_id"],
        "tags": tags,
    }
    t0 = time.monotonic()
    status = "ok"
    err: str | None = None
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            await resp.read()
            if resp.status != 200:
                status = "http_error"
                err = f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        status = "timeout"
    except Exception as e:  # noqa: BLE001
        status = "client_error"
        err = f"{type(e).__name__}: {e}"
    results.append(
        {
            "latency_seconds": time.monotonic() - t0,
            "status": status,
            "error": err,
        }
    )


def summarize(results: list[dict], wall: float, requested_rps: float) -> dict:
    latencies = sorted(r["latency_seconds"] for r in results if r["status"] == "ok")

    def pct(p: float) -> float:
        if not latencies:
            return float("nan")
        k = int(round(p * (len(latencies) - 1)))
        return latencies[k]

    return {
        "requested_rps": requested_rps,
        "wall_clock_seconds": wall,
        "total_requests": len(results),
        "achieved_rps": (len(results) / wall) if wall > 0 else 0.0,
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "timeouts": sum(1 for r in results if r["status"] == "timeout"),
        "http_errors": sum(1 for r in results if r["status"] == "http_error"),
        "client_errors": sum(1 for r in results if r["status"] == "client_error"),
        "latency_p50": pct(0.50),
        "latency_p95": pct(0.95),
        "latency_p99": pct(0.99),
        "latency_max": latencies[-1] if latencies else float("nan"),
    }


async def drive(args: argparse.Namespace) -> None:
    if not PERF_POOL.exists():
        raise SystemExit(f"{PERF_POOL} not found - run scripts/load_data.py first")

    questions = [json.loads(line) for line in PERF_POOL.read_text().splitlines() if line.strip()]
    if not questions:
        raise SystemExit(f"{PERF_POOL} is empty")

    rnd = random.Random(args.seed)
    results: list[dict] = []
    interval = 1.0 / args.rps
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is not None:
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass

    connector = aiohttp.TCPConnector(limit=0)
    tags = {
        "source": args.tag_source,
        "phase": args.tag_phase,
        "run": args.tag_run,
    }

    async with aiohttp.ClientSession(connector=connector) as session:
        start = time.monotonic()
        next_fire = start
        tasks: list[asyncio.Task] = []

        print(
            f"Starting continuous load at {args.rps:.2f} RPS against {args.agent_url}. "
            "Press Ctrl+C to stop.",
            flush=True,
        )

        reporter = start + args.report_every
        while not stop_event.is_set():
            q = rnd.choice(questions)
            tasks.append(asyncio.create_task(fire_one(session, args.agent_url, q, results, tags)))
            next_fire += interval

            now = time.monotonic()
            if now >= reporter:
                summary = summarize(results, now - start, args.rps)
                print(json.dumps(summary), flush=True)
                reporter = now + args.report_every

            sleep_for = next_fire - time.monotonic()
            if sleep_for > 0:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
                except asyncio.TimeoutError:
                    pass

        if tasks:
            await asyncio.wait(tasks, timeout=60.0)
        wall = time.monotonic() - start

    print("\nStopped continuous load.")
    print(json.dumps(summarize(results, wall, args.rps), indent=2))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rps", type=float, default=2.0, help="target requests/second")
    p.add_argument("--agent-url", default=AGENT_URL_DEFAULT)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--report-every", type=int, default=15, help="seconds between progress summaries")
    p.add_argument("--tag-source", default="continuous-load")
    p.add_argument("--tag-phase", default="manual-load")
    p.add_argument("--tag-run", default="adhoc")
    args = p.parse_args()
    asyncio.run(drive(args))


if __name__ == "__main__":
    main()
