# Implementation Plan

## Workflow Agreements

- We will implement this assignment step by step as a learning exercise.
- `IMPLEMENTATION.md` will be referred to as "the doc" in our conversation.
- The doc should be updated when new workflow agreements, decisions, or clarified execution rules are established.
- Work is split into two tracks:
  - `Local Track`: complete and validate everything possible on the local machine with a placeholder backend.
  - `H100 Track`: repeat the required final validation, tuning, measurements, and screenshots on the real VM with the H100.
- We will treat each checklist item as a checkpoint.
- After each checklist item, execution pauses automatically.
- After each checklist item, Codex summarizes:
  - what was done
  - what was learned
  - any blockers or deviations
  - what the next checklist item is
- Codex must wait for explicit user confirmation before proceeding to the next checklist item.
- If a checklist item reveals that the plan should change, Codex should propose a plan adjustment before continuing.
- Final reported metrics, eval quality, and SLO conclusions must come from the H100 track, not the local placeholder backend.
- Local-track results are for wiring, debugging, and learning only unless explicitly marked otherwise.

## Two-Track Overview

`Local Track` exists to finish code, wiring, and dry-run validation without depending on scarce H100 time. This is where we complete the assignment implementation, verify the agent flow, validate the eval runner, and prepare the observability/reporting pieces.

`H100 Track` exists to generate the real assignment evidence and final deliverables. This is where we run the actual `Qwen/Qwen3-30B-A3B-Instruct-2507` endpoint, validate the final dashboard and traces, collect screenshots, run baseline and post-tuning evals, and determine the true SLO outcome.

### Current Selected Local Placeholder Stack

- Local backend approach: `WSL2 + vLLM + Qwen2.5-3B-Instruct`
- Reason for selection: this keeps the local development environment closer to the real assignment architecture than a hosted API or a non-vLLM local runner.
- Constraint note: local results remain for wiring, debugging, and learning only; final metrics and conclusions must still come from the H100 track.
- Current bootstrap note: the WSL Python environment can be synced for the application stack, and local `vllm` now depends on additional Linux build/runtime tooling such as `gcc`, `g++`, Python development headers, `nvcc`, and `ninja`.
- Current runtime note: the main repo remains on `D:\Homework\mlops-assignment`, but the local `vllm` runtime uses a separate WSL-native repo copy at `~/mlops-assignment-wsl` because the Windows-mounted path caused WSL `p9` filesystem stalls for `transformers` and `vllm`.
- Current version note: local `vllm` was upgraded from `0.10.2` to `0.23.0` to resolve the tokenizer compatibility issue seen with `Qwen/Qwen2.5-3B-Instruct`.
- Current launcher note: manual local `vllm` startup uses `run_vllm.sh` from the WSL-local repo copy, not from `/mnt/d/...`.

## Local Track Checklist

1. `[x]` `Repository and environment inspection`
   - Confirm repo structure, key files, and current scaffold.
   - Confirm local hardware/backend constraints and placeholder-backend approach.

2. `[x]` `Local environment bootstrap`
   - Create local env configuration from template.
   - Install dependencies.
   - Load the dataset subset required by the repo.

3. `[x]` `Observability stack startup`
   - Start Docker services.
   - Verify Prometheus, Grafana, and Langfuse are reachable locally.

4. `[x]` `Placeholder backend decision and startup`
   - Select the local-compatible placeholder backend.
   - Configure `.env` to point the agent at it.
   - Verify the backend responds through an OpenAI-compatible interface.

5. `[x]` `Agent prompt design`
   - Implement prompt text for generate, verify, and revise.
   - Ensure verifier output format is strict and easy to parse.

6. `[x]` `Agent graph implementation`
   - Implement `verify_node`, `revise_node`, and `route_after_verify`.
   - Keep the loop cap and history behavior aligned with the assignment.

7. `[ ]` `Agent server smoke test`
   - Run the agent server.
   - Send manual `/answer` requests.
   - Confirm at least one question exercises a revise loop.

8. `[ ]` `Langfuse local tracing hookup`
   - Configure local Langfuse credentials.
   - Confirm traces appear with node-level spans.
   - Confirm metadata tags strategy works.

9. `[ ]` `Eval runner implementation`
   - Implement `evals/run_eval.py`.
   - Confirm final correctness, iteration counts, and per-iteration pass-rate logic.

10. `[ ]` `Local eval dry run`
    - Run the eval set locally against the placeholder backend.
    - Validate result JSON structure and inspect failure patterns.

