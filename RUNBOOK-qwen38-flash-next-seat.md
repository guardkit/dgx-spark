# Runbook: Qwen3.8-Flash-Next on a single DGX Spark

**Purpose:** serve Qwen3.8-Flash-Next on a single DGX Spark with an OpenAI-compatible API for chat, coding, tool use and other applications. This runbook stages the model on `spark-fcf6`, validates serving performance and stability, and provides a repeatable start/stop procedure.
**Machine:** `spark-fcf6` (DGX Spark / GB10, 128 GB unified memory).
**Kind:** additive overlay on the existing local fleet. Phase 1 asserts that state before displacement.
**Status:** researched and artifact-pinned on 2026-09-08; **not executed on a Spark**. Throughput and memory gates below are proposed acceptance thresholds, not local measurements.
**Predecessors:** the Spark's local llama-swap fleet is working; no two-box DeepSeek or other dedicated seat is active on this machine. A LiteLLM gateway is optional (Appendix B).
**Execution results:** `RESULTS-qwen38-flash-next-seat-<run-id>.md`, written once at final disposition, with the drift report and gate receipts. Do not manufacture a results file from this research.
**Expected duration:** allow 1–3 hours for initial image/checkpoint transfer, 10–30 minutes for startup, and 30–60 minutes for gates.
**Research:** [recipe comparison](./qwen38-flash-next-single-spark-research-2026-09-08.md). **Method:** [runbook conventions](./RUNBOOK-CONVENTIONS.md).

The executable lane is **travelinlance Hybrid Sharp v2, patched vLLM, full PLE table on local NVMe, GPU gather, BF16 KV, prefix cache, MTP off**. Its image is the one identified in the shared Spark Arena entry. Tony's faster NVIDIA/MTP recipe disables prefix caching and is a separate future lane. Do not mix its flags, patches or checkpoint with this one.

**Displacement:** the Spark's existing model fleet is unavailable while this dedicated seat stands. The procedure snapshots and restores that fleet, including its tutor, embedding and speech services.

```text
Applications ── OpenAI-compatible API ──▶ spark-fcf6 :8888/v1
                                              patched vLLM, TP=1
                                              local NVMe PLE table
                                              native context 262144

Optional: applications ── existing LiteLLM gateway ──▶ same model endpoint

Spark: llama-swap + model keepalives STOPPED while Qwen occupies the machine
```

```text
Execution modes:
  fresh  — run phases in order, then restore or retain the isolated seat as recorded
  re-run — inspect existing evidence/container first; reuse exact staged artifacts;
           never overwrite the original fleet/config snapshots
  update — recon records drift; change pins through a reviewed revision before running
```

## PINS (v1.1, 2026-09-09; one source of truth)

Run in Bash on **spark-fcf6**, from this repository. Keep this shell for the Spark phases. A different target machine requires an explicit runbook revision. Environment paths and a new run ID identify this execution; they are not floating software versions.

