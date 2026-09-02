# Runbook: Runtime LoRA adapter serving on GB10 — vLLM v0.25.0, UNPATCHED (no LoRA patches; one broken file removed at container start — see PINS)

**Status:** **Executed once, 2026-08-24, on this image and this snapshot** — Q1 PASS, Q2 PASS,
Q3 **50/51** (17/17 · 17/17 · 16/17). Written up in
[`RESULTS-vllm-lora-adapter-serving-2026-08-24.md`](./RESULTS-vllm-lora-adapter-serving-2026-08-24.md).
That run served **one** adapter (`po-v5`); this version of the runbook extends it to four adapters
and adds Q4 (do two requests run side by side?), both still unproven. Supersedes the ad-hoc
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
                  WHY THIS OLD RELEASE, AND NOT THE CURRENT ONE: v0.25.0 is the release that was
                  PROVEN HERE (2026-08-24, 50/51) to carry the LoRA resolver fix and load Gemma 4.
                  v0.26.x and v0.27.1 CANNOT LOAD GEMMA 4 (v0.27.1 proved by execution here): they ship
                  transformers >= 5.14, whose per-layer attention config for Gemma 4 (transformers
                  #47384, in 5.15.0) makes a plain `getattr` on `head_dim` raise in vLLM's
                  `get_head_size()`.
                  v0.28.0 (tag 2026-08-24, arm64 image 2026-08-26) CONTAINS THE vLLM-SIDE FIX — PR
                  #49797 "Fix Gemma 4 for upcoming Transformers version" (merged 2026-08-10; not in
                  0.27.x per the maintainer) — and its LoRA resolver, FusedMoE experts path and `gemma4`
                  reasoning parser are unchanged. It is therefore the CANDIDATE to replace this pin.
                  UNTESTED HERE: do not move the pin until the no-LoRA control launch, the LoRA start
                  and the Q2 effectiveness check have been run on the v0.28.0 image (read from source,
                  never executed — the 2026-08-24 lesson). Whether its cu129 image still ships the
                  broken torchcodec is also unknown until run; keep the removal step.
                  The v0.27.1 failure, for the record: `AmbiguousGlobalPerLayerAttributeError: 'head_dim' is
                  a per-layer attribute`; it fails identically with `--enable-lora` removed (base-model
                  support, not adapters), and `--hf-overrides` cannot help because the guard fires on
                  attribute ACCESS, not on the value.
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
eval              fleet-evals task po-held-007-feature-spec (suite po-heldout-spec, reps 1..3)
                  RUNNER: `harness/run_po_spec_eval.py` — NOT `run_po_eval.py`, which has no
                  assembly for this task and exits 1. It takes neither --suite nor --task.
                  Always pass `--temperature 0` (the runner sends nothing by default and the
                  server then samples) and `--out DIR` (PO_EVAL_OUTPUT_DIR on the command line is
                  a no-op). See "THE RUNNER FOR THIS EXAM" before Phase 2.
                  grading: `python3 -m pytest test/ -q` = 17 test functions
BASELINE          17/17 — the same adapter, same snapshot, under vLLM 0.19.2rc1.dev134 WITH
                  three local patches. This run must match it with ZERO patches.
                  MOST RECENT UNPATCHED RESULT: 50/51 on 2026-08-24 (17/17 · 17/17 · 16/17).
