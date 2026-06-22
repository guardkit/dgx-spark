# Runbook: Single-Spark Bring-Up — Unboxed GB10 → Trusted Multi-Model Endpoint

**Status:** Draft (exemplar for the conventions in [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md); the DDD South West demo spine). Execute end-to-end at least twice before the talk: once to verify, once as a dress rehearsal. Flip to **Verified** after the first green walkthrough.

**Purpose:** Take a DGX Spark / GB10 from fresh to a **trusted, self-verifying multi-model inference endpoint on `:9000`** — built by an **agent** (Claude Code / Codex / OpenCode) *executing this runbook*, not by hand. The procedure is version-pinned; the gotchas are gates; a Phase 0 recon pass reports what's drifted upstream before anything runs. It stands up the **public, all-open-model config** committed at [`examples/llama-swap-config.public.yaml`](./examples/llama-swap-config.public.yaml) — every model is downloadable, so a viewer can replicate the whole box. (The operator's personal post-Graphiti variant is **Appendix B**.)

```
clients (agents, Claude Code — OpenAI / Anthropic-compatible)
   │
   ▼
llama-swap :9000          ← the front door (all-llama.cpp; one process tree under a USER systemd unit)
   └── always-on preload (~65 GB resident, ~50 GB headroom) — all open, downloadable:
         workhorse (Qwen3.6-35B-A3B) · coach (Gemma-4-26B-A4B) · chat (gpt-oss-20b) · embed (Qwen3-Embedding-0.6B)
   └── on-demand: gpt-oss-120b ("big-brain" Player; evicts the fleet)
   (vLLM-in-Docker vision models are out of scope — see below)
```