11. `[ ]` `Grafana dashboard implementation`
    - Extend the provisioned dashboard JSON.
    - Prepare required latency, throughput, and KV-cache panels.
    - If the placeholder backend lacks real vLLM metrics, note which panels are structurally ready and must be finalized on H100.

12. `[ ]` `Load-test dry run`
    - Run a short load test locally.
    - Confirm request flow, output JSON, and dashboard/tracing visibility.

13. `[ ]` `Report skeleton preparation`
    - Create the future `REPORT.md` structure or a clear outline.
    - Prepare section headings and placeholders for final H100-only results.

14. `[ ]` `Local-track review checkpoint`
    - Confirm all code paths are complete locally.
    - Produce a short readiness summary for the H100 track.

## H100 Track Checklist

1. `[ ]` `VM setup and connectivity`
   - Connect to the VM.
   - Forward required ports: `3000`, `3001`, `8000`, `8001`, `9090`.
   - Confirm local browser access to the services.

2. `[ ]` `VM bootstrap`
   - Clone or sync the repo.
   - Install dependencies.
   - Create `.env`.
   - Load the dataset.
   - Start the Docker observability stack.

3. `[ ]` `Real vLLM launch`
   - Start vLLM for `Qwen/Qwen3-30B-A3B-Instruct-2507`.
   - Capture exact serving flags and rationale notes for the report.

4. `[ ]` `Manual vLLM validation`
   - Test several eval questions manually.
   - Confirm output looks like sensible SQL.
   - Capture `screenshots/vllm_manual_query.png`.

5. `[ ]` `Grafana metric validation`
   - Verify live vLLM metrics populate the intended dashboard panels.
   - Adjust panel queries if needed.
   - Capture `screenshots/grafana_serving.png`.

6. `[ ]` `Agent validation on real backend`
   - Run the agent server against the H100 vLLM endpoint.
   - Confirm successful end-to-end answers and at least one revise path.

7. `[ ]` `Langfuse validation on real backend`
   - Confirm traces, waterfall spans, and metadata tags.
   - Capture `screenshots/langfuse_trace.png` and `screenshots/langfuse_tags.png`.

8. `[ ]` `Baseline eval`
   - Run the 30-question eval against the real backend.
   - Save `results/eval_baseline.json`.
   - Capture `screenshots/grafana_eval_run.png`.

9. `[ ]` `Baseline analysis`
   - Record overall pass rate, per-iteration pass rates, and baseline latency observations.
   - Decide whether the agent loop is materially helping.

10. `[ ]` `Baseline load test`
    - Run the SLO load test at an initial RPS.
    - Record achieved RPS, error rates, and latency percentiles.

11. `[ ]` `Tuning iteration 1`
    - Form a metrics-backed hypothesis.
    - Change one serving parameter or configuration choice.
    - Re-run the load test and compare outcomes.

12. `[ ]` `Tuning iteration 2`
    - Repeat the same disciplined loop with a new hypothesis.

13. `[ ]` `Tuning iteration 3+`
    - Continue until the SLO is hit or the gap is well quantified and explained.

14. `[ ]` `Before/after evidence capture`
    - Save the screenshots that best show the meaningful tuning change:
    - `screenshots/grafana_before.png`
    - `screenshots/grafana_after.png`

15. `[ ]` `Post-tuning eval`
    - Run the eval set again on the final tuned config.
    - Save `results/eval_after_tuning.json`.
    - Compare quality against baseline.

16. `[ ]` `Final report completion`
    - Write the final `REPORT.md`.
    - Include serving config, baseline eval, tuning log, final SLO result, agent value assessment, and specific future work.

17. `[ ]` `Submission audit`
    - Confirm all required deliverables exist in the repo and are named correctly.

## Checkpoint Protocol

- At the end of each checklist item, stop work.
- Provide a short checkpoint note with:
  - status
  - outputs or artifacts created
  - important observations
  - proposed next step
- Do not begin the next checklist item until the user explicitly confirms.

## Checkpoint Log

### Local Track 1 - Repository and environment inspection

- Status: completed
- Date: 2026-06-13
- What was done:
  - inspected the repo structure and assignment scaffold
  - reviewed the main assignment documentation and key implementation files
  - confirmed the local-machine role as a development-only environment
  - selected `WSL2 + vLLM + Qwen2.5-3B-Instruct` as the local placeholder approach
