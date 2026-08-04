# RESULTS — Single-Spark Bring-Up (2026-08-04)

**Mode:** re-run on the reference box `promaxgb10-41b1` (built box, live personal lineup replaced by the public config). Executed end-to-end by an agent (Claude Code / Fable 5). **This is the v219→v245 promotion-validation run the PINS block called for — v245 is VALIDATED GREEN.**
**Wall-clock:** ~25 min including recon (the preload was ~20 s — GGUFs were warm in page cache from the personal fleet; a genuinely cold box will see minutes).

## Gate outcomes (Phase 5.4 table, filled)

| Gate | Result | Note |
|---|---|---|
| P0.3 Drift report emitted + reviewed | **PASS** | committed `DRIFT-single-spark-bring-up-2026-08-04.md` (01e8c2a) — 1 pin drift (v245→v247 upstream), 10 flags; run proceeded on PINS |
| P3.1 llama-swap == pinned v245 | **PASS (on intent)** | runbook grep FAILED on a version-string format change — see finding F1 |
| P2.2 llama-server GPU-bound (used_memory > 0) | **PASS** | 53,554 MiB across 3 children, all `/usr/local/bin/llama-server` (b9430), after preload |
| P3.3 config asserts (matrix / no-f16-KV / no-mmap / timeout / binary) | **PASS ×5** | |
| P4.2 cgroup under a systemd llama-swap.service | **PASS** | `user@1000.service/app.slice/llama-swap.service` — user unit, not an editor scope |
| P4.3 total unified < 115 GB | **PASS** | **65 GB total** unified used · 52.3 GB compute-apps resident (runbook expected ~53) |
| P4.3 keepalive timer active | **PASS** | public-fleet variant installed; timer active AND a manual service run probed clean ("All configured models are ready") |
| P5.1 three always-on aliases listed | **PASS** | `workhorse` · `coach` · `embed` + `gpt-oss-120b` registered on-demand — exactly the public set |
| P5.2 workhorse /v1/messages + throughput | **PASS** | **64.1 tok/s warm**, `stop_reason: end_turn`, thinking + text blocks — see finding F3 |
| P5.3 embeddings dim == configured (1024) | **PASS** | Qwen3-Embedding-0.6B → 1024 |

## Recorded numbers

- **Total unified:** 65 GB used at steady state (ceiling 115; freeze on record at 114)
- **Compute-apps resident:** 52.3 GB (workhorse 24,420 MiB · coach 19,871 MiB · embed 9,279 MiB)
- **Workhorse throughput:** 64.1 tok/s warm (1,905 output tokens / 29.7 s, `/v1/messages`); 61–64 tok/s across three smokes
- **Embed dims:** 1024
- **Preload-to-ready:** ~20 s (page-cache warm; not representative of a cold box)
- **Versions in service:** llama-swap **v245** (30470a4) · llama.cpp **b9430** (d48a56eff) at `/usr/local/bin/llama-server`

## Drift report

[`DRIFT-single-spark-bring-up-2026-08-04.md`](./DRIFT-single-spark-bring-up-2026-08-04.md) (committed 01e8c2a). Nothing promoted this run; the run itself *was* the validation of the 2026-08-01 v219→v245 promotion. Next-promotion candidates recorded there: v247 (ui-svelte security fix), v230 `-config-dir`, and a llama.cpp build bump for the post-b9430 GB10/CUDA fixes (#24933, #25530, #26588).

## Failures & follow-ups (all non-blocking; bundle into one runbook PR)

- **F1 — P3.1 version gate false-FAIL (the run's gate-catch):** v245 prints `version: v245 (30470a4)`; v219 printed `version: 219 (…)`. The upstream version string grew a `v` prefix inside the promotion gap, so the runbook's `grep "version: ${SWAP_VER}"` fails against a *correct* binary. Verified the pin by inspection + a format-tolerant re-assert (`grep -E "version: v?245[^0-9]"`). **PR: make the gate regex `version: v?${SWAP_VER}`.**
- **F2 — Phase 0.1 snippet still hardcodes `PINNED_SWAP=v219`** — a stale mirror of the PINS block (v245 since 2026-08-01), violating the "pin lives in one place" rule. Run used the PINS value. **PR: read the pin from one variable or update the snippet.**
- **F3 — P5.2 smoke's `max_tokens: 256` is below Qwen3.6's thinking budget** under `--reasoning auto`: at 256 and even 1024 tokens the reply is a `thinking` block only (verified genuine chain-of-thought on both `/v1/messages` and `/v1/chat/completions` — not a template leak). At 3072 the model closes thinking and emits the answer (`end_turn`, 1,905 tokens). **PR: raise the smoke to `max_tokens: 3072` and note "thinking-only reply at small budgets" in Phase 7 triage.** Client guidance: budget ≥2K output tokens for the workhorse, or request `--reasoning off` behavior per client.
- **Run nuance (documented deviation):** the unit was **stopped before** the binary+config swap rather than letting `-watch-config` hot-reload under the outgoing v219 — avoids a double ~40 GB cold-load and makes the run validate v245's own startup/preload path. Consider noting this ordering in §3.2 for re-runs on a live box.
- **Box-state note:** this box's personal lineup was replaced by the public config (the §3.2 ⚠️ fired as designed). Backups: config `config.yaml.bak-20260804-213319` · v219 binary `/usr/local/bin/llama-swap.bak-v219` · personal keepalive script `.bak-20260804-personal` + unit `.bak-20260804` files · prior user unit `~/.config/systemd/user/llama-swap.service.bak-20260804`. Restore = copy back config (+ optionally binary/keepalive) and `systemctl --user restart llama-swap`.
- **Status flip:** first green walkthrough complete — the runbook header's Draft→**Verified** flip is ready to go in the same amendments PR (with the PINS note "reference box runs v219 until this run is green" now satisfiable).
