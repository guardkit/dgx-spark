# RESULTS — showcard LT-0 (personal likeness LoRA spike), run 2026-07-17 (Node B = spark-fcf6)

Status: **ADAPTER TRAINED + TEST MATRIX GREEN — 8/8 renders PASS at 1280x720, 0
failures.** This is the LT-0 receipts stage. The DF-024 likeness verdict is
**Rich's attended judgment of the delivered sheet at 100% face crops** — this doc
delivers the receipts and the sheet; it does **not** pronounce the gate and records
**no likeness verdict** (binding rule 1). Every visual read here is labelled
*advisory framing (not a likeness judgment)* and uses mechanical/quality words only.

The trained adapter, every intermediate checkpoint, the dataset images, and all
renders/crops are **LIKENESS DATA** and live on Node B only — **no operator image
bytes in this or any repo.** Committed here: scripts, configs, prompts, timings,
sha256 hashes, counts, notes.

**Operator go (asked-once, 2026-07-17):** Rich ruled **"No re-shoot yet — proceed"**
on the existing Jul-12 green-screen set (`~/Pictures/showcard-operator/rich/`,
mtimes confirmed unchanged from the 07-12 shoot). LT-0 ran on that set per his ruling.

---

## 1. Dataset (on-box only; NOT committed)

- **Source:** `~/Pictures/showcard-operator/rich/` — READ-ONLY, 56 frames
  (DSC00038–DSC00093), 7008×4672 each. Originals proven untouched: `work/originals-ls-{before,after}.txt`
  byte-identical (dir sha256 `2db32c34…`). All processing copies EXIF-transposed
  outputs into new files; no source frame modified/moved/deleted.
- **COUNT: 20 curated training frames** → `flux_data/rw0man/` (target 18–24; 20
  chosen for variety without duplicate-flooding). Filenames (curation is text, not
  image bytes): DSC00039, 00041, 00042, 00045, 00047, 00049, 00051, 00054, 00055,
  00058, 00060, 00065, 00069, 00070, 00072, 00076, 00078, 00084, 00087, 00093.
- **Curation criteria:** the shoot is one tripod green-screen presenter setup
  heavily dominated (~35 near-identical frames) by a single "holding a box out to
  camera" pose. Curation deliberately samples ACROSS the variety axes — front
  neutral / front smile / point-up / point-across / hold-at-chest / box-front /
  turned-3/4 — and takes only ONE representative per axis, dropping the
  near-duplicate box-front flood (over-representing one pose harms a likeness LoRA).
  Eyes must be visible (identity-load-bearing); glasses ON in all 20 except the sole
  glasses-off frame DSC00039 (kept for eyewear/expression variety). Faces sharp,
  subject chest-up with headroom, no cut faces. Full per-frame rationale:
  `work/dataset-notes.md` (on box).
- **Held-out (never trained):** dataset-prep held out **DSC00043** and **DSC00086**
  (copied EXIF-transposed to `reference/held-out-*.jpg` as Kontext reference
  candidates). The stage-R identity sheet additionally used **DSC00044** and
  **DSC00062** as held-out reference faces (also NOT in the 20-frame training set)
  plus in-set representatives DSC00042 and DSC00069 for the reference strip.
- **`flip_aug = false` rationale:** the shipped tjtoy/sparkgpu subsets use
  `flip_aug = true`; that is the ONE deliberate deviation from the sample subsets.
  Faces are asymmetric (hair parting, brow/eye asymmetry, glasses sit slightly
  off-level); a horizontal flip teaches a mirrored face and dilutes identity — a net
  harm for a personal-likeness LoRA, so flip augmentation is OFF. Shipped 2-concept
  file preserved verbatim as `flux_data/data.toml.playbook-sample`.
- **Caption convention:** MIRRORS the sample exactly — `class_tokens`-only, **no
  per-image `.txt` caption files** (the tjtoy/ and sparkgpu/ dirs ship images only).
  Identity carried by `class_tokens = "rw0man person"`.
- **Processing** (`dataset_prep.py` + `crops.json`, both committed — filenames /
  crop boxes / text only): `exif_transpose` → crop per `crops.json` → resize longest
  side to 1024 → JPEG q95. All 20 verified: PIL-loadable, RGB, longest side == 1024.

