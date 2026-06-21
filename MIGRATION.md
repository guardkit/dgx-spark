# Migration map: `guardkit` → `dgx-spark`

Inventory of the DGX Spark material currently in `guardkit/`, where each piece lands here, and its status. The Spark work is split across two `guardkit` locations:

- `guardkit/docs/research/dgx-spark/` — docs, runbooks, research, diagrams, grammars
- `guardkit/scripts/` — the operational `llama-swap-*` systemd units, keep-alive, health-check, infra

---

## Recommended approach: copy-then-retire (not move yet)

**Copy** the material in so `dgx-spark` is complete and becomes the canonical home, but **do not delete the `guardkit` copies until a coordinated cutover**. Two reasons it isn't a clean `mv`:

1. **Live systemd installs source from `guardkit/scripts/`.** `RUNBOOK-v3` §5.6/§5.7 install the keep-alive and health-check units *from* `$REPO/scripts/…`, and dev unit `ExecStart` lines point at those repo paths. Moving the scripts breaks the documented install + rollback flow and any running dev units.
2. **Hardcoded paths.** Several runbooks and the rollback blocks reference `~/Projects/appmilla_github/guardkit/scripts/…` and `…/graphiti-mcp-config.yaml.pre-llamacpp.bak`. These must be updated *before* the originals go away.

So: copy → update internal cross-references to the new repo → prove the new repo is the source of truth → then, in a separate cutover, repoint systemd `ExecStart`/install commands and delete the `guardkit` copies.

**Defect to fix in flight:** `llama-swap-setup.md` contains unresolved git merge-conflict markers (`<<<<<<<` / `=======` / `>>>>>>>`) through §12–§15 (the dynamic-VRAM launcher, the LiteLLM Phase-4 section, and future-enhancements). Produce a single clean canonical version here; do not copy the conflicted file verbatim.

---

## Docs & runbooks (`guardkit/docs/research/dgx-spark/` → repo root)

| Source file | → Destination | Status | Notes |
|---|---|---|---|
| `README.md` (current operational state) | `ARCHITECTURE-current.md` | current | The live model lineup / matrix sets / routing recipes. This repo's `README.md` is the new front page; the old one becomes the steady-state architecture doc. |
| `AUTOBUILD-ON-LLAMA-SWAP-findings.md` | same name | current | Primary chronological findings log §1–§11. The history of record. |
| `RUNBOOK-v3-production-deployment.md` | same name | current arch / historical lineup | Architectural sections current; model table superseded by `ARCHITECTURE-current.md`. |
| `RUNBOOK-v2-all-llamacpp-architecture.md` | same name | validation runbook | Pairs with `RESULTS-v2`. |
| `RUNBOOK-qwen3.6-27b-validation.md` | same name | validation runbook | Pairs with `RESULTS-qwen3.6-27b`. |
| `RUNBOOK-two-spark-video-capture.md` | same name | current | Capture spine for the two-Spark talk. |
| `gemma4-as-graphiti-experiment-runbook.md` | same name | worked example | The §9.8 failed experiment, preserved as a pattern. |
| `RESULTS-v3-production-deployment.md` | same name | record | 65 GB VRAM, 41.32 tok/s workhorse. |
| `RESULTS-v2-all-llamacpp-validation.md` | same name | record | The evidence that eliminated vLLM. |
| `RESULTS-qwen3.6-27b-validation.md` | same name | record | The evidence that pivoted dense→MoE. |
| `VALIDATION-D6F4-gap-fix-results.md` | same name | record | Six D6F4 gaps PASS. |
| `VALIDATION-OPS-7CB1-9F2A-results.md` | same name | record | Keep-alive revival + concurrency tuning. |
| `POST-VALIDATION-model-strategy-revision.md` | same name | decision | Dense-27B → MoE-35B-A3B pivot. |
| `gb10-memory-budget-and-macbook-offload.md` | same name | current | Where the 121 GB goes. |
| `gb10-model-requirements-matrix.md` | same name | current-ish | Role mapping valid; speed expectations superseded. |
| `two-spark-serving-research-and-references.md` | same name | current | Two-Spark research + the diagrams section. |
| `qwen3.6-27b-gb10-community-research.md` | same name | research | Forum research. |
| `llama-swap-keepalive-start-stop.md` | same name | current | Keep-alive control + when-to-pause recipes. |
| `llama-swap-systemd-supervision.md` | same name | current | User-unit with `-watch-config`. |
| `llama-swap-config.yaml` | `examples/llama-swap-config.example.yaml` | superseded | Live config is at `/opt/llama-swap/config/config.yaml`. Keep as an annotated example only. |
| `llama-swap-setup.md` | `RUNBOOK-llama-swap-setup.md` | historical + **conflicted** | **Resolve merge conflicts first.** Keep the SM121 build flags + dynamic-VRAM launcher; fold the LiteLLM section into a clean Phase-4 appendix. |
| `dark-factory-economics-and-model-serving.md` | `history/` | historical | April 2026 cost-crisis research; conclusions superseded. |
| `dark-factory-dataset-factory-conversation-starter.md` | `history/` | historical | |
| `TASK-graphiti-yaml-endpoint-migration.md` | `history/` | historical | The 2026-04-29 endpoint migration task. |
| `DGX Spark, Nemotron3, and NVFP4 … Braun.pdf` | `reference/` | background | NVFP4 optimisation reading. |
| `diagrams/` (6 files) | `diagrams/` | current | 3 `.svg` + 3 `.excalidraw`. |
| `grammars/` (3 files) | `grammars/` | current | Coach-verdict GBNF + README. |

## Operational scripts (`guardkit/scripts/` → `scripts/`)

| Source | → Destination | Status | Notes |
|---|---|---|---|
| `llama-swap-keepalive.{sh,service,timer}` | `scripts/` | current | **Live install sources from `guardkit` today** — mirror here, repoint at cutover. |
| `llama-swap-healthcheck.{sh,service,timer}` | `scripts/` | current | Same caveat. |
| `infra-up.sh` / `infra-down.sh` / `infra-status.sh` + `infra/` | `scripts/` | review | Confirm Spark-scoped vs guardkit-wide before copying. |
| `archive-vllm/` | `scripts/archive-vllm/` | historical | Rollback target for the pre-llama.cpp pure-vLLM stack. |

---

## New, native to this repo

| File | Status |
|---|---|
| `README.md` | done — repo front page. |
| `RUNBOOK-CONVENTIONS.md` | done — the method (recon → drift → gates). |
| `MIGRATION.md` | done — this file. |
| `TALK-ddd-southwest-got-a-spark-now-what.md` | done — DDD abstract + session spine. |
| `RUNBOOK-single-spark-bring-up.md` | **next** — the exemplar runbook under the new conventions; the talk's live demo. |

---

## Execution status

Nothing has been copied yet — this file is the plan. Next steps, in order:
1. Build `RUNBOOK-single-spark-bring-up.md` (exemplar-before-template).
2. Copy the **current** docs above, updating internal cross-refs to this repo.
3. Mirror the operational scripts (live installs keep pointing at `guardkit` until cutover).
4. Resolve `llama-swap-setup.md` conflicts into a clean `RUNBOOK-llama-swap-setup.md`.
5. Coordinated cutover: repoint systemd `ExecStart`/install commands, then retire the `guardkit` copies.
