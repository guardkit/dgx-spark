#!/usr/bin/env bash
# audio-parakeet.sh — launch Parakeet TDT 0.6B v3 STT (NeMo, OpenAI-compatible
# /v1/audio/transcriptions) under llama-swap for the unified voice pins
# (RUNBOOK-gb10-voice-unified-2026-07 Phase 1; unified-voice-orientation §2).
#
# Invoked by llama-swap as:  audio-parakeet.sh <PORT>
# Serves FastAPI on <PORT> (container :8000). Routes: /health, /v1/models,
# /v1/audio/transcriptions (multipart: file [+ model/language/response_format,
# `model` accepted-and-ignored so LPA's STT_MODEL=parakeet-tdt passes through).
#
# IMAGE: martinb78/parakeet-tdt-v3-spark — community GB10/ARM64 container
# (github.com/mARTin-B78/dgx-spark-parakeet-asr, vendored into dgx-spark repo
# under vendor/). Single-maintainer artifact → pinned by DIGEST, not tag.
# The model weights are baked into the image at build time (~1.2 GB in
# /root/.cache/huggingface), so no volume mounts and no NGC/HF key at runtime.
# HF_HUB_OFFLINE=1 enforces ADR-POC-015 local-only: cache-hit or fail, never
# a network fetch. Verified 2026-07-05: cold start → /health ready ~15 s,
# "front center" WAV + webm/opus both transcribe correctly, ~4.7 GB GPU.
#
# RESIDENCY: registered ttl:0 + member of EVERY matrix.set (never evicted,
# never evicts others). ~5 GB is affordable even in the tight exclusive sets
# (autobuild_go/po_eval ~95-105 GB peak → ~100-110 with both audio models).
set -euo pipefail

PORT="${1:?usage: audio-parakeet.sh <PORT>}"
NAME="audio-parakeet"
IMAGE="${AUDIO_PARAKEET_IMAGE:-martinb78/parakeet-tdt-v3-spark@sha256:298efedc5b970292dd14b6c244f943eb4b40146725adf105b0ce4519ab2fec67}"

# Remove any stale container from a prior crash so --name does not conflict.
docker rm -f "$NAME" >/dev/null 2>&1 || true

# exec so llama-swap's child IS the `docker run` client; llama-swap stops us
# via cmdStop (`docker stop audio-parakeet`); `--rm` cleans up either way.
exec docker run --rm --name "$NAME" \
  --gpus all \
  --shm-size 16g \
  -p "${PORT}:8000" \
  -e HF_HUB_OFFLINE=1 \
  -e NCCL_P2P_DISABLE=1 \
  "$IMAGE"
