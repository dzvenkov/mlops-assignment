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
- Current bootstrap note: the WSL Python environment can be synced for the application stack, but local `vllm` installation is deferred until Linux build prerequisites such as `gcc`, `g++`, and Python development headers are available in WSL.

## Local Track Checklist

1. `[x]` `Repository and environment inspection`
   - Confirm repo structure, key files, and current scaffold.
   - Confirm local hardware/backend constraints and placeholder-backend approach.

2. `[x]` `Local environment bootstrap`
   - Create local env configuration from template.
   - Install dependencies.
   - Load the dataset subset required by the repo.

3. `[ ]` `Observability stack startup`
   - Start Docker services.
   - Verify Prometheus, Grafana, and Langfuse are reachable locally.

4. `[ ]` `Placeholder backend decision and startup`
   - Select the local-compatible placeholder backend.
   - Configure `.env` to point the agent at it.
   - Verify the backend responds through an OpenAI-compatible interface.

5. `[ ]` `Agent prompt design`
   - Implement prompt text for generate, verify, and revise.
   - Ensure verifier output format is strict and easy to parse.

6. `[ ]` `Agent graph implementation`
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