```bash
set -euo pipefail
set -a
TARGET_HOST=spark-fcf6
RECIPE_REPO=https://github.com/lancelind/qwen3.8-Flash-DGX
RECIPE_REV=4e1b246aa141e04bd45c20bd1334512988c3770b
IMAGE=ghcr.io/lancelind/qwen38-flash-dgx@sha256:62a77b7c2806385cd23aeb7f6c4979b29f1b0db941bdc0f4791da90aa15f5bb9
IMAGE_SOURCE_REV=a35c3cc2935dff63eea8a664509a5931b4b82ea2
MODEL_REPO=travelinlance/Qwen3.8-Flash-Next-RadixArk-NVFP4-Hybrid-Sharp
MODEL_REV=1f2ba8b30e34097058610938864b1991cfffa24b
CONFIG_SHA=e765305daba0951974308f4d32c075b52a6a45974730d273f2216718a994d624
TEMPLATE_SHA=d1f22a89eac3609dcfaa7b471b1f7d23bee2f084d275d26f4f8231d1d7908f4e
TOKENIZER_CONFIG_SHA=4fe0a03ee26eff55fae0b92cc12e2d946563333eb9dce7322ba783b3dfb7e7a7
GENERATION_CONFIG_SHA=e70c136c1b78ddc1fb0905bac8e733a4dc448d4f852a5dd75143fffc70be550e
INDEX_SHA=1c8b8da8ea5c789e23ca58639f18bbb2431ca340b1d62d77f45d974aa8870ecc
SHARD_COUNT=206
SERVED_ID=qwen3.8-flash-next
GATEWAY_ROW=qwen3.8-flash-next        # optional gateway alias, Appendix B
SEAT_PORT=8888
CONTAINER=qwen38-seat
CTX=262144
SEQS=8
CHUNK=8192
GMU=0.75
KV_TYPE=auto                         # BF16 in this image/config, assert in startup log
TOOL_PARSER=qwen3_coder
REASONING_PARSER=qwen3
COMPILATION_CONFIG='{"cudagraph_mode":"PIECEWISE","splitting_ops":["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen3_8_flash_next_ple_short_conv","vllm::qwen3_8_flash_next_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::sparse_attn_indexer"]}'
DISK_MIN_GIB=200                    # first staging: model + image/extraction margin
PRELAUNCH_AVAILABLE_GIB=105
MEM_USED_MAX_GIB=109                # effective used = MemTotal - MemAvailable
MEM_AVAILABLE_MIN_GIB=12
COLD_START_MAX_S=1800
ROUTE_TIMEOUT_S=900
DECODE_FLOOR=18                     # diagnostic floor for THIS no-MTP lane
WARM_RATIO_MAX=0.5                  # warm TTFT <= half cold TTFT, isolated engine
LONG_STREAM_MIN_S=90
STREAM_MAX_TOKENS=4096
CACHE_TEST_LENGTHS='20000 64000 100000 120000 250000'
REPO_DIR=$PWD
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
RUN_DIR=$HOME/qwen38-seat-runs/$RUN_ID
MODEL_DIR=$HOME/models/qwen38-hybrid-sharp/$MODEL_REV
set +a
```

The image manifest and ARM64 child were verified during research. Its **build-source revision** differs from the later **recipe-document revision** above. The HF revision also pins the Sharp/froggeric v22.1 template. `kv-cache-dtype auto` is intentional: this lane does not adopt Tony's FP8-KV patch. No YaRN, HashK compression, PLE removal, speculative configuration, indexer edits or runtime package upgrades.

## Phase 0: Recon (read-only, advisory)

Compare current heads/revisions with PINS; record newer issues without changing the procedure. Fixed sources:

