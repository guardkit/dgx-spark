# RESULTS — showcard KR-0 (Kontext fidelity spike), run 2026-07-13 (Node B = spark-fcf6)

Status: **MATRIX GREEN — 15/15 renders PASS, no failures. Kontext is usable on this
stack; NOT parked.** The DF-024 render-track verdict is the operator's *attended*
judgment of the fidelity sheet — this doc delivers that sheet and the receipts; it does
**not** pronounce the gate.

This is the KR0-MATRIX stage. KR0-PREP (the slotted Kontext graph + the subject-image
render gate, validated end-to-end) landed at `3381431`; this run consumes it.

PINS as-run:
- **Model:** `flux1-dev-kontext_fp8_scaled.safetensors` — Comfy-Org packaged repack
  (fp8_scaled, **UNGATED**), size **11904640136 B (~11.9 GB)**,
  **sha256 `630ba795ec64283b4230ea23cf79406c2c68b7c578229ed139f30043eadb30a2`**.
  Source: `https://huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI` (the
  `split_files/diffusion_models` repack of black-forest-labs/FLUX.1-Kontext-dev).
  Loaded via `CheckpointLoaderSimple` from the **host-mounted** checkpoints dir
  (`~/dgx-spark-playbooks/nvidia/flux-finetuning/assets/models/checkpoints` →
  `/workspace/ComfyUI/models/checkpoints`) — **persistent, survives a container recreate.**
  The `UNETLoader`/`diffusion_models` path is not host-mounted, hence the packaged
  full-checkpoint repack (VAE+CLIP baked or reused) over the gated diffusion-only weights.
- **Text encoders + VAE:** REUSED from CR-0, unchanged — `t5xxl_fp16.safetensors` +
  `clip_l.safetensors` via `DualCLIPLoader(type=flux)`, `ae.safetensors` via `VAELoader`.
- **ComfyUI 0.3.62** (container `cr0-comfyui`, full Kontext node set) · Pillow **11.3.0**.
- **Graph:** `scripts/showcard-kr0/slotted_kontext.api.json` (committed).

## Slot map (ratified `slotted_kontext.api.json`)

```
slot                node  class_type               inject-field   as-run
SC_CKPT             91    CheckpointLoaderSimple   ckpt_name      flux1-dev-kontext_fp8_scaled.safetensors
SC_PROMPT           6     CLIPTextEncode           text           per-render edit instruction
SC_SUBJECT_IMAGE    40    LoadImage                image          uploaded reference (POST /upload/image)
SC_GUIDANCE         60    FluxGuidance             guidance       2.5 (default, not overridden)
SC_SEED             25    RandomNoise              noise_seed     42 / 7 / 123 / 999
SC_STEPS            17    BasicScheduler           steps          20 (scheduler=simple, default)
SC_SIZE             90    EmptySD3LatentImage      width/height   1280x720 (owns output size)
```

Kontext-specific chain (the KR0-PREP addition, DF-024 §3 "image-input slot mechanism"):
`SC_SUBJECT_IMAGE (LoadImage) → FluxKontextImageScale (41) → VAEEncode_reference (42) →
ReferenceLatent (43) → FluxGuidance (60) → BasicGuider (22) → SamplerCustomAdvanced (13)`.
Sampler `euler`, scheduler `simple`. **Output resolution is owned by SC_SIZE
(EmptySD3LatentImage), NOT by the reference** — `FluxKontextImageScale` only sizes the
reference for encoding — so the exact-1280x720 output gate is enforced identically to CR-0
and passed on all 15.

## The fidelity matrix (4 photos × 3 prompts × seed 42 = 12, + DSC00042×studio×{7,123,999} = 3)

All renders **1280×720, PASS** (exact-size gate). Wall time = full submit→poll→download,
warm (Kontext already resident) except where noted.

