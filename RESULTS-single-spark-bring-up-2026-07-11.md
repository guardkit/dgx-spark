# RESULTS — Single-Spark Bring-Up (2026-07-11)

**Host:** `spark-fcf6` (NVIDIA GB10, aarch64, 20 cores, CUDA 13.0, 121 GB usable unified)
**Mode:** `fresh` (no prior fleet on the box). Executed by an agent running
[`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) as the prerequisite for the
LiteLLM front-door overlay. **Outcome: GREEN** — `:9000` serving the four always-on aliases.

## Gate outcomes (Phase 5.4 table, filled)

| Gate | Result | Note |
|---|---|---|
| P0.3 Drift report emitted + reviewed | ✅ PASS | [`DRIFT-single-spark-bring-up-2026-07-11.md`](./DRIFT-single-spark-bring-up-2026-07-11.md) — 1 drift (llama-swap v219→v238, expected/pinned), 0 flags |
| P2.2 llama-server GPU-bound (used_memory > 0) | ✅ PASS | 63,867 MiB (62.4 GB) held across 4 `llama-server` procs after preload — not CPU fallback |
| P3.3 config asserts (matrix / no-f16-KV / no-mmap / timeout / binary) | ✅ PASS | all five |
| P4.2 cgroup under a systemd llama-swap.service | ✅ PASS | `user@1000.service/app.slice/llama-swap.service` — not a Chromium/editor scope |
| P4.3 total unified < 115 GB | ✅ PASS | **76 GB** total unified used (~45 GB headroom); resident compute-apps 62.4 GB |
| P4.3 keepalive timer active | ✅ PASS | `llama-swap-keepalive.timer` active; live run reported "all models ready" |
| P5.1 four always-on aliases listed | ✅ PASS | `chat` · `coach` · `embed` · `workhorse` (+ on-demand `gpt-oss-120b` registered) |
| P5.2 workhorse tool-call + throughput | ✅ PASS | 256-tok gen in 4.51 s ≈ **56.8 tok/s** warm; `thinking`+`text` blocks, `stop_reason=end_turn`; self-ID "Qwen" |
| P5.3 embeddings dim == configured (1024) | ✅ PASS | 1024 dims |

## Recorded numbers

- **llama-swap:** `version: 219` (commit 4ca9c478, built 2026-05-29) — the pinned release.
- **llama.cpp:** built for SM121 `121a-real` from upstream commit **`13f2b28`** (shallow clone → `--version`
  prints cosmetic `version: 1`; real identity is the commit). GPU-bound gate proves the build.
- **Total unified memory:** 76 GB used at fleet rest (< 115 GB ceiling), ~44 GB free.
- **Resident (compute-apps):** 62.4 GB across the four preloaded models
  (workhorse 23,393 MiB · coach 18,748 MiB · chat 12,447 MiB · embed 9,279 MiB).
- **Workhorse throughput:** ~56.8 tok/s warm (target ≥ 40).
- **Embed dims:** 1024 (Qwen3-Embedding-0.6B).
- **Model GGUFs staged (49 GB total):** workhorse 22.4 GB · coach 17.0 GB · chat 12.1 GB · embed 0.6 GB.

## Drift report

[`DRIFT-single-spark-bring-up-2026-07-11.md`](./DRIFT-single-spark-bring-up-2026-07-11.md). Nothing promoted —
the one drift (llama-swap v219→v238) is deliberately pinned; v219 installed as-per PINS.

## Failures & follow-ups (drift found while executing — candidates for a PR to the runbook/scripts)

1. **Runbook Phase 3.1 llama-swap asset URL is stale.** The step downloads
   `…/releases/download/v219/llama-swap-linux-arm64` (a bare binary) → **404**. The v219 release ships
   **tarballs** (`llama-swap_219_linux_arm64.tar.gz`). Worked around by download→extract→install.
   *Fix:* update Phase 3.1 to fetch the `_linux_arm64.tar.gz` asset and extract the binary.
2. **`scripts/stage-public-models.sh` chat model source/glob is wrong.** It pulls `chat` from
   `unsloth/gpt-oss-20b-GGUF --include *mxfp4*`, but that repo has **no** `*mxfp4*` file (only standard
   quants F16/Q4_K_M/UD-Q4_K_XL/…), so the download produced no `.gguf` and `set -e` aborted the script
   (embed never ran). Worked around by sourcing the native-MXFP4 file from the **official**
   `ggml-org/gpt-oss-20b-GGUF` (`gpt-oss-20b-mxfp4.gguf`, 12.1 GB) into the exact config path.
   *Fix:* point the chat stage at `ggml-org/gpt-oss-20b-GGUF` (or select an explicit unsloth quant).
3. **`HF_HUB_ENABLE_HF_TRANSFER` is deprecated** in the installed `huggingface_hub` (1.23.0) — transfers now
   use **Xet**; the env var is a no-op warning. Harmless; consider dropping it / switching to
   `HF_XET_HIGH_PERFORMANCE`.
4. **Keepalive assets in `scripts/` are the operator's personal lineup** (`qwen-graphiti`, `nomic-embed`,
   `coach-ft-v3`; guardkit ExecStart path). For the public fleet a public-fleet variant was installed at
   `/usr/local/bin/llama-swap-keepalive.sh` with `MODEL_PROBE_KIND` = workhorse/coach/chat/embed, plus
   matching `.service`/`.timer` in `/etc/systemd/system/`. *Consider* committing a
   `scripts/llama-swap-keepalive.public.sh` so the runbook has a public keepalive to install.

## Endpoint

`llama-swap :9000` is live and serving. Managed via `systemctl --user … llama-swap`; linger enabled so it
survives logout/boot. Ready for the additive LiteLLM `:4000` front-door overlay.