- [Lance recipe repository](https://github.com/lancelind/qwen3.8-Flash-DGX), [model revision metadata](https://huggingface.co/api/models/travelinlance/Qwen3.8-Flash-Next-RadixArk-NVFP4-Hybrid-Sharp).
- [NVIDIA thread 381228](https://forums.developer.nvidia.com/t/qwen3-8-flash-next/381228), [single-Spark SGLang thread 381859](https://forums.developer.nvidia.com/t/single-dgx-spark-qwen-3-8-flash-next-at-43tok-sec-in-coding/381859), [recipe comparison 382522](https://forums.developer.nvidia.com/t/which-single-spark-qwen3-8-flash-next-thread-is-the-best/382522).
- [Tony's repository](https://github.com/tonyd2wild/Qwen3.8-Flash-Next-NVFP4-DGX-Spark), [prefix-cache issue #54173](https://github.com/vllm-project/vllm/issues/54173), [blazux implementation notes](https://github.com/blazux/qwen3.8-Flash-DGX).
- [Shared Arena entry](https://spark-arena.com/benchmark/7ec7eaf7-a10c-403d-be52-c44c0fc64539). Distinguish the embedded recipe, workload row and concurrency from the headline.

Produce `DRIFT-qwen38-flash-next-<run-id>.md` in the conventions format at final disposition. Unreachable research sources are recorded as skipped; they do not invalidate cached immutable artifacts. Failure to obtain a required pinned artifact does halt staging.

## Phase 0.5: Pre-flight (read-only)

```bash
test "$(hostname -s)" = "$TARGET_HOST"
test "$(uname -m)" = aarch64
test -f "$REPO_DIR/scripts/qwen38-seat-probe.py"
sudo -n true
docker info >/dev/null
systemctl --user is-active --quiet llama-swap
test "$(systemctl --user show llama-swap -p LoadState --value)" != masked
test -z "$(ss -H -ltn "sport = :$SEAT_PORT")"
test -z "$(docker ps -aq --filter "name=^/${CONTAINER}$")"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
docker ps --format '{{.Names}} {{.Image}}'
systemctl --user list-timers --all --no-pager
python3 - <<'PY'
import os, shutil
assert shutil.disk_usage(os.path.expanduser('~')).free >= int(os.environ['DISK_MIN_GIB']) * 2**30
print('PASS first-stage disk margin')
PY
```

Inspect `findmnt -T "$HOME/models"` (or its existing parent) and `lsblk -o NAME,TYPE,TRAN,ROTA,MOUNTPOINTS`: **model storage must be local NVMe**, not NFS/SMB or remote storage. Inventory all GPU consumers and scheduled launchers. A DeepSeek, qwen35-122b, another vLLM, training job or unknown scheduled GPU job is a failed exclusivity precondition; resolve its ownership before proceeding. Do not stop unidentified workloads. Record driver, OS, Docker/runtime versions, power/clock settings and free memory; keep those settings fixed during validation.

**Re-run:** if the exact seat already exists, compare its image, command, model mount and original run directory first, then resume at Phase 5 with the original snapshots. If it differs, finish its teardown before starting a fresh run. The fresh preflight deliberately refuses to delete/recreate an existing container.

## Phase 1: Base precondition and recovery snapshot

**Spark.** A successful HTTP response is insufficient: require a nonempty model catalog from the base fleet, and retain its exact IDs and configuration hashes for restoration.

```bash
umask 077
mkdir -p "$RUN_DIR"
curl -fsS --max-time 10 localhost:9000/v1/models > "$RUN_DIR/fleet-before.json"
python3 - "$RUN_DIR/fleet-before.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))['data']
assert d and all(x.get('id') for x in d)
print('PASS base fleet catalog')
PY
systemctl --user is-active llama-swap-keepalive.timer > "$RUN_DIR/keepalive-before.txt" || true
systemctl --user cat llama-swap > "$RUN_DIR/llama-swap-unit-before.txt"
sha256sum /opt/llama-swap/config/config.yaml > "$RUN_DIR/fleet-config-before.sha256"
free -b > "$RUN_DIR/memory-before.txt"
git rev-parse HEAD > "$RUN_DIR/runbook-repo-commit.txt"
sha256sum "$REPO_DIR/scripts/qwen38-seat-probe.py" "$REPO_DIR/RUNBOOK-qwen38-flash-next-seat.md" > "$RUN_DIR/procedure.sha256"
```

**Gate:** the local catalog and recovery snapshots exist, and clients of the fleet have finished their active work before displacement. The Spark's green base is required even though it is about to be drained.

## Phase 2: Stage immutable artifacts (fleet still serving)

Pull without GPU access and assert architecture/provenance. Reuse the image only if these assertions pass.

```bash
docker pull --platform linux/arm64 "$IMAGE"
docker image inspect "$IMAGE" > "$RUN_DIR/image.json"
python3 - "$RUN_DIR/image.json" <<'PY'
import json, os, sys
d = json.load(open(sys.argv[1]))[0]
assert d['Architecture'] == 'arm64'
assert os.environ['IMAGE'] in d['RepoDigests']
assert d['Config']['Labels']['org.opencontainers.image.revision'] == os.environ['IMAGE_SOURCE_REV']
print('PASS pinned ARM64 image')
PY
mkdir -p "$MODEL_DIR"
docker run --rm --network host --entrypoint python3 \
  -v "$MODEL_DIR:/model" "$IMAGE" -c \
  'from huggingface_hub import snapshot_download; import sys; snapshot_download(repo_id=sys.argv[1],revision=sys.argv[2],local_dir="/model")' \
  "$MODEL_REPO" "$MODEL_REV"
docker run --rm --network host --entrypoint python3 -i \
  -v "$MODEL_DIR:/model:ro" -v "$RUN_DIR:/evidence" "$IMAGE" - "$MODEL_REPO" "$MODEL_REV" <<'PY'
import hashlib, json, sys
from pathlib import Path
from huggingface_hub import HfApi
p = Path('/model')
names = set(json.loads((p/'model.safetensors.index.json').read_text())['weight_map'].values())
files = {f.rfilename: f for f in HfApi().model_info(sys.argv[1], revision=sys.argv[2], files_metadata=True).siblings}
manifest = {}
for name in sorted(names):
    f = files[name]
    assert f.lfs and f.lfs.sha256, ('missing upstream LFS digest', name)
    digest = hashlib.sha256()
    with (p/name).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    assert digest.hexdigest() == f.lfs.sha256, ('weight checksum mismatch', name)
    manifest[name] = f.lfs.sha256
Path('/evidence/weights.sha256.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('PASS every indexed weight shard matches pinned upstream SHA-256')
PY
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
p = Path(os.environ['MODEL_DIR'])
checks = {'config.json':'CONFIG_SHA', 'chat_template.jinja':'TEMPLATE_SHA',
          'tokenizer_config.json':'TOKENIZER_CONFIG_SHA', 'generation_config.json':'GENERATION_CONFIG_SHA',
          'model.safetensors.index.json':'INDEX_SHA'}
for name, env in checks.items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest() == os.environ[env], name
index = json.loads((p/'model.safetensors.index.json').read_text())
shards = set(index['weight_map'].values())
assert len(shards) == int(os.environ['SHARD_COUNT'])
assert all((p/f).is_file() and (p/f).stat().st_size > 0 for f in shards)
c = json.loads((p/'config.json').read_text())['text_config']
assert c['max_position_embeddings'] == int(os.environ['CTX'])
assert (c['indexer_budget'], c['indexer_compress_ratio']) == (2048, 4)
assert c['ple_embedding_dtype'] == 'float8_e4m3fn'
assert 'ngram' in ' '.join(index['weight_map'])
assert json.loads((p/'tokenizer_config.json').read_text())['chat_template'] == (p/'chat_template.jinja').read_text()
print('PASS model control files, complete indexed shard set, intact PLE configuration')
PY
```

The hash pass reads the entire checkpoint and retains a private upstream-derived manifest. On an offline re-run, compare every shard against that retained manifest instead of querying HF again; absence of either upstream hashes or the retained manifest is a failed identity gate. Never patch HF blobs, convert side layers again, or run `pip install -U` in this container. Read and retain the included model licence.

## Phase 3: Drain Node B and protect the memory envelope

Stop any additional **identified** fleet keepalive/loader timers from Phase 0.5, recording their prior state. The canonical units are below. A runtime mask prevents a dependency such as LiteLLM's `Wants=llama-swap` from reviving the fleet during this attended trial. If the mask cannot take effect, halt before launching.

```bash
for unit in llama-swap-keepalive.timer llama-swap-keepalive.service; do
  if test "$(systemctl --user show "$unit" -p LoadState --value)" != not-found; then
    systemctl --user stop "$unit"
  fi
done
systemctl --user stop llama-swap.service
systemctl --user mask --runtime llama-swap.service
test "$(systemctl --user show llama-swap -p LoadState --value)" = masked
! systemctl --user is-active --quiet llama-swap
! pgrep -x llama-server
python3 - <<'PY'
import os
m = {k:int(v.split()[0]) for k,v in (s.split(':',1) for s in open('/proc/meminfo'))}
assert m['MemAvailable']/2**20 >= float(os.environ['PRELAUNCH_AVAILABLE_GIB'])
print('PASS drained memory headroom')
PY
systemd-run --user --unit=qwen38-memory-guard --collect \
  /usr/bin/python3 "$REPO_DIR/scripts/qwen38-seat-probe.py" memory \
  --container "$CONTAINER" --evidence "$RUN_DIR" \
  --min-available-gib "$MEM_AVAILABLE_MIN_GIB" --max-used-gib "$MEM_USED_MAX_GIB"
systemctl --user is-active --quiet qwen38-memory-guard
```

The guard samples total unified memory and swap counters every two seconds, keeps JSONL, and stops this seat on a breach. It permits pre-existing inactive swap occupancy but **no new swap growth or swap I/O**. Its limits apply through load, probes and trial work. Do not use `nvidia-smi` memory/utilisation as the sole GB10 residency gate. Do not drop host caches during serving: this recipe relies on the page cache.

## Phase 4: Launch the seat

Use the upstream v2 launch configuration with only estate port/paths changed. Explicit local `/model` and offline flags avoid the PLE loader's repo-ID/local-path failure. No restart policy is enabled: after a reboot, the normal fleet can return without competing with an automatically restarted seat. Persistent service deployment would need its own ownership and startup-order change.

```bash
docker run -d --name "$CONTAINER" --restart no --gpus all \
  --network host --ipc=host --shm-size 16g \
  -v "$MODEL_DIR:/model:ro" -v "$RUN_DIR/cache:/root/.cache" \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e VLLM_PLE_MMAP=1 -e VLLM_PLE_GPU_GATHER=1 -e VLLM_PLE_DECODE_WARM=1 \
  -e VLLM_PLE_MMAP_WORKERS=32 -e VLLM_PLE_MMAP_PREWARM=0 \
  -e VLLM_QSA_EXACT_TOPK=1 -e VLLM_USE_FLASHINFER_SAMPLER=1 \
  -e VLLM_FP8_HYBRID=1 -e VLLM_USE_DEEP_GEMM=0 \
  --entrypoint "" "$IMAGE" \
  vllm serve /model --served-model-name "$SERVED_ID" \
  --host 0.0.0.0 --port "$SEAT_PORT" --load-format safetensors \
  --max-model-len "$CTX" --max-num-seqs "$SEQS" --gpu-memory-utilization "$GMU" \
  --enable-prefix-caching --enable-chunked-prefill --max-num-batched-tokens "$CHUNK" \
  --compilation-config "$COMPILATION_CONFIG" \
  --no-enable-flashinfer-autotune --kv-cache-dtype "$KV_TYPE" \
  --enable-auto-tool-choice --tool-call-parser "$TOOL_PARSER" --reasoning-parser "$REASONING_PARSER"

deadline=$((SECONDS + COLD_START_MAX_S))
until curl -fsS --max-time 3 "localhost:$SEAT_PORT/health" >/dev/null; do
  test "$SECONDS" -lt "$deadline"
  test ! -f "$RUN_DIR/memory.failed"
  systemctl --user is-active --quiet qwen38-memory-guard
  test "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" = true
  sleep 5
done
docker logs "$CONTAINER" > "$RUN_DIR/startup.log" 2>&1
docker inspect "$CONTAINER" > "$RUN_DIR/container.json"
docker exec "$CONTAINER" python3 -c \
  'import torch,vllm; assert torch.cuda.is_available(); assert torch.cuda.get_device_capability()==(12,1); print(vllm.__version__,torch.__version__,torch.version.cuda)' \
  > "$RUN_DIR/runtime-versions.txt"
curl -fsS "localhost:$SEAT_PORT/v1/models" > "$RUN_DIR/seat-models.json"
python3 - "$RUN_DIR/seat-models.json" <<'PY'
import json, os, sys
rows = [x for x in json.load(open(sys.argv[1]))['data'] if x['id']==os.environ['SERVED_ID']]
assert len(rows)==1 and rows[0]['max_model_len']==int(os.environ['CTX'])
print('PASS serving ID and native context')
PY
```

**Gate:** log confirms successful GPU PLE gather (including its startup self-test), hybrid dispatch, BF16 KV, prefix caching and a KV pool sufficient for one native-context request. Record the actual cache capacity; do not infer long-request capacity from `SEQS`. Check for ignored tensors, fallback kernels, non-finite output or tracebacks; unexplained load/runtime errors halt the run. Retain exact log evidence for each assertion. Missing observability is unresolved, not PASS.

Thinking-off is a **request setting**, because this pinned Sharp template defaults to thinking on. The probes send `chat_template_kwargs: {enable_thinking: false}` explicitly. Clients requesting thinking-off must send/preserve that setting. These probes validate the thinking-off profile; validate other reasoning settings separately for the intended workload. Do not add a newer vLLM server flag without verifying that this older image supports it.

## Phase 5: Serving gates on the isolated engine

The helper uses only Python's standard library. Its tool calls are synthetic; it never runs model-suggested commands. It verifies structured SSE tool calls, JSON arguments, tool-result continuation, unassisted JSON output, and absence of reasoning content/tokens. All failures exit nonzero and keep diagnostic receipts.

```bash
python3 scripts/qwen38-seat-probe.py protocols --base-url "http://localhost:$SEAT_PORT" \
  --model "$SERVED_ID" --evidence "$RUN_DIR/direct"
for length in $CACHE_TEST_LENGTHS; do
  python3 scripts/qwen38-seat-probe.py cache --base-url "http://localhost:$SEAT_PORT" \
    --model "$SERVED_ID" --prompt-tokens "$length" --warm-ratio "$WARM_RATIO_MAX" \
    --evidence "$RUN_DIR/direct"
  test ! -f "$RUN_DIR/memory.failed"
done
python3 scripts/qwen38-seat-probe.py decode --base-url "http://localhost:$SEAT_PORT" \
  --model "$SERVED_ID" --decode-floor "$DECODE_FLOOR" --max-tokens "$STREAM_MAX_TOKENS" \
  --min-seconds "$LONG_STREAM_MIN_S" --evidence "$RUN_DIR/direct"
systemctl --user is-active --quiet qwen38-memory-guard
test ! -f "$RUN_DIR/memory.failed"
! systemctl --user is-active --quiet llama-swap
```

Cache probes tokenize the actual rendered request, reset the isolated engine's prefix cache, then compare a cold request with its repeat, a changed question on the same prefix, and an unrelated prefix. Expected answers are asserted, not judged by another model. The tests cover a range of prompt lengths through 250K, exercising the native window beyond the historical corruption boundary. **Do not run cache-reset probes once clients use the seat.** A needle smoke does not establish general long-context reasoning quality.

The decode receipt reports native usage tokens, time to first content/tool delta, approximate decode rate `(completion_tokens - 1)/(last_delta - first_delta)` and whole-request rate separately. Stream chunks are not tokens. Do not label `completion_tokens / whole_request_seconds` as decode speed. This no-MTP lane should not inherit the older runbook's 35 tok/s floor. A naturally short reply cannot prove the 90-second timeout gate; record it as inconclusive and exercise a suitable real long generation before proceeding. No `ignore_eos` counting benchmark.

## Phase 6: Decision gate

| Gate | Required evidence | Result |
|---|---|---|
| Base and displacement | original local catalog and configuration; private recovery snapshot | NOT RUN |
| Artifact identity | image digest/ARM64/source label; HF revision/control hashes; indexed shards | NOT RUN |
| Exclusivity | Spark fleet and loader timers stopped; mask effective; no other GPU seat | NOT RUN |
| Startup | health within pinned window; GPU/SM121; successful PLE/hybrid load; BF16 KV | NOT RUN |
| Context/cache | measured token lengths through 250K; correct cold/warm/changed/unrelated answers; warm ratio | NOT RUN |
| Protocol | auto/required/named tool choice; valid arguments and continuation; JSON; thinking off | NOT RUN |
| Timing | native-usage decode above floor; >90-second direct stream | NOT RUN |
| Memory | every phase inside envelope; no new swap or swap I/O; guard active | NOT RUN |
| Optional gateway (Appendix B) | exact row; client access; tools/long stream; existing routes preserved; spend record if persistence configured | NOT RUN / N/A |
| Recovery | restored catalog/config/timers, or retained isolated seat explicitly recorded | NOT RUN |

Phases 1–5 PASS = **serving-ready** at the direct API. Run Appendix B before completing this table if gateway access is part of the deployment; otherwise mark that row N/A. A failed required gate stops dependent work and invokes teardown; preserve logs rather than swapping recipes or raising memory utilisation.

## Phase 7: Cleanup, retention and results

To retain the server after validation, record that disposition, keep the memory guard and fleet mask active, and keep clients within the measured workload. To end the model session and restore the fleet, execute Appendix A. The container will not auto-restart after reboot. No unattended production service is installed by this runbook.

Write RESULTS once at final disposition, including on a terminal failed run: procedure commit/hashes, all artifact pins, hardware/runtime versions, recon drift, raw receipt locations, every measured gate, failures/retries, min available/max used memory, swap counters, actual KV pool, client/route evidence where applicable, and restored/retained state. Research numbers must remain labelled external. Scrub keys/private prompts from any evidence committed to this public repository; keep private backups in the run directory.

## Appendix A: Teardown / rollback

1. **Clients/gateway:** stop new requests and wait for active ones to finish. If Appendix B added a gateway row or client key grant, remove only this session's additions. Restore the private config backup only if no intervening edits occurred; otherwise apply the inverse row change. Restart the gateway if changed and verify its original catalog and representative existing routes.
2. **Spark:** stop the model container before releasing the fleet mask. Preserve its logs. Run the following in the original pinned shell/run context:

```bash
docker logs "$CONTAINER" > "$RUN_DIR/final-seat.log" 2>&1 || true
docker stop --time 30 "$CONTAINER" || true
test "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" = false
docker rm "$CONTAINER"
systemctl --user stop qwen38-memory-guard || true
systemctl --user unmask --runtime llama-swap.service
systemctl --user daemon-reload
systemctl --user start llama-swap.service
if grep -qx active "$RUN_DIR/keepalive-before.txt"; then
  systemctl --user start llama-swap-keepalive.timer
fi
sha256sum -c "$RUN_DIR/fleet-config-before.sha256"
deadline=$((SECONDS + COLD_START_MAX_S))
until curl -fsS --max-time 5 localhost:9000/v1/models > "$RUN_DIR/fleet-after.json"; do
  test "$SECONDS" -lt "$deadline"
  sleep 5
done
python3 - "$RUN_DIR" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1])
def ids(name): return sorted(x['id'] for x in json.loads((p/name).read_text())['data'])
assert ids('fleet-before.json') == ids('fleet-after.json')
print('PASS restored fleet catalog')
PY
```

3. Restore every other timer/loader identified in preflight to its saved state; perform the tutor/embedding/speech health probes appropriate to the original snapshot. A matching catalog alone does not prove those models can load. Check memory after revival and verify the model container is no longer running. Cached weights and image stay on disk for reuse; deletion is not necessary for rollback.

**Failure before container creation:** skip container commands only after `docker inspect` establishes that it does not exist; still stop this run's memory guard and restore any units this run changed. If the fleet was already masked before this run, preflight should have halted: never unmask another operation's isolation. If restoration fails, RESULTS must say restoration failed rather than declaring teardown complete.


## Appendix B: Optional LiteLLM gateway access

The direct API is `http://spark-fcf6.local:8888/v1`, model `qwen3.8-flash-next`. Clients may connect directly, or use an existing LiteLLM gateway for model aliases, keys and accounting. The Dell's existing dashboard/Postgres can record calls to this remote model; installing another database on the Spark is not required. An existing gateway without persistence can route requests but does not provide stored spend records.

After Phase 5 passes, record the selected gateway host/address, its current model catalog and a private config backup. Test Spark connectivity from that host and from the actual client environment. Resolve and record its LAN address if mDNS is unavailable. No tensor-parallel networking is needed.

Add exactly one explicit row to the existing `model_list`, before catch-all mappings. This fragment uses `GATEWAY_ROW`, `SERVED_ID`, `SEAT_PORT` and `ROUTE_TIMEOUT_S` from PINS. An application may choose its own gateway alias without changing the model server.

```yaml
- model_name: qwen3.8-flash-next
  litellm_params:
    model: openai/qwen3.8-flash-next
    api_base: http://spark-fcf6.local:8888/v1
    api_key: local-unused
    timeout: 900
```

Validate using the gateway's existing YAML parser. Require exactly one new row and assert that removing it yields the original parsed configuration. Preserve existing model routes and settings, including `fallbacks: []` and `context_window_fallbacks: []`; an unavailable Qwen endpoint must fail visibly. Add the alias to the intended virtual key's allowlist when needed, preserving its existing grants. Use client virtual keys for inference, not the master key.

Restart only the selected gateway through its existing service. Reassert the Spark's fleet remains masked/inactive and the memory guard is active. If the gateway is on the Spark, check its unit dependencies before restarting: `Wants=llama-swap` is the known fleet-revival trap. Do not replace its whole config with the repository's example file; that file includes routes specific to another host.

From the real client environment, run the helper's `protocols` and `decode` modes against the selected gateway URL, using its alias and the pinned thresholds from Phase 5. Set `QWEN38_API_KEY` from the client's existing secret environment if authentication is enabled. Do not run the cache-reset probe through the gateway; those are engine administration routes.

**Gate:** the client can call the exact alias; tool choice, JSON, thinking-off requests and a >90-second stream survive the full path; original routes still work. If that gateway has spend persistence, locate the probe requests in its database. Record the gateway and results, or mark this appendix N/A for direct-only access.