| subject (pose)                     | prompt    | seed | seconds | result |
|------------------------------------|-----------|------|---------|--------|
| DSC00042 (solo neutral)            | studio    | 42   | 50.1    | PASS   |
| DSC00042 (solo neutral)            | tech      | 42   | 50.1    | PASS   |
| DSC00042 (solo neutral)            | energetic | 42   | 50.2    | PASS   |
| DSC00045 (solo pointing up)        | studio    | 42   | 54.1    | PASS   |
| DSC00045 (solo pointing up)        | tech      | 42   | 50.1    | PASS   |
| DSC00045 (solo pointing up)        | energetic | 42   | 50.1    | PASS   |
| DSC00060 (holding device, 2-hand)  | studio    | 42   | 50.1    | PASS   |
| DSC00060 (holding device, 2-hand)  | tech      | 42   | 50.1    | PASS   |
| DSC00060 (holding device, 2-hand)  | energetic | 42   | 50.1    | PASS   |
| DSC00069 (turned, presenting)      | studio    | 42   | 50.1    | PASS   |
| DSC00069 (turned, presenting)      | tech      | 42   | 50.1    | PASS   |
| DSC00069 (turned, presenting)      | energetic | 42   | 50.1    | PASS   |
| DSC00042 (solo neutral)            | studio    | 7    | 52.1    | PASS   |
| DSC00042 (solo neutral)            | studio    | 123  | 50.1    | PASS   |
| DSC00042 (solo neutral)            | studio    | 999  | 50.1    | PASS   |

Per-render receipt JSONs: `scripts/showcard-kr0/results/*.receipt.json` (15, committed —
verified text/JSON only, no image bytes). Full run log: `results/matrix.log`.

**Timing:** dead-flat **~50s/render** at 20 steps, fp8 Kontext, 1280×720. The two outliers
(54.1s, 52.1s) are poll-granularity jitter, not real spread. 15 renders in ~13 min wall.
No draft/final ladder was exercised this spike (the CR-0 `--steps 8` fallback slot exists on
SC_STEPS if a faster draft tier is later wanted; 50s was already cheap enough to run the
full matrix at final quality).

The three prompt styles, as-run (each ends with the identity-preservation clause
"Keep this man's face, glasses, hair and shirt exactly as in the photo"):
- **studio** — "clean professional photo studio against a single solid deep-teal backdrop,
  chest-up framing with generous empty negative space above and to one side for a headline,
  soft even key lighting."
- **tech** — "rim-lit high-tech desk surrounded by glowing computer monitors and server
  hardware, moody cinematic teal-and-orange colour grade, dramatic side rim lighting,
  shallow depth of field."
- **energetic** — "bold vibrant abstract background of colourful energy streaks and a
  high-contrast gradient of saturated light, dynamic punchy composition, high energy."
