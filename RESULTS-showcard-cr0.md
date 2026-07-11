# RESULTS — showcard CR-0, run 2026-07-11 (Node B = spark-fcf6)

Status: **GREEN** — showcard S-A is unblocked (DF-023 §2.10). Not parked.

PINS as-run: playbooks `e450849a6ae5387a80a0d3abc2c86506ee551283` · ComfyUI **0.3.62**
(from the pinned playbook's Dockerfile.inference — comfyanonymous checkout
`4ffea0e864275301329ddb5ecc3fbc7211d7a802`) · Pillow **11.3.0** · vLLM seat image
`vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404`.

## Decision Gate (Phase 7)

| # | Gate | Phase | Result |
|---|---|---|---|
| 0 | Drift report emitted, or `recon: skipped` recorded (advisory) | 0 | **PASS** — no drift: playbooks pinned == HEAD; FLUX.2-klein-9B HTTP 200; FLUX.1-dev gated HTTP 200. No DRIFT file needed. |
| 1 | GPU · ≥60GB disk · passwordless sudo · token file valid · repo clone present · fonts · Pillow venv | 0.5–0.6 | **PASS** — all: GPU ✓, disk 3422G, sudo -n ✓, token valid, repo ✓, DejaVu fonts ✓, Pillow 11.3.0 ✓, :8188 free, docker ✓. |
| 2 | granite-vision listed + answering on :9000 | 1 | **PASS** — listed + `"content"` returned. |
| 3 | ComfyUI `/system_stats` reports a CUDA device (no CPU fallback); detached launch | 2 | **PASS** — device `cuda:0 NVIDIA GB10 : native`; container `cr0-comfyui` run with `docker run -d` (detached, survives session). |
| 4 | flux1-dev*.safetensors staged >20G; klein staged **or** fallback recorded | 3 | **PASS** — flux1-dev.safetensors 23.8GB (PASS-fluxdev-staged). **klein unstaged** (reason below) → pre-authorized fallback recorded. |
| 5 | API-format export done; slot map ratified; `slotted_flux.api.json` committed | 4 | **PASS** — export done headlessly (see note); slot map ratified; file committed. |
| 6 | Headless 1280×720 render PASS on FLUX.1-dev, seconds recorded | 4 | **PASS** — `final-fluxdev.png 1280x720 in 360.9s` (50 steps). |
| 7 | Headless render PASS on the draft tier (klein **or** `--steps 8` fallback), path + seconds recorded | 4 | **PASS** — `draft-tier.png 1280x720 in 24.1s` via **flux1-dev-fast `--steps 8`**. |
| 8 | Composite + bbox metadata + two degraded variants written | 5 | **PASS** — composite.png + -lowcontrast + -tinytext; fitted 85px; headline height at 168px width = 22.4px. |
| 9 | Probe 1: json_schema parse PASS **or** fallback wire demonstrated + recorded | 6 | **PASS** — all 3 responses parsed via **`json_schema`** on a healthy seat (guided decoding on the vision endpoint proven). See memory-contention note. |
| 10 | Probe 2: discrimination verdict recorded (either value) | 6 | **PASS (recorded)** — **CLUMPED**: good=0.80, degraded=[0.80, 0.80], required gap ≥0.15 not met. |

All rows filled ⇒ CR-0 **GREEN**.

## THE TWO DECISIONS SHOWCARD CONSUMES
```
evaluator wire   = json_schema          (guided decoding on the granite-vision seat PARSED cleanly)
ladder           = flux1-dev-fast       (klein = FLUX.2, unsupported by the pinned ComfyUI 0.3.62)
```

## Renders
- final-tier: **360.9s** (FLUX.1-dev, 50 steps, seed 42, 1280×720) — sha256 d625a1c0…5f5440
- draft-tier: **24.1s** via **flux1-dev-fast `--steps 8`** (seed 42, 1280×720) — sha256 e6b39897…6df034
- ~15× speedup draft→final on the same slotted graph; a real, usable draft/final ladder.

## Slot map (ratified `cr0_slot_graph.py` output)
```
slot         node   class_type             inject-field
SC_CKPT      91     CheckpointLoaderSimple
SC_PROMPT    6      CLIPTextEncode         text
SC_SEED      25     RandomNoise            noise_seed
SC_SIZE      90     EmptyLatentImage       width/height
SC_SIZE_MSF  61     ModelSamplingFlux      width/height   (tracks SC_SIZE — flux shift schedule kept in sync)
SC_STEPS     17     BasicScheduler         steps          (enables the --steps 8 fallback)
```
No WARN emitted (ModelSamplingFlux slotted; SC_STEPS present).

## Probes (`results/probe.json` verbatim)
```json
{
  "wire": "json_schema",
  "model": "granite-vision-4-1-4b",
  "seed": 42,
  "max_tokens": 500,
  "scores": {
    "composite.png":            {"headline_legibility": 0.8, "focal_clarity": 0.7, "contrast": 0.9},
    "composite-lowcontrast.png":{"headline_legibility": 0.8, "focal_clarity": 0.7, "contrast": 0.9},
    "composite-tinytext.png":   {"headline_legibility": 0.8, "focal_clarity": 0.7, "contrast": 0.9}
  },
  "discrimination": "CLUMPED"
}
```

