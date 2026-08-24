# Runbook: Runtime LoRA adapter serving on GB10 — vLLM v0.27.1, UNPATCHED

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
vLLM image        vllm/vllm-openai:v0.27.1-aarch64-cu129   (released 2026-08-11)
                  WHY NOT cu130-nightly: ABANDONED — last built 2026-04-23 while cu129 ships
                  daily. The `cu130` name reads as newer than `cu129` and is not. Running it
                  cost us a wrong upstream issue (vllm#53470, closed not-planned).
base snapshot     unsloth/gemma-4-26b-a4b-it @ 60941ad6341d0b7af91277ff25c4175f08b56819
                  WHY THIS EXACT SNAPSHOT: it is the one the adapter was TRAINED on. Serving
                  d722512f instead scored 15/17; pinning the trained-on snapshot scored 17/17.
                  A snapshot mismatch looks exactly like a bad adapter.
adapter           ~/fine-tuning/output/po-gemma4-v5/lora-adapter-vllm   (r=16, ~1.9 GB)
seat dials        --max-model-len 32768 --max-num-seqs 4 --gpu-memory-utilization 0.62
                  --no-enable-prefix-caching --limit-mm-per-prompt '{"image":0}'
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

**Q2 is the one with no upstream answer.** Do not infer it from Q1 passing.

**Known non-defect:** tasks 004/005 diverge on **template, not adapter** — merged (GGUF template,
`--reasoning auto`) emits `<think>…`; vLLM+adapter (HF `chat_template.jinja`, no reasoning parser)
emits a tool call and stops. Do NOT read that as an adapter regression.

---

## Phase 0: Recon (read-only, advisory — degrade gracefully if offline)

```bash
HUB=https://hub.docker.com/v2/repositories/vllm/vllm-openai
PINNED_TAG=v0.27.1-aarch64-cu129; PINNED_VER=v0.27.1
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
abandoned; a **version pin** with an old build date is correct by design.

## Phase 0.5: Pre-flight (checks only — halts)

```bash
docker image inspect vllm/vllm-openai:v0.27.1-aarch64-cu129 >/dev/null && echo PASS-image || echo FAIL-image
SNAP=$HOME/.cache/huggingface/hub/models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819
[ -d "$SNAP" ] && echo PASS-snapshot || echo FAIL-snapshot
[ -f "$HOME/fine-tuning/output/po-gemma4-v5/lora-adapter-vllm/adapter_model.safetensors" ] \
  && echo PASS-adapter || echo FAIL-adapter
docker exec forge-prod forge --config /var/forge/forge.yaml status 2>/dev/null \
  | grep -qE 'RUNNING|PAUSED|QUEUED' && echo "FAIL-estate: a build is non-terminal — DO NOT PROCEED" \
                                     || echo PASS-estate
```

**▶ GATE:** all PASS, or stop. `FAIL-estate` is absolute — the factory owns the GPU.

## Phase 1: Serve UNPATCHED

**The point of this phase is what is NOT here.** The superseded spike mounted three patched
files; this run mounts **none**. If any is needed again, Q1 is answered NO.

```bash
SNAP=/hf/hub/models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819
curl -sS -m 30 http://127.0.0.1:9000/unload >/dev/null 2>&1     # free the seats (reload on demand)
until [ "$(free -g | awk '/Mem:/{print $7}')" -ge 90 ]; do sleep 5; done
docker rm -f vllm-lora >/dev/null 2>&1
docker run -d --rm --name vllm-lora --gpus all --ipc=host -p 8010:8000 \
  -v "$HOME/.cache/huggingface":/hf:ro \
  -v "$HOME/fine-tuning/output/po-gemma4-v5/lora-adapter-vllm":/adapter:ro \
  vllm/vllm-openai:v0.27.1-aarch64-cu129 \
  --model "$SNAP" --served-model-name gemma4-base \
  --enable-lora --max-lora-rank 16 --lora-modules po-v5=/adapter \
  --max-model-len 32768 --max-num-seqs 4 --no-enable-prefix-caching \
  --gpu-memory-utilization 0.62 --limit-mm-per-prompt '{"image":0}'
```

**▶ GATE Q1** — serves, and **both** model ids are advertised:

```bash
for i in $(seq 1 150); do curl -sf -m 5 http://127.0.0.1:8010/v1/models >/dev/null && break; sleep 10; done
curl -s http://127.0.0.1:8010/v1/models | jq -r '.data[].id' | sort | tee /tmp/vllm-ids.txt
grep -q '^gemma4-base$' /tmp/vllm-ids.txt && grep -q '^po-v5$' /tmp/vllm-ids.txt \
  && echo "PASS-Q1 unpatched serve + adapter registered" || echo "FAIL-Q1"
docker logs vllm-lora 2>&1 | grep -i 'get_expert_mapping' && echo "FAIL-Q1: expert-mapping error" || true
```

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

Record the outcome in `RESULTS-*`, including **what was NOT proved**.
