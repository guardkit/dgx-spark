# Vendored community audio containers (voice-unified pins, 2026-07-05)

Both GB10 voice containers are **single-maintainer community artifacts** — per
the standing note in `study-tutor/docs/research/ideas/unified-voice-orientation.md`
§3, their Dockerfiles are vendored here and the launch scripts pin image
**digests**, never tags. If either image vanishes from Docker Hub, rebuild from
these sources.

| Component | Upstream | Vendored @ commit | Image digest (pinned in launch script) |
|---|---|---|---|
| STT — Parakeet TDT 0.6B v3 | github.com/mARTin-B78/dgx-spark-parakeet-asr | `97b70f0cd2df3df51ab961e94e7ee7cc7000dbd5` | `martinb78/parakeet-tdt-v3-spark@sha256:298efedc5b970292dd14b6c244f943eb4b40146725adf105b0ce4519ab2fec67` |
| TTS — Qwen3-TTS 0.6B CustomVoice | github.com/mARTin-B78/dgx-spark-faster-qwen3-tts | `dbcbddedb4ea5c6e2c2b2d36379da3273cc1c9c6` | `martinb78/faster-qwen3-tts-dgx-spark@sha256:e1c69bc4362d98b6ee18b61e9d4f2ee8ae78ece2a4c20f300f4f282e6cd6c8dd` |

Note: the orientation doc's image name `martinb78/dgx-spark-parakeet-asr` was
wrong (that's the GitHub repo name); the Docker Hub image is
`martinb78/parakeet-tdt-v3-spark`.

## Layout

- `dgx-spark-parakeet-asr/` — upstream as-is (Dockerfile under `docker/`,
  FastAPI app under `app/`, model baked into the image at build time; the
  compose file's NGC_API_KEY is only needed to build, not to run).
- `dgx-spark-faster-qwen3-tts/` — upstream as-is minus audio samples
  (`Dockerfile` at root uses the **cu130** torch wheel index — correct for the
  GB10's CUDA 13; `config/` holds the mode-specific servers that the container
  runs from a **host mount**, not from the image).
- `dgx-spark-faster-qwen3-tts/deployed/` — the AS-DEPLOYED copy of the
  CustomVoice server mounted at `/opt/llama-swap/audio/qwen3-tts-config` on the
  GB10, with one local patch: **`/health` returns 503 until the model is loaded
  AND CUDA-graph warmup has completed** (upstream returns 200 with
  `model_loaded:false` during load, which would fool llama-swap's
  `checkEndpoint` into routing before the warmup finishes). Diff against
  `../config/run_customvoice_server.py` to see the patch.

## Serving topology

Both containers are registered in llama-swap behind `:9000` as a persistent
group (`ttl: 0`, member of every `matrix.set`, FIRST in the preload order —
their CUDA context creation fails if the big family loads first and leaves the
box near the memory ceiling). Launch scripts: `../scripts/audio-parakeet.sh`,
`../scripts/audio-qwen3tts.sh`. Live config mirror:
`../examples/llama-swap-config.gb10-live-2026-07-05-voice-unified.yaml`.

Standup evidence + measurements:
`lpa-platform-poc/docs/runbooks/RESULTS-gb10-voice-unified-2026-07.md`.
