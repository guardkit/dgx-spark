# RESULTS — showcard LT-0 (personal likeness LoRA spike), run 2026-07-17 (Node B = spark-fcf6)

Status: **TEST MATRIX GREEN — 8/8 renders PASS at 1280x720, 0 failures.** This is
the LT-0 test-matrix + identity-sheet stage (the R stage). The DF-024 likeness
verdict is **Rich's attended judgment of the delivered sheet at 100% crops** — this
doc delivers the receipts and the sheet; it does **not** pronounce the gate, and it
records **no likeness verdict** (binding rule 1). Any visual read here is advisory
framing, mechanical/quality words only.

The trained adapter, every checkpoint, the dataset images, and all renders/crops
are LIKENESS DATA and live on Node B only — **no operator image bytes in this or
any repo.** Committed here: scripts, configs, prompts, timings, hashes, counts.

## Adapter under test (on-box only; NOT committed)
- **rw0man_lt0.safetensors** — final DreamBooth LoRA, **5071060480 B**,
  **sha256 `510b40aa57ffcb3828f41389bc6ca78b2d9d981899f0b35e7d9ce9f4f5f792fa`**.
  Trigger token **`rw0man person`**. In
  `~/dgx-spark-playbooks/nvidia/flux-finetuning/assets/models/loras/` (host-mounted
  into cr0-comfyui; visible via `/object_info/LoraLoaderModelOnly`).
  Intermediate checkpoints also on box: `-000025/-000050/-000075.safetensors`
  (checkpoint-75 sha256 `1ebad082e63a49ae921971db207f70fc121fd6ee181eefcf32526cf23a3eef66`).
  Training config (from `scripts/showcard-lt0/launch_train_lt0.sh`, playbook flags
  verbatim): network_module lora_flux, dim 256 / alpha 256, Prodigy optimizer,
  lr 1.0, cosine_with_restarts, 100 epochs, save_every 25, bf16, dataset 20 curated
  frames @1024 (`flux_data/rw0man`, class_tokens "rw0man person", flip_aug off).

## Stack / PINS as-run
- **ComfyUI 0.3.62**, container `cr0-comfyui` (image flux-comfyui), `127.0.0.1:8188`.
  Started from Exited state at run open (`docker start cr0-comfyui`); no recreate.
- **Path (a) model:** `flux1-dev.safetensors` (**23.8 GB, full precision, NOT fp8**,
  checkpoints dir) via `CheckpointLoaderSimple`; MODEL only is used.
- **Path (b) model:** `flux1-kontext-dev.safetensors` (**23.8 GB full precision**,
  diffusion_models dir) via `UNETLoader` (weight_dtype=default).
- **Text encoders + VAE (both paths):** `t5xxl_fp16.safetensors` + `clip_l.safetensors`
  via `DualCLIPLoader(type=flux)`; `ae.safetensors` via `VAELoader`.
- **LoRA node:** `LoraLoaderModelOnly(rw0man_lt0.safetensors, strength_model=1.0)`.
- **Sampler:** euler / simple / 48 steps / `FluxGuidance` (a) 3.5, (b) 2.5 /
  `EmptySD3LatentImage` 1280x720 (owns output size) / `SamplerCustomAdvanced`.
- Pillow 10.2.0. Graphs committed: `scripts/showcard-lt0/lora_dev_plain.api.json`
  (path a), `lora_kontext_ref.api.json` (path b). Prompts+seeds: `matrix.json`.

## Path (a) graph arrangement (LoRA-on-FLUX.1-dev, plain generation)
```
slot / node             class_type              as-run
SC_CKPT      (91)        CheckpointLoaderSimple  flux1-dev.safetensors  -> MODEL only
SC_LORA      (92)        LoraLoaderModelOnly     rw0man_lt0.safetensors, strength 1.0
             (61)        ModelSamplingFlux       max_shift 1.15 base_shift 0.5 (1280x720)
DualCLIPLoader(11)       DualCLIPLoader          t5xxl_fp16 + clip_l (type flux)
SC_PROMPT    (6)         CLIPTextEncode          per-render (each begins "rw0man person")
SC_GUIDANCE  (60)        FluxGuidance            3.5
SC_STEPS     (17)        BasicScheduler          simple, 48 steps, denoise 1.0
             (16)        KSamplerSelect          euler
SC_SEED      (25)        RandomNoise             42 / 8675309
SC_SIZE      (90)        EmptySD3LatentImage     1280x720 (owns output size)
VAELoader(10)/VAEDecode(8)/SaveImage(9)
```
Chain: CkptLoader->LoraLoaderModelOnly->ModelSamplingFlux->BasicGuider/BasicScheduler.
CLIP is taken straight from DualCLIPLoader (model-only LoRA -> no CLIP branch).

Path (b) = `slotted_kontext.api.json` adapted: `CheckpointLoaderSimple(fp8)` replaced
by `UNETLoader(flux1-kontext-dev.safetensors, default)`, `LoraLoaderModelOnly` inserted
between the loader and BasicGuider/BasicScheduler, reference photo uploaded via
`POST /upload/image` into SC_SUBJECT_IMAGE -> FluxKontextImageScale -> VAEEncode ->
ReferenceLatent -> FluxGuidance. Steps overridden 20->48; 1280x720.

## The test matrix (8 renders, all 1280x720, size gate PASS)
Every path-(a) prompt begins with the trigger `rw0man person`; themes: studio
(indigo gradient), tech (desk + hardware), outdoor (natural-light casual).
Wall time = server-side execution_start->execution_success from /history.

