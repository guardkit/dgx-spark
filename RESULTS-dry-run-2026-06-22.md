# RESULTS — Runbook Dry Run (2026-06-22)

**What:** a **read-only** dry run of [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) and [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) against the live reference box **`promaxgb10-41b1`** (Dell ProMax GB10) — *before* recording the videos. Every read-only gate/check was executed on the proven box; every mutating step (build / download / config-deploy / systemd / TP / firmware) was **static-validated only** (nothing built, downloaded, installed, started, or generated).

**Why:** catch broken gate *commands* (regex/flag/path bugs, destructive steps, false-passing gates) before they bite on camera. The box runs the **personal** lineup and the new Spark + CX-7 cable are not here, so a true fresh-install / two-node run wasn't possible — but the gate mechanics and command correctness were fully exercisable.

---

## Verdict

**Gate mechanics are sound.** Every read-only gate ran and **passed (or lineup-diffed correctly)** on the proven box, and the prior-audit fixes verified working live (recon version-regex parses `9430`; GPU-bound gate passes at ~74 GB across 4 procs; `command -v llama-server` fallback resolves; cgroup gate passes on the user unit; config grep-asserts pass).

**5 real bugs + several doc/staging gaps were found and fixed** (commit `dbecc7b` + the self-contained-runbook refactor below). The single-Spark runbook is **record-ready** — the agent stages the models (Phase 1.5) and builds + installs the binary (Phase 2) as runbook steps; on a fresh box there are **no manual prerequisites**. The two-Spark runbook's gates + installs are now correct for when the cable lands.

---

## Bugs found → fixed (commit `dbecc7b`)

| Sev | Where | Bug | Fix |
|---|---|---|---|
| 🔴 | two-Spark P7 | LiteLLM no-cloud gate **false-passes** — empty `context_window_fallbacks: []` satisfies the `fallbacks: []` *substring* even when `fallbacks:` is populated, defeating the DF-001 cloud-spend guard | anchored both greps to line-start `^\s*` |
| 🔴 | two-Spark P0.1/P1 | `flint` is not on DGX OS (ships `mstflint`) → the firmware brick-guard would silently skip | `flint` → `mstflint` |
| 🔴 | two-Spark P4.1 | hardcoded `MPI_HOME` + OpenMPI not preinstalled → the NCCL `all_gather_perf` build fails | added `apt install libopenmpi-dev openmpi-bin` + resolve `MPI_HOME` from `mpicc --showme:incdirs` |
| 🟠 | two-Spark P4.2 | busbw parse needs a decimal → misreads an integer bandwidth / column drift | `awk '/Avg bus bandwidth/{print $NF}'` |
| 🟠 | single P3.3 | no check that the config's `/usr/local/bin/llama-server` exists → all 5 models fail at start if Phase 2.1's copy was skipped | added a binary-exists assert |
| 🟠 | single P1.1 | `nvidia-smi … memory.total` reports `[N/A]` on GB10 (unified memory); comment implied "~128 GiB" | dropped memory from the query; capacity confirmed via `free -g` |
| + | single P1.2, P3.3; two-Spark P8 | "128 GB"→"~121 usable"; f16-KV grep hardened for `=`; `/running` admin-endpoint shape noted as build-dependent | reworded / hardened |

---

## Execution model — clone → execute → walk away

The runbooks are **self-contained executable specs**. The flow is: clone the repo, point an agent (Claude Code / Codex) at the runbook, say **execute**. The agent runs *every* step — `apt install` build deps, `stage-public-models.sh` (the ~35 GB model pull, Phase 1.5), the llama.cpp build + binary install to `/usr/local/bin` (Phase 2), llama-swap install + config deploy (Phase 3), start + gates (Phases 4–5). Long downloads/builds run **inline** — you edit out the wait; there are **no manual prerequisites** on a fresh box.

The only **non-agent** inputs:
- **One decision:** fresh Spark vs rehearsal on this reference box. ⚠️ On the reference box, Phase 3.2 deploys the public config to `/opt/llama-swap/config/config.yaml` — which **clobbers the live 712-line personal config**. For a rehearsal here, back it up first (`cp … config.yaml.bak`) or skip the deploy step. On a fresh Spark this is a non-issue.
- **`EXPECT_DIM`** (Phase 5.3): `1024` for the public Qwen3-Embedding (the default); `768` only if validating against the live nomic-embed.
- **Sudo:** the agent needs sudo (apt / systemd / writing to `/opt`) — i.e. run it as a user with (passwordless) sudo. That's the one environment precondition, not a per-runbook step.

## Expected "failures" that are NOT bugs (lineup-diffs)

- `/v1/models` shows the 13-model **personal** lineup, not the 4 public aliases (`workhorse/coach/chat/embed`).
- Embeddings dim is **768** (live nomic-embed) vs **1024** (public Qwen3-Embedding) — the documented swap.
- The public `chat`/`embed` GGUFs are absent until staged; the live coach is the fine-tuned `coach-ft-v3` (`--reasoning off`) vs the public stock Gemma-4 (`--reasoning auto`).

## Two-Spark — what the runbook installs vs what's physically manual

Same model: the agent executes everything software — `apt install libopenmpi-dev openmpi-bin build-essential` + build nccl-tests (Phase 4), `pip install litellm` + launch (Phase 7), set up the pinned vLLM (`jasl/vllm dda4668b` + `torch 2.9.1`) + launch the TP Proposer (Phase 8). All inline; edit out the waits.

The only **physically manual** inputs (unavoidable, narratable on camera):
- **Plug in the CX-7 cable** (Phase 3) — one physical action.
- **Firmware update + any reboot** (Phase 2) — `fwupdmgr` is a step, but a firmware flash may need a reboot; resume the runbook after.

Already present on the box (no install needed): `mstflint`, `perftest` (`ib_write_bw`), `ibdev2netdev`, `fwupdmgr`, `nvidia-smi`. Pre-verify `curl :9000/running` returns `{running:[…]}` on llama-swap v219 (Phase 8 precondition) during the single-Spark baseline.

## Notes / corrections

- The **keepalive timer is ACTIVE** (firing every 5 min since 2026-06-21 18:13) — an earlier note that it was stopped was wrong; no restart needed.
- The SVGs are content-correct but should be **re-exported from their `.excalidraw` sources** for clean box auto-sizing.
- DF-004 stays **PROPOSED** until the on-hardware TP=2 vs single-node vs PP=2 benchmark when the cable lands.

*Method: [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — gates decide, research informs, a human ratifies. This dry run executed the gates read-only on the reference box; no procedure was mutated mid-run.*