---

## 2. Training config (VERBATIM) + the two-attempt story

### 2a. Launcher — `scripts/showcard-lt0/launch_train_lt0.sh` (committed)

The launcher **mirrors the playbook `assets/launch_train.sh` flag-for-flag.** The
playbook defaults ARE the recorded config; the launcher changes NOTHING about them.
Deviations, exhaustively:
- **(a)** `--output_name=rw0man_lt0` (playbook: `flux_dreambooth`) — the LT-0 adapter name.
- **(b)** `docker run -d --name lt0-flux-train` (playbook: `-it --rm`) — detached +
  named so logs survive retrieval and the container is inspectable post-exit; removed
  with `docker rm` after logs captured.
- **(c)** nothing else. Every `accelerate` / `flux_train_network.py` flag, every
  mount, every ulimit is byte-identical to the playbook launcher.

The training command, verbatim as run:

```
accelerate launch --num_processes=1 --num_machines=1 --mixed_precision=bf16 \
  --main_process_ip=127.0.0.1 --main_process_port=29500 --num_cpu_threads_per_process=2 \
  flux_train_network.py \
  --pretrained_model_name_or_path=models/checkpoints/flux1-dev.safetensors \
  --clip_l=models/text_encoders/clip_l.safetensors \
  --t5xxl=models/text_encoders/t5xxl_fp16.safetensors \
  --ae=models/vae/ae.safetensors \
  --dataset_config=flux_data/data.toml \
  --output_dir=models/loras/ --prior_loss_weight=1.0 --output_name=rw0man_lt0 \
  --save_model_as=safetensors --network_module=networks.lora_flux \
  --network_dim=256 --network_alpha=256 \
  --learning_rate=1.0 --optimizer_type=Prodigy --lr_scheduler=cosine_with_restarts \
  --gradient_accumulation_steps 4 --gradient_checkpointing --sdpa \
  --max_train_epochs=100 --save_every_n_epochs=25 --mixed_precision=bf16 \
  --guidance_scale=1.0 --timestep_sampling=flux_shift --model_prediction_type=raw \
  --torch_compile --persistent_data_loader_workers \
  --cache_latents --cache_latents_to_disk \
  --cache_text_encoder_outputs --cache_text_encoder_outputs_to_disk
```

`data.toml` subset as run (the one field changed from the sample is `flip_aug`):
```
[general]  shuffle_caption = false   keep_tokens = 2
[[datasets]]  resolution = 1024   batch_size = 1
  [[datasets.subsets]]
    image_dir = "flux_data/rw0man"   class_tokens = "rw0man person"
    num_repeats = 1   is_reg = false   flip_aug = false
```
100 epochs × 20 images ÷ (batch 1 × grad-accum 4) → **500 optimizer steps**.

### 2b. Measured wall times

| stage | measured | note |
|-------|----------|------|
| docker image build (`Dockerfile.train` → `flux-train`) | **~95 s** | 11:32:24Z build-start → 11:33:59Z launch; base layers cached, only the GL-dev apt layer rebuilt (52.4 s) |
| latent + text-encoder caching (attempt 2, to first optimizer step) | **~4 min** | container start 13:29:53 → step 1 logged at timer 04:06 |
| **training (attempt 2, the run that completed)** | **step loop 5:52:48; wall 13:29:53 → 19:29:01 (~6 h)** | 500/500 steps, exit 0, all 4 checkpoints saved |
| per-render (test matrix) | see §4 table | 102–198 s path (a); 388–530 s path (b) |

### 2c. The two-attempt story (honest and complete)

**Attempt 1 — seats-resident phase (11:33:59 → ~12:54, ~80 min wall as logged;
never reached a usable adapter).** Two launches, both defeated by resident
llama-swap seats:
- **First launch** (`work/train-20260717-oom-attempt1.log`): container up 11:33:59Z;
  caching 11:34:08 → 11:38:58; first optimizer steps at **266 → 115 s/it**; **OOM —
  died `<Signals.SIGKILL: 9>` at ~step 3/500** with the `coach` GGUF seat resident on
  the 128 GB UMA box.