**Machine:** `promaxgb10-41b1` (the Dell ProMax GB10 reference box) or a fresh DGX Spark / GB10, DGX OS, Blackwell **SM121**, 128 GB unified memory (**121 GB usable**, safe ceiling **115 GB**).
**Conventions:** [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — recon → drift report → gates; promotion by PR.
**Prior art it stands on:** [NVIDIA dgx-spark-playbooks](https://github.com/NVIDIA/dgx-spark-playbooks) (official) · [DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719) · [martinB78 full-stack guide](https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580) · [Dre Dyson](https://dredyson.com/) · [Spark Arena leaderboard](https://spark-arena.com/leaderboard) · [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap). The Phase 0 recon re-checks these at run time.
**Source material (now in this repo):** [`RUNBOOK-v3-production-deployment.md`](./RUNBOOK-v3-production-deployment.md) (the proven procedure), [`RUNBOOK-llama-swap-setup.md`](./RUNBOOK-llama-swap-setup.md) (SM121 build flags + dynamic-VRAM launcher + LiteLLM Phase-4 appendix; the §12–§15 merge conflicts are resolved), [`ARCHITECTURE-current.md`](./ARCHITECTURE-current.md) (steady-state lineup). The committed [`examples/llama-swap-config.public.yaml`](./examples/llama-swap-config.public.yaml) is the runbook's canonical config target.
**Expected wall-clock:** fresh box **~60–90 min** (the llama.cpp build + model staging dominate); a re-run on a built box **~15 min**.
**On-stage target:** the demo is the **recon → execute → gate-catch arc** on a box with llama.cpp already built — **~8–10 min** (see Talk Track).
**Outputs:** `RESULTS-single-spark-bring-up-<YYYY-MM-DD>.md`, the committed `DRIFT-single-spark-bring-up-<YYYY-MM-DD>.md`, and the live `/opt/llama-swap/config/config.yaml`.

---

## PINS (single source of truth — steps reference these, gates assert them, recon checks them)

```
PINS (set 2026-06-21)
  llama-swap            v219                         single-dash flags; matrix coexistence (v208+; reference box runs v219)
  llama.cpp             SM121 build, 121a-real       PR #17570 (Anthropic Messages API); last-verified build b9430 (2026-05-30)
  workhorse  GGUF       Qwen3.6-35B-A3B-Instruct UD-Q4_K_XL   unsloth/Qwen3.6-35B-A3B-GGUF     (Player)
  coach      GGUF       Gemma-4-26B-A4B-it UD-Q4_K_XL         unsloth/gemma-4-26B-A4B-it-GGUF  (Coach; stock/open)
  chat       GGUF       gpt-oss-20b MXFP4                     unsloth/gpt-oss-20b-GGUF         (general chat)
  embed      GGUF       Qwen3-Embedding-0.6B Q8_0            Qwen/Qwen3-Embedding-0.6B-GGUF    (1024 dims)
  big (opt)  GGUF       gpt-oss-120b MXFP4                    ggml-org/gpt-oss-120b-GGUF       (on-demand Player)
  KV_CACHE_TYPE         q8_0                         on large-ctx models (workhorse / coach)
  MEM_CEILING_GB        115                          121 usable; freeze observed at 114 (TOTAL unified, not just compute-apps)
  ENDPOINT              :9000
  CONFIG                examples/llama-swap-config.public.yaml   (this runbook's canonical target)
```

When recon flags drift on a pin, the fix is a **PR editing this block** — never a runtime edit (conventions §6).

---

## What this runbook does NOT cover

- **vLLM-in-Docker vision models** (`granite-docling`, `granite-vision-*`). Separate; the LPA POC owns them.
- **The LiteLLM Phase-4 routing layer.** The live front door here is **llama-swap on `:9000`**. LiteLLM (the martinB78 pattern: LiteLLM → llama-swap) is a separate appendix/runbook — don't imply it's in production.
- **The operator's personal fine-tuned Coach (`coach-ft-v3`) + the post-Graphiti lineup.** That is **Appendix B** — a diff against the public config, not the public demo.
- **Two-Spark / tensor-parallel.** That's the second talk; capture spine in `RUNBOOK-two-spark-video-capture.md`.
- **Fine-tuning / dataset work.** Out of scope.
- **Cloud-LLM escalation.** Zero cloud on the critical path (DECISION-DF-001). If a step needs the network it's *additive* and degrades gracefully.

---

## Demo narrative (Talk Track) — read this first

The runbook below is the operator script; this is what you say while the agent runs it. The on-stage demo runs Phase 0 + a thin slice of Phases 2–5 on a box that already has llama.cpp built.

1. **Frame** (~45s): "I'm going to stand up a multi-model inference box — but I'm not going to type setup commands. I'm going to have a coding agent *run a runbook*, and watch it catch a known landmine before it costs me an afternoon."
2. **Credit the giants** (~30s): topology slide; name NVIDIA's playbooks, the forum, martinB78, Dre Dyson, Spark Arena, llama-swap. "I'm standing on all of this. What I added is the layer that makes it reproducible and self-checking."
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
PINNED_SWAP=v219
LATEST_SWAP=$(curl -s --max-time 10 https://api.github.com/repos/mostlygeek/llama-swap/releases/latest | jq -r .tag_name 2>/dev/null)
[ -z "$LATEST_SWAP" ] && echo "[recon] llama-swap check SKIPPED (offline)" \
  || { [ "$PINNED_SWAP" = "$LATEST_SWAP" ] && echo "[OK] llama-swap $PINNED_SWAP == latest" \
                                          || echo "[DRIFT] llama-swap pinned $PINNED_SWAP, latest $LATEST_SWAP"; }

# llama.cpp built version vs upstream HEAD (advisory — we pin a build, not a tag).
# Point LLAMA_SERVER at the IN-SERVICE binary: /usr/local/bin if Phase 2.1 copied
# it there, else the build tree (the reference box serves from ~/llama.cpp-new/build/bin).
LLAMA_SERVER=$(command -v llama-server || echo ~/llama.cpp-new/build/bin/llama-server)
BUILT=$("$LLAMA_SERVER" --version 2>&1 | grep -oE 'version: [0-9]+' | grep -oE '[0-9]+' | head -1 || echo "unbuilt")
HEAD=$(curl -s --max-time 10 https://api.github.com/repos/ggml-org/llama.cpp/tags | jq -r '.[0].name' 2>/dev/null)
echo "[info] llama.cpp built=b${BUILT} upstream_latest_tag=${HEAD:-offline}"
```

Repeat the pattern for HF model-repo revisions as needed. (The `version: <N>` parse matches current `llama-server --version` output, which prints a bare integer, not a `b<N>` tag.)

### 0.2 Source scan (fixed list, LLM judgment)

Agent instruction — **tightly scoped, never "search the web and adapt":**

```
RECON SOURCES (fixed)
  - NVIDIA DGX Spark / GB10 forum   topics: llama-swap, llama.cpp SM121 build,
      gpu-memory-utilization, memory freeze, --no-mmap, vLLM aarch64
  - github.com/NVIDIA/dgx-spark-playbooks   (llama-cpp / cli-coding-agent updates)
  - github.com/mostlygeek/llama-swap   releases + open issues
  - github.com/ggml-org/llama.cpp      releases + SM121-tagged issues
  - Spark Arena leaderboard            (model-ranking shifts)
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
/usr/local/cuda/bin/nvcc --version | grep release                # build (Phase 2) needs this exact path
uname -m                                                          # expect aarch64
```
**Pass:** GB10 reported; `nvcc` present at `/usr/local/cuda/bin/nvcc`; `aarch64`. If `nvcc` is missing, install the CUDA toolkit before continuing (Phase 2.1 hardcodes that path).

### 1.2 Confirm headroom

```bash
df -h /opt 2>/dev/null || df -h /          # need ~80 GB free for model staging
free -g                                    # confirm 128 GB unified visible
```
**Pass:** ≥ 80 GB free on the model volume.

### 1.3 Confirm models on disk (or plan downloads)

```bash
# Search BOTH the HF cache and the served model root (/opt/llama-swap/models is canonical).
for pat in "qwen3.6*35*a3b" "gemma*4*26b*a4b*it" "gpt-oss-20b" "qwen3*embedding*0.6"; do
  f=$(find ~/.cache/huggingface /opt/llama-swap/models -iname "*${pat}*.gguf" 2>/dev/null | head -1)
  echo "${pat}: ${f:-NOT FOUND}"
done
```
**Pass:** all four resolve. If any are missing, download the GGUFs named in the PINS block (use `HF_HUB_ENABLE_HF_TRANSFER=1`; use the Blackwell-tuned / Unsloth GGUF repos) into `/opt/llama-swap/models/<dir>/`. **Note the case-sensitivity gate:** glob with `-iname`, not `-name` (registry row, conventions §8). The served path is `/opt/llama-swap/models/` — staging only into the HF cache will pass this glob but the config `--model` paths must point at what you actually serve.

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
`121a-real` = real (not PTX) Blackwell SM121 kernels (eugr's recommendation). Build takes 5–15 min. `LLAMA_CURL=ON` enables `--hf-repo` model pulls; `FA_ALL_QUANTS=ON` covers all KV-quant flash-attn paths.
**Already-built box:** the reference machine serves from `~/llama.cpp-new/build/bin/llama-server` and did **not** copy into `/usr/local/bin`. Phase 0.1 and the 2.2 gate use `command -v llama-server` (falling back to the build tree), so they find whichever is in service. The committed public config points `cmd:` at `/usr/local/bin/llama-server` — either `cp` the built binary there (above) or edit the config's binary path to the build tree.

### 2.2 **▶ GATE — assert GPU-bound (catches the silent-CPU-fallback trap)**

A generic ARM64 build silently runs CPU-only at ~2 tok/s. Prove the GPU is doing the work. **This gate is only meaningful once a model is RESIDENT** — a bare `--version` loads nothing, and process-presence alone cannot tell "no model loaded" from "CPU fallback." Run it **after** the Phase 4 preload (or load one model first) and assert the GPU is actually holding weights (`used_memory > 0`):

```bash
LLAMA_SERVER=$(command -v llama-server || echo ~/llama.cpp-new/build/bin/llama-server)
"$LLAMA_SERVER" --version
USED=$(nvidia-smi --query-compute-apps=process_name,used_memory --format=csv,noheader,nounits \
        | awk -F', *' '/llama-server/ {s+=$2} END{print s+0}')
awk -v u="$USED" 'BEGIN{exit !(u>0)}' \
  && echo "GATE PASS: llama-server GPU-bound (${USED} MiB on device)" \
  || echo "GATE FAIL: no llama-server GPU memory — CPU fallback OR no model loaded. STOP."
```
**FAIL → halt.** If a model *is* loaded and this still fails, rebuild with the flags above; do not proceed on a CPU-only binary.

---

## Phase 3: Install llama-swap + deploy the config &nbsp;·&nbsp; **▶ GATES: single-dash flags · matrix block · --no-mmap · q8_0 · healthCheckTimeout**

### 3.1 Install llama-swap (pinned, not `latest`)

```bash
ARCH=$(uname -m); case "$ARCH" in aarch64|arm64) BIN=llama-swap-linux-arm64;; *) echo "unsupported $ARCH"; exit 1;; esac
sudo curl -L -o /usr/local/bin/llama-swap \
  "https://github.com/mostlygeek/llama-swap/releases/download/v219/$BIN"   # PIN, per PINS block
sudo chmod +x /usr/local/bin/llama-swap
sudo mkdir -p /opt/llama-swap/{config,logs,models}; sudo chown -R $USER:$USER /opt/llama-swap
```
**Pass:** binary present (`llama-swap --version` → `version: 219`). (Pinning, not floating `latest`, is itself a convention — the release cadence is several versions/week. v219+ keeps the single-dash flag contract.)

### 3.2 Deploy the config — gates baked into the structure

Copy the committed public config into place (it is the single source of truth for this runbook; every non-obvious setting is a gate annotated in-file):

```bash
sudo install -D -m644 examples/llama-swap-config.public.yaml /opt/llama-swap/config/config.yaml
```

It ships the four always-on open models (`workhorse` · `coach` · `chat` · `embed`) plus on-demand `gpt-oss-120b`, with the gotchas encoded as config (each maps to a registry row in conventions §8):

- `healthCheckTimeout: 600` — 120B-class cold load exceeds the default → 504.
- `matrix.sets` declaring the fleet coexists — without it, llama-swap evicts on every cross-model request → load→kill→load thrash.
- `hooks.on_startup.preload` for all four — deterministic cold-start.
- Every `cmd`: `--no-mmap`, `--jinja`, `-ngl 999`; `--cache-type-k/v q8_0` on the large-ctx models (workhorse/coach). f16 KV degrades on SM121 / blows the ceiling at large ctx.

**Adjust before starting:** the `--model` paths to where you staged the GGUFs (Phase 1.3) and the binary path (`/usr/local/bin/llama-server`, or the build tree per Phase 2.1).

### 3.3 **▶ GATE — config asserts before starting**

```bash
CFG=/opt/llama-swap/config/config.yaml
grep -q 'matrix:' "$CFG"            && echo "GATE PASS: matrix coexistence block present" || echo "GATE FAIL: no matrix block — eviction thrash. STOP."
grep -q 'healthCheckTimeout: 600' "$CFG" && echo "GATE PASS: cold-load timeout" || echo "GATE FAIL: raise healthCheckTimeout to ≥600."
! grep -q -- '--cache-type-k f16\|--cache-type-v f16' "$CFG" && echo "GATE PASS: no explicit f16 KV" || echo "GATE FAIL: f16 KV present."
grep -cq -- '--no-mmap' "$CFG" && echo "GATE PASS: --no-mmap present" || echo "GATE FAIL: add --no-mmap."
```
Any FAIL → fix the config, re-assert, then start. **`--config` will be rejected** by v208+ — the start command uses single-dash flags (next phase).

---

## Phase 4: Start + preload &nbsp;·&nbsp; **▶ GATES: memory ceiling · systemd cgroup · keep-alive**

### 4.1 Start under a USER systemd unit — **not** a system/root unit, **not** a VS Code terminal

The reference box supervises llama-swap as a **user** unit. A `User=root` *system* unit races the user-owned `/opt/llama-swap/` tree for `:9000` — that legacy system unit is parked as `llama-swap.service.legacy-*.bak`. Use a user unit + linger so it boots without a login:

```bash
mkdir -p ~/.config/systemd/user /opt/llama-swap/logs
cat > ~/.config/systemd/user/llama-swap.service <<'EOF'
[Unit]
Description=llama-swap (all-llama.cpp front door)
After=network-online.target
[Service]
Type=simple
ExecStart=/usr/local/bin/llama-swap -config /opt/llama-swap/config/config.yaml -listen :9000 -watch-config
Restart=on-failure
RestartSec=5
StandardOutput=append:/opt/llama-swap/logs/llama-swap.log
StandardError=append:/opt/llama-swap/logs/llama-swap.log
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload && systemctl --user enable --now llama-swap
sudo loginctl enable-linger "$USER"                       # survives logout / boots without login
sudo systemctl disable --now llama-swap.service 2>/dev/null || true   # ensure no root unit races :9000 on reboot
```
Single-dash flags (`-config`, `-listen`, `-watch-config`) — GNU double-dash is silently rejected (registry row). Manage it with `systemctl --user …` (note the `--user`).

### 4.2 **▶ GATE — cgroup is a systemd llama-swap unit, not a Chromium/editor scope**

Running the binary from a VS Code terminal puts the whole process tree in VS Code's Chromium cgroup, where the editor's lifecycle reaps it and bypasses `Restart=` — an invisible failure with no kernel evidence (registry row, RUNBOOK-v3 §10.2). The user unit's cgroup is under `user@.service/.../app.slice/llama-swap.service`; a system unit's is under `system.slice/llama-swap.service`. Accept either; reject editor scopes:

```bash
CG=$(cat /proc/$(pgrep -x llama-swap)/cgroup)
echo "$CG" | grep -qE '/llama-swap\.service$' && ! echo "$CG" | grep -qE 'app-|chromium|vscode|code-' \
  && echo "GATE PASS: under a systemd llama-swap.service cgroup (user or system), not an editor scope" \
  || echo "GATE FAIL: process is in a chromium/app- scope (or not under llama-swap.service) — start via 'systemctl --user', not a terminal. STOP."
```

### 4.3 Preload + **▶ GATES — under the 115 GB ceiling (TOTAL unified) + keep-alive firing**

Trigger the four loads (one `curl` each, per RUNBOOK-v3 §5.4), wait for ready, then assert memory. The documented freeze (114 GB) is a **total unified-memory** event, not a compute-apps event — so check both, and gate on the total:

```bash
# (1) compute-apps resident (GPU-held weights + KV) — informational
USED_MIB=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits | awk '{s+=$1} END{print s+0}')
USED_GB=$(awk -v m="$USED_MIB" 'BEGIN{printf "%.1f", m/1024}')
# (2) TOTAL unified-memory pressure — the load-bearing ceiling check
TOTAL_USED_GB=$(free -g | awk '/^Mem:/ {print $3}')
echo "Resident (compute-apps): ${USED_GB} GB · total unified used: ${TOTAL_USED_GB} GB"
awk -v g="$TOTAL_USED_GB" 'BEGIN{exit !(g < 115)}' \
  && echo "GATE PASS: total unified ${TOTAL_USED_GB} GB < 115 GB ceiling" \
  || echo "GATE FAIL: total unified ${TOTAL_USED_GB} GB ≥ 115 GB — freeze risk (114 GB freeze on record). Trim ctx/-np or a model. STOP."
```
**Expected:** ~65 GB resident for the four, ~50 GB headroom. Then install the keep-alive timer (RUNBOOK-v3 §5.6) — **llama-swap does not auto-revive crashed children** (registry row) — **and assert it is actually firing** (enabled-but-stopped is the real failure state; `is-enabled` is not enough):

```bash
systemctl is-active --quiet llama-swap-keepalive.timer \
  && echo "GATE PASS: keepalive timer active" \
  || echo "GATE FAIL: keepalive timer not active (enabled ≠ active) — run: sudo systemctl start llama-swap-keepalive.timer. STOP."
```

---

## Phase 5: Validate the endpoint (the trust gates)

### 5.1 Models list

```bash
curl -sf http://localhost:9000/v1/models | jq -r '.data[].id' | sort
```
**Pass:** the four always-on aliases present (`workhorse`, `coach`, `chat`, `embed`). The on-demand `gpt-oss-120b` is also registered (it loads only on request). This is a subset/presence check — production configs legitimately register additional opt-in models.

### 5.2 Workhorse tool-calling + throughput

```bash
curl -s http://localhost:9000/v1/messages -H "Content-Type: application/json" -H "x-api-key: not-needed" \
  -d '{"model":"workhorse","max_tokens":256,"messages":[{"role":"user","content":"Write an async Python function to publish to NATS subject fleet.register."}]}' \
  > /tmp/spark-smoke.json
```
**What the reply should look like (load-bearing lines):** a `content` array with assistant text (and, for the tool variant, a `tool_use` block); `stop_reason` present. ~256 tokens should return in ~5–6 s (≈ 40+ tok/s warm). If you get plain text where a tool was expected, `--jinja` isn't active. (Throughput is not gated here — it's a read-only smoke; record the number in RESULTS.)

### 5.3 Embeddings — dim matches the configured model

```bash
EXPECT_DIM=1024   # Qwen3-Embedding-0.6B = 1024; set 768 if you swapped in nomic-embed-text-v1.5
DIM=$(curl -s http://localhost:9000/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"embed","input":"dim check"}' | jq '.data[0].embedding | length')
[ "$DIM" = "$EXPECT_DIM" ] \
  && echo "GATE PASS: embeddings == ${DIM} dims (matches configured embed model)" \
  || echo "GATE FAIL: embeddings ${DIM} dims, expected ${EXPECT_DIM} — your RAG index dim MUST match the served model. STOP."
```
**▶ GATE:** the served dim must equal what your RAG index expects (a mismatch silently corrupts retrieval). The public config ships Qwen3-Embedding-0.6B at **1024** dims; nomic-embed-text-v1.5 is the **768**-dim drop-in (the original wrong-dim gotcha was a config claiming 1024 against a 768-dim nomic model — set `EXPECT_DIM` to whatever you serve). Graphiti extraction smoke is out of scope for the public box (Appendix B / the personal config).

### 5.4 Decision Gate

| Gate | Result | Note |
|---|---|---|
| P0.3 Drift report emitted + reviewed | | committed `DRIFT-*` |
| P2.2 llama-server GPU-bound (used_memory > 0) | | after preload; not CPU fallback / not-loaded |
| P3.3 config asserts (matrix / no-f16-KV / no-mmap / timeout) | | |
| P4.2 cgroup under a systemd llama-swap.service | | not Chromium/editor scope |
| P4.3 total unified < 115 GB | | **record GB** |
| P4.3 keepalive timer active | | not merely enabled |
| P5.1 four always-on aliases listed | | workhorse · coach · chat · embed |
| P5.2 workhorse tool-call + throughput | | **record tok/s** |
| P5.3 embeddings dim == configured (1024) | | |

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
## Recorded numbers     total unified GB · workhorse tok/s · embed dims
## Drift report         link to DRIFT-<date>.md + what was promoted (if anything)
## Failures & follow-ups
```

---

## Phase 7: Failure modes — fast triage during rehearsal

| Symptom | Likely cause | Fix |
|---|---|---|
| Inference at ~2 tok/s | ARM64 binary fell back to CPU | Phase 2.2 gate; rebuild with `121a-real`; confirm `nvidia-smi` shows `llama-server` with used_memory > 0 |
| `--config` not parsed / llama-swap won't start | v208+ wants single-dash flags | use `-config` / `-listen` (Phase 4.1) |
| Requests thrash: load→kill→load on each model | no `matrix.sets` coexistence block | add it (config ships it); `ttl:0` governs idle only, not request-driven eviction |
| Box freezes / heavy swap during preload | crossed the 121 GB ceiling | Phase 4.3 **total-unified** gate; trim `--ctx-size` or `-np` (recall: `-np` splits ctx across slots) |
| Children die and never come back | parent `Restart=` doesn't revive children | install + **start** keep-alive timer (RUNBOOK-v3 §5.6); assert `is-active` |
| Process vanishes when the editor reloads | tree captured by VS Code Chromium cgroup | Phase 4.2 gate; start via `systemctl --user`, not a terminal |
| `systemctl status llama-swap` says "not found" but it's running | it's a **user** unit | use `systemctl --user status llama-swap` |
| 504 on first big request | cold load > `healthCheckTimeout` | raise to ≥600 |
| RAG retrieval garbage / dim error | served embed dim ≠ index dim | Phase 5.3 gate; match `EXPECT_DIM` to the served model (1024 Qwen3-Embedding / 768 nomic) |
| Plain text where a `tool_use` was expected | `--jinja` missing | add `--jinja` to the model `cmd` |
| `curl /v1/models` refused | llama-swap not running | `systemctl --user status llama-swap`; tail `/opt/llama-swap/logs/llama-swap.log` (native process — `docker logs` won't work) |

---

## Phase 8: Demo close

- [ ] Phase 0 drift report committed (`DRIFT-*`)
- [ ] Decision Gate table (5.4) all green, numbers recorded
- [ ] RESULTS file written, evidence bundle saved
- [ ] If green: tag the commit (`git tag single-spark-bring-up-rehearsal-$(date +%F)`)

Leave running for subsequent work: `llama-swap` (it *is* the endpoint). Nothing to tear down — the endpoint staying up is the deliverable. For the **stage** run, the win is the recon → execute → **gate-catch** arc landing in ~8–10 min; the box staying served afterward is the proof.

---

## Appendix A: See also

- [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — the method (recon → drift → gates) and the full gotcha→gate registry.
- [`examples/llama-swap-config.public.yaml`](./examples/llama-swap-config.public.yaml) — the canonical config this runbook deploys.
- [`RUNBOOK-v3-production-deployment.md`](./RUNBOOK-v3-production-deployment.md) — the proven end-to-end procedure this exemplar distils.
- [`RUNBOOK-llama-swap-setup.md`](./RUNBOOK-llama-swap-setup.md) — SM121 build flags, model downloads, the dynamic-VRAM launcher, the LiteLLM Phase-4 appendix (merge conflicts resolved).
- `TALK-ddd-southwest-got-a-spark-now-what.md` — the talk this runbook is the live demo for.

---

## Appendix B: Operator's personal variant (post-Graphiti)

The author's own box runs a **diff** against the public config, not a separate procedure. It keeps the proven workhorse, swaps the stock Coach for a fine-tune, and drops the Graphiti/RAG models (the author is moving off Graphiti). It is documented here rather than committed as a file because the fine-tune (`coach-ft-v3`) is not public.

**Diff against `examples/llama-swap-config.public.yaml`:**

- **`coach` → `coach-ft-v3`** — fine-tuned Gemma-4-26B-A4B MoE (Q4_K_M), `--reasoning off` (its trained non-thinking posture), `--ctx-size 98304`, q8_0 KV. Same ~26B-A4B footprint as the stock Coach → memory-neutral swap. The stock `coach` block may be kept as an on-demand fallback.
- **Drop `chat` and `embed`** — the personal box runs "pure headroom": only `workhorse` + `coach-ft-v3` are always-on (~51 GB resident, ~64 GB free), maximising swap-in room for on-demand `gpt-oss-120b`.
- **Preload set** = `[workhorse, coach-ft-v3]`; the `all` matrix.set = `wh & cfv3`.
- **gpt-oss-120b** stays on-demand (set `big: "go & cfv3"`) — the lead single-Spark Player for hard runs; pause the keepalive timer before a long 120b run so it doesn't revive the fleet on top of the 120b → OOM.

**Reproducibility note:** `coach-ft-v3` is a single ~16.8 GB GGUF on the box (`/opt/llama-swap/models/coach-ft-v3/`); back up the GGUF **and** its re-derivation set (the v3 LoRA adapter, the training dataset, and `RESULTS-coach-v3.md`) off-box so the personal config survives a rebuild.
