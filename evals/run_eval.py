"""Eval runner using execution accuracy.

Reads evals/eval_set.jsonl, calls the agent at AGENT_URL on each question,
then compares the agent's SQL output to the gold SQL by *executed rows*
(canonicalized: sorted, stringified, None-coerced to empty).

Helpers (run_sql / canonicalize / matches) are provided. You implement
eval_one() and summarize().

Run:
    uv run python evals/run_eval.py --out results/eval_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path

import httpx

try:
    from agent.graph import MAX_ITERATIONS as MAX_SQL_ATTEMPTS
except Exception:  # noqa: BLE001
    MAX_SQL_ATTEMPTS = 3

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_FILE = ROOT / "evals" / "eval_set.jsonl"
DEFAULT_OUT_FILE = ROOT / "results" / "eval_baseline.json"
DB_DIR = ROOT / "data" / "bird"
AGENT_URL_DEFAULT = "http://localhost:8001/answer"


# ---------- Helpers (provided) -----------------------------------------

def run_sql(db_id: str, sql: str, timeout: float = 5.0) -> tuple[bool, list[tuple] | None, str | None]:
    """Run sql against db_id in read-only mode. Returns (ok, rows, error)."""
    path = DB_DIR / f"{db_id}.sqlite"
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout) as conn:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            return True, rows, None
    except Exception as e:  # noqa: BLE001
        return False, None, f"{type(e).__name__}: {e}"


def canonicalize(rows: list[tuple] | None) -> list[tuple] | None:
    """Sort rows; coerce cells to str; None -> ''."""
    if rows is None:
        return None
    return sorted(tuple("" if c is None else str(c) for c in row) for row in rows)


def matches(gold_rows: list[tuple] | None, pred_rows: list[tuple] | None) -> bool:
    if gold_rows is None or pred_rows is None:
        return False
    return canonicalize(gold_rows) == canonicalize(pred_rows)


# ---------- Implement these (Phase 5) ----------------------------------

def eval_one(question: dict, agent_url: str) -> dict:
    """Score one question. Return a dict capturing per-iteration correctness."""
    payload = {
        "question": question["question"],
        "db": question["db_id"],
        "tags": {
            "source": "eval",
            "phase": "baseline-eval",
            "run": "baseline",
        },
    }

    gold_ok, gold_rows, gold_error = run_sql(question["db_id"], question["gold_sql"])

    result: dict = {
        "db_id": question["db_id"],
        "question": question["question"],
        "gold_sql": question["gold_sql"],
        "gold_ok": gold_ok,
        "gold_error": gold_error,
        "agent_http_ok": False,
        "agent_status_code": None,
        "agent_ok": False,
        "agent_error": None,
        "final_sql": "",
        "iterations": 0,
        "attempts": [],
        "final_correct": False,
    }

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(agent_url, json=payload)
    except Exception as e:  # noqa: BLE001
        result["agent_error"] = f"{type(e).__name__}: {e}"
        return result

    result["agent_status_code"] = resp.status_code
    result["agent_http_ok"] = resp.status_code == 200

    if resp.status_code != 200:
        result["agent_error"] = resp.text
        return result

    body = resp.json()
    result["agent_ok"] = bool(body.get("ok", False))
    result["agent_error"] = body.get("error")
    result["final_sql"] = body.get("sql", "")
    result["iterations"] = int(body.get("iterations", 0))

    history = body.get("history", [])
    sql_attempts = [
        entry.get("sql", "")
        for entry in history
        if entry.get("node") in {"generate_sql", "revise"} and entry.get("sql")
    ]

    for idx, sql in enumerate(sql_attempts):
        pred_ok, pred_rows, pred_error = run_sql(question["db_id"], sql)
        correct = gold_ok and pred_ok and matches(gold_rows, pred_rows)
        result["attempts"].append(
            {
                "iteration": idx,
                "sql": sql,
                "exec_ok": pred_ok,
                "exec_error": pred_error,
                "correct": correct,
            }
        )

    if result["attempts"]:
        result["final_correct"] = bool(result["attempts"][-1]["correct"])
    else:
        result["final_correct"] = False

    return result


def summarize(results: list[dict]) -> dict:
    """Aggregate per-question results.

    Per-iteration carry-forward: if the agent terminated at iteration j < k
    (verify said ok at j, or it hit MAX_ITERATIONS at j < k), treat the
    question's iteration-k result as identical to its iteration-j result.
    The agent stopped emitting; whatever it had at termination is what
    would have been served had we polled at iteration k.
    """
    total = len(results)
    final_correct = sum(1 for r in results if r.get("final_correct"))
    avg_iterations = (
        sum(int(r.get("iterations", 0)) for r in results) / total if total else 0.0
    )

    pass_rate_by_iteration: dict[str, float] = {}
    for k in range(MAX_SQL_ATTEMPTS):
        carried_correct = 0
        for r in results:
            attempts = r.get("attempts", [])
            if not attempts:
                is_correct = False
            elif k < len(attempts):
                is_correct = bool(attempts[k]["correct"])
            else:
                is_correct = bool(attempts[-1]["correct"])
            carried_correct += int(is_correct)
        pass_rate_by_iteration[str(k)] = (carried_correct / total) if total else 0.0

    return {
        "total_questions": total,
        "overall_pass_rate": (final_correct / total) if total else 0.0,
        "final_correct": final_correct,
        "average_iterations": avg_iterations,
        "pass_rate_by_iteration": pass_rate_by_iteration,
        "agent_http_failures": sum(1 for r in results if not r.get("agent_http_ok")),
        "agent_execution_failures": sum(
            1
            for r in results
            if r.get("agent_http_ok") and not r.get("agent_ok", False)
        ),
    }


# ---------- Main (provided) --------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_FILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_FILE)
    parser.add_argument("--agent-url", default=AGENT_URL_DEFAULT)
    args = parser.parse_args()

    questions = [json.loads(line) for line in args.eval_set.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(questions)} eval questions from {args.eval_set}")

    results: list[dict] = []
    t0 = time.monotonic()
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['db_id']}: {q['question'][:60]}...", flush=True)
        results.append(eval_one(q, args.agent_url))
    elapsed = time.monotonic() - t0

    summary = summarize(results)
    out = {
        "summary": summary,
        "wall_clock_seconds": elapsed,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
