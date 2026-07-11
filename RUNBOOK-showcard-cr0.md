# Runbook: showcard CR-0 — ComfyUI render + VLM critique spike (Node B)

**Purpose:** retire the four unproven claims the showcard build stands on, before any repo code exists: (1) headless, parameterized ComfyUI rendering on GB10; (2) a committed SC_\*-slotted workflow graph; (3) `response_format json_schema` guided decoding on the **vision** endpoint; (4) VLM score discrimination (or a recorded clumping finding). Decision of record: `ai-transition/docs/decisions/DECISION-DF-023-*.md`; consumer: the showcard lane spec (`ai-transition/docs/lane-showcard-design-spec-2026-07-11.md` §6 — S-A binds this runbook's committed graph).
**Machine:** Node B (the second Spark). Node A is never touched — the PO fine-tune calendar owns it.
**Kind:** additive overlay (conventions §2.1) — layers on Node B's green llama-swap `:9000` end-state. Phase 1 is the machine-checked precondition gate.
**One-time box setup:** passwordless sudo for the operator user (README → Running a runbook) — gated in Phase 0.5.
**Execution-results link:** `RESULTS-showcard-cr0.md` (skeleton in Phase 8).
**Expected duration:** **~2h for the probe content** once ComfyUI stands (model downloads dominate wall-clock, ~34GB). **Park trigger: Appendix B's wording is authoritative.**

**Target architecture:**
```
 Node B (this runbook)                                   Node B (precondition, already green)
┌──────────────────────────────────────────────┐   ┌────────────────────────────────────┐
│ ComfyUI :8188 (playbook flux-comfyui image)  │   │ llama-swap :9000                   │
│   FLUX.1-dev (finals) · draft tier (Phase 3) │   │   granite-vision-4-1-4b            │
│        ▲ POST /prompt (SC_* slotted graph)   │   │        ▲ chat/completions +        │
│        │                                     │   │        │ response_format json_schema│
│  cr0_render.py ─▶ cr0_overlay.py ─▶ cr0_vlm_probe.py ─────┘                            │
│  (scripts/showcard-cr0/ — stdlib + Pillow)   │   └────────────────────────────────────┘
└──────────────────────────────────────────────┘
```

Execution modes:
```
  fresh    — run top to bottom (first spike)
  re-run   — idempotent; gates re-verify against the live box (downloads skip-if-present)
  update   — Phase 0 recon reports drift; re-run affected phases; record new baselines in RESULTS
```

---

## PINS (runbook v2, set 2026-07-11)

```
DGX_SPARK_REPO          ~/dgx-spark            (the clone of THIS repo on Node B; every phase
                                                cd's here explicitly — cwd never assumed to persist)
HF_TOKEN source         ~/.cache/huggingface/token  (written by `huggingface-cli login`, done
                                                2026-07-10; every phase that needs it runs
                                                `export HF_TOKEN=$(cat ~/.cache/huggingface/token)`
                                                — never hunt the filesystem for secrets)
dgx-spark-playbooks     e450849a6ae5387a80a0d3abc2c86506ee551283  (2026-07-10; nvidia/flux-finetuning + nvidia/comfy-ui)
ComfyUI                 whatever the pinned playbook's Dockerfile.inference builds — record the
                        actual version from /system_stats in RESULTS (float-with-baseline: the
                        playbook owns this pin; upstream latest release was v0.27.0 on 2026-06-30)
FLUX.1-dev              black-forest-labs/FLUX.1-dev (HF-GATED; anchor file flux1-dev.safetensors,
                        gate floor -size +20G)
draft tier              black-forest-labs/FLUX.2-klein-9B (public repo, verified reachable 2026-07-11)
                        FALLBACK on ANY klein failure (staging OR render): flux1-dev-fast =
                        FLUX.1-dev + `--steps 8` on the same slotted graph (SC_STEPS slot;
                        pre-authorized by the lane spec §4.1)
DRAFT_FAST_STEPS        8
VLM seat                granite-vision-4-1-4b on llama-swap :9000/v1 (Node B; standing since the LPA work)
Pillow                  11.3.0 (pip, venv-local — overlay + probe variants only)
ports                   ComfyUI :8188 · llama-swap :9000
DISK_FLOOR_GB           60   (FLUX.1-dev fp8 + text encoders + VAE ≈ 34GB; klein adds ~18GB)
render timeout caps     draft 300s · final 900s   (matches lane spec §4.1 render.timeout_s)
probe decoding          temperature=0.0 · seed=42 · max_tokens=500  (max-tokens ceiling is load-bearing)
spread floor            0.15 on headline_legibility, good vs degraded variants
```

---

## Phase 0: Recon (read-only, advisory — degrade gracefully if offline)

```bash
PIN=e450849a6ae5387a80a0d3abc2c86506ee551283
LATEST=$(curl -s https://api.github.com/repos/NVIDIA/dgx-spark-playbooks/commits/main | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('sha',''))
except Exception: print('')")
if [ -z "$LATEST" ]; then echo "recon: skipped (source unreachable)"; \
elif [ "$PIN" = "$LATEST" ]; then echo "playbooks: pinned == HEAD"; \
else echo "DRIFT: playbooks pinned ${PIN:0:8}, HEAD ${LATEST:0:8}"; fi
export HF_TOKEN=$(cat ~/.cache/huggingface/token)
curl -s -o /dev/null -w "FLUX.2-klein-9B reachable: HTTP %{http_code}\n" https://huggingface.co/api/models/black-forest-labs/FLUX.2-klein-9B
curl -s -o /dev/null -w "FLUX.1-dev gated access: HTTP %{http_code}\n" -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/models/black-forest-labs/FLUX.1-dev
```

Emit the drift report (conventions §5) into `DRIFT-showcard-cr0-<date>.md` if anything drifts; record `recon: skipped` in RESULTS if offline. Do NOT edit steps mid-run.

## Phase 0.5: Pre-flight (checks only, no side effects)

```bash
nvidia-smi >/dev/null && echo PASS-gpu || echo FAIL-gpu
[ $(df -BG --output=avail /home | tail -1 | tr -dc 0-9) -ge 60 ] && echo PASS-disk || echo FAIL-disk
sudo -n true 2>/dev/null && echo PASS-sudo || echo "FAIL-sudo (one-time box setup: passwordless sudo — README)"
[ -s ~/.cache/huggingface/token ] && echo PASS-token-file || echo "FAIL-token-file (huggingface-cli login was done 2026-07-10 — if the file is absent on THIS box, run huggingface-cli login once; the licence acceptance already exists)"
export HF_TOKEN=$(cat ~/.cache/huggingface/token)
curl -s -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami-v2 | grep -q '"name"' && echo PASS-token-valid || echo FAIL-token-valid
[ -x ~/dgx-spark/scripts/showcard-cr0/cr0_render.py ] && echo PASS-repo || echo "FAIL-repo (clone this repo to ~/dgx-spark on Node B first)"
{ [ -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ] || [ -f /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf ]; } && echo PASS-fonts || echo "FAIL-fonts (apt install fonts-dejavu-core)"
! ss -tlnp 2>/dev/null | grep -q ':8188 ' && echo PASS-port-free || echo "WARN: :8188 already bound (re-run mode? check it's ComfyUI)"
docker info >/dev/null 2>&1 && echo PASS-docker || echo "WARN: no docker — use the native comfy-ui playbook README (fallback path, Phase 2b)"
```

**HALT on any FAIL.**

## Phase 0.6: Workspace (first side effects — a disposable venv)

```bash
{ python3 -m venv ~/cr0-venv && ~/cr0-venv/bin/pip install -q pillow==11.3.0 \
  && ~/cr0-venv/bin/python -c "import PIL; print('PASS-pillow', PIL.__version__)"; } || echo "FAIL-pillow (python3-venv installed?)"
```

**HALT on FAIL.**

## Phase 1: Precondition gate (the overlay law — assert the base, never re-run it)

```bash
curl -s http://127.0.0.1:9000/v1/models | grep -q 'granite-vision-4-1-4b' && echo PASS-vlm-listed || echo FAIL-vlm-listed
curl -s http://127.0.0.1:9000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"granite-vision-4-1-4b","max_tokens":8,"messages":[{"role":"user","content":"say ok"}]}' \
  | grep -q '"content"' && echo PASS-vlm-answers || echo FAIL-vlm-answers
```

**HALT on FAIL** — the base llama-swap runbook owns the fix; this file never edits Node B's serving state.

## Phase 2: ComfyUI up (dockerized playbook image — the vendored-container pattern)

```bash
git clone https://github.com/NVIDIA/dgx-spark-playbooks ~/dgx-spark-playbooks 2>/dev/null || true
git -C ~/dgx-spark-playbooks fetch --all --tags --quiet   # re-run mode: a stale clone must still reach the pin
git -C ~/dgx-spark-playbooks checkout e450849a6ae5387a80a0d3abc2c86506ee551283
cd ~/dgx-spark-playbooks/nvidia/flux-finetuning/assets
# Read README.md for the current build+launch invocation (Dockerfile.inference + launch_comfyui.sh).
# Build the inference image and launch ComfyUI on :8188 exactly as the playbook says — no improvisation;
# if the playbook's steps fail, that is Appendix B territory, not a rewrite-the-steps moment.
# LAUNCH DETACHED: docker run -d (or for fallback 2b: systemd-run --user / nohup + disown) — a foreground
# server blocks the agent's shell, and a process in the editor's cgroup is reaped when the session ends
# (registry row "Process under VS Code cgroup"), contradicting Phase 8's leave-standing.
```

Gate (GPU-bound check — catches the silent CPU fallback, registry row "Generic ARM64 binary"):

```bash
curl -s http://127.0.0.1:8188/system_stats | python3 -c "
import sys,json; s=json.load(sys.stdin)
devs=[d.get('type','') for d in s.get('devices',[])]
print('PASS-comfyui-gpu' if any('cuda' in d.lower() for d in devs) else 'FAIL-comfyui-gpu', devs)
print('comfyui_version:', s.get('system',{}).get('comfyui_version','unknown'))  # record in RESULTS"
```

Native-path (2b) extra gate: `/proc/$(pgrep -f 'ComfyUI|main.py --listen' | head -1)/cgroup` shows a systemd/user unit, not an editor scope.

**Trap (playbook-documented):** UMA buffer-cache pressure between heavy runs — `sync; echo 3 | sudo tee /proc/sys/vm/drop_caches` between Phase 4 renders if the box stalls (sudo is passwordless per Phase 0.5's gate).

## Phase 3: Model staging (skip-if-present; HF bearer downloads with resume)

```bash
export HF_TOKEN=$(cat ~/.cache/huggingface/token)
```

Use the playbook's `download.sh` pattern (already `curl -C - -H "Authorization: Bearer $HF_TOKEN"`) / its `models/` layout for **FLUX.1-dev**. Then probe the **draft tier**:

```bash
curl -s -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/models/black-forest-labs/FLUX.2-klein-9B \
  | python3 -c "import sys,json; m=json.load(sys.stdin); print('klein files:', [f['rfilename'] for f in m.get('siblings',[])][:10])"
```

Gate (mechanical):

```bash
find ~/dgx-spark-playbooks/nvidia/flux-finetuning/assets/models -iname 'flux1-dev*.safetensors' -size +20G | grep -q . && echo PASS-fluxdev-staged || echo FAIL-fluxdev-staged
# klein: every file the API listed above exists non-empty under models/ → PASS-klein-staged,
# or record "klein unstaged: <reason>" in RESULTS and take the PINS fallback — NOT a park condition.
```

Note: "does the pinned ComfyUI have node support for klein" is **not evaluable here** — Phase 4's render is that test; any klein FAIL there routes to the same fallback.

## Phase 4: Export + slot the graph, then headless render per ladder model

1. **Export API format (mandatory, one UI touch — verified: the playbook's `base_flux.json` ships in UI-canvas format, which the API cannot execute).** Load `assets/workflows/base_flux.json` in the ComfyUI browser UI once, enable dev mode, **Save (API format)** as `~/base_flux.api.json`. This is the only permitted UI interaction; the renders themselves are never clicked.
2. **Slot it** (the format gate now verifies the export was done right):

```bash
cd ~/dgx-spark/scripts/showcard-cr0
python3 cr0_slot_graph.py ~/base_flux.api.json -o slotted_flux.api.json
```

Ratify the printed slot map (one wrong slot ⇒ the render gate below catches it; heed any `WARN` about ModelSamplingFlux/SC_STEPS). **Commit `slotted_flux.api.json` to this directory** — it seeds every showcard v0 template (lane spec §4.2).

3. **Final-tier render, then the UMA flush, then the draft tier:**

```bash
cd ~/dgx-spark/scripts/showcard-cr0
python3 cr0_render.py slotted_flux.api.json --prompt "dramatic teal-and-orange tech workshop background, dgx spark on desk, shallow depth of field, no text" --seed 42 -o results/final-fluxdev.png --timeout 900
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
# Draft tier — klein if Phase 3 staged it:
python3 cr0_render.py slotted_flux.api.json --prompt "dramatic teal-and-orange tech workshop background, dgx spark on desk, shallow depth of field, no text" --seed 42 --model <klein-file-per-Phase-3> -o results/draft-tier.png --timeout 300
# FALLBACK on ANY draft-tier FAIL (staging, graph/loader rejection, or timeout) — flux1-dev-fast:
# python3 cr0_render.py slotted_flux.api.json --prompt "..." --seed 42 --steps 8 -o results/draft-tier.png --timeout 300
```

Gate: **both** renders print `PASS … 1280x720 in <N>s` (receipts land beside the PNGs; seconds → RESULTS; which draft path ran → RESULTS).

## Phase 5: Deterministic typography offline (+ probe variants)

```bash
cd ~/dgx-spark/scripts/showcard-cr0
~/cr0-venv/bin/python cr0_overlay.py results/final-fluxdev.png -o results/composite.png --variants
```

Gate: `PASS` with three files written + the fitted px + headline bbox metadata printed (`height_at_168w_px` — the showcard Tier-1 arithmetic, previewed here; the script gates canvas containment and badge safe-area itself).

## Phase 6: The two VLM probes (the load-bearing unknowns)

```bash
cd ~/dgx-spark/scripts/showcard-cr0
python3 cr0_vlm_probe.py results/composite.png results/composite-lowcontrast.png results/composite-tinytext.png \
  --endpoint http://127.0.0.1:9000/v1 --model granite-vision-4-1-4b -o results/probe.json
```

- **Probe 1 gate (guided decoding on vision):** `PASS (probe 1)` via `json_schema` — OR the script fails, you re-run with `--no-schema`, that passes, and RESULTS records **`evaluator wire = prompt-json + retry`** (a design decision the lane spec §9 risk 3 pre-authorizes; showcard S-B2 consumes it). Either recorded outcome passes the phase; an unrecorded one does not.
- **Probe 2 gate (discrimination):** the verdict line — `DISCRIMINATES` or `CLUMPED` — is **recorded either way**. CLUMPED is a finding, not a failure: it means Tier-1 + the human pick carry showcard sessions, filed honestly in RESULTS.

## Phase 7: Decision Gate

| # | Gate | Phase | Result |
|---|---|---|---|
| 0 | Drift report emitted, or `recon: skipped` recorded (advisory) | 0 | |
| 1 | GPU · ≥60GB disk · passwordless sudo · token file valid · repo clone present · fonts · Pillow venv | 0.5–0.6 | |
| 2 | granite-vision listed + answering on :9000 | 1 | |
| 3 | ComfyUI `/system_stats` reports a CUDA device (no CPU fallback); detached launch | 2 | |
| 4 | flux1-dev*.safetensors staged >20G; klein staged **or** fallback recorded | 3 | |
| 5 | API-format export done; slot map ratified; `slotted_flux.api.json` committed | 4 | |
| 6 | Headless 1280×720 render PASS on FLUX.1-dev, seconds recorded | 4 | |
| 7 | Headless render PASS on the draft tier (klein **or** `--steps 8` fallback), path + seconds recorded | 4 | |
| 8 | Composite + bbox metadata + two degraded variants written | 5 | |
| 9 | Probe 1: json_schema parse PASS **or** fallback wire demonstrated + recorded | 6 | |
| 10 | Probe 2: discrimination verdict recorded (either value) | 6 | |

All rows filled ⇒ CR-0 **green**: showcard S-A is unblocked (DF-023 §2.10). Park per Appendix B's trigger, which is authoritative.

## Phase 8: Cleanup, RESULTS, hand-off

- Leave ComfyUI standing on :8188 (it is showcard's render box; a systemd unit is S-C's business, not tonight's). It was launched detached (Phase 2), so it survives the session.
- Write `RESULTS-showcard-cr0.md` from this skeleton:

```markdown
# RESULTS — showcard CR-0, run <date>
Status: GREEN | PARKED (Appendix B)
PINS as-run: playbooks <sha> · ComfyUI <version from gate 3> · Pillow <ver>
Decision Gate: <the Phase 7 table, Result column filled>
Renders: final-tier <N>s · draft-tier <N>s via <klein | flux1-dev-fast --steps 8>
Slot map: <the ratified cr0_slot_graph.py output>
Probes: <results/probe.json verbatim>
THE TWO DECISIONS SHOWCARD CONSUMES:
  evaluator wire   = json_schema | prompt-json+retry
  ladder           = klein | flux1-dev-fast
Drift: <report | none | recon skipped>
```

- Commit: `slotted_flux.api.json`, `RESULTS-showcard-cr0.md`, `results/*.receipt.json`, `results/probe.json`, `results/composite.bbox.json`, any `DRIFT-*` (PNGs optional — small ones only).
- Update the two dated pointers: lane spec §6 CR-0 row (ai-transition) and plan-of-record Track H cell — CR-0 ✅ with the two decisions inline.

## Appendix A: Rollback

`docker stop` the ComfyUI container (or stop the systemd-run unit); staged model weights may stay on disk (re-runs skip-if-present) or be deleted to reclaim ~35–50GB; the venv is disposable; nothing in this runbook touched llama-swap, Node A, or any fleet config.

## Appendix B: Park note (the kill criterion — this wording is authoritative)

**Park trigger: gates 3 and 6 not both green by the end of evening two, OR any Decision-Gate row proven permanently unfillable at any point.** On trigger: STOP. File `RESULTS-showcard-cr0.md` with status **PARKED**, the failing gate, the exact error evidence, and the drift report. Point the lane spec §6 CR-0 row at it. Parking here costs two evenings; discovering the same failure inside the orchestrated build would cost five sessions — that arithmetic is why this runbook gates the build.