- What was learned:
  - the repo is scaffolded cleanly around prompts, graph logic, evals, and observability
  - this machine is not suitable for the final required 30B serving target
  - the local track should stay focused on wiring, validation, and learning
- Blockers or deviations:
  - none
- Next checkpoint:
  - `Local Track` checkpoint 2 `Local environment bootstrap`

### Local Track 2 - Local environment bootstrap

- Status: completed
- Date: 2026-06-13
- What was done:
  - verified WSL availability with Ubuntu on WSL2
  - confirmed Linux `Python 3.12.3` and Linux `uv`
  - created the WSL project environment with `uv sync --frozen --no-install-package vllm`
  - loaded the dataset with `uv run python scripts/load_data.py`
  - generated `evals/eval_set.jsonl` and `load_test/perf_pool.jsonl`
- What was learned:
  - the general Python environment is usable for early assignment work
  - local `vllm` installation needs additional Linux build prerequisites
  - dataset generation is working and produced the expected SQLite corpus and eval inputs
- Blockers or deviations:
  - full local `vllm` install was deferred because WSL lacks `gcc`, `g++`, and likely Python development headers
- Next checkpoint:
  - `Local Track` checkpoint 3 `Observability stack startup`

### Local Track 3 - Observability stack startup

- Status: completed
- Date: 2026-06-13
- What was done:
  - started Docker Desktop and launched the assignment stack with `docker compose up -d`
  - verified the assignment containers for Prometheus, Grafana, Langfuse, Postgres, Redis, ClickHouse, and MinIO started
  - confirmed local reachability of:
    - `http://localhost:9090` for Prometheus
    - `http://localhost:3000` for Grafana
    - `http://localhost:3001` for Langfuse
- What was learned:
  - the observability stack works locally on the expected assignment ports once the Docker engine is running
  - Grafana and Langfuse needed a short warm-up period before responding cleanly to HTTP checks
- Blockers or deviations:
  - initial startup was blocked by another local Docker stack already using ports `3000` and `9090`
  - checkpoint completion required stopping the conflicting stack before retrying
- Next checkpoint:
  - `Local Track` checkpoint 4 `Placeholder backend decision and startup`

### Local Track 4 - Placeholder backend decision and startup

- Status: completed
- Date: 2026-06-14
- What was done:
  - selected `Qwen/Qwen2.5-3B-Instruct` as the local placeholder model
  - updated local `.env` to use `Qwen/Qwen2.5-3B-Instruct`
  - verified WSL GPU visibility and PyTorch CUDA access
  - confirmed that running heavy Python libraries from the mounted path `/mnt/d/Homework/mlops-assignment` was unreliable for local `vllm`
  - created a WSL-native runtime repo copy at `~/mlops-assignment-wsl`
  - installed and synced the WSL-local runtime environment there
  - upgraded the repo dependency from `vllm 0.10.2` to `vllm 0.23.0` and refreshed `uv.lock`
  - added a manual launcher script `run_vllm.sh` for local WSL runtime startup
  - verified that `vllm 0.23.0` progressed through tokenizer initialization, model download, model weight loading, and compile/warmup on the WSL-local repo copy
  - installed WSL CUDA toolkit support so `nvcc` is now available to the local runtime
  - identified a later `flashinfer` JIT dependency on `ninja` and installed `ninja-build` in WSL
  - reran the local server after installing `ninja-build` and collected a newer startup log from the WSL-local runtime
  - adjusted `run_vllm.sh` to use a safer local configuration by disabling the FlashInfer sampler, pinning a conservative attention backend, and enabling eager execution
  - copied the updated launcher into the WSL-local runtime repo and successfully started the OpenAI-compatible vLLM server on `http://localhost:8000`
  - verified that `http://localhost:8000/metrics` exposes live `vllm:*` metrics and that Prometheus is scraping the `vllm` target successfully
- What was learned:
  - `vllm 0.10.2` had a tokenizer compatibility issue with the installed `transformers` stack for `Qwen/Qwen2.5-3B-Instruct`
  - `vllm 0.23.0` resolves that tokenizer issue and gets much further into startup
  - the WSL-local repo copy is the correct runtime location; the mounted `/mnt/d/...` repo is not reliable for local `vllm`
  - local startup required lowering GPU memory utilization to `0.85` to clear the initial VRAM budget gate on the RTX 3060 12 GB
  - after the NVIDIA driver update and reboot, the startup path moved past the earlier CUDA-toolkit gate and then failed later in `flashinfer` JIT compilation because `ninja` was missing
  - after installing `ninja-build`, startup progressed further again, and the next blocker is no longer a missing executable but a `flashinfer` CUDA compilation compatibility failure
  - on this WSL + RTX 3060 setup, a safer local profile was needed to avoid the failing `flashinfer` sampling path
  - the local placeholder backend is now good enough for agent wiring, manual requests, and local observability validation
