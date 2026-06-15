#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Optional toggles:
#   INSTALL_SYSTEM_PACKAGES=1  Install Ubuntu packages with apt. Default: 1
#   INSTALL_DOCKER=0           Install docker + compose plugin. Default: 0
#   START_DOCKER_STACK=0       Run `docker compose up -d` after bootstrap. Default: 0
#   LOAD_DATA=1                Run scripts/load_data.py. Default: 1
#   RUN_UV_SYNC=1              Run `uv sync --frozen`. Default: 1
#   CREATE_ENV_FILE=1          Create .env from .env.example if missing. Default: 1
#
# Optional values to inject into .env:
#   HF_TOKEN=...
#   VLLM_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
#   LANGFUSE_PUBLIC_KEY=...
#   LANGFUSE_SECRET_KEY=...
#   LANGFUSE_HOST=http://localhost:3001

INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-1}"
INSTALL_DOCKER="${INSTALL_DOCKER:-0}"
START_DOCKER_STACK="${START_DOCKER_STACK:-0}"
LOAD_DATA="${LOAD_DATA:-1}"
RUN_UV_SYNC="${RUN_UV_SYNC:-1}"
CREATE_ENV_FILE="${CREATE_ENV_FILE:-1}"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

update_env_var() {
  local key="$1"
  local value="$2"
  local env_file="$ROOT_DIR/.env"

  python3 - "$env_file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]

lines = env_path.read_text().splitlines() if env_path.exists() else []
updated = False
out = []
for line in lines:
    if line.startswith(f"{key}="):
        out.append(f"{key}={value}")
        updated = True
    else:
        out.append(line)

if not updated:
    out.append(f"{key}={value}")

env_path.write_text("\n".join(out) + "\n")
PY
}

if [[ "$INSTALL_SYSTEM_PACKAGES" == "1" ]]; then
  log "Installing Ubuntu system packages"
  sudo apt-get update
  sudo apt-get install -y \
    build-essential \
    python3-dev \
    python3-venv \
    curl \
    git \
    ca-certificates \
    pkg-config
fi

if [[ "$INSTALL_DOCKER" == "1" ]]; then
  log "Installing Docker and Compose plugin"
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
  log "Docker group updated for $USER. You may need to log out and back in for non-sudo docker usage."
fi

if ! need_cmd uv; then
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if [[ "$CREATE_ENV_FILE" == "1" && ! -f "$ROOT_DIR/.env" ]]; then
  log "Creating .env from .env.example"
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if [[ -f "$ROOT_DIR/.env" ]]; then
  if [[ -n "${HF_TOKEN:-}" ]]; then
    log "Writing HF_TOKEN into .env"
    update_env_var "HF_TOKEN" "$HF_TOKEN"
  fi

  if [[ -n "${VLLM_MODEL:-}" ]]; then
    log "Writing VLLM_MODEL into .env"
    update_env_var "VLLM_MODEL" "$VLLM_MODEL"
  fi

  if [[ -n "${LANGFUSE_PUBLIC_KEY:-}" ]]; then
    log "Writing LANGFUSE_PUBLIC_KEY into .env"
    update_env_var "LANGFUSE_PUBLIC_KEY" "$LANGFUSE_PUBLIC_KEY"
  fi

  if [[ -n "${LANGFUSE_SECRET_KEY:-}" ]]; then
    log "Writing LANGFUSE_SECRET_KEY into .env"
    update_env_var "LANGFUSE_SECRET_KEY" "$LANGFUSE_SECRET_KEY"
  fi

  if [[ -n "${LANGFUSE_HOST:-}" ]]; then
    log "Writing LANGFUSE_HOST into .env"
    update_env_var "LANGFUSE_HOST" "$LANGFUSE_HOST"
  fi
fi

if [[ "$RUN_UV_SYNC" == "1" ]]; then
  log "Syncing Python environment with uv"
  uv sync --frozen
fi

if [[ "$LOAD_DATA" == "1" ]]; then
  log "Loading dataset and generating eval/load-test inputs"
  uv run python scripts/load_data.py
fi

if [[ "$START_DOCKER_STACK" == "1" ]]; then
  log "Starting Docker observability stack"
  if need_cmd docker; then
    if docker compose version >/dev/null 2>&1; then
      docker compose up -d
    else
      sudo docker compose up -d
    fi
  else
    log "Docker is not installed. Re-run with INSTALL_DOCKER=1 or install Docker manually."
    exit 1
  fi
fi

log "Bootstrap complete"
cat <<'EOF'

Suggested next steps:
1. Review .env and fill any remaining secrets.
2. Start vLLM with:
   uv run python -m vllm.entrypoints.openai.api_server --model "$VLLM_MODEL" --host 0.0.0.0 --port 8000
   or use scripts/start_vllm.sh
3. Start the agent server with:
   uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001
4. If Docker was started, verify:
   http://localhost:3000  Grafana
   http://localhost:3001  Langfuse
   http://localhost:9090  Prometheus

EOF