```

When recon flags drift on a pin, the fix is a **PR editing this block** — never a runtime edit (§6).

---

## What this run must answer (state BEFORE running)

| # | Question | Prior evidence | Falsified if |
|---|---|---|---|
| Q1 | Does an unpatched vLLM **start** with a LoRA on MoE Gemma 4? | Failed on the April build (`get_expert_mapping` AttributeError). **PASS on 2026-08-24** on this image and snapshot: served in 470 s, 0 expert-mapping errors, 0 LoRA warnings — but with **one** adapter mounted, not four. | engine exits non-zero / no `/v1/models` |
| Q2 | Is the adapter **effective**, or silently inert? | #39815 open, its fix #39816 **unmerged**, yet **PASS on 2026-08-24** for `po-v5` (greedy, same prompt/server: base 879 chars vs adapter 893, different hashes). Why it worked with the fix unmerged is **not known** — do not carry the pass over to a different adapter without re-testing. | adapter arm scores == base arm |
| Q3 | Parity with the merged seat? | 17/17 with 3 patches (merged seat: 17/17 × 3, clean). Unpatched vLLM on 2026-08-24 scored **50/51** — 17/17 · 17/17 · **16/17**, the miss a spec-content slip. | adapter arm < 17/17 |
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
# It FAILS CLOSED: silence because the command could not run is not permission to proceed.
if ! FORGE_STATUS=$(docker exec forge-prod forge --config /var/forge/forge.yaml status 2>&1); then
  echo "FAIL-estate: cannot read forge status — DO NOT PROCEED"; echo "$FORGE_STATUS" | tail -5
elif printf '%s\n' "$FORGE_STATUS" | grep -qE 'RUNNING|PAUSED|QUEUED'; then
  echo "FAIL-estate: a build is non-terminal — DO NOT PROCEED"
  printf '%s\n' "$FORGE_STATUS" | grep -E 'RUNNING|PAUSED|QUEUED'
else
  echo PASS-estate
fi
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

# Wait for the seats to release, but NEVER forever: 60 tries x 5 s = 5 minutes, then say who is
# still holding the memory. An unbounded `until` here stops the runbook dead with no message.
for _ in $(seq 1 60); do
  AVAIL_GB=$(free -g | awk '/Mem:/{print $7}')          # column 7 = "available"
  [ "$AVAIL_GB" -ge 90 ] && break
  sleep 5
done
if [ "$AVAIL_GB" -lt 90 ]; then
  # FAIL-CLOSED, and it must not kill the operator's shell: the container start lives in the
  # else-branch, so a memory failure cannot fall through into it.
  echo "FAIL-memory: only ${AVAIL_GB} GB available after 5 minutes (need 90). STOP — do not start"
  echo "the container. What still holds the memory:"
  ps -eo rss,pid,comm --sort=-rss | head -9 \
    | awk 'NR>1{printf "  %6.1f GB  pid %-8s %s\n",$1/1048576,$2,$3}'
  curl -sS -m 10 http://127.0.0.1:9000/running 2>/dev/null \
    | head -c 400 | sed 's/^/  llama-swap still running: /'; echo
  echo "  (a seat still loaded means the /unload above did not take — check llama-swap by hand)"
else
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
fi
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

## THE RUNNER FOR THIS EXAM — read before Phase 2 or 3

Three things about the exam command are easy to get wrong, and each one silently produces a
worthless answer rather than an error.

- **The runner is `harness/run_po_spec_eval.py`, NOT `harness/run_po_eval.py`.** This task's answer
  is a tree of files, not one response string, so the general runner has no assembly for it: it
  exits 1 with `ValueError: No runner assembly registered for task 'po-held-007-feature-spec'`
  (`run_po_eval.py:161`), which the task's own `instruction.md` (line 73, under "Harness assembly")
  states is by design. The dedicated runner serves this one task only, so it **rejects `--suite` and
  `--task`** (exit 2, `unrecognized arguments`). Do not add them back.
- **`--temperature 0` must be on the command line.** The runner's `--temperature` and `--top-p`
  default to `None`, which sends nothing and lets the server sample. Q2's whole falsification test
  is "identical output means the adapter is inert" — under sampling the two arms differ no matter
  what the adapter does, so Q2 would pass automatically and prove nothing. The 2026-08-24 run that
  produced 50/51 did pin it; its receipts read
  `"gen_params_sent": {"temperature": 0.0, "max_tokens": 16384}`. Check that line in every
  `config.json` before believing any result below.
- **Receipts go where `--out` says, and nowhere else.** Setting `PO_EVAL_OUTPUT_DIR` on the command
  line does nothing: the runner sets that variable itself, per rep, when it calls the grader
  (`run_po_spec_eval.py:312`). Use `--out`; without it results land in
  `fleet-evals/runs/po-heldout-spec/<utc-stamp>-<model>/`.

With `--out DIR`, each rep's receipts are at
`DIR/po-held-007-feature-spec/rep<N>/` — `grade.txt` (the pytest output), `config.json` (what was
actually sent), `response.txt`, and the generated `features/` tree. **Read `grade.txt`, never a
summary line from the terminal.**

## Phase 2: Q2 — is the adapter actually DOING anything?

Two arms, same prompt, same server, greedy (`--temperature 0`, pinned in the command below).
**This is the question upstream has not answered.**

```bash
cd ~/Projects/appmilla_github/fleet-evals
for M in gemma4-base po-v5; do
  python3 harness/run_po_spec_eval.py --model "$M" --endpoint http://127.0.0.1:8010/v1 \
    --temperature 0 --rep 1 --grade \
    --out $HOME/fine-tuning/output/vllm-q2-$M 2>&1 | tail -5