- Blockers or deviations:
  - startup required a local-only workaround for `flashinfer` CUDA compilation failure, including:
    - `error: class "cub::_V_300302_SM_860::BlockAdjacentDifference<__nv_bool, 512, 1, 1>" has no member "FlagHeads"`
  - related context:
    - local runtime now passes filesystem, tokenizer, driver, VRAM-budget, `nvcc`, and `ninja` toolchain issues
    - the workaround was to change local-serving configuration rather than continue debugging that kernel path
- Runtime paths and artifacts:
  - main editable repo: `D:\Homework\mlops-assignment`
  - WSL-local runtime repo: `~/mlops-assignment-wsl`
  - manual launcher in main repo: `run_vllm.sh`
  - manual launcher must be copied/run from the WSL-local repo for local `vllm`
- Next checkpoint:
  - `Local Track` checkpoint 5 `Agent prompt design`

### Local Track 5 - Agent prompt design

- Status: completed
- Date: 2026-06-14
- What was done:
  - implemented `GENERATE_SQL_SYSTEM` and `GENERATE_SQL_USER` in `agent/prompts.py`
  - implemented `VERIFY_SYSTEM` and `VERIFY_USER` with a strict JSON-only contract for verifier output
  - implemented `REVISE_SYSTEM` and `REVISE_USER` so the revise step can use the schema, prior SQL, execution result, and verifier complaint
  - kept the prompt instructions aligned with the existing scaffold in `agent/graph.py` and the Phase 3 targets in `README.md`
- What was learned:
  - the safest local prompt style for this checkpoint is narrow and explicit: SQL-only for generate/revise, JSON-only for verify
  - the verifier prompt should focus on obvious failure cases from the assignment: SQL errors, empty-but-implausible results, and mismatched answer shape
  - the revise prompt benefits from preserving correct parts of the prior query rather than asking for a full restart every time
- Blockers or deviations:
  - none at the prompt-design level
  - prompt quality against the local 3B model is still provisional and will need real behavioral validation once the graph nodes are implemented
- Outputs or artifacts:
  - `agent/prompts.py`
- Next checkpoint:
  - `Local Track` checkpoint 6 `Agent graph implementation`

### Local Track 6 - Agent graph implementation

- Status: completed
- Date: 2026-06-15
- What was done:
  - implemented `verify_node` in `agent/graph.py`
  - implemented `revise_node` in `agent/graph.py`
  - implemented `route_after_verify` in `agent/graph.py`
  - added a small helper to defensively extract a JSON object from verifier output
  - kept iteration counting aligned with the existing generate node and `MAX_ITERATIONS`
  - validated the updated graph code from WSL against the Windows repo path using the working WSL Python environment
- What was learned:
  - we can keep the Windows repo as the editing source of truth while using WSL for meaningful runtime-style validation
  - the verifier path benefits from defensive JSON extraction because even strict prompts may still be wrapped in fences or stray text
  - the local checkpoint-6 logic is now structurally ready for end-to-end agent testing
- Blockers or deviations:
  - direct Windows-side environment checks were not useful for this runtime step because the working dependency environment lives in WSL
  - no code blocker remains for checkpoint 6 itself
- Outputs or artifacts:
  - `agent/graph.py`
- Verification:
  - WSL `py_compile` check passed for the updated agent files
  - WSL behavioral check passed for:
    - verifier false branch
    - verifier true branch
    - revise SQL extraction
    - router end/revise decisions
- Next checkpoint:
  - `Local Track` checkpoint 7 `Agent server smoke test`

## Success Criteria For This File

- `IMPLEMENTATION.md` exists at the repo root.
- The workflow agreements are the first section in the file.
- Both tracks have separate numbered step-by-step checklists.
- The pause-after-each-checkpoint protocol is explicit and unambiguous.
- The checklists are specific enough that we can execute them one item at a time without redefining scope mid-run.

## Assumptions

- We will keep checkpoint granularity fairly fine so this remains a learning workflow rather than a bulk execution plan.
- "Confirm before proceeding" means explicit user confirmation in chat, not implied continuation.
- The local machine remains a placeholder-development environment; the H100 VM remains the source of final evidence.
