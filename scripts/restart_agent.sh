#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
WORKERS="${WORKERS:-1}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/agent-$TIMESTAMP.log"
PID_FILE="$LOG_DIR/agent.pid"

mkdir -p "$LOG_DIR"

kill_existing_agent() {
  local pids=()

  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      pids+=("$pid")
    fi
  fi

  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pgrep -f "uvicorn agent\\.server:app .*--port $PORT" || true)

  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(pgrep -f "python .*uvicorn agent\\.server:app .*--port $PORT" || true)

  if command -v lsof >/dev/null 2>&1; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] && pids+=("$pid")
    done < <(lsof -ti tcp:"$PORT" || true)
  fi

  if [[ "${#pids[@]}" -eq 0 ]]; then
    echo "No existing agent process found on port $PORT"
    return
  fi

  mapfile -t unique_pids < <(printf '%s\n' "${pids[@]}" | awk 'NF && !seen[$0]++')
  echo "Stopping existing agent process(es): ${unique_pids[*]}"
  kill "${unique_pids[@]}" 2>/dev/null || true
  sleep 2

  for pid in "${unique_pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      echo "Force killing stubborn process $pid"
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

start_agent() {
  cd "$ROOT_DIR"
  nohup uv run uvicorn agent.server:app --host "$HOST" --port "$PORT" --workers "$WORKERS" >"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" >"$PID_FILE"
  sleep 2

  if kill -0 "$pid" 2>/dev/null; then
    echo "Agent started on http://localhost:$PORT"
    echo "PID: $pid"
    echo "Workers: $WORKERS"
    echo "Log: $LOG_FILE"
  else
    echo "Agent failed to stay up. Check log: $LOG_FILE" >&2
    tail -n 50 "$LOG_FILE" >&2 || true
    exit 1
  fi
}

kill_existing_agent
start_agent