(Verbatim prompt text is on every receipt's `prompt` field and in `results/matrix.log`.)

## Whole-box memory / residency behaviour (as-measured)

Free-mem checkpoints from `results/matrix.log` (128 GB UMA box, `free -m`):

| point                                   | mem_avail | used   |
|-----------------------------------------|-----------|--------|
| pre-run (GGUF seats resident, ComfyUI idle) | 27.1 GB | 97.5 GB |
| **after GET :9000/unload** (seats released) | **97.1 GB** | 27.5 GB |
| renders 1–2 (Kontext resident, no seat)     | ~96.5 GB | ~28 GB |
| render 3 onward (a GGUF seat reloaded on demand mid-run) | **24–31 GB** | 93–100 GB |

- **Seats unloaded before the batch:** the resident llama-swap GGUF seats (`chat` =
  gpt-oss-20b, `coach` = gemma-4-26B, plus whatever else llama-swap held) were released
  with a single **`GET 127.0.0.1:9000/unload`** — permitted per the whole-box residency
  lesson; seats reload on demand. No config/daemon edits. That freed **70 GB** (27→97 GB
  available).
- **A seat reloaded on demand ~render 3** (another consumer hit :9000 during the run),
  dropping available to **~24–31 GB** — and **every render still passed.** This is the
  material difference from CR-0: fp8 Kontext (~11.9 GB) is far lighter than CR-0's
  flux1-dev (23.8 GB), so **Kontext-resident-and-busy coexisted with a reloaded GGUF seat**
  inside the UMA ceiling on this run. CR-0's "flux + VLM cannot both be resident-and-busy"
  law was written for the 23.8 GB flux1-dev; the S-C residency law still holds as written,
  but Kontext's lighter footprint gives real headroom the composite-tier flux did not.
- Practical constraint carried forward: unloading competing seats before a render batch is
  still the right hygiene (it removed all contention risk and cost nothing — seats reload
  on demand), but a stray seat reload mid-batch was survivable here, not fatal.

## Fidelity sheet (delivery)

`kr0_sheet.py` → labelled contact sheet, **3036×1140**, reference photo leftmost per row
(red label), renders as columns labelled `style · s<seed>`. The DSC00042 row groups the
four studio renders (seeds 42/7/123/999) adjacently for the seed-stability eyeball.

Delivered to **viewing dirs only, no repo** (likeness law — no image bytes committed):
- Node B: `~/showcard-sessions/kr0/kr0-fidelity-sheet.png`
- GB10:   `/home/richardwoollcott/showcard-live2-renders/kr0-fidelity-sheet.png`

## Builder's-eye identity note — ADVISORY, **NOT the gate verdict**

**The operator's attended judgment of the sheet is the DF-024 gate.** The following is one
executor's eyeball, filed as advisory colour only:

- **Identity holds convincingly across prompts and seeds.** In the four DSC00042 studio
  renders (seeds 42/7/123/999) the face, glasses, hairline, and the grey graphic tee are
  recognizably the *same man* render-to-render — seed variation moves background gradient
  and micro-expression, not identity. Good seed stability.
- The grey graphic tee (with its coloured chest print), glasses, and hair are carried
  faithfully in nearly every render across all four subjects; the held device (DSC00060/69)
  and the pointing gesture (DSC00045) survive into the generated scene.
- **studio** and **energetic** keep the subject large, chest-up, front-facing — ideal
  showcard hero framing, and identity is strongest there.
- **tech** is the weakest of the three for likeness: the "rim-lit desk" prompt pulls a full
  *seated-at-a-keyboard* scene, so the face lands smaller, darker, and sometimes turned —
  still recognizably him, but the least identity-forward framing. This is a **prompt-framing**
  consequence (the scene prompt overrode chest-up composition), not a model fidelity failure;
  a tighter "chest-up, face to camera" clause would likely recover it.
- No obvious identity collapse, no melted/uncanny faces, no wrong-person renders in the set.

On this executor's read Kontext clears the fidelity bar for the studio/energetic styles and
is close for tech pending a framing tweak — **but the binding verdict is Rich's, attended,
on the delivered sheet.** A park verdict remains available to him; nothing here forces success.

## Park-relevant findings

- **None forcing a park.** The one soft spot (tech-style framing pulling a seated wide scene)
  is a prompt-authoring fix inside the same graph, not a stack limitation.
- fp8 Kontext's lighter footprint (§residency) is a positive finding: the render-box vs
  VLM-seat contention that shaped S-C is materially eased on the Kontext tier.

## Hand-off state

- `cr0-comfyui` left **standing** on :8188 (Kontext resident / idle; reloads on next
  `/prompt`). ComfyUI is showcard's render box.
- llama-swap seats left to **reload on demand** (unloaded during the batch via GET /unload;
  no config touched). No daemon/config edits made.
- Writes confined to the named dirs: `~/showcard-kr0/` (scripts + renders + receipts + log),
  `~/showcard-sessions/kr0/` (sheet + manifest), and the GB10 viewing dir
  `~/showcard-live2-renders/`. **No image bytes in any repo.**
- Committed (LOCAL, path-limited): `scripts/showcard-kr0/results/*.receipt.json`,
  `scripts/showcard-kr0/results/matrix.log`, and this file. The graph + render/sheet scripts
  were already committed at `3381431`.
```
selected subjects: DSC00042 (neutral) · DSC00045 (pointing) · DSC00060 (holding device) · DSC00069 (presenting)
matrix: 15/15 PASS @ 1280x720, ~50s each, 0 failures
```
