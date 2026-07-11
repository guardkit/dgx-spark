# RESULTS: granite-vision VLM seat — spark-fcf6

**Runbook:** `RUNBOOK-granite-vision-seat.md` (v1, 2026-07-11)
**Host:** `spark-fcf6` (GB10-class Spark, this repo's "Node B")
**Executed:** 2026-07-11 by Claude Code (rich@appmilla.com)
**Mode:** fresh (first seat on this box)
**Outcome:** ✅ **SEAT LIVE** — all 8 decision gates PASS.

---

## Decision Gate table

| # | Gate | Phase | Result |
|---|---|---|---|
| 0 | Recon recorded (drift or skipped) — advisory | 0 | ✅ model repo HTTP 200 · image tag still published — **no source drift** |
| 1 | GPU · disk · sudo · docker+nvidia runtime · repo · config · healthCheckTimeout ≥600 | 0.5 | ✅ PASS **after remediation** (docker + nvidia-runtime — see Deviations) |
| 2 | llama-swap green on :9000 | 1 | ✅ PASS-llamaswap-green |
| 3 | HF token valid on this box (CR-0 prerequisite) | 2 | ✅ PASS-token (user-pasted READ token, whoami-v2 verified) |
| 4 | Weights staged (~8GB in the hub cache) | 3 | ✅ PASS-weights (7.5G, full snapshot: 2× safetensors + config/tokenizer/preprocessor) |
| 5 | Pinned vLLM image present | 4 | ✅ PASS-image |
| 6 | Launch script installed executable | 5 | ✅ PASS-script (had to create `/opt/llama-swap/scripts/` — see Deviations) |
| 7 | Config backed up → stanza added → YAML valid → service active → model listed | 6 | ✅ PASS-yaml · PASS-service · PASS-listed |
| 8 | 1-token smoke answers (cold start within healthCheckTimeout) | 7 | ✅ PASS-smoke (`content:"ok"`, finish_reason stop) |

## Cold-start seconds

**175 s** (2m55s) — first-ever container load on this box. Longer than Node A's documented ~106 s (first-load compile/warmup on a fresh box), but well within the global `healthCheckTimeout: 600`. vLLM `0.22.0-7b38ff0e`.

## Matrix-set decision (deliberate — this box declares `matrix.sets`)

**Decision: added `gv` to the `all` set** (`all: "wh & co & ch & em & gv"`), plus matrix var `gv: granite-vision-4-1-4b`. gv stays **on-demand** (`ttl 1800`, NOT in `hooks.on_startup.preload`).

**Rationale:** this box's always-on fleet is ~65–71 GB (lighter than Node A's LPA family ~80 GB). Fleet + gv ~26 GB ≈ ~97 GB estimated, under the ~115 GB ceiling — so unlike Node A (which crossed the ceiling and needed an `lpa`-only set), this "lightly-loaded Node B" can carry gv in the default set, exactly as the runbook's matrix-set note anticipates. Co-residency in `all` also **avoids the keepalive-eviction thrash** Node A's rival-set design hit: gv now coexists with the fleet the keepalive probes, so neither evicts the other.

**Validated on-box (not just estimated):**
- Unified memory with fleet + gv both resident: **95 GB used / 121 GB total** — matches the ~97 GB estimate, ~26 GB headroom to the ceiling.
- `workhorse` (a fleet member) still answered after gv loaded → **no eviction**; co-residency confirmed behaviorally.

## Weight-staging path taken

**Path (b) — HF download**, not (a) rsync (no `~/.ssh/config`/nodeA route wired on this box). Ungated model, so no token needed for the pull. **Command drift:** the runbook's pinned `huggingface-cli download` is deprecated and now a no-op on this box — used `hf download ibm-granite/granite-vision-4.1-4b` (`hf` v1.23.0) instead. See `DRIFT-granite-vision-seat-2026-07-11.md`.

## PINS as-run

