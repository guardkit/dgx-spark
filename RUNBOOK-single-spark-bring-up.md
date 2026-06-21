# Runbook: Single-Spark Bring-Up — Unboxed GB10 → Trusted Multi-Model Endpoint

**Status:** Draft (exemplar for the conventions in [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md); the DDD South West demo spine). Execute end-to-end at least twice before the talk: once to verify, once as a dress rehearsal. Flip to **Verified** after the first green walkthrough.

**Purpose:** Take a DGX Spark / GB10 from fresh to a **trusted, self-verifying multi-model inference endpoint on `:9000`** — built by an **agent** (Claude Code / Codex / OpenCode) *executing this runbook*, not by hand. The procedure is version-pinned; the gotchas are gates; a Phase 0 recon pass reports what's drifted upstream before anything runs.

```
clients (agents, Claude Code — OpenAI / Anthropic-compatible)
   │
   ▼
llama-swap :9000          ← the front door (all-llama.cpp; one process tree under systemd)
   └── always-on preload (~80 GB resident, ~40 GB headroom):
         qwen-graphiti · nomic-embed · qwen36-workhorse · architect-agent
   (on-demand models + vLLM vision models are out of scope — see below)
```

**Machine:** `promaxgb10-41b1` (or a fresh GB10), DGX OS, Blackwell **SM121**, 128 GB unified memory (**121 GB usable**, safe ceiling **115 GB**).
**Conventions:** [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — recon → drift report → gates; promotion by PR.
**Prior art it stands on:** NVIDIA GB10 playbooks · [DGX Spark forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719) · [martinB78 full-stack guide](https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580) · Dre Dyson · [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap). The Phase 0 recon re-checks these at run time.
**Source material:** `RUNBOOK-v3-production-deployment.md` (the proven procedure), `RUNBOOK-llama-swap-setup.md` (SM121 build flags + dynamic-VRAM launcher), `ARCHITECTURE-current.md` (steady-state lineup).
**Expected wall-clock:** fresh box **~60–90 min** (the llama.cpp build + model staging dominate); a re-run on a built box **~15 min**.
**On-stage target:** the demo is the **recon → execute → gate-catch arc** on a box with llama.cpp already built — **~8–10 min** (see Talk Track).
**Outputs:** `RESULTS-single-spark-bring-up-<YYYY-MM-DD>.md`, the committed `DRIFT-single-spark-bring-up-<YYYY-MM-DD>.md`, and the live `/opt/llama-swap/config/config.yaml`.

---

## PINS (single source of truth — steps reference these, gates assert them, recon checks them)

```
PINS (set 2026-06-19)
  llama-swap            v208                         single-dash flags; matrix coexistence
  llama.cpp             SM121 build, 121a-real       PR #17570 (Anthropic Messages API)
  workhorse  GGUF       Qwen3.6-35B-A3B-Instruct UD-Q4_K_XL
  graphiti   GGUF       Qwen2.5-14B-Instruct Q8_0
  embed      GGUF       nomic-embed-text-v1.5 F16    (768 dims)
  architect  GGUF       Gemma 4 26B-A4B Q4_K_M       (+ thinking template)
  KV_CACHE_TYPE         q8_0
  MEM_CEILING_GB        115                          121 usable; freeze observed at 114
  ENDPOINT              :9000
```

When recon flags drift on a pin, the fix is a **PR editing this block** — never a runtime edit (conventions §6).

---

## What this runbook does NOT cover

- **vLLM-in-Docker vision models** (`granite-docling`, `granite-vision-*`). Separate; the LPA POC owns them.
- **The LiteLLM Phase-4 routing layer.** The live front door here is **llama-swap on `:9000`**. LiteLLM (the martinB78 pattern: LiteLLM → llama-swap) is a separate appendix/runbook — don't imply it's in production.
- **Two-Spark / tensor-parallel.** That's the second talk; capture spine in `RUNBOOK-two-spark-video-capture.md`.
- **Fine-tuning / dataset work.** Out of scope.
- **Cloud-LLM escalation.** Zero cloud on the critical path (DECISION-DF-001). If a step needs the network it's *additive* and degrades gracefully.

---

## Demo narrative (Talk Track) — read this first

The runbook below is the operator script; this is what you say while the agent runs it. The on-stage demo runs Phase 0 + a thin slice of Phases 2–5 on a box that already has llama.cpp built.

1. **Frame** (~45s): "I'm going to stand up a multi-model inference box — but I'm not going to type setup commands. I'm going to have a coding agent *run a runbook*, and watch it catch a known landmine before it costs me an afternoon."
2. **Credit the giants** (~30s): topology slide; name NVIDIA's playbooks, the forum, martinB78, Dre Dyson, llama-swap. "I'm standing on all of this. What I added is the layer that makes it reproducible and self-checking."
3. **Run Phase 0 recon** (~2 min): kick it off; **show the drift report** — the deterministic pin checks (`llama-swap`, `llama.cpp`, model repos) plus the forum scan, with one flagged regression. "Notice it didn't rewrite a single step. It told me what changed since I pinned this, and left the procedure alone."
4. **Agent executes** (~3 min): let it move through the pinned build/serve steps; narrate over it.
5. **A gate fires** (~2 min) — the money shot. The run hits the assertion for the flagged regression (e.g. the ARM64 silent-CPU-fallback gate, or the 115 GB memory-ceiling gate) and **halts loudly**. "That's the difference between a blog post and a runbook. The blog says *watch out*. The gate *stops*."
6. **Fix is a PR, not a hack** (~1 min): update the pin, reviewed, re-run green. "Reproducible, not improvised."
7. **Land it** (~45s): "Got it reliable on one box. The next question is two boxes — and the answer surprised me." → tee the capacity-not-speed talk.

On-stage total: ~8–10 min. Buffer for the agent's pace.

---

## Phase 0: Recon (read-only, advisory) — emits the drift report

No side effects. Fixed sources only. Output is a drift report, never edited steps. Degrades gracefully (DF-001): if the network is down, record `recon: skipped` and proceed on the PINS.

### 0.1 Deterministic pin checks (no LLM judgment)

```bash
echo "=== Phase 0.1: deterministic pin checks ==="
# llama-swap pinned vs latest release
PINNED_SWAP=v208
LATEST_SWAP=$(curl -s --max-time 10 https://api.github.com/repos/mostlygeek/llama-swap/releases/latest | jq -r .tag_name 2>/dev/null)
[ -z "$LATEST_SWAP" ] && echo "[recon] llama-swap check SKIPPED (offline)" \
  || { [ "$PINNED_SWAP" = "$LATEST_SWAP" ] && echo "[OK] llama-swap $PINNED_SWAP == latest" \
                                          || echo "[DRIFT] llama-swap pinned $PINNED_SWAP, latest $LATEST_SWAP"; }

# llama.cpp built commit vs upstream HEAD (advisory — we pin a build, not a tag)
BUILT=$(~/llama.cpp/build/bin/llama-server --version 2>&1 | grep -oE 'b[0-9]+' | head -1 || echo "unbuilt")
HEAD=$(curl -s --max-time 10 https://api.github.com/repos/ggml-org/llama.cpp/tags | jq -r '.[0].name' 2>/dev/null)
echo "[info] llama.cpp built=${BUILT} upstream_latest_tag=${HEAD:-offline}"
```

Repeat the pattern for the graphiti fork tag and HF model-repo revisions as needed.

### 0.2 Source scan (fixed list, LLM judgment)

Agent instruction — **tightly scoped, never "search the web and adapt":**

```
RECON SOURCES (fixed)
  - NVIDIA DGX Spark / GB10 forum   topics: llama-swap, llama.cpp SM121 build,
      gpu-memory-utilization, memory freeze, --no-mmap, vLLM aarch64
  - github.com/mostlygeek/llama-swap   releases + open issues
  - github.com/ggml-org/llama.cpp      releases + SM121-tagged issues
  - Dre Dyson blog                     new posts since the PINS date
TASK: "Report only items newer than the PINS date that affect a pinned component
       or a known gotcha. Emit a drift report. Do NOT propose edited steps. Do NOT
       change any pin."
```

### 0.3 Emit the drift report

Write `DRIFT-single-spark-bring-up-<timestamp>.md` in the format of conventions §5 (pin checks + source scan + a one-line verdict). Commit it next to the RESULTS file. **▶ GATE (advisory):** if any `[DRIFT]`/`[FLAG]` lines exist, the operator reviews them before promoting pins — but the run proceeds on the current PINS regardless.

---

## Phase 1: Pre-flight (go/no-go — no side effects yet)

### 1.1 Confirm hardware, DGX OS, CUDA

```bash
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader   # expect GB10 / ~128 GiB
/usr/local/cuda/bin/nvcc --version | grep release
uname -m                                                          # expect aarch64
```
**Pass:** GB10 reported; `nvcc` present; `aarch64`. If `nvcc` is missing, install the CUDA toolkit before continuing.

### 1.2 Confirm headroom

```bash
df -h /opt 2>/dev/null || df -h /          # need ~80 GB free for model staging
free -g                                    # confirm 128 GB unified visible
```
**Pass:** ≥ 80 GB free on the model volume.

### 1.3 Confirm models on disk (or plan downloads)

```bash
for pat in "qwen3.6*35*q4" "qwen2.5*14*q8" "nomic*f16" "gemma*4*26b*a4b*q4"; do
  f=$(find ~/.cache/huggingface -iname "*${pat}*.gguf" 2>/dev/null | head -1)   # -iname: files are lowercase
  echo "${pat}: ${f:-NOT FOUND}"
done
```
**Pass:** all four resolve. If any are missing, download per `RUNBOOK-llama-swap-setup.md` §4 (use `HF_HUB_ENABLE_HF_TRANSFER=1`; use the Blackwell-tuned GGUF repos). **Note the case-sensitivity gate:** glob with `-iname`, not `-name` (registry row, conventions §8).

---

## Phase 2: Build llama.cpp for SM121 &nbsp;·&nbsp; **▶ GATE: GPU-bound, not silent CPU**

### 2.1 Build with the Blackwell real-kernel target

```bash
sudo apt-get install -y libcurl4-openssl-dev clang cmake
git clone https://github.com/ggml-org/llama.cpp.git ~/llama.cpp 2>/dev/null; cd ~/llama.cpp
export CUDACXX=/usr/local/cuda/bin/nvcc PATH=/usr/local/cuda/bin:$PATH
cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=ON -DGGML_CUDA_FA_ALL_QUANTS=ON \
      -DCMAKE_CUDA_ARCHITECTURES=121a-real -DGGML_NATIVE=ON
cmake --build build --config Release -j 20
sudo cp build/bin/llama-server build/bin/llama-cli build/bin/llama-bench /usr/local/bin/
```
`121a-real` = real (not PTX) Blackwell SM121 kernels (eugr's recommendation). Build takes 5–15 min.

### 2.2 **▶ GATE — assert GPU-bound (catches the silent-CPU-fallback trap)**

A generic ARM64 build silently runs CPU-only at ~2 tok/s. Prove the GPU is doing the work:

```bash
# warm a tiny model and confirm llama-server shows up as a CUDA compute app
/usr/local/bin/llama-server --version
# during any later inference:
nvidia-smi --query-compute-apps=process_name --format=csv,noheader | grep -q llama-server \
  && echo "GATE PASS: llama-server is GPU-bound" \
  || echo "GATE FAIL: no llama-server in nvidia-smi compute-apps — CPU fallback. STOP."
```
**FAIL → halt.** Rebuild with the flags above; do not proceed on a CPU-only binary.

---

## Phase 3: Install llama-swap + write the config &nbsp;·&nbsp; **▶ GATES: single-dash flags · matrix block · --no-mmap · q8_0 · healthCheckTimeout**

### 3.1 Install llama-swap (pinned, not `latest`)

```bash
ARCH=$(uname -m); case "$ARCH" in aarch64|arm64) BIN=llama-swap-linux-arm64;; *) echo "unsupported $ARCH"; exit 1;; esac
sudo curl -L -o /usr/local/bin/llama-swap \
  "https://github.com/mostlygeek/llama-swap/releases/download/v208/$BIN"   # PIN, per PINS block
sudo chmod +x /usr/local/bin/llama-swap
sudo mkdir -p /opt/llama-swap/{config,logs}; sudo chown -R $USER:$USER /opt/llama-swap
```
**Pass:** binary present. (Pinning, not floating `latest`, is itself a convention — the release cadence is several versions/week.)

### 3.2 Write the config — gates baked into the structure

Write `/opt/llama-swap/config/config.yaml` with the four always-on models. The non-obvious settings below are **gates encoded as config** (each maps to a registry row in conventions §8):

- `healthCheckTimeout: 600` — 120B-class cold load exceeds the default → 504 (registry row).
- `matrix.sets` declaring all four coexist — without it, llama-swap v208 evicts on every cross-model request → load→kill→load thrash (registry row).
- `hooks.on_startup.preload` for all four — deterministic cold-start.
- Every `cmd`: `--no-mmap` (unified-memory slowdown), `--cache-type-k/v q8_0` (f16 KV degrades on SM121), `--jinja` (tool use), `-ngl 999`.

```yaml
healthCheckTimeout: 600
startPort: 5800
logLevel: info
matrix:
  vars: { qg: qwen-graphiti, ne: nomic-embed, qw: qwen36-workhorse, aa: architect-agent }
  sets: { all: "qg & ne & qw & aa" }            # coexistence — prevents eviction thrash
hooks:
  on_startup:
    preload: [qwen-graphiti, nomic-embed, qwen36-workhorse, architect-agent]
models:
  "qwen36-workhorse":           # AutoBuild Player/Coach, Forge, Jarvis-reasoner
    cmd: >
      /usr/local/bin/llama-server --port ${PORT} --host 0.0.0.0
      --model <WORKHORSE_GGUF> --alias qwen36-workhorse
      --ctx-size 65536 --batch-size 2048 --ubatch-size 2048 --threads 16 -ngl 999
      --no-mmap --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0
      --jinja --reasoning off --temp 0.6 --top-p 0.95 -np 1
    checkEndpoint: /health
    ttl: 0
    concurrencyLimit: 2
    aliases: [autobuild-player, coach, forge-orchestrator, claude-sonnet-4-6]
  # qwen-graphiti (Q8_0, --ctx-size 65536 -np 4 → 16K/slot; see -np ctx-split gate),
  # nomic-embed (--embedding, dims 768), and architect-agent (Gemma 4 + thinking
  # template) follow the same shape — copy their blocks from ARCHITECTURE-current.md
  # / RUNBOOK-v3 §5.2 and substitute the resolved <…_GGUF> paths.
```

### 3.3 **▶ GATE — config asserts before starting**

```bash
CFG=/opt/llama-swap/config/config.yaml
grep -q 'matrix:' "$CFG"            && echo "GATE PASS: matrix coexistence block present" || echo "GATE FAIL: no matrix block — eviction thrash. STOP."
grep -q 'healthCheckTimeout: 600' "$CFG" && echo "GATE PASS: cold-load timeout" || echo "GATE FAIL: raise healthCheckTimeout to ≥600."
! grep -q -- '--cache-type-k f16\|--cache-type-v f16' "$CFG" && echo "GATE PASS: KV is q8_0" || echo "GATE FAIL: f16 KV present."
grep -cq -- '--no-mmap' "$CFG" && echo "GATE PASS: --no-mmap present" || echo "GATE FAIL: add --no-mmap."
```
Any FAIL → fix the config, re-assert, then start. **`--config` will be rejected** by v208 — the start command uses single-dash flags (next phase).

---

## Phase 4: Start + preload &nbsp;·&nbsp; **▶ GATES: memory ceiling · systemd cgroup · keep-alive**

### 4.1 Start under systemd — **not** from a VS Code terminal

```bash
sudo tee /etc/systemd/system/llama-swap.service >/dev/null <<'EOF'
[Unit]
Description=llama-swap (all-llama.cpp front door)
After=network-online.target
[Service]
Type=simple
ExecStart=/usr/local/bin/llama-swap -config /opt/llama-swap/config/config.yaml -listen :9000 -watch-config
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now llama-swap
```
Single-dash flags (`-config`, `-listen`, `-watch-config`) — GNU double-dash is silently rejected (registry row).

### 4.2 **▶ GATE — cgroup is the systemd unit, not a Chromium/editor scope**

Running the binary from a VS Code terminal puts the whole process tree in VS Code's Chromium cgroup, where the editor's lifecycle reaps it and bypasses `Restart=` — an invisible failure with no kernel evidence (registry row, RUNBOOK-v3 §10.2).

```bash
cat /proc/$(pgrep -x llama-swap)/cgroup | grep -q 'llama-swap.service' \
  && echo "GATE PASS: under system.slice/llama-swap.service" \
  || echo "GATE FAIL: process is in a chromium/app- scope — start via systemctl, not a terminal. STOP."
```

### 4.3 Preload + **▶ GATE — under the 115 GB ceiling**

Trigger the four loads (one `curl` each, per RUNBOOK-v3 §5.4), wait for ready, then assert memory:

```bash
USED_MIB=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits | awk '{s+=$1} END{print s+0}')
USED_GB=$(awk -v m="$USED_MIB" 'BEGIN{printf "%.1f", m/1024}')
echo "Resident: ${USED_GB} GB"
awk -v g="$USED_GB" 'BEGIN{exit !(g < 115)}' \
  && echo "GATE PASS: ${USED_GB} GB < 115 GB ceiling" \
  || echo "GATE FAIL: ${USED_GB} GB ≥ 115 GB — freeze risk (114 GB freeze on record). Trim ctx/-np. STOP."
```
**Expected:** ~80 GB resident for the four, ~40 GB headroom. Then install the keep-alive timer (RUNBOOK-v3 §5.6) — **llama-swap does not auto-revive crashed children** (registry row).

---

## Phase 5: Validate the endpoint (the trust gates)

### 5.1 Models list

```bash
curl -sf http://localhost:9000/v1/models | jq -r '.data[].id' | sort
```
**Pass:** all four aliases present (`qwen36-workhorse`, `qwen-graphiti`, `nomic-embed`, `architect-agent`).

### 5.2 Workhorse tool-calling + throughput

```bash
curl -s http://localhost:9000/v1/messages -H "Content-Type: application/json" -H "x-api-key: not-needed" \
  -d '{"model":"qwen36-workhorse","max_tokens":256,"messages":[{"role":"user","content":"Write an async Python function to publish to NATS subject fleet.register."}]}' \
  > /tmp/spark-smoke.json
```
**What the reply should look like (load-bearing lines):** a `content` array with assistant text (and, for the tool variant, a `tool_use` block); `stop_reason` present. ~256 tokens should return in ~5–6 s (≈ 40+ tok/s warm). If you get plain text where a tool was expected, `--jinja` isn't active.

### 5.3 Graphiti JSON + embeddings dims

```bash
curl -s http://localhost:9000/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed","input":"dim check"}' | jq '.data[0].embedding | length'
```
**▶ GATE:** dims **== 768** (not 1024 — the embedding-dims registry row). Then run the Graphiti `json_object` extraction smoke from RUNBOOK-v3 §6.1 (expect ≥6 entities / ≥3 relationships).

### 5.4 Decision Gate

| Gate | Result | Note |
|---|---|---|
| P0.3 Drift report emitted + reviewed | | committed `DRIFT-*` |
| P2.2 llama-server GPU-bound | | not CPU fallback |
| P3.3 config asserts (matrix / q8_0 / no-mmap / timeout) | | |
| P4.2 cgroup under systemd | | not Chromium scope |
| P4.3 resident < 115 GB | | **record GB** |
| P5.1 all 4 aliases listed | | |
| P5.2 workhorse tool-call + throughput | | **record tok/s** |
| P5.3 embeddings == 768 dims | | |
| P5.3 Graphiti JSON extraction | | ≥6 ent / ≥3 rel |

---

## Phase 6: Evidence capture → RESULTS

```bash
mkdir -p evidence/single-spark-bring-up
cp /opt/llama-swap/config/config.yaml evidence/single-spark-bring-up/config-$(date +%F).yaml
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv > evidence/single-spark-bring-up/vram-$(date +%F).csv
# the DRIFT report from Phase 0.3 lives at the repo root, committed
```
Then write `RESULTS-single-spark-bring-up-<YYYY-MM-DD>.md`:

```
# RESULTS — Single-Spark Bring-Up (<YYYY-MM-DD>)
## Gate outcomes        (the Phase 5.4 table, filled)
## Recorded numbers     resident GB · workhorse tok/s · embed dims
## Drift report         link to DRIFT-<date>.md + what was promoted (if anything)
## Failures & follow-ups
```

---

## Phase 7: Failure modes — fast triage during rehearsal

| Symptom | Likely cause | Fix |
|---|---|---|
| Inference at ~2 tok/s | ARM64 binary fell back to CPU | Phase 2.2 gate; rebuild with `121a-real`; confirm `nvidia-smi` shows `llama-server` |
| `--config` not parsed / llama-swap won't start | v208 wants single-dash flags | use `-config` / `-listen` (Phase 4.1) |
| Requests thrash: load→kill→load on each model | no `matrix.sets` coexistence block | add it (Phase 3.2); `ttl:0` governs idle only, not request-driven eviction |
| Box freezes / heavy swap during preload | crossed the 121 GB ceiling | Phase 4.3 gate; trim `--ctx-size` or `-np` (recall: `-np` splits ctx across slots) |
| Children die and never come back | parent `Restart=` doesn't revive children | install keep-alive timer (RUNBOOK-v3 §5.6) |
| Process vanishes when the editor reloads | tree captured by VS Code Chromium cgroup | Phase 4.2 gate; start via `systemctl`, not a terminal |
| 504 on first big request | cold load > `healthCheckTimeout` | raise to ≥600 |
| Graphiti writes fail / embeddings mismatch | dims set to 1024 | set `dimensions: 768` (Phase 5.3) |
| Plain text where a `tool_use` was expected | `--jinja` missing | add `--jinja` to the model `cmd` |
| `curl /v1/models` refused | llama-swap not running | `systemctl status llama-swap`; tail `/opt/llama-swap/logs/llama-swap.log` (it's a native process — `docker logs` won't work) |

---

## Phase 8: Demo close

- [ ] Phase 0 drift report committed (`DRIFT-*`)
- [ ] Decision Gate table (5.4) all green, numbers recorded
- [ ] RESULTS file written, evidence bundle saved
- [ ] If green: tag the commit (`git tag single-spark-bring-up-rehearsal-$(date +%F)`)

Leave running for subsequent work: `llama-swap` (it *is* the endpoint). Nothing to tear down — the endpoint staying up is the deliverable. For the **stage** run, the win is the recon → execute → **gate-catch** arc landing in ~8–10 min; the box staying served afterward is the proof.

---

## See also

- [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — the method (recon → drift → gates) and the full gotcha→gate registry.
- `RUNBOOK-v3-production-deployment.md` — the proven end-to-end procedure this exemplar distils.
- `RUNBOOK-llama-swap-setup.md` — SM121 build flags, model downloads, the dynamic-VRAM launcher, the LiteLLM Phase-4 appendix.
- `TALK-ddd-southwest-got-a-spark-now-what.md` — the talk this runbook is the live demo for.
