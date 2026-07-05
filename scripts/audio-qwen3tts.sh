#!/usr/bin/env bash
# audio-qwen3tts.sh — launch Qwen3-TTS 0.6B CustomVoice (faster-qwen3-tts,
# OpenAI-compatible /v1/audio/speech) under llama-swap for the unified voice
# pins (RUNBOOK-gb10-voice-unified-2026-07 Phase 2; Kokoro-82M is the named
# fallback, no longer the pin).
#
# Invoked by llama-swap as:  audio-qwen3tts.sh <PORT>
# Serves FastAPI on <PORT> (container :8000). Routes: /health, /speakers,
# /v1/models, /v1/audio/speech (JSON: model [ignored], voice, input,
# response_format wav|pcm|mp3|zip, speed). English speakers: Ryan (the LPA
# TTS_VOICE pin), Aiden.
#
# IMAGE: martinb78/faster-qwen3-tts-dgx-spark — community GB10/ARM64 container
# (github.com/mARTin-B78/dgx-spark-faster-qwen3-tts, vendored into dgx-spark
# repo under vendor/; torch from the cu130 wheel index → CUDA 13 correct for
# the GB10). Single-maintainer artifact → pinned by DIGEST, not tag.
#
# SERVER CODE IS MOUNTED, NOT BAKED: /config holds our vendored copy of
# run_customvoice_server.py with the /health endpoint PATCHED to return 503
# until the model is loaded AND CUDA-graph warmup has completed (upstream
# returns 200 with model_loaded:false during load, which would fool
# llama-swap's checkEndpoint into routing before the ~25 s warmup is done).
# Because tts_model is assigned only after the warmup synthesis, health 200
# ⇒ warmed ⇒ the first real request never pays graph capture.
#
# WEIGHTS: /opt/llama-swap/models/qwen3-tts/Qwen3-TTS-12Hz-0.6B-CustomVoice
# (hf download, 2.4 GB on disk), mounted read-only. No network at runtime:
# HF_HUB_OFFLINE=1 (ADR-POC-015 local-only; the zip/timestamps format would
# need the HF-hosted ForcedAligner and is intentionally unavailable).
#
# MEMORY (measured 2026-07-05): ~3-4 GB resident incl. CUDA graphs; load +
# warmup ~25 s WITH free memory. TRAP: CUDA context creation fails outright
# (cudaErrorMemoryAllocation on cudaMemGetInfo) when the box is at ~110 GB
# used — if this model must cold-start while the full family is resident and
# memory is tight, unload something first (see RESULTS-gb10-voice-unified).
# PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True per the granite-vision
# lesson (unified-memory allocator behaviour).
#
# RESIDENCY: registered ttl:0 + member of EVERY matrix.set (persistent audio
# group with parakeet) — loaded once, never evicted, never re-pays warmup.
set -euo pipefail

PORT="${1:?usage: audio-qwen3tts.sh <PORT>}"
NAME="audio-qwen3tts"
IMAGE="${AUDIO_QWEN3TTS_IMAGE:-martinb78/faster-qwen3-tts-dgx-spark@sha256:e1c69bc4362d98b6ee18b61e9d4f2ee8ae78ece2a4c20f300f4f282e6cd6c8dd}"
MODEL_DIR="${AUDIO_QWEN3TTS_MODEL_DIR:-/opt/llama-swap/models/qwen3-tts/Qwen3-TTS-12Hz-0.6B-CustomVoice}"
CONFIG_DIR="${AUDIO_QWEN3TTS_CONFIG_DIR:-/opt/llama-swap/audio/qwen3-tts-config}"

# Remove any stale container from a prior crash so --name does not conflict.
docker rm -f "$NAME" >/dev/null 2>&1 || true

# exec so llama-swap's child IS the `docker run` client; llama-swap stops us
# via cmdStop (`docker stop audio-qwen3tts`); `--rm` cleans up either way.
exec docker run --rm --name "$NAME" \
  --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  -p "${PORT}:8000" \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e HF_HUB_OFFLINE=1 \
  -v "${MODEL_DIR}:/models/Qwen3-TTS-CustomVoice:ro" \
  -v "${CONFIG_DIR}:/config:rw" \
  "$IMAGE" \
  /bin/bash -c "python3 /config/run_customvoice_server.py \
    --model /models/Qwen3-TTS-CustomVoice \
    --voices /config/customvoice_voices.json \
    --port 8000 \
    --max-seq-len 2048"
