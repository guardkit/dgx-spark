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

## Running a runbook

Clone the repo, point an agent (Claude Code / Codex / OpenCode) at a runbook, and tell it to execute:

```bash
git clone https://github.com/guardkit/dgx-spark.git && cd dgx-spark
claude "execute RUNBOOK-single-spark-bring-up.md"      # or: codex exec … / opencode run …
```

The agent runs **every** step itself — `apt`/`pip` installs, the ~35 GB model pull (Phase 1.5), the llama.cpp build + binary install, llama-swap install, config deploy, start, and the validation gates. Long downloads/builds run **inline** — edit the wait out of any recording. There are **no manual prerequisites** beyond the one-time box setup below.

### One-time box setup: passwordless sudo

The runbooks use `sudo` (apt, `install` to `/usr/local/bin`, `mkdir`/`chown` `/opt`, `systemctl`, `fwupdmgr`, …). For the agent to run **unattended**, the operator user needs **passwordless sudo** — otherwise the first `sudo` blocks on a password the agent can't type. The agent can't enable this itself (enabling sudo needs sudo), so run it **once per box** (you enter your password this one time):

```bash
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/90-spark-agent >/dev/null
sudo chmod 0440 /etc/sudoers.d/90-spark-agent
sudo visudo -cf /etc/sudoers.d/90-spark-agent      # must print "parsed OK"
```

- **Run the agent as that user, not root** — the runbooks supervise llama-swap as a *user* systemd unit (`systemctl --user` + `loginctl enable-linger`); running as root breaks that supervision model.
- **Revoke** when you're done filming: `sudo rm /etc/sudoers.d/90-spark-agent`.
- `NOPASSWD:ALL` is fine for a **dedicated** Spark. On a shared box, scope it to just the commands the runbooks invoke (`apt-get, apt, apt-mark, install, cp, mkdir, chown, systemctl, tee, fwupdmgr, nvidia-smi, visudo`) — tighter, at the cost of brittleness if one is missed.

The only other non-agent inputs are **physical** and **two-Spark-only**: plugging in the ConnectX-7 cable, and any firmware reboot. Everything else is a step the agent runs.

---

## Current stack (steady state)

The architecture the public single-Spark runbook stands up — LiteLLM `:4000` in front of the llama-swap `:9000` fleet ([`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md)):

```
clients (agents, Claude Code, OpenAI/Anthropic-compatible) 
   │
   ▼
LiteLLM :4000           ← the front door (control plane: claude-* wildcard · per-agent keys · spend; NO cloud fallback, DF-001)
   │   (LiteLLM-down fallback: clients may hit llama-swap :9000 directly)
   ▼
llama-swap :9000        ← the unified-memory model layer (all-llama.cpp; one process tree under a user systemd unit)
   └── always-on fleet (~65 GB): workhorse (Qwen3.6-35B-A3B) · coach (Gemma-4-26B-A4B) · chat (gpt-oss-20b) · embed (Qwen3-Embedding-0.6B, 1024-dim)
   └── on-demand: gpt-oss-120b (evicts the fleet)
```

- **LiteLLM `:4000` is the front door** — the *full* community stack (martinB78 → Dre Dyson → dasroot: `client → LiteLLM → llama-swap → engines`), not a llama-swap-only subset. It is a router / control plane only (per-agent keys, `claude-*` wildcard, spend, fallback policy); llama-swap underneath owns model lifecycle / unified memory. [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) Phase 5.4 stands it up on one node; [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) extends it across two ([`DECISION-DF-004`](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md), PROPOSED).
- Constraint **DECISION-DF-001**: no cloud API on the dark-factory critical path — enforced as a LiteLLM config gate (`fallbacks: []` + `context_window_fallbacks: []`, and no cloud model named as a fallback target). Recon/search is *additive*, never on the critical path (see conventions).
- Hardware: `promaxgb10-41b1`, 121 GB usable of 128 GB unified, safe ceiling ~115 GB. (`:9000` is *this box's* llama-swap port — the upstream community default is `:8080`; the universal part is the single-proxy-port principle.)

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
