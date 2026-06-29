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

## Distillation mode — Player-Coach placement on two boxes (candidate, not committed)

> **Status: under consideration.** The distillation-mode/dataset-factory *design* lives in the external **guardkit** repo, not here — this section is only the **serving/memory placement** analysis for running it across these two boxes. Two accuracy flags: the PP-vs-TP throughput numbers below are **PROPOSED (cited), not yet measured on this hardware** (DF-004 flips PROPOSED→ACCEPTED only after the two-Spark Phase 9 benchmark), and **uneven PP on the pinned `jasl/vllm dda4668b` build is unverified** — a test item, not a known capability.

**The question:** run a big teacher Player (DeepSeek-V4-Flash) + the Coach for a long (50+ hr) distillation run. The aggregate memory fits easily (2×115 ≈ 230 GB vs DeepSeek ~158 + Coach ~17), so can the *per-box* split be made **uneven** to give the Coach headroom?

**Does TP=2 have to be ~50/50? Yes — confirmed.** Tensor parallelism shards every weight matrix across the two ranks (each tensor dim ÷ TP size), so a uniform-architecture model splits ~50/50 by construction; there is no asymmetric-TP knob. (~158 GB → ~79 GB/node — `RUNBOOK-two-spark-bring-up.md:289`.)

**The lever for an UNEVEN split is Pipeline Parallelism** — PP splits by contiguous *layers*, not tensor dimensions, so you can put fewer layers on the Coach's box:
- **SGLang** supports it explicitly — `SGLANG_PP_LAYER_PARTITION=15,15,15,16` names the per-rank layer counts.
- **vLLM** (incl. the pinned `jasl/vllm dda4668b`) exposes **no flag** to specify the partition; its default is an even split. **Treat user-controlled uneven PP on vLLM as unproven until you test it on the pinned build.**
- PP is also plausibly the *throughput-correct* cross-node choice for a batch job anyway (lower per-pass link traffic than TP's per-forward-pass all-reduce; the repo cites **PP ~555 vs TP ~252 tok/s @batch128** — PROPOSED). TP wins only single-stream (batch=1).

So your intuition is right: **the aggregate fits; TP's forced 50/50 is what makes one box tight.** Going TP→PP and skewing layers off the Coach box rebalances it — but then **watch the heavy box as the new KV constraint** at long context (under PP, KV follows layer ownership; rebalance toward ~45/55 if it grows).

**Placements, ranked (per-box vs the 115 GB safe ceiling):**

| Rank | Placement | Coach box | Other box | Verdict |
|---|---|---|---|---|
| **1 — default** | `gpt-oss-120b` Player + Coach, **one box, NO cross-node** | Coach ~17–26 GB (+ ~65 GB fleet if the Dell keeps serving) | Player ~65–93 GB (gpt-oss 63 + KV) | **comfortable**; Dell **stays up** (this *is* Mode 3); no interconnect tax. Cost: gpt-oss-120b is a **weaker teacher** than 284B DeepSeek. |
| **2 — your question, literally** | DeepSeek **PP=2 uneven** (~40/60 layers), Coach on the light box | ~81–99 GB | ~97–110 GB | **comfortable IF uneven PP works on your build**; takes **both boxes → Dell down** 50+ hr; vLLM uneven-PP unverified (or use SGLang). |
| **3 — avoid** | DeepSeek **TP=2** + co-resident Coach on one box | ~98–117+ GB at the factory regime → trips the ceiling | ~76–91 GB | **tight→no**; both boxes + Dell down, and only fits if you starve ctx / `--max-num-seqs 2` — which defeats a throughput/batch job (and decode collapses under concurrency; MTP makes TP worse cross-node). |

**A simplifier worth knowing:** the factory's Player and Coach run **sequentially** — the Coach grades *after* the Player generates (`gb10-model-requirements-matrix.md` R5/R6, marked never-concurrent). They never compute at the same instant. In row 1 they even **co-fit resident** (~80 GB on one box), so the Coach grades between Player batches with no swap thrash and the Dell untouched.

**Recommendation:** default to **row 1** — one-box `gpt-oss-120b` Player + Coach (the repo's already-documented Mode 3). Only go cross-node if **DeepSeek-class teacher quality is the actual factory bottleneck**; if so, prefer **PP over TP**, and first run two tests on the pinned `jasl/vllm dda4668b`: (a) whether uneven PP partitioning is configurable at all, and (b) the PP-vs-TP throughput on *your* hardware — falling back to **SGLang** (explicit `SGLANG_PP_LAYER_PARTITION`) or **even PP=2 with the Coach placed off the strategist boxes** if vLLM won't take an uneven partition. Either way, a DeepSeek cross-node Player takes the Dell's day-to-day fleet **down for the whole run** (Mode 2 territory).

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