- **Relaunch** (`work/train-attempt1-full.log`): 11:49:54 → 12:54:04; climbed only to
  **step 20/500 at 83 → 180 s/it, the per-step rate degrading as it ran.** Root
  cause: the **`llama-swap-keepalive.timer` revives the standing seats
  (workhorse / coach / chat / embed) on a ~5-minute cycle and is NOT lease-aware**,
  so it re-loaded seats within minutes of each `GET :9000/unload` and defeated the
  residency prep — training never got the exclusive box the playbook wants. The
  coordinator stopped this run for the residency fix.
- **Residency fix (coordinator, for the batch window):** the keepalive timer was
  **paused for the window** (restored at stage-R box-restore), the seats unloaded via
  `GET :9000/unload`, and `drop_caches` run — giving the exclusive box.

**Attempt 2 — exclusive box (13:29:53 → 19:29:01, completed).** 500/500 steps, exit
0. Per-step rate **~42–53 s/it** (52.65 s/it warming at step 20, settling to
~42–46 s/it; final `500/500 [5:52:48<00:00, 42.34s/it]`). Checkpoints saved at
epochs 25/50/75 and the final adapter.

### 2d. Wall-clock finding (contradicts the handoff's cited class)

The LT-0 handoff cites a **"~90-min measured class"** train on this box. **That does
NOT hold at the playbook defaults on this box.** Even on the exclusive box
(attempt 2), the measured band is **~42–53 s/it × 500 steps ≈ 5 h 53 m step-time,
~6 h wall.** The ~90-min figure appears to describe a shorter/smaller-step
configuration than the playbook's `max_train_epochs=100` default on a 20-image set.
Recorded as measured; timings are receipts, not promises.

---

## 3. Adapter under test (on-box only; NOT committed, NEVER uploaded)

- **Name:** `rw0man_lt0.safetensors` — final DreamBooth LoRA. Trigger token
  **`rw0man person`**. Size **5,071,060,480 B (~5.07 GB)**.
- **sha256 `510b40aa57ffcb3828f41389bc6ca78b2d9d981899f0b35e7d9ce9f4f5f792fa`**.
- **BOTH on-box locations (identical bytes, same sha256 verified):**
  1. `~/dgx-spark-playbooks/nvidia/flux-finetuning/assets/models/loras/rw0man_lt0.safetensors`
     — host-mounted into `cr0-comfyui` at `/workspace/ComfyUI/models/loras`
     (visible via `/object_info/LoraLoaderModelOnly`); the render-path copy.
  2. `~/models/loras-operator/rw0man-lt0-v1.safetensors` — the retained/named copy
     per handoff §1.2.
- **Intermediate checkpoints (also on box, likeness data):**
  `rw0man_lt0-000025 / -000050 / -000075.safetensors` in the loras dir (each 5.07 GB;
  checkpoint-75 sha256 `1ebad082e63a49ae921971db207f70fc121fd6ee181eefcf32526cf23a3eef66`).
- **The law, restated:** the adapter, every checkpoint, and the dataset images are
  likeness data — **never committed to any repo, never staged, never uploaded, they
  stay on this box.** Provenance records `lora: {name, sha256}` whenever the adapter
  participates in a render.

---

## 4. Stack / PINS as-run + test matrix

- **ComfyUI 0.3.62**, container `cr0-comfyui` (image `flux-comfyui`), `127.0.0.1:8188`.
- **Path (a):** `flux1-dev.safetensors` (**23.8 GB full precision, NOT fp8**,
  checkpoints dir) via `CheckpointLoaderSimple` (MODEL only).
- **Path (b):** `flux1-kontext-dev.safetensors` (**23.8 GB full precision**,
  diffusion_models dir) via `UNETLoader` (weight_dtype=default).
- **Text encoders + VAE (both):** `t5xxl_fp16.safetensors` + `clip_l.safetensors`
  via `DualCLIPLoader(type=flux)`; `ae.safetensors` via `VAELoader`.