```
host                    spark-fcf6
model                   ibm-granite/granite-vision-4.1-4b  (Apache-2.0, ungated; 7.5G on disk)
vLLM image              vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404
image digest            sha256:05590eb0b9a1045a4d4b7348e3b71341c1e016062d7357e768ef28e6ac2de453
                        (local id fa2b47223ad3, ~31 GB)
launch script           /opt/llama-swap/scripts/vllm-granite-vision.sh  (from repo, unmodified)
serving params          GPU_UTIL 0.12 · MAX_LEN 8192 · MAX_SEQS 4  (script defaults)
llama-swap stanza       ttl 1800 · concurrencyLimit 4 · checkEndpoint /health ·
                        aliases granite-vision-4.1-4b, granite-vision
matrix                  var gv=granite-vision-4-1-4b ; set all="wh & co & ch & em & gv"
config file             /opt/llama-swap/config/config.yaml  (root:root 644; user unit llama-swap)
config backup           /opt/llama-swap/config/config.yaml.bak-20260711-pre-granite-vision
healthCheckTimeout      600 (global, unchanged)
cold-start observed     175 s
resident (fleet+gv)     95 GB / 121 GB unified
HF cache                ~/.cache/huggingface/hub/models--ibm-granite--granite-vision-4.1-4b
HF token file           ~/.cache/huggingface/token  (staged for showcard CR-0's gated FLUX.1-dev; chmod 600)
disk free /home         3422 GB
```

---

## Deviations from runbook (drift / remediation)

The runbook's Phase 0.5 pre-flight caught two **base-box setup gaps** and HALTed as designed. With the operator's approval ("fix both, continue") they were remediated in place; then two further execution-environment drifts were handled. None required editing runbook steps.

1. **docker group** — the run user (`richardwoollcott`, uid 1000) was not in the `docker` group, so the rootless `docker` the llama-swap user-unit needs would fail. This is the box's **first docker-based seat**, so docker access had never been exercised via llama-swap before.
   - Durable fix: `sudo usermod -aG docker richardwoollcott` (takes effect for the llama-swap user-manager on next reboot/re-login).
   - **Bridge for this run:** the long-running `user@1000` systemd manager (which parents both llama-swap and this agent session) predates the group change and can't be restarted without killing the session, so a socket ACL — `sudo setfacl -m u:1000:rw /var/run/docker.sock` — grants uid-1000 access immediately, independent of group. **This ACL is not persistent across a docker daemon restart**; after the next reboot the group membership supersedes it. If docker is restarted before then, re-apply the setfacl or ensure a fresh login so the group is in effect.

2. **nvidia container runtime** — `nvidia-container-toolkit` 1.19.1 was installed but the nvidia runtime was **not registered** in the Docker daemon (`Runtimes: … runc` only), so the script's `docker run --gpus all` would have had no GPU.
   - Fix: `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker` → `Runtimes: runc io.containerd.runc.v2 nvidia`. **Persistent** (written to `/etc/docker/daemon.json`).

3. **`/opt/llama-swap/scripts/` missing** (Phase 5) — this box's existing seats are all direct `llama-server --model …/models/…` GGUF invocations, so no scripts dir existed. Created it (uid-1000 owned, matching the sibling `config/`,`logs/`,`models/` dirs) before installing the launch script. Ran without `sudo` (parent `/opt/llama-swap` is uid-1000 owned) — the runbook's `sudo cp` still works, just needs the dir first.

4. **`huggingface-cli` deprecated** (Phase 3) — now a no-op that prints "use `hf` instead". Used `hf download` (`hf` 1.23.0). → `DRIFT-granite-vision-seat-2026-07-11.md`.

**Process note (self-inflicted, no box impact):** the background watcher I used to await the weight download `pgrep -f 'hf download …'`-matched *its own command line*, so it read "still downloading" for ~1h after the download had actually finished (17:51). Verified completion by the stable byte count + absent python process, not the pgrep. Future watchers must exclude their own PID / match the python process specifically.
