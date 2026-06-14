#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".venv/bin/python" ]]; then
  echo "Expected .venv/bin/python in $ROOT_DIR"
  echo "Run this from the Linux/WSL repo copy after 'uv sync --frozen'."
  exit 1
fi

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

LOG_DIR="${VLLM_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${VLLM_LOG_FILE:-$LOG_DIR/vllm-$TIMESTAMP.log}"

MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-3B-Instruct}"
HOST="${VLLM_HOST:-0.0.0.0}"
PORT="${VLLM_PORT:-8000}"
GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.85}"
DTYPE="${VLLM_DTYPE:-half}"
ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-FLASH_ATTN}"
ENFORCE_EAGER="${VLLM_ENFORCE_EAGER:-1}"
DISABLE_CASCADE_ATTN="${VLLM_DISABLE_CASCADE_ATTN:-1}"
USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

export VLLM_USE_FLASHINFER_SAMPLER="$USE_FLASHINFER_SAMPLER"

echo "Starting vLLM"
echo "Repo: $ROOT_DIR"
echo "Model: $MODEL"
echo "Host: $HOST"
echo "Port: $PORT"
echo "DType: $DTYPE"
echo "Attention backend: $ATTENTION_BACKEND"
echo "GPU memory utilization: $GPU_MEMORY_UTILIZATION"
echo "Enforce eager: $ENFORCE_EAGER"
echo "Disable cascade attention: $DISABLE_CASCADE_ATTN"
echo "Use FlashInfer sampler: $USE_FLASHINFER_SAMPLER"
echo "Log: $LOG_FILE"
echo

{
  echo "[$(date --iso-8601=seconds)] Launching vLLM"
  cmd=(
    .venv/bin/python -u -m vllm.entrypoints.openai.api_server
    --model "$MODEL"
    --host "$HOST"
    --port "$PORT"
    --dtype "$DTYPE"
    --attention-backend "$ATTENTION_BACKEND"
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  )

  if [[ "$ENFORCE_EAGER" == "1" ]]; then
    cmd+=(--enforce-eager)
  fi

  if [[ "$DISABLE_CASCADE_ATTN" == "1" ]]; then
    cmd+=(--disable-cascade-attn)
  fi

  printf '[%s] Command: ' "$(date --iso-8601=seconds)"
  printf '%q ' "${cmd[@]}"
  printf '\n'

  "${cmd[@]}"
} 2>&1 | tee "$LOG_FILE"