- **LoRA node:** `LoraLoaderModelOnly(rw0man_lt0.safetensors, strength_model=1.0)`.
- **Sampler:** euler / simple / **48 steps** / `FluxGuidance` (a) 3.5, (b) 2.5 /
  `EmptySD3LatentImage` 1280×720 (owns output size) / `SamplerCustomAdvanced`.
- Pillow 10.2.0. Graphs committed: `scripts/showcard-lt0/lora_dev_plain.api.json`
  (path a), `lora_kontext_ref.api.json` (path b). Prompts + seeds: `matrix.json`.

**Test matrix — 8 renders, all 1280×720, size gate PASS ×8, 0 failures.** Path-(a)
prompts each begin with the trigger `rw0man person`; themes studio / tech / outdoor;
seeds 42 and 8675309. Path (b) = LoRA stacked on Kontext + one held-out reference
photo (DSC00044). Wall = server-side `execution_start → execution_success`.

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

\* a-studio-42 was first rendered in a 144.2 s smoke check; the deterministic matrix
re-run hit ComfyUI's result cache (server 0.1 s, identical bytes) — **144.2 s is the
true compute time** and is what the sheet/README carry.

Path-(a) spread (102–198 s) tracks UMA contention: an independent coach session kept
reviving the `coach` GGUF seat on `:9000` on demand mid-batch. Path (b) is far slower
(388–530 s): full-precision Kontext (23.8 GB) + the ~5 GB LoRA + reference VAE encode
ran with only ~47–48 GB available — light swap, not a stack fault.

Per-render receipts: `renders/*.receipt.json` (on box, viewing dir — prompt, seed,
wall, sha256; NOT committed, they sit beside image bytes). Summary:
`renders/render_matrix_receipts.json`.

### Path-(b) Kontext-transfer observation — advisory framing (not a likeness judgment)

Recorded exactly as stage R observed, mechanical words only: the dev-trained LoRA
stacked onto FLUX.1-Kontext-dev + reference **did NOT visibly degrade** — both path-(b)
frames are sharp, well-composed, coherent at the face, no washout/incoherence. The
"a dev-trained LoRA may not transfer onto Kontext" risk the handoff flagged **did not
materialise mechanically this run.** This is a transfer/quality note only; it says
nothing about whether any frame looks like the operator.

---

## 5. Whole-box residency / memory receipts (as-measured, 128 GB UMA)

**Train batch prep** (`work/pre-residency.log`): only the `coach` seat
(gemma-4-26B) resident at open → MA-26 lease acquired (owner `showcard-lt0`, seat
`coach`, `/opt/llama-swap/leases/coach.lease.json`) → `GET :9000/unload` OK,
`/running` empty → `free -g` 43 used / **78 avail** → `drop_caches` → 77 free /
**78 avail**; `cr0-comfyui` left Up. The keepalive timer then revived seats and
defeated this (see §2c) until the coordinator paused the timer for the window.

**Render batch** (`free -g`):

| point                                                          | avail | used |
|----------------------------------------------------------------|-------|------|
| run open (coach seat resident, cr0-comfyui Exited)             | 94    | 26   |
| after GET :9000/unload + cr0-comfyui start                    | 95    | 26   |
| path (a) mid-batch (flux1-dev resident + coach reloaded on demand) | 3–60 | 60–80 |
| **docker restart cr0-comfyui between paths** (release flux RSS) | 95    | 26   |
| path (b) (Kontext full-precision + LoRA resident)             | 47–48 | 73–74 |
| box restored (keepalive on, seats reload)                     | 47    | 74   |

- Seats unloaded before each batch via `GET 127.0.0.1:9000/unload`; MA-26 lease
  `coach` held by owner `showcard-lt0` for the window.
- **`/free` does NOT release flux RSS** — between path (a) and path (b) a
  `docker restart cr0-comfyui` was required to drop flux1-dev's ~24 GB before loading
  full-precision Kontext (restored avail 40→95 GB). Recorded.
- Full-precision flux1-dev (a) and Kontext (b) are each ~24 GB residents; unlike
  KR-0's fp8 Kontext (~12 GB) they leave far less headroom — why path (b) ran slow
  under the concurrent coach seat.

