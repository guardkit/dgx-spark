# dgx-spark

Runbooks, research, decisions, and operational scripts for running a local AI inference fleet on the **Dell DGX Spark / GB10** (Blackwell SM121, 128 GB unified memory).

This is the consolidated home for the DGX Spark work that was previously scattered across `guardkit/docs/research/dgx-spark/` and `guardkit/scripts/`. See [`MIGRATION.md`](./MIGRATION.md) for what moved and what is still pending.

---

## What this repo is (and isn't)

The community has already documented *how to set up a Spark* thoroughly — NVIDIA's own playbooks, the DGX Spark forum, martinB78's full-stack guide, Dre Dyson's blog series, `mostlygeek/llama-swap`. This repo does **not** re-document that. It stands on it.

What this repo adds is the **operationalisation layer**: the setup knowledge turned into **runbooks that an agent executes** (Claude Code / Codex / OpenCode), where

- the procedure is **version-pinned and deterministic**,
- the hard-won gotchas are encoded as **gates that fail loudly** rather than prose warnings, and
- a **Phase 0 recon pass** checks the forum and upstream repos *the moment you run it* and emits a drift report — so the runbook is honest about what's changed since it was pinned, without rewriting itself.

The contribution is the method and the gates, not the stack. See [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md).

---

## Current stack (steady state)

Honest snapshot of what actually runs in production today:

```
clients (agents, Claude Code, OpenAI/Anthropic-compatible) 
   │
   ▼
llama-swap :9000        ← THE deployed front door (all-llama.cpp; one process tree)
   ├── always-on preload (~80 GB): qwen-graphiti, nomic-embed, qwen36-workhorse, architect-agent
   └── on-demand + matrix sets: tutor, coder, vision (vLLM-in-Docker for a few vision models)
```

- **LiteLLM** is the **Phase 4 routing layer** (the martinB78/community pattern: LiteLLM → llama-swap → vLLM/llama.cpp). It is documented and validated but is **not yet the live front door** — today, agents point at llama-swap on `:9000` directly. Talks/docs should present it that way.
- Hardware: `promaxgb10-41b1`, 121 GB usable of 128 GB unified. Safe ceiling ~115 GB.
- Constraint **DECISION-DF-001**: no cloud API on the dark-factory critical path. Recon/search is *additive*, never on the critical path (see conventions).

---

## Layout

Flat + prefixed, matching the established house convention:

| Prefix / dir | Contents |
|---|---|
| `RUNBOOK-*.md` | Executable runbooks (the deliverables an agent runs). |
| `RESULTS-*.md` / `VALIDATION-*.md` | Execution records / gate outcomes for a given runbook. |
| `DECISION-*.md` | ADRs (or pointers to the canonical ones in `guardkit/docs/decisions/`). |
| `TALK-*.md` | Conference / meetup talk abstracts and session spines. |
| `RUNBOOK-CONVENTIONS.md` | **The method.** Runbook anatomy + the recon→drift→gates pattern. |
| `MIGRATION.md` | Inventory map from the old `guardkit` locations into this repo. |
| `diagrams/` | Architecture diagrams (`.svg` + editable `.excalidraw`). |
| `grammars/` | GBNF grammars (e.g. Coach verdict constraints). |
| `scripts/` | Operational scripts: llama-swap systemd units, keep-alive, health-check, infra. |

---

## Prior art (credit where due)

- [NVIDIA DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719)
- [martinB78 — full-stack LiteLLM + llama-swap + vLLM + llama.cpp on GB10](https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580)
- [Dre Dyson — multi-model stack build + gotchas](https://dredyson.com/)
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) · [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard)

These are the sources the runbooks are built from. The Phase 0 recon pass re-checks them at execution time.