done

# the comparison, from the files — not from the terminal.
# A MISSING FILE IS A FAILURE, never a blank line: an empty read here would look like "no difference".
for M in gemma4-base po-v5; do
  R=$HOME/fine-tuning/output/vllm-q2-$M/po-held-007-feature-spec/rep1
  [ -s "$R/response.txt" ] || { echo "FAIL-Q2: no response.txt for $M at $R — the arm did not run"; continue; }
  python3 -c "import json,sys;print('$M temp sent:', json.load(open('$R/config.json'))['gen_params_sent'])"
  echo "$M $(wc -c < "$R/response.txt") chars  sha256 $(sha256sum "$R/response.txt" | cut -c1-16)"
done
```

**▶ GATE Q2:** the two arms must **differ** — different byte counts and different hashes from the
two `response.txt` files above. Identical output = the adapter is inert (#39815 alive) — record it
and stop; Q3 is then meaningless. If either `config.json` does not show `temperature: 0.0`, the
comparison is void: fix the command and re-run.

## Phase 3: Q3 — parity with the merged seat

All three pre-registered reps, greedy, into one run directory.

```bash
cd ~/Projects/appmilla_github/fleet-evals
python3 harness/run_po_spec_eval.py --model po-v5 --endpoint http://127.0.0.1:8010/v1 \
  --temperature 0 --grade --out $HOME/fine-tuning/output/vllm-q3 2>&1 | tail -20

# read the grades from the files, one line per rep.
# A MISSING grade.txt IS A FAILURE, never a blank line.
for N in 1 2 3; do
  G=$HOME/fine-tuning/output/vllm-q3/po-held-007-feature-spec/rep$N/grade.txt
  [ -s "$G" ] || { echo "rep$N: FAIL-Q3 no grade.txt at $G — the rep did not run or was not graded"; continue; }
  LINE=$(grep -Eo '[0-9]+ (passed|failed)(, [0-9]+ (passed|failed))*' "$G" | tail -1)
  [ -n "$LINE" ] && echo "rep$N: $LINE" \
                 || { echo "rep$N: FAIL-Q3 grade.txt has no pytest summary line — last 5 lines:"; tail -5 "$G"; }
done
```

Reps are frozen at **1..3**. The harness refuses `--rep 4`; adding reps until the number improves is
exam-shopping, and it was already tried and refused on 2026-08-24.

**▶ GATE Q3:** **17/17 on each of the three reps** = parity, adapter serving proven unpatched.
15/17 → check the snapshot pin FIRST (see PINS), not the adapter. **A single 16/17 rep is a repeat,
not a new regression:** the 2026-08-24 run scored 17/17 · 17/17 · **16/17** (50/51), the one failure
being `test_gate_po_held_007.py:191`, a spec-content slip where the summary's Integration section
omitted the `features/{slug}/{slug}_summary.md` path. Compare against that, not against a clean
sheet.

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