---

## 6. Deliverables — sheet + evidence (viewing dir, on box only)

**Sheet location: `/home/richardwoollcott/showcard-sessions/lt0-20260717/`** (Spark
viewing dir). Contents:
- `renders/` — 8 PNGs @1280×720 (`<path>-<theme>-<seed>.png`) + per-render receipts.
- `crops/` — face crops cut at NATIVE resolution, **zero resampling** (the 100%
  judging files): `ref_*_face.png` (real-photo references — held-out DSC00044 /
  DSC00062 + training reps DSC00042 / DSC00069) and `<render>_face.png` (8).
- `identity-sheet.png` (1738×4286) — reference-faces strip, then per-render pairs
  `[ held-out ref DSC00044 | render ]`.
- `contact-sheet.png` (1282×1702) — all 8 renders labelled path/theme/seed/time.
- `README.txt` — what Rich is viewing + how to judge + the advisory-only header.

**GB10 viewing dir NOT delivered** (`~/showcard-live2-renders/`): from Node B the
GB10 was **unreachable this session — publickey denied.** Recorded honestly; the
coordinator mirrors the sheet to the GB10 surface if a second viewing dir is wanted.
No operator image bytes leave the box for this delivery.

### Builder's-eye note — advisory framing (not a likeness judgment), mechanical only

Only Rich judges likeness (binding rule 1); the following claims nothing about likeness:
- All 8 frames are sharp, correctly exposed, coherent at the face, exactly 1280×720;
  no melted faces, no double-faces, no observed diffusion artifacts.
- Path (a) plain generation strongly reproduces the training-set CONTEXT: grey
  graphic tee in every frame; "outdoor" still renders the green training backdrop;
  box-holding / desk poses recur — adapter anchoring, not a frame defect.
- Path (b) Kontext+LoRA+reference did not visibly degrade (see §4).
- None of the above is evidence about whether any frame looks like the operator.

---

## 7. Hand-off state

- `cr0-comfyui` left **Up** on :8188 (Kontext resident/idle; reloads on next `/prompt`).
  No stray training container (`lt0-flux-train` removed after logs captured).
- `llama-swap-keepalive.timer` **restarted → active** (the coordinator paused it for
  the batch window; restarting restores standing-seat revival). Seat lease `coach`
  **released** (lease dir holds only `README.txt`). `GET :9000/running` → **200**.
- Playbook-checkout edits noted for RESULTS (all under its working dirs, per rule 5):
  `flux_data/rw0man/` (dataset, likeness data), `flux_data/data.toml` (rewritten to
  the single rw0man subset; sample preserved as `data.toml.playbook-sample`),
  `models/loras/rw0man_lt0*.safetensors` (adapter + 3 checkpoints, likeness data),
  `flux-train` docker image built. No playbook source outside its working dirs touched.
- Committed (LOCAL, path-limited, **NOT pushed**): `scripts/showcard-lt0/**`
  (`dataset_prep.py`, `crops.json`, `launch_train_lt0.sh`, `lora_dev_plain.api.json`,
  `lora_kontext_ref.api.json`, `render_matrix.py`, `build_sheet.py`, `matrix.json`)
  and this `RESULTS-showcard-lt0.md`. **No image bytes, no adapter, no dataset, no
  checkpoint in any commit.**

```
dataset: 20 curated frames (on box) | flip_aug=false (sole deviation) | held-out DSC00043/00086 (+ sheet refs DSC00044/00062)
train: attempt 1 seats-resident FAILED (OOM SIGKILL @step3, then step 20/500 @83->180 s/it, stopped for residency fix)
       attempt 2 exclusive box EXIT 0, 500/500 @ ~42-53 s/it, ~6h wall — the "~90-min class" does NOT hold at playbook defaults
adapter rw0man_lt0.safetensors 5.07GB sha256 510b40aa...f792fa (on box only; 2 locations, identical)
matrix: 8/8 PASS @1280x720, 0 failures | path a 6 (102-198s) | path b 2 (388-530s)
```

**Verdict: PENDING — Rich's attended judgment at 100% face crops,
reference-beside-render (only the operator judges likeness).**
