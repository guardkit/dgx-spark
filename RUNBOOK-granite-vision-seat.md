# Runbook: granite-vision VLM seat — vLLM container under llama-swap

**Purpose:** add the `granite-vision-4-1-4b` vision seat to a Spark whose llama-swap `:9000` is already green — repeatably, on any box in the fleet. Written for Node B (the showcard CR-0 prerequisite: `RUNBOOK-showcard-cr0.md` Phase 1 gates on this seat); it is the same procedure that built the seat on Node A on 2026-05-30 (this box's `config.yaml.bak-2026-05-30-pre-granite-vision` is that install's receipt).
**Machine:** any GB10-class Spark with a green llama-swap (base: `RUNBOOK-llama-swap-setup.md` / `RUNBOOK-single-spark-bring-up.md`).
**Kind:** additive overlay (conventions §2.1) — Phase 1 asserts the base; this runbook touches ONLY the seat's delta (weights, image, script, one config stanza).
**One-time box setup:** passwordless sudo (README → Running a runbook).
**Execution-results link:** `RESULTS-granite-vision-seat-<host>.md`.
**Expected duration:** ~20 min + the weight transfer (~8GB: minutes over the CX-7/LAN rsync path, longer via HF download).

**Provenance (the "where did this come from" record):**
- **Model:** `ibm-granite/granite-vision-4.1-4b` — IBM's granite-vision HF collection, Apache-2.0, **NOT licence-gated** (no HF token needed to pull it). Selected 2026-05 in the LPA POC as the newest/largest image-text-to-text model of the collection (`lpa-platform-poc/docs/history/lpa-extraction-e2e-smoke-3.md`); first pull ~8GB (`…smoke-4.md`). Architecture `Granite4VisionForConditionalGeneration`.
- **Serving engine:** vLLM in a docker container (NOT llama.cpp/GGUF) — llama-swap spawns/stops the container per request via the launch script; llama-swap stays the one memory manager (findings §9.3: standalone vLLM's memory profiling clashed with the unified-memory pool).
- **Launch script:** `scripts/vllm-granite-vision.sh` (vendored in this repo 2026-07-11 from Node A's `/opt/llama-swap/scripts/` — the full WHY block lives in its header).
- **Known limitation (recorded honestly):** on Node A, 4.1-4b showed a 1-token EOS-collapse on one specific LPA form page under greedy decoding, un-tuneable across 7 smokes — which is why `granite-vision-3-3-2b` (LlavaNext family) exists as a registered fallback there (`vllm-granite-vision-3-3-2b.sh`). Document-extraction-specific; whether it matters for thumbnail scoring is exactly what CR-0's probes measure.

Execution modes:
```
  fresh    — run top to bottom (first seat on this box)
  re-run   — idempotent; pulls/copies skip-if-present, gates re-verify
  update   — Phase 0 recon reports drift; re-run affected phases; new baselines in RESULTS
```

---

## PINS (runbook v1, set 2026-07-11)

```
model                   ibm-granite/granite-vision-4.1-4b   (HF, Apache-2.0, ungated; ~8GB)
vLLM image              vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404
                        WHY: native Granite4VisionForConditionalGeneration needs vLLM ≥ v0.21 —
                        the older cu130-nightly (0.18.1rc1) falls back to TransformersMultiModal
                        and crashes on load ("no module or parameter named 'image_newline'").
                        Verified on Blackwell sm_121 2026-05-30; ~106s cold start + bind.
launch script           $DGX_SPARK_REPO/scripts/vllm-granite-vision.sh → /opt/llama-swap/scripts/
serving params          GPU_UTIL 0.12 (~15GB target; ~26GB observed resident on Node A first-load
                        — budget against the 115GB ceiling row) · MAX_LEN 8192 · MAX_SEQS 4
llama-swap stanza       ttl 1800 · concurrencyLimit 4 · checkEndpoint /health ·
                        aliases granite-vision-4.1-4b, granite-vision
config file             /opt/llama-swap/config/config.yaml   (user unit `llama-swap`;
                        backup convention: config.yaml.bak-<date>-pre-granite-vision BEFORE edit)
healthCheckTimeout      ≥ 600 globally (covers the ~106s container cold start — registry row
                        "Cold-load 504")
HF cache                ~/.cache/huggingface   (weights land in hub/models--ibm-granite--granite-vision-4.1-4b)
HF token file           ~/.cache/huggingface/token  (NOT needed for this model; staged here anyway
                        because showcard CR-0's FLUX.1-dev pull IS gated — Phase 2)
DGX_SPARK_REPO          ~/Projects/appmilla_github/dgx-spark   (fleet folder convention)
DISK_FLOOR_GB           15
```

---

## Phase 0: Recon (read-only, advisory — degrade gracefully if offline)

```bash
curl -s -o /dev/null -w "model repo reachable: HTTP %{http_code}\n" https://huggingface.co/api/models/ibm-granite/granite-vision-4.1-4b || echo "recon: skipped (source unreachable)"
docker manifest inspect vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404 >/dev/null 2>&1 && echo "image tag: still published" || echo "recon: image tag not confirmable (offline or auth) — proceed on the local/pinned copy"
```

Drift → `DRIFT-granite-vision-seat-<date>.md`. Never edit steps mid-run.

## Phase 0.5: Pre-flight (checks only)

```bash
nvidia-smi >/dev/null && echo PASS-gpu || echo FAIL-gpu
[ $(df -BG --output=avail /home | tail -1 | tr -dc 0-9) -ge 15 ] && echo PASS-disk || echo FAIL-disk
sudo -n true 2>/dev/null && echo PASS-sudo || echo FAIL-sudo
docker info >/dev/null 2>&1 && echo PASS-docker || echo FAIL-docker
docker info 2>/dev/null | grep -qi 'nvidia' && echo PASS-nvidia-runtime || echo "FAIL-nvidia-runtime (nvidia-container-toolkit)"
[ -x ~/Projects/appmilla_github/dgx-spark/scripts/vllm-granite-vision.sh ] && echo PASS-repo || echo "FAIL-repo (git pull the fleet clone)"
[ -f /opt/llama-swap/config/config.yaml ] && echo PASS-config || echo FAIL-config
awk '/healthCheckTimeout/{print ($2>=600)?"PASS-healthtimeout":"FAIL-healthtimeout (must be >=600 for the ~106s cold start)"}' /opt/llama-swap/config/config.yaml
```

**HALT on any FAIL.**

## Phase 1: Precondition gate (the overlay law)

```bash
curl -s http://127.0.0.1:9000/v1/models | grep -q '"id"' && echo PASS-llamaswap-green || echo FAIL-llamaswap-green
```

**HALT on FAIL** — the base bring-up runbook owns the fix.

## Phase 2: HF token onto this box (prerequisite for what FOLLOWS this seat)

`granite-vision-4.1-4b` itself is **ungated — this phase is not needed to serve it**. It is staged here because the box's next runbook (showcard CR-0) pulls the **licence-gated** FLUX.1-dev and gates on `~/.cache/huggingface/token`. Two ways, pick one:

```bash
# (a) login on this box — paste a READ-scope token from huggingface.co/settings/tokens
pip install -q -U "huggingface_hub[cli]" 2>/dev/null || python3 -m venv ~/gvseat-venv && ~/gvseat-venv/bin/pip install -q "huggingface_hub[cli]"
~/gvseat-venv/bin/huggingface-cli login     # writes ~/.cache/huggingface/token

# (b) copy from a box that already has it (the licence acceptance is account-level):
#   ssh <this-box> 'mkdir -p ~/.cache/huggingface && chmod 700 ~/.cache/huggingface'
#   scp ~/.cache/huggingface/token <this-box>:~/.cache/huggingface/token
#   ssh <this-box> 'chmod 600 ~/.cache/huggingface/token'
```

Gate:

```bash
curl -s -H "Authorization: Bearer $(cat ~/.cache/huggingface/token)" https://huggingface.co/api/whoami-v2 | grep -q '"name"' && echo PASS-token || echo FAIL-token
```

## Phase 3: Stage the weights (skip-if-present; pick ONE path)

```bash
# (a) rsync from a box that already has them (Node A; fastest, tokenless):
rsync -a --info=progress2 nodeA:~/.cache/huggingface/hub/models--ibm-granite--granite-vision-4.1-4b ~/.cache/huggingface/hub/
# (b) HF download (ungated — works with or without the token):
~/gvseat-venv/bin/huggingface-cli download ibm-granite/granite-vision-4.1-4b
```

Gate:

```bash
[ -d ~/.cache/huggingface/hub/models--ibm-granite--granite-vision-4.1-4b ] && du -sh ~/.cache/huggingface/hub/models--ibm-granite--granite-vision-4.1-4b && echo PASS-weights || echo FAIL-weights
```

(Pre-staged weights mean the serve path never needs network or a token — the launch script mounts this cache read-through.)

## Phase 4: Pull the pinned vLLM image

```bash
docker pull vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404
docker image inspect vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404 >/dev/null && echo PASS-image || echo FAIL-image
```

## Phase 5: Install the launch script

```bash
sudo cp ~/Projects/appmilla_github/dgx-spark/scripts/vllm-granite-vision.sh /opt/llama-swap/scripts/vllm-granite-vision.sh
sudo chmod +x /opt/llama-swap/scripts/vllm-granite-vision.sh
[ -x /opt/llama-swap/scripts/vllm-granite-vision.sh ] && echo PASS-script || echo FAIL-script
```

## Phase 6: Config stanza (backup first — the house convention)

```bash
sudo cp /opt/llama-swap/config/config.yaml /opt/llama-swap/config/config.yaml.bak-$(date +%Y%m%d)-pre-granite-vision
```

Insert into the `models:` block (verbatim — this is the stanza serving on Node A):

```yaml
  "granite-vision-4-1-4b":
    cmd: /opt/llama-swap/scripts/vllm-granite-vision.sh ${PORT}
    cmdStop: docker stop vllm-granite-vision
    checkEndpoint: /health
    ttl: 1800                # on-demand: auto-unload after 30 min idle
    concurrencyLimit: 4
    aliases:
      - "granite-vision-4.1-4b"
      - "granite-vision"
```

**Matrix-set note:** if this box's config declares `matrix.sets`, add the seat to a set **deliberately** (registry row: no set declared → cross-model load-thrash). On Node A the seat is `lpa`-set-only because ~26GB resident crossed the 115GB ceiling next to the full family; a lightly-loaded Node B can carry it in the default set. Decide against THIS box's residents, record the choice in RESULTS.

```bash
python3 -c "import yaml; yaml.safe_load(open('/opt/llama-swap/config/config.yaml')); print('PASS-yaml')" || echo FAIL-yaml
systemctl --user restart llama-swap && sleep 3 && systemctl --user is-active llama-swap && echo PASS-service || echo FAIL-service
curl -s http://127.0.0.1:9000/v1/models | grep -q 'granite-vision-4-1-4b' && echo PASS-listed || echo FAIL-listed
```

## Phase 7: Live smoke (spins the container — ~106s cold start is normal)

```bash
time curl -s http://127.0.0.1:9000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"granite-vision-4-1-4b","max_tokens":8,"messages":[{"role":"user","content":"say ok"}]}' \
  | grep -q '"content"' && echo PASS-smoke || echo FAIL-smoke
```

The **vision** probe (image in, `response_format json_schema` out) is deliberately NOT here — it is showcard CR-0 Phase 6's job, with receipts.

## Phase 8: Decision Gate + RESULTS

| # | Gate | Phase | Result |
|---|---|---|---|
| 0 | Recon recorded (drift or skipped) — advisory | 0 | |
| 1 | GPU · disk · sudo · docker+nvidia runtime · repo · config · healthCheckTimeout ≥600 | 0.5 | |
| 2 | llama-swap green on :9000 | 1 | |
| 3 | HF token valid on this box (CR-0 prerequisite) | 2 | |
| 4 | Weights staged (~8GB in the hub cache) | 3 | |
| 5 | Pinned vLLM image present | 4 | |
| 6 | Launch script installed executable | 5 | |
| 7 | Config backed up → stanza added → YAML valid → service active → model listed | 6 | |
| 8 | 1-token smoke answers (cold start within healthCheckTimeout) | 7 | |

Write `RESULTS-granite-vision-seat-<host>.md`: gate table + cold-start seconds + matrix-set decision + weight-staging path taken ((a) or (b)) + PINS as-run. Commit it with any DRIFT file.

## Appendix: Rollback

Restore the Phase 6 backup over `config.yaml`, `systemctl --user restart llama-swap` — the seat is gone and the base is exactly as the backup captured it. `docker rmi` the image and delete the hub cache dir only if the ~19GB matters; re-runs skip-if-present either way.
