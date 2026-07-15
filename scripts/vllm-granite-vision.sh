#!/usr/bin/env bash
# vllm-granite-vision.sh — launch IBM Granite Vision 4.1-4b under vLLM for
# llama-swap. Replaces granite-docling-258M as the LPA extraction VLM
# (~16× more params, designed for general document understanding — the
# 258M model could not structure UK LPA Section 2/4/7 attorney form-grids
# under the LPA POC's smoke test).
#
# Invoked by llama-swap as:  vllm-granite-vision.sh <PORT>
# Serves the vLLM OpenAI API (/v1/chat/completions) on <PORT> (container :8000).
# Used by the LPA extraction project for PDF page → markdown conversion;
# Docling POSTs each rasterised page as a user message containing
# {type:text} + {type:image_url, image_url:{url:"data:image/png;base64,..."}}.
#
# WHY under llama-swap (vs standalone): same reason as vllm-docling.sh — letting
# llama-swap own the unified-memory pool removes the KV-cache memory-profiling
# clash that crashed standalone vLLM. One memory manager. See findings §9.3.
#
# WHY v0.22.0-aarch64-cu129-ubuntu2404: granite-vision-4.1-4b has the
# `Granite4VisionForConditionalGeneration` architecture, which is NATIVELY
# supported by vLLM v0.21+. The cu130-nightly image we originally pinned
# (vLLM 0.18.1rc1) was too old — it fell back to TransformersMultiModalFor-
# CausalLM and crashed with `ValueError: There is no module or parameter
# named 'image_newline'` during model load. The v0.22.0 cu129 aarch64 image
# (released 2026-05-29) has the native impl and loads + serves cleanly on
# Blackwell sm_121 — verified 2026-05-30 (~106 s cold start + bind). The
# pinned cu130-nightly tag is kept for granite-docling (which doesn't need
# the newer vLLM and is on a known-good cuDNN). Do NOT change docling's
# image just because this one changed — they're scoped per-script.
#
# RESIDENCY: in config.yaml this model is a member of the `lpa` matrix.set
# ONLY (NOT `all`). Actual measured cost is ~26 GB resident (vs initial
# estimate of 12-15 GB) — co-residency with the family at ~80 GB plus
# gv ~26 GB = ~106 GB, which crosses the §9.4 freeze threshold. So
# requesting granite-vision triggers a switch to the `lpa` set (gv + qw +
# ne, ~56 GB resident), evicting qg + aa + dl until the model unloads at
# the ttl 1800 idle timeout — same operational pattern as the (removed)
# qwen-coder-next had under §9.2.
#
# OPERATIONAL: if a long LPA session needs to outlast the keepalive's 5-min
# probe cycle, pause the timer first:
#     sudo systemctl stop llama-swap-keepalive.timer
# Re-enable after. The keepalive probes qg+ne+qw+aa (the always-on set);
# a probe for qg while in `lpa` mode would switch back to `all`, evicting
# gv mid-session.
#
# Overridable via env: VLLM_GV_IMAGE, VLLM_GV_GPU_UTIL, VLLM_GV_MAX_SEQS,
# VLLM_GV_MAX_LEN, HF_CACHE, HF_TOKEN.
set -euo pipefail

PORT="${1:?usage: vllm-granite-vision.sh <PORT>}"
NAME="vllm-granite-vision"
IMAGE="${VLLM_GV_IMAGE:-vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404}"
MODEL="ibm-granite/granite-vision-4.1-4b"
HF_CACHE="${HF_CACHE:-/home/richardwoollcott/.cache/huggingface}"
# Util sized for ~15 GB allocation (~12% of 124 GB unified). 4B bf16 weights
# ~8 GB + KV at max-len 8192 × max-num-seqs 4 ≈ 2-3 GB + activations.
# The LPA runbook suggested 0.40 (~50 GB) — that's wasteful given the model
# size; bump only if KV pressure shows up under real load.
GPU_UTIL="${VLLM_GV_GPU_UTIL:-0.12}"
MAX_LEN="${VLLM_GV_MAX_LEN:-8192}"
MAX_SEQS="${VLLM_GV_MAX_SEQS:-4}"

# PER-BOX --limit-mm-per-prompt.image VALUE (Rich RATIFIED 2026-07-15):
#   Node A (promaxgb10-41b1) keeps image=1 — its granite-vision serves
#   lpa-platform-poc / docling single-image OCR under the fleet memory budget.
#   Node B (spark-fcf6) runs image=6 — the showcard anchors-AS-IMAGES
#   experiment needs >1 image per prompt (07-12 S-C session; anchors degraded
#   to text at cap=1); live-proven on Node B since SC-LIVE2. The Node B delta
#   is exactly that one flag (verified at ratification: live == the pre-change
#   .bak + that line; the .bak was then deleted — THIS record is the recovery).
#   A re-provision of Node B re-applies image=6 by hand from this note.
#   See llama-swap-seat-leases.md §Residue for the decision trail.

# Remove any stale container from a prior crash so --name does not conflict.
docker rm -f "$NAME" >/dev/null 2>&1 || true

# exec so llama-swap's child IS the `docker run` client; llama-swap stops us
# via cmdStop (`docker stop vllm-granite-vision`); `--rm` cleans up either way.
# HF_HUB_OFFLINE is NOT set here (unlike docling) because the model isn't yet
# cached locally — first launch needs network access to pull the weights.
# After the first successful launch, remove HF_TOKEN if it isn't needed.
exec docker run --rm --name "$NAME" \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -p "${PORT}:8000" \
  -v "${HF_CACHE}:/root/.cache/huggingface" \
  -e HF_TOKEN="${HF_TOKEN:-}" \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  --entrypoint vllm \
  "$IMAGE" \
  serve "$MODEL" \
    --host 0.0.0.0 --port 8000 \
    --served-model-name granite-vision-4-1-4b granite-vision-4.1-4b granite-vision \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_LEN" \
    --max-num-seqs "$MAX_SEQS" \
    --limit-mm-per-prompt.image=1 \
    --enforce-eager \
    --trust-remote-code