## Findings & notes (recorded honestly)

**1. klein / draft-ladder decision — `flux1-dev-fast` (not a park condition).**
FLUX.2-klein-9B is a **FLUX.2** model (diffusers layout: `transformer/`, `text_encoder/`,
`vae/` + a single `flux-2-klein-9b.safetensors`). The pinned ComfyUI 0.3.62 exposes
**zero** FLUX.2 node classes (grepped all 477 classes in `/object_info` for `flux2` →
empty; the loader set is the classic flux1-era set), and the base graph's
`CheckpointLoaderSimple`/`UNETLoader` are flux1-only. klein cannot load here. Rather
than download ~18GB to prove a known-negative, support was tested empirically and
cheaply via `/object_info`. Draft tier therefore uses the lane-spec-§4.1-pre-authorized
`flux1-dev --steps 8` fallback on the same SC_STEPS-slotted graph — which also
exercises the identical loader/graph the mandatory final render already proved.

**2. Probe 1 (json_schema) — PASSED, after a memory-contention recovery worth recording.**
The first probe attempt FAILED with `llama-swap: upstream command exited prematurely`,
and the seat's vLLM container was gone. Root cause was **UMA-ceiling contention, not a
json_schema incompatibility**: this shared box had ComfyUI's python process holding
**22.4GB** of resident flux weights (ComfyUI's `/free` unloads from its manager but the
CUDA caching allocator retains RSS) *on top of* the box's other resident llama-swap GGUF
seats (`chat`=gpt-oss-20b, `coach`=gemma-4-26B, `-ngl 999 --no-mmap`). MemAvailable had
fallen to ~9GB, so llama-swap's on-demand cold-start of the granite seat (~26GB, GPU_UTIL
0.12) OOM'd (`dmesg`: `NVRM ... Out of memory [NV_ERR_NO_MEMORY]`). Recovery (no base
serving-state edits): restarted `cr0-comfyui` to release the 22.4GB flux hold (server
left standing per Phase 8), dropped caches → MemAvailable 48.5GB; llama-swap then
cold-started the seat cleanly (~174s, within the ≥600s healthCheckTimeout) and answered.
Re-run of the probe then **PASSED via json_schema** on all 3 images. Phase 1 originally
passed for the same reason it failed later — at Phase 1 ComfyUI was not yet loaded.

  → **Operational constraint for showcard S-C to carry:** the ComfyUI+flux render box and
  the granite VLM seat **cannot both hold model weights while working** on this 128GB UMA
  box alongside its other resident GGUF seats. The evaluator must run when flux is
  unloaded (or unload flux before scoring). "Both listening" is fine; "both resident +
  busy" exceeds the ceiling. The `evaluator wire = json_schema` decision stands — it was
  never a wire problem.

**3. Probe 2 (discrimination) — CLUMPED (a finding, not a failure).**
granite-vision-4-1-4b scored the good composite, the low-contrast variant, and the
tiny-text variant **identically** (headline_legibility 0.80 for all three; focal 0.70,
contrast 0.90 across the board) — despite the good composite visibly carrying a large,
stroked, high-contrast headline and the variants being deliberately degraded. The VLM
does not discriminate headline legibility at this scale. Per the lane spec, **Tier-1
deterministic gates (the bbox arithmetic — headline height 22.4px at 168px width, already
emitted by `cr0_overlay.py`) plus the human pick carry showcard sessions**; the VLM score
is not load-bearing for the legibility gate. Filed, not hidden.

**4. API-format export was done headlessly (no browser touch available).**
The runbook's "one UI touch — Save (API format)" is a browser action unavailable to a
headless operator. The UI-canvas `base_flux.json` was converted to API format
programmatically (a faithful `graphToPrompt` reimplementation: link inputs →
`[src_id, slot]`; widget values mapped positionally; the `control_after_generate` value
trailing the `RandomNoise.noise_seed` widget dropped; the `Reroute` node resolved as a
pass-through so `SamplerCustomAdvanced.latent_image` points directly at `EmptyLatentImage`).
Verified: reroute resolved to `["90",0]`, seed=25 (not `"fixed"`), all links wired. The
render gate (`cr0_render.py`, exact-size + loud-injection) was the semantic validator and
passed on both tiers, confirming the conversion.

## Drift
none — recon clean (playbooks pinned == HEAD; both model repos reachable). No DRIFT file.

## Hand-off state
- ComfyUI left **standing detached** on :8188 (container `cr0-comfyui`, currently idle /
  no model resident after the recovery restart — reloads on next `/prompt`). It is
  showcard's render box; a systemd unit is S-C's business.
- granite-vision seat **standing** on :9000 (llama-swap-managed, ttl 1800 auto-unload).
- Committed: `scripts/showcard-cr0/slotted_flux.api.json`, this file,
  `results/*.receipt.json`, `results/probe.json`, `results/composite.bbox.json`,
  and the small render/composite PNGs.
