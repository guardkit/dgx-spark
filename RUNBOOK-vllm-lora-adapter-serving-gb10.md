# Runbook: Runtime LoRA adapter serving on GB10 — vLLM v0.25.0, UNPATCHED (no LoRA patches; one broken file removed at container start — see PINS)

**Status:** **Unproven** — first execution pending. Supersedes the ad-hoc
`~/fine-tuning/scripts/vllm_lora_spike.sh` (which pinned an abandoned image; see §0 WHY).

**Purpose:** Prove that a **stock, unpatched** vLLM serves a **runtime LoRA adapter** against a
**MoE Gemma 4** base on the GB10, at parity with the merged seat. If it holds, one resident base
plus swappable ~1.9 GB adapters replaces N × 25 GB merged seats — the change that dissolves the
seat-swap problem for the factory.

**Conventions:** [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — recon → drift report → gates.

**Outputs:** `RESULTS-vllm-lora-adapter-serving-<YYYY-MM-DD>.md`, `DRIFT-vllm-lora-adapter-serving-<YYYY-MM-DD>.md`.

**Estate constraint (READ FIRST):** this runbook **unloads the llama-swap seats** and needs
≥90 GB of the 121 GB unified pool. It **cannot** run beside factory work. Confirm every forge
build is TERMINAL before starting (`forge status`) — see
[[forge-restart-mid-flight-and-the-lying-runner-2026-08-24]].

---

## PINS (runbook v1, set 2026-08-24)

```
vLLM image        vllm/vllm-openai:v0.25.0-aarch64-cu129   (built 2026-07-11)
                  WHY THIS OLD RELEASE, AND NOT THE CURRENT ONE: v0.25.0 is the ONLY release that
                  both (a) carries the LoRA resolver fix and (b) predates the breakage below.
                  v0.26.x and v0.27.1 CANNOT LOAD GEMMA 4 AT ALL — they ship transformers 5.14 or
                  newer, whose heterogeneity guard refuses a plain `getattr` on any attribute of a
                  config with per-layer attributes, and vLLM's `get_head_size()`
                  (`transformers_utils/model_arch_config_convertor.py`) does exactly that. It fails
                  with `AmbiguousGlobalPerLayerAttributeError: 'head_dim' is a per-layer attribute`,
                  it fails identically with `--enable-lora` removed (so it is base-model support,
                  not adapters), `--hf-overrides` does not help (the guard fires on access, not on
                  the value), and it is not fixed on vLLM main. transformers 5.14.0 shipped
                  2026-07-15; the v0.25.0 image was built four days earlier with transformers 5.13.0.
                  Being behind the current release is CORRECT HERE, not drift to be closed.
                  WHY NOT cu130-nightly: ABANDONED — last built 2026-04-23 while cu129 ships
                  daily. The `cu130` name reads as newer than `cu129` and is not. Running it
                  cost us a wrong upstream issue (vllm#53470, closed not-planned).
                  KNOWN DEFECT IN THIS IMAGE, UNRELATED TO LoRA: it ships a broken torchcodec — a
                  CUDA-13 build (`libnvrtc.so.13`) inside a CUDA-12.9 image — which raises at
                  `import vllm` and kills the server before any model work. vLLM catches ImportError
                  but not this RuntimeError, so an ABSENT torchcodec is fine and a PRESENT-BUT-BROKEN
                  one is fatal. The container therefore deletes it at start (Phase 1). We decode no
                  video. Say this out loud in the results: "unpatched" means no LoRA patches, and
                  must never be allowed to hide this removal.
base snapshot     unsloth/gemma-4-26b-a4b-it @ 60941ad6341d0b7af91277ff25c4175f08b56819
                  WHY THIS EXACT SNAPSHOT: it is the one the adapter was TRAINED on. Serving
                  d722512f instead scored 15/17; pinning the trained-on snapshot scored 17/17.
                  A snapshot mismatch looks exactly like a bad adapter.
adapters          one directory holding one vLLM-format export per adapter, e.g.
                  ~/fine-tuning/output/vllm-exports/{po-v5,po-v6,coach-v4,plan-v2}
                  (each r=16, ~1.9 GB). po-v5 is
                  ~/fine-tuning/output/po-gemma4-v5/lora-adapter-vllm — the known-good reference
                  export; never modify it. The rest come from the per-expert converter
                  (`~/fine-tuning/scripts/convert_moe_lora_to_per_expert.py`).
seat dials        --max-model-len 32768 --max-num-seqs 4 --gpu-memory-utilization 0.55
                  --max-loras N --max-cpu-loras 2N  (N = adapters served together)
                  --reasoning-parser gemma4
                  --no-enable-prefix-caching --limit-mm-per-prompt '{"image":0}'
                  Arithmetic for 0.55 and the reason for the reasoning parser: Phase 1.
eval              fleet-evals task po-held-007-feature-spec (suite po-heldout-spec, reps 3)
                  grading: `python3 -m pytest test/ -q` = 17 test functions
BASELINE          17/17 — the same adapter, same snapshot, under vLLM 0.19.2rc1.dev134 WITH
                  three local patches. This run must match it with ZERO patches.
```

When recon flags drift on a pin, the fix is a **PR editing this block** — never a runtime edit (§6).

---

## What this run must answer (state BEFORE running)

| # | Question | Prior evidence | Falsified if |
|---|---|---|---|
| Q1 | Does an unpatched vLLM **start** with a LoRA on MoE Gemma 4? | Failed on the April build (`get_expert_mapping` AttributeError). Fixed upstream in v0.25.0 — **read from source, never executed here.** | engine exits non-zero / no `/v1/models` |
| Q2 | Is the adapter **effective**, or silently inert? | #39815 open, its fix #39816 **unmerged**. Our inertness evidence is all April-era. | adapter arm scores == base arm |
| Q3 | Parity with the merged seat? | 17/17 with 3 patches | adapter arm < 17/17 |
| Q4 | Does **one process serve several adapters at the same time** (parallel slots)? | The current workhorse runs llama.cpp with `-np 1`, which serialises: on 2026-09-01 a simultaneous pair of identical requests took **2.0×** the time of one alone. | a simultaneous pair takes ≥ 1.5× a single request (Phase 1b) |

**Q2 is the one with no upstream answer.** Do not infer it from Q1 passing.

**The planner adapter is served but NOT exam-gated here.** The planner's held-out exam
(`po-held-008`) has no runner assembly — there is no machine grader for it in this lane. Serve
`plan-v2` so it is loaded and counted in Q4's slot test, and record its exam result as
**"not gated"**. Do not invent a grader to fill the gap.

**Known non-defect:** tasks 004/005 diverge on **template, not adapter** — merged (GGUF template,
`--reasoning auto`) emits `<think>…`; vLLM+adapter without a reasoning parser emits a tool call and
stops. That is why Phase 1 passes `--reasoning-parser gemma4`. Do NOT read the divergence as an
adapter regression.

---

## Phase 0: Recon (read-only, advisory — degrade gracefully if offline)

```bash
HUB=https://hub.docker.com/v2/repositories/vllm/vllm-openai
PINNED_TAG=v0.25.0-aarch64-cu129; PINNED_VER=v0.25.0
PUSHED=$(curl -s "$HUB/tags/$PINNED_TAG" | jq -r '.last_updated // empty' | cut -c1-10)
[ -n "$PUSHED" ] && echo "image tag $PINNED_TAG: last built $PUSHED" \
                 || echo "recon: image tag not confirmable — proceed on the local copy"
LATEST_VER=$(curl -s "$HUB/tags?page_size=100&name=aarch64-cu129&ordering=last_updated" \
  | jq -r '[.results[].name | capture("^(?<v>v[0-9]+\\.[0-9]+\\.[0-9]+)-aarch64-cu129").v] | first // empty')
if   [ -z "$LATEST_VER" ];              then echo "recon: latest-release lookup unavailable — proceed on PINS"
elif [ "$LATEST_VER" = "$PINNED_VER" ]; then echo "vLLM image: pinned == latest ($PINNED_VER)"
else echo "DRIFT: vLLM image pinned $PINNED_VER, latest $LATEST_VER"; fi

# PUBLISHED IS NOT MAINTAINED — report the BUILD DATE, never just existence.
```

**▶ GATE (advisory):** operator reviews drift. A **rolling** tag with an old build date is
abandoned; a **version pin** with an old build date is correct by design. **On this runbook a DRIFT
line is the EXPECTED output and is not an action:** v0.25.0 is deliberately behind current because
every later release fails to load Gemma 4 (see PINS). Only re-open the pin when an upstream release
notes fix `get_head_size()` for per-layer attributes.

## Phase 0.5: Pre-flight (checks only — halts)

```bash
docker image inspect vllm/vllm-openai:v0.25.0-aarch64-cu129 >/dev/null && echo PASS-image || echo FAIL-image
SNAP=$HOME/.cache/huggingface/hub/models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819
[ -d "$SNAP" ] && echo PASS-snapshot || echo FAIL-snapshot
ADAPTERS=$HOME/fine-tuning/output/vllm-exports
for A in "$ADAPTERS"/*/; do
  [ -f "$A/adapter_model.safetensors" ] && echo "PASS-adapter $(basename "$A")" \
                                        || echo "FAIL-adapter $(basename "$A")"
done

# ESTATE GATE — absolute. If ANY row of forge status shows RUNNING, PAUSED or QUEUED, STOP
# and report. Do not unload seats, do not start a container, do not "just check something first".
docker exec forge-prod forge --config /var/forge/forge.yaml status 2>/dev/null \
  | grep -qE 'RUNNING|PAUSED|QUEUED' && echo "FAIL-estate: a build is non-terminal — DO NOT PROCEED" \
                                     || echo PASS-estate
```

**▶ GATE:** all PASS, or stop. `FAIL-estate` is absolute — the factory owns the GPU.

## Phase 1: Serve UNPATCHED

**The point of this phase is what is NOT here.** The superseded spike mounted three patched
files; this run mounts **none**. If any is needed again, Q1 is answered NO.

Four things in the command below are not cosmetic:

- **`--entrypoint bash … rm -rf …/torchcodec*`** — the image's torchcodec is broken and kills
  `vllm` at import (PINS). Deleting it is an image-packaging workaround, **not** a LoRA patch.
- **`--reasoning-parser gemma4`** — the base chat template primes a `<|channel>thought` section in
  every generation prompt. Without a parser that thinking text lands in `content` and breaks the
  file markers the graders read. Required for `plan-v2` and `qav`, harmless for the rest.
- **`--max-loras N`** — the maximum number of *different* adapters vLLM will serve **in one batch**;
  it defaults to **1**, so leaving it unset serialises everything the moment two adapters are in
  flight together. Set it to the number of adapters mounted. `--max-cpu-loras` is the host-side
  cache and must be at least `--max-loras`; 2N gives room to swap without evicting a live one.
- **`--gpu-memory-utilization 0.55`** — this fraction is of the **whole 121 GB unified pool**, which
  the GPU and CPU share, not of some GPU-only budget. 0.55 × 121 ≈ **66 GB**, which holds the
  **49 GB** bf16 base + **1.9 GB per adapter** (4 adapters ≈ 7.6 GB) + KV cache with room to spare,
  and leaves ~55 GB — comfortably more than the **~30 GB** the rest of the estate needs for the
  21 GB workhorse and the small always-on seats. The default of 0.92 would claim ~111 GB and starve
  llama.cpp outright.

**No `--rm`.** A container that dies in 20 seconds must leave its log behind. Remove it by hand in
Phase 4, after the logs are captured.

```bash
SNAP=/hf/hub/models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819
ADAPTERS=$HOME/fine-tuning/output/vllm-exports        # one subdirectory per adapter export
N=$(find "$ADAPTERS" -mindepth 1 -maxdepth 1 -type d | wc -l)
curl -sS -m 30 http://127.0.0.1:9000/unload >/dev/null 2>&1     # free the seats (reload on demand)
until [ "$(free -g | awk '/Mem:/{print $7}')" -ge 90 ]; do sleep 5; done
docker rm -f vllm-lora >/dev/null 2>&1
docker run -d --name vllm-lora --gpus all --ipc=host -p 8010:8000 \
  -v "$HOME/.cache/huggingface":/hf:ro \
  -v "$ADAPTERS":/adapters:ro \
  --entrypoint bash vllm/vllm-openai:v0.25.0-aarch64-cu129 -c \
  'rm -rf /usr/local/lib/python3.12/dist-packages/torchcodec* && exec vllm serve "$@"' _ \
  --model "$SNAP" --served-model-name gemma4-base \
  --enable-lora --max-lora-rank 16 \
  --lora-modules po-v5=/adapters/po-v5 po-v6=/adapters/po-v6 \
                 coach-v4=/adapters/coach-v4 plan-v2=/adapters/plan-v2 \
  --max-loras "$N" --max-cpu-loras "$((2*N))" \
  --reasoning-parser gemma4 \
  --max-model-len 32768 --max-num-seqs 4 --no-enable-prefix-caching \
  --gpu-memory-utilization 0.55 --limit-mm-per-prompt '{"image":0}'
```

**▶ GATE Q1** — serves, and **every** model id is advertised:

```bash
for i in $(seq 1 150); do curl -sf -m 5 http://127.0.0.1:8010/v1/models >/dev/null && break; sleep 10; done
curl -s http://127.0.0.1:8010/v1/models | jq -r '.data[].id' | sort | tee /tmp/vllm-ids.txt
MISSING=0
for M in gemma4-base po-v5 po-v6 coach-v4 plan-v2; do
  grep -qx "$M" /tmp/vllm-ids.txt || { echo "missing: $M"; MISSING=1; }
done
[ "$MISSING" -eq 0 ] && echo "PASS-Q1 unpatched serve + all adapters registered" || echo "FAIL-Q1"
docker logs vllm-lora 2>&1 | grep -i 'get_expert_mapping' && echo "FAIL-Q1: expert-mapping error" || true
docker logs vllm-lora 2>&1 | grep -i 'not in the model.s supported LoRA target modules' \
  && echo "WARN: tensors SKIPPED — adapter may be silently inert (see Q2)" || true
```

## Phase 1b: Q4 — do two requests actually run side by side?

Two **identical** greedy requests to the **same** adapter, fired at the same moment, against one
alone. If the server serialises them the pair takes about twice as long; if it batches them the pair
costs barely more than one. The comparison point is the current workhorse: llama.cpp with `-np 1`
measured **2.0×** on 2026-09-01.

```bash
OUT=$HOME/fine-tuning/output/vllm-concurrency/phase1b.csv
mkdir -p "$(dirname "$OUT")"; echo "arm,requests,seconds" > "$OUT"
REQ='{"model":"po-v6","temperature":0,"max_tokens":256,"messages":[
       {"role":"user","content":"List the phases of a feature build, one per line."}]}'
fire(){ curl -sS -o /dev/null -m 300 -H 'Content-Type: application/json' \
             -d "$REQ" http://127.0.0.1:8010/v1/chat/completions; }
now(){ date +%s.%N; }

fire                                              # warm-up, NOT recorded: the first call pays
                                                  # cold start and a prefix miss, not queueing
S0=$(now); fire;               S1=$(now)
P0=$(now); fire & fire & wait; P1=$(now)
printf 'single,1,%.2f\npair,2,%.2f\n' "$(echo "$S1-$S0"|bc)" "$(echo "$P1-$P0"|bc)" >> "$OUT"
cat "$OUT"
awk -F, 'NR>1{v[$1]=$3} END{r=v["pair"]/v["single"];
  printf "pair/single = %.2fx (llama.cpp -np 1 measured 2.0x on 2026-09-01) — %s\n",
         r, (r<1.5 ? "PASS-Q4 slots are real" : "FAIL-Q4 requests are serialised")}' "$OUT"
```

**▶ GATE Q4:** PASS if the pair completes in **less than 1.5×** the single. Receipt is the CSV at
`~/fine-tuning/output/vllm-concurrency/phase1b.csv` — quote the two times and the ratio from that
file, never from memory of the terminal.

## Phase 2: Q2 — is the adapter actually DOING anything?

Two arms, same prompt, same server, greedy. **This is the question upstream has not answered.**

```bash
cd ~/Projects/appmilla_github/fleet-evals
for M in gemma4-base po-v5; do
  PO_EVAL_OUTPUT_DIR=$HOME/fine-tuning/output/vllm-q2-$M \
  python3 harness/run_po_eval.py --model "$M" --endpoint http://127.0.0.1:8010/v1 \
    --suite po-heldout-spec --task po-held-007-feature-spec --rep 1 --grade \
    2>&1 | tail -5
done
```

**▶ GATE Q2:** the two arms must **differ**. Identical output = the adapter is inert (#39815
alive) — record it and stop; Q3 is then meaningless.

## Phase 3: Q3 — parity with the merged seat

```bash
PO_EVAL_OUTPUT_DIR=$HOME/fine-tuning/output/vllm-q3 \
python3 harness/run_po_eval.py --model po-v5 --endpoint http://127.0.0.1:8010/v1 \
  --suite po-heldout-spec --task po-held-007-feature-spec --grade 2>&1 | tail -20
```

**▶ GATE Q3:** **17/17** = parity, adapter serving proven unpatched. 15/17 → check the snapshot
pin FIRST (see PINS), not the adapter.

## Phase 4: Restore the estate (MANDATORY — do not skip on failure)

```bash
docker logs vllm-lora > $HOME/fine-tuning/output/vllm-lora-$(date +%Y%m%dT%H%M%S).log 2>&1
docker rm -f vllm-lora >/dev/null 2>&1
curl -sf -m 20 http://127.0.0.1:9000/v1/models >/dev/null && echo "PASS-restore llama-swap answering" || echo "FAIL-restore"
docker ps --format '{{.Names}}' | grep -q forge-prod && echo "PASS-forge up" || echo "FAIL-forge"
```

## Decision Gate

| Q1 | Q2 | Q3 | Meaning |
|---|---|---|---|
| PASS | differ | 17/17 | **Adapter serving is production-ready unpatched.** Open the seat-consolidation lane. |
| PASS | differ | <17/17 | Serving works, quality gap — check snapshot pin, then template divergence. |
| PASS | **same** | — | #39815 alive: loads, silently inert. **Do not ship.** Report on #39815 with this receipt. |
| FAIL | — | — | Still needs patches. Record which. |

**Q4 is recorded beside this table, not inside it.** It does not change any row above: adapter
serving can be production-ready with requests serialised, and can be worthless-but-parallel. Record
the ratio from the Phase 1b CSV either way. A PASS on Q4 is what makes one vLLM process a
replacement for the `-np 1` workhorse rather than only a replacement for the merged seats.

Record the outcome in `RESULTS-*`, including **what was NOT proved** — the planner adapter's exam
among them: served, loaded, counted in Q4, **not gated**.
