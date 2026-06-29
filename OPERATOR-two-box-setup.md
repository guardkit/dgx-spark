# Operator Two-Box Setup — Dell ProMax GB10 (Node A) + DGX Spark (Node B)

Personal operations guide for **my** two-GB10 deployment. **This is not a public runbook** — it maps my two boxes onto the public runbooks + decision records and is my day-to-day operating playbook. The executable procedures live in the runbooks and the version pins live in their PINS blocks; this doc deliberately does **not** duplicate them (they'd rot). It is roles + bring-up order + operating modes.

> Companions (the procedures + pins live here): [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) · [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) · [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) · [`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md) · [`DECISION-DF-004`](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md) · the single-Spark runbook's **Appendix B** (my personal fleet config).

---

## The two boxes

| | **Dell ProMax GB10** (`promaxgb10-41b1`) | **New DGX Spark** |
|---|---|---|
| **Two-Spark role** | **Node A** — day-to-day fleet host | **Node B** — heavy / long work |
| **Fleet** | my **personal** lineup (Appendix B): `coach-ft-v3`, `qwen36-workhorse`, `qwen-graphiti`, `nomic-embed`, `embed`, `granite-docling`/`granite-vision-*`, `gemma4-coach`/`gemma4-tutor`/`gemma4-31b`, `qwen3-coder-30b`, `gpt-oss-120b`, `architect-agent` | the **public** fleet (`workhorse`/`coach`/`chat`/`embed` + on-demand `gpt-oss-120b`); idle or dormant during heavy work |
| **Software baseline** | already a full single-Spark baseline (llama-swap v219 · llama.cpp b9430 SM121 · CUDA 13 · llama-swap user unit + linger · system keepalive) | gets that baseline by running the single-Spark runbook |
| **Day-to-day** | serves my agents (Jarvis / forge / AutoBuild / DeepAgents) on `:9000` (+ optional LiteLLM `:4000`) | runs DeepSeek-V4-Flash **with** Node A (cross-node TP) **or** the agentic dataset factory, solo |

---

## Bring-up order (one time)

### New DGX Spark = Node B
1. **One-time box setup:** passwordless sudo (README → *one-time box setup*); run the agent **as your user, not root**.
2. `claude "execute RUNBOOK-single-spark-bring-up.md"` — validates the box, builds llama.cpp (SM121), stands up the public fleet on `:9000`. On a fresh box the Phase 3.2 config-backup step is a no-op and it installs clean.
3. *(optional)* `claude "execute RUNBOOK-litellm-front-door.md"` — only if you want a local gateway on Node B for the dataset-factory work; **not needed** for cross-node TP (the unified front door lives on Node A).

### Dell ProMax = Node A
- It is **already** a working single-Spark box. **Do NOT run `RUNBOOK-single-spark-bring-up.md` on it** — Phase 3.2 would overwrite `/opt/llama-swap/config/config.yaml` and `-watch-config` would reload the fleet instantly, tearing down my personal lineup. It only needs the cross-node layer (below).

### Connect the pair — run once, from Node A (the Dell)
`claude "execute RUNBOOK-two-spark-bring-up.md"` — **one coordinated bring-up for the pair**, not two separate runs. It adds (additively, no llama-swap-config overwrite): CX-7 firmware on both, the ConnectX-7 cable + NCCL fabric, passwordless SSH between the boxes, power-off mitigation, vLLM on both, and the unified **LiteLLM `:4000`** front door on Node A. Per-node steps (firmware, vLLM install) are applied to each box; it coordinates Node B over SSH.

**The one adaptation:** the two-Spark Phase 7 LiteLLM `model_list` is written for the *public* aliases. Edit it to the Dell's **real** aliases before deploying:
- `model_name: workhorse` → `model: openai/qwen36-workhorse`
- add `model_name: coach` → `model: openai/coach-ft-v3`
- `embed` matches as-is; `strategist` and `claude-opus` rows unchanged.
- Confirm the live aliases with `curl -s localhost:9000/v1/models | jq -r '.data[].id'`.

(Applying the front door restarts the Dell's llama-swap once to pick up the CPU-affinity drop-in → a one-time ~81 GB fleet bounce. Schedule it.)

---

## Operating modes (time-shared — the DF-004 memory rule)

The **~115 GB safe ceiling per box** is the constraint that makes these *modes*, not simultaneous states.

### Mode 1 — Day-to-day fleet (default)
Dell (Node A) serves my personal fleet to agents via `:9000` / LiteLLM `:4000`. New Spark (Node B) runs its own fleet or sits idle. No TP, no cabling exercised — two independent single-Spark boxes.

### Mode 2 — Cross-node strategist: DeepSeek-V4-Flash (on demand)
A model too big for one box (~150–158 GB → ~75–80 GB **per node**, sharded TP=2 — see the two-Spark PINS). The shard **cannot co-reside with a full fleet** (~79 GB shard + my ~81 GB Dell fleet ≫ 115 GB), so this is **time-shared with Mode 1, never concurrent**: pause day-to-day serving → run the big model → resume.

```bash
# (1) Drain the fleet on BOTH boxes:
sudo systemctl stop llama-swap-keepalive.timer     # system timer — on each box
systemctl --user stop llama-swap                   # fleet goes dormant (start to revive)
# (2) Launch DeepSeek-V4-Flash --tp 2 across the pair  → two-Spark Phase 8
#     ... use the strategist via LiteLLM :4000 (model_name: strategist) ...
# (3) Tear down the strategist, then revive BOTH fleets:
systemctl --user start llama-swap
sudo systemctl start llama-swap-keepalive.timer
```
(DF-004: a second box buys **capacity, not single-stream speed** — you stack to run a model that doesn't fit one node, time-shared.)

### Mode 3 — Standalone long-run on Node B: the agentic dataset factory (50+ hrs)
Run the dataset factory on the **new Spark alone**. **Not** a two-Spark/TP scenario — no cabling, no NCCL, no draining the Dell. The Dell is untouched and keeps serving day-to-day the whole time.

```bash
# On the new Spark (Node B) ONLY — free the box for the long job:
sudo systemctl stop llama-swap-keepalive.timer
systemctl --user stop llama-swap
# run the dataset factory (its Player model fits one box, e.g. gpt-oss-120b ~63 GB)
# when done:
systemctl --user start llama-swap
sudo systemctl start llama-swap-keepalive.timer
```

---

## Safety — never clobber the Dell
- **Do not run `RUNBOOK-single-spark-bring-up.md`, or deploy the public llama-swap config, on the Dell.** It overwrites `/opt/llama-swap/config/config.yaml`; `-watch-config` reloads instantly, tearing down `coach-ft-v3`, Graphiti, the fleet-memory relay's `embed`, and the vision models. The Dell's config is my **Appendix-B personal variant**.
- The Dell keeps timestamped `config.yaml.bak-<ts>` backups before every change — keep that discipline (the runbooks now do this automatically before any config overwrite).
- Dress-rehearse new runbooks on the **new Spark or a scratch box**, never the Dell.

---

## See also
- [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) — the base fleet runbook (run on Node B). **Appendix B** = my personal fleet config.
- [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) — the optional LiteLLM `:4000` overlay.
- [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) — the cross-node procedure; its Node-roles section documents these three modes + the alias note.
- [`ARCHITECTURE-current.md`](./ARCHITECTURE-current.md) — my current steady-state lineup on the Dell.
- [`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md) (single-Spark front door) · [`DECISION-DF-004`](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md) (two-Spark topology + memory rule).