| name              | path | theme   | seed    | server s | gate |
|-------------------|------|---------|---------|----------|------|
| a-studio-42       | a    | studio  | 42      | 144.2*   | PASS |
| a-studio-8675309  | a    | studio  | 8675309 | 111.4    | PASS |
| a-tech-42         | a    | tech    | 42      | 197.8    | PASS |
| a-tech-8675309    | a    | tech    | 8675309 | 102.0    | PASS |
| a-outdoor-42      | a    | outdoor | 42      | 164.3    | PASS |
| a-outdoor-8675309 | a    | outdoor | 8675309 | 143.4    | PASS |
| b-studio-42       | b    | studio  | 42      | 530.0    | PASS |
| b-tech-42         | b    | tech    | 42      | 387.6    | PASS |

*a-studio-42 was rendered once in a smoke check at 144.2s; the deterministic
matrix re-run hit ComfyUI's result cache (server 0.1s, identical bytes) — the
144.2s figure is the true compute time and is what the sheet/README carry.

Timings are receipts, not promises. Path-(a) spread (102-198s) tracks UMA memory
contention: an independent coach session kept reviving the `coach` GGUF seat on
:9000 on demand mid-batch, cutting available memory. Path-(b) is far slower
(388-530s) — full-precision Kontext (23.8 GB) + the 5 GB LoRA + reference VAE
encode ran with only ~47-48 GB available (light swap), not a stack fault.

Per-render receipts: `renders/*.receipt.json` (on box, viewing dir — includes
prompt, seed, wall time, sha256; NOT committed, they sit beside image bytes).
Matrix summary: `renders/render_matrix_receipts.json`.

## Whole-box residency / memory (as-measured, `free -g`, 128 GB UMA)
| point                                              | avail | used |
|----------------------------------------------------|-------|------|
| run open (coach seat resident, cr0-comfyui Exited) | 94    | 26   |
| after GET :9000/unload + cr0-comfyui start         | 95    | 26   |
| path (a) mid-batch (flux1-dev resident + coach reloaded on demand) | 3-60 | 60-80 |
| **docker restart cr0-comfyui between paths** (release flux RSS) | 95 | 26 |
| path (b) (Kontext full-precision + LoRA resident)  | 47-48 | 73-74 |
| box restored (keepalive on, seats reload)          | 47    | 74   |

- Seats unloaded before each batch via **`GET 127.0.0.1:9000/unload`** (MA-26
  lease `coach` held by owner `showcard-lt0` for the window). A coach consumer
  reloaded the seat on demand mid-run repeatedly; every render still passed.
- **`/free` does not release flux RSS** — between path (a) and path (b) a
  `docker restart cr0-comfyui` was required to drop flux1-dev's ~24 GB before
  loading full-precision Kontext; that restored avail 40->95 GB. Recorded.
- Full-precision flux1-dev (a) and Kontext (b) are each ~24 GB residents; unlike
  KR-0's fp8 Kontext (~12 GB) they leave much less headroom, which is why the
  path-(b) renders ran slow under the concurrent coach seat.

## Deliverables (viewing dir `~/showcard-sessions/lt0-20260717/`, on box only)
- `renders/` — 8 PNGs @1280x720 (`<path>-<theme>-<seed>.png`) + receipts.
- `crops/` — face crops at NATIVE resolution, zero resampling: `ref_*_face.png`
  (4 real-photo references: held-out DSC00044/DSC00062 + training reps
  DSC00042/DSC00069) and `<render>_face.png` (8). These are the 100% judging files.
- `identity-sheet.png` (1738x4286) — reference faces strip, then per-render pairs
  [ held-out ref DSC00044 | render ].
- `contact-sheet.png` (1282x1702) — all 8 renders labelled path/theme/seed/time.
- `README.txt` — what Rich is viewing + how to judge + the advisory-only header.
- GB10 mirror NOT done from this local executor (no SSH this session); the
  coordinator mirrors to `~/showcard-live2-renders/` if a second viewing surface
  is wanted.

## Builder's-eye note — ADVISORY framing, mechanical words only, NOT a verdict
Only Rich judges likeness (binding rule 1); the following claims nothing about
likeness:
- All 8 frames are sharp, correctly exposed, coherent at the face, 1280x720; no
  melted faces, no double-faces, no diffusion artifacts observed.
- Path (a) plain generation strongly reproduces the training-set CONTEXT against
  the prompt: grey graphic tee in every frame; "outdoor" still renders the green
  training backdrop; box-holding / desk poses recur — adapter anchoring, not a
  frame defect.
- Path (b) Kontext+LoRA+reference did NOT visibly degrade (the honesty-note risk
  from the handoff did not materialise this run): both frames are clean and
  well-composed, no washout/incoherence.

## Hand-off state
- `cr0-comfyui` left **Up** on :8188 (Kontext resident/idle; reloads on next /prompt).
- `llama-swap-keepalive.timer` **restarted → active** (the coordinator paused it
  for the batch window; restarting restores standing-seat revival — it reloads the
  standing seats within ~5 min). Seat lease `coach` **released** (status FREE).
  `GET :9000/running` → **200**. Final `free -g`: 47 avail / 74 used.
- Committed (LOCAL, path-limited, **not pushed**): `scripts/showcard-lt0/render_matrix.py`,
  `lora_dev_plain.api.json`, `lora_kontext_ref.api.json`, `build_sheet.py`,
  `matrix.json`, and this file. No image bytes, no adapter, no dataset in the commit.
```
matrix: 8/8 PASS @ 1280x720, 0 failures | path a 6 (102-198s) | path b 2 (388-530s)
adapter rw0man_lt0.safetensors sha256 510b40aa...f792fa (on box only) | Rich judges the sheet
```
