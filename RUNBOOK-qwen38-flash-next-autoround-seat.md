# Runbook: Qwen3.8-Flash-Next AutoRound on a single DGX Spark

**Purpose:** serve Qwen3.8-Flash-Next on a single DGX Spark with an OpenAI-compatible API for chat, coding, tool use and other applications. This runbook stages the model on `spark-fcf6`, validates serving performance and stability, and provides a repeatable start/stop procedure.
**Machine:** `spark-fcf6` (DGX Spark / GB10, 128 GB unified memory).
**Kind:** additive overlay on the existing local fleet. Phase 1 asserts that state before displacement.
**Status:** **`22g` configuration retained on 2026-09-19 under the unchanged 120 decimal GB total-RAM ceiling**, after the host's kernel fix (`kho=off`) returned about 9.3 GiB at boot. Normal endpoint: `http://spark-fcf6.local:8888/v1`, development APIs disabled. Cache pool 708,497 tokens. Protocol, fixed-prefix 250K, growing-history to 250K and sustained-generation checks passed; peak effective used RAM was 117.09 GB, 2.91 GB under the ceiling. Steady generation is 56–59 tok/s, with a slow patch of about 40 tok/s for a few minutes after loading or after a very large prompt. Two 130K conversations stay cached together; two 250K conversations still do not. Fallbacks are `19g` (tested the same day, peak 113.90 GB) or an untested `20g`–`21g`. See [current allocation results](./RESULTS-qwen38-flash-next-kv-ceiling-20260919T090408Z.md), the [2026-09-10 allocation results](./RESULTS-qwen38-flash-next-kv-ceiling-20260910T181629Z.md), where `19g` was retained and a `20g` trial crossed 120 GB, and the [prior 12 GB validation](./RESULTS-qwen38-flash-next-autoround-seat-20260910T165917Z.md). No Factory task-quality comparison or multi-day soak test has run.
**Predecessors:** the Spark's local llama-swap fleet is working; no two-box DeepSeek or other dedicated seat is active on this machine. A LiteLLM gateway is optional (Appendix B).
**Execution results:** `RESULTS-qwen38-flash-next-autoround-seat-<run-id>.md`, written once at final disposition, with the drift report and gate receipts. Do not manufacture a results file from this research.
**Expected duration:** allow several hours for the initial source build, 116 GiB of model/table transfer and verification, then 10–30 minutes for startup and 1–2 hours for gates.
**Research:** [September 10 reassessment](./qwen38-flash-next-reassessment-2026-09-10.md), [original comparison](./qwen38-flash-next-single-spark-research-2026-09-08.md). **Reference configuration:** [Lance Hybrid Sharp runbook](./RUNBOOK-qwen38-flash-next-seat.md). **Method:** [runbook conventions](./RUNBOOK-CONVENTIONS.md).

The executable configuration is **Saren AutoRound hybrid, patched vLLM, full FP8 PLE table on local NVMe with CPU gather, BF16 KV, prefix caching, MTP=3, private 65,536-token draft vocabulary, exact QSA top-k**. All 512 main-model experts remain present, with the original ten selected per token. This is a separate checkpoint and serving stack from the Lance reference; local serving validation does not establish a task-quality advantage over that reference or the baseline coder.

The author's roughly 50–60 tok/s results use different conditions, including a remote-RAM PLE table, thinking enabled and a different top-k path. The local `12g`, `19g` and `22g` configurations have their own serving receipts; these are not reproductions of those external conditions. Exact top-k trades prefill speed for avoiding the custom kernel's reported long-context failure. The optional [Factory evaluation](./QWEN38-software-factory-evaluation.md) still needs to rank configurations by time to correctly completed tasks.

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

## PINS (v1.7, 2026-09-10; one source of truth)

Run in Bash on **spark-fcf6**, from this repository. Keep this shell for the Spark phases. A different target machine requires an explicit runbook revision. Environment paths and a new run ID identify this execution; they are not floating software versions.

```bash
set -euo pipefail
set -a
TARGET_HOST=spark-fcf6
RECIPE_REPO=https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound
RECIPE_REV=1633d4bc11701c04d7cbd633994421466d1eff1d
BASE_IMAGE=vllm/vllm-openai:qwen38-flash-next@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8
KERNEL_REV=e0ef69d4f5575dad00d34e05479eaf4c6547bace
MODEL_REPO=Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN
MODEL_REV=19f9710c8f6600a32e15fb98bc77613ee8ec369b
PLE_REPO=Saren/Qwen3.8-Flash-Next-ple-table-fp8
PLE_REV=50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14
CONFIG_SHA=f87b6d87a4ee12156dbbbb7e8d1d86be315de956e6c7956da701accdbb1f1344
TEMPLATE_SHA=c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041
TOKENIZER_CONFIG_SHA=792fa3f0cb88b111e54ef3134c873531008c4df471d108da17903426e308aa7b
GENERATION_CONFIG_SHA=6ef70d6670f24f03a9041724c7663ef26bc1e678d10f79c93fe11c192ba14b7d
INDEX_SHA=fda0a55cae7353d2d7b6029adf3ec4d3ca4751fd1e9788a084503388c07d154a
SHARD_COUNT=68
PLE_FILE_COUNT=33
SERVED_ID=qwen3.8-flash-next-autoround
GATEWAY_ROW=qwen3.8-flash-next-autoround        # optional gateway alias, Appendix B
SEAT_PORT=8888
SEAT_BIND_HOST=127.0.0.1            # validation includes development cache-reset APIs
NORMAL_BIND_HOST=0.0.0.0           # only after disabling development APIs, Appendix C
DEV_APIS=1                        # required for /reset_prefix_cache in the pinned image
CONTAINER=qwen38-autoround-seat
RUNTIME_MASK=$XDG_RUNTIME_DIR/systemd/user.control/llama-swap.service
SWAP_FILE=/swap.img                  # runtime deactivation only; preserve fstab and sysctls
CTX=262144
SEQS=8
CHUNK=8192
GMU=0.01
KV_BYTES=22g                       # owner-selected 2026-09-19 (v1.8); needs kho=off on the host; fall back to 19g, or a tested 20g/21g
MTP=3
EXACT_TOPK=1
DET_TOPK=0
DRAFT_VOCAB=/opt/llm/draft_vocab_65536.npy
PREWARM=1
LOAD_FORMAT=fastsafetensors
KV_TYPE=auto                         # BF16 in this image/config, assert in startup log
TOOL_PARSER=qwen3_xml
REASONING_PARSER=qwen3
COMPILATION_CONFIG='{"cudagraph_mode":"PIECEWISE","splitting_ops":["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen3_8_flash_next_ple_short_conv","vllm::qwen3_8_flash_next_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::sparse_attn_indexer","vllm::ple_mmap_lookup"]}'
DISK_MIN_GIB=200                    # first staging: model + PLE + image/build margin
PRELAUNCH_AVAILABLE_GIB=105
DRAIN_SETTLE_MAX_S=60               # GPU allocations can release after service stop returns
MEM_USED_MAX_BYTES=120000000000     # user-selected total effective RAM ceiling, decimal bytes
MEM_USED_MAX_GIB=$(python3 -c 'import sys; print(int(sys.argv[1])/2**30)' "$MEM_USED_MAX_BYTES")
MEM_AVAILABLE_MIN_GIB=$(python3 -c 'import sys; total=int(next(x.split()[1] for x in open("/proc/meminfo") if x.startswith("MemTotal:")))*1024; ceiling=int(sys.argv[1]); assert total>ceiling; print((total-ceiling)/2**30)' "$MEM_USED_MAX_BYTES")
COLD_START_MAX_S=1800
ROUTE_TIMEOUT_S=900
DECODE_FLOOR=30                     # proposed diagnostic floor, not a performance promise
WARM_RATIO_MAX=0.5                  # warm TTFT <= half cold TTFT, isolated engine
LONG_STREAM_MIN_S=90
STREAM_MAX_TOKENS=8192
CACHE_TEST_LENGTHS='20000 64000 94000 96000 110000 120000 250000'
REPO_DIR=$PWD
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
RUN_DIR=$HOME/qwen38-autoround-seat-runs/$RUN_ID
BUILD_DIR=$RUN_DIR/recipe
MODEL_DIR=$HOME/models/qwen38-autoround/$MODEL_REV
PLE_DIR=$HOME/models/qwen38-ple-fp8/$PLE_REV
set +a
```

The Dockerfile pins the base image and the external kernel sources/checksums. Phase 2 builds a local image, records its immutable **image ID**, and uses that ID throughout; there is no claimed prebuilt Saren image digest. A rebuild is a new build receipt, even from the same source. Preserve the built image for exact re-runs.

**Memory accounting:** the guard defines effective used RAM as `MemTotal - MemAvailable`. The operator selected **120 decimal GB** as the ceiling for the larger-pool trial. PINS converts that once to **111.758709 GiB used** and derives the matching available floor from this host's `MemTotal`: **9.930851 GiB**, with 121.689560 GiB total. The old 109 GiB used / 12 GiB available thresholds no longer constrain this profile. Keep both limits consistent; changing only one would leave the other silently enforcing a lower ceiling. Confirm units and reclaimable-cache accounting when comparing monitoring tools. The operator's multi-day observation informed the selected ceiling; these local probes do not themselves constitute a multi-day soak test.

**v1.2 change:** reduce the explicit KV pool from `20g` to `12g`, saving 7.451 GiB of requested allocation. Image, checkpoint, context, MTP, top-k environment, swap procedure and guard thresholds are unchanged. Require the engine to admit native context and all serving gates to pass; a smaller pool's actual capacity and performance are not assumed.

**v1.3 probe correction:** the first `12g` launch reached API readiness within the memory limits, then halted because the probe expected `finish_reason=tool_calls` for a named-tool request. The saved response had the correct structured call and arguments. The pinned image's serving implementation explicitly uses `stop` for named tools. The probe now accepts `stop` or `tool_calls` for that mode only; automatic/required calls still require `tool_calls`, and all structured-call, argument and continuation assertions remain. Preserve the original failed probe receipt and record the corrected helper hash before rerunning.

**v1.4 validation setup correction:** this image registers `/reset_prefix_cache` only when `VLLM_SERVER_DEV_MODE=1`. Enable those APIs for the isolated validation phase and bind the server to loopback. Cache-reset helpers must also assert the returned `success` value when present; HTTP 200 alone does not establish a reset. Before exposing the seat to network clients, restart the same serving configuration with development APIs disabled and the intended network bind address, then recheck health, protocol, memory and the client path. Preserve both container receipts. Do not expose development APIs to network clients.

**v1.5 prompt-sizing correction:** the original fixed-prefix helper destructively shortened its filler and could not recover after undershooting the 250K target. It now uses bounded binary search over the unchanged source text and requires the rendered prompt to fall within target through target+128 tokens. Preserve the original pre-inference failure and the corrected helper hash; completed earlier-length receipts remain valid.

**v1.6 evidence/content correction:** save completed raw responses before content assertions. The repeated-character heuristic now excludes bounded Python section comments made of 64–120 `=` or `-` characters; repeated text and oversized separators remain failures. A captured 8,192-token response contained ten ordinary `# ===...` separators, causing the original heuristic to fail. Its measured timing and output were reviewed from the retained raw receipt; original failures remain recorded. This serving smoke does not require a complete module within the output cap and does not establish task correctness. Appendix C describes normal-mode exposure after isolated validation.

**v1.7 allocation/ceiling change:** the user authorized increasing KV while treating 120 decimal GB as the total-RAM ceiling. An 18 GB pool passed startup/protocol/96K cache checks. A 20 GB pool crossed the ceiling at 120.026 GB during growing history and was stopped by the guard. The selected **19 GB** pool passed protocol, fixed-prefix 250K, growing-history 20K/96K/250K and sustained-generation checks, with a validation peak of 118.534 GB. This changes memory policy explicitly; it does not reinterpret the earlier guard failures as passes. A separate 20 GB test returned correct answers for two independent 250K contexts but failed the warm-reuse target for one of them. Advertised cache-token capacity is not a guarantee of fast retention of two full contexts; no such claim is made for 19 GB.

**v1.8 allocation change (2026-09-19):** the owner selected a **22 GB** pool, for the larger amount of cached conversation it gives a local coding-agent harness. The 120 decimal GB ceiling and both guard thresholds are unchanged. This pin depends on the host: kernel `7.0.0-1019-nvidia` reserves about 9.3 GiB at boot unless `kho=off` is on the kernel command line (NVIDIA's `nvidia-spark-grub-kho` package), and on the unfixed kernel a 19 GB seat ran out of memory and went into swap. Before starting the seat, require `grep -o kho=off /proc/cmdline` to succeed, or use a kernel that does not enable Kexec HandOver. On the fixed host, 19 GB was re-tested (peak 113.90 GB) and 22 GB passed protocol, fixed-prefix 250K, growing history to 250K and sustained generation, with a peak of **117.09 GB**, at least 12.64 GiB available, no swap and no guard stop. That is 2.91 GB under the ceiling, a thinner margin than any earlier retained size. Steady generation is unchanged at 56–59 tok/s; the PLE table's page cache is smaller (about 11–12 GiB, against about 22 GiB at 14 GB), which shows as a slow patch of about 40 tok/s for a few minutes after loading or after a very large prompt. Two independent 130K conversations stay cached together at 19 and 22 GB; two 250K conversations do not at either size. The 22 GB run was made on the normal-mode seat without cache resets, against freshly started containers, which departs from the isolated validation this runbook prescribes; see the [results](./RESULTS-qwen38-flash-next-kv-ceiling-20260919T090408Z.md) and [drift](./DRIFT-qwen38-flash-next-kv-ceiling-20260919T090408Z.md).

**Fallback from 22 GB:** if the guard stops the seat, swap counters move, or generation on real traffic stays well below the 44.6 tok/s measured at 14 GB, set `KV_BYTES=19g`, which was tested on the fixed host. An in-between `20g` or `21g` is permitted but untested there: expect about 644,000 tokens and a peak near 115.0 GB at `20g`, and about 676,000 tokens and near 116.0 GB at `21g`, and run the serving gates again before retaining either. The 2026-09-10 `20g` trial crossed the ceiling, in a run whose totals were about 4.6 GB higher than the 2026-09-19 totals at the same 19 GB setting. The results file gives the commands for swapping the live container.

The top-level upstream `serve.sh` supplies MTP=3, eight sequences, explicit KV sizing and `qwen3_xml`; the inner launcher has different defaults. This runbook spells out the intended values. The checkpoint supplies INT4 main/draft experts, INT8 output head and FP8 side layers. The draft vocabulary changes proposal efficiency, especially for CJK; it is not a vocabulary restriction on target output. No YaRN, HashK, reduced routed-expert count, never-evict prompt pin, RDMA or runtime package upgrades.

## Phase 0: Recon (read-only, advisory)

Compare current heads/revisions with PINS; record newer issues without changing the procedure. Fixed sources:

- [Saren source](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound), [checkpoint metadata](https://huggingface.co/api/models/Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN), [PLE metadata](https://huggingface.co/api/models/Saren/Qwen3.8-Flash-Next-ple-table-fp8).
- [Long-context kernel failure report](https://github.com/jschmied/qwen38-flash-next-gb10/commit/7fede41fc726), [blazux implementation and issues](https://github.com/blazux/qwen3.8-Flash-DGX), [vLLM prefix-cache issue #54173](https://github.com/vllm-project/vllm/issues/54173).
- [NVIDIA recipe comparison](https://forums.developer.nvidia.com/t/which-single-spark-qwen3-8-flash-next-thread-is-the-best/382522), [Tony's repository](https://github.com/tonyd2wild/Qwen3.8-Flash-Next-NVFP4-DGX-Spark), [shared Arena reference](https://spark-arena.com/benchmark/7ec7eaf7-a10c-403d-be52-c44c0fc64539).

The September 10 report observed a custom top-k shared-memory failure during a 95,239-token prefill on another GB10 stack. It is not a proven universal context ceiling for this image. The selected exact fallback avoids that kernel; the 94K/96K and growing-history gates still have to pass. Exact top-k does not promise bit-identical whole-model output, particularly with Marlin atomic adds enabled.

Produce `DRIFT-qwen38-flash-next-autoround-<run-id>.md` in the conventions format at final disposition. Unreachable research sources are recorded as skipped; they do not invalidate cached immutable artifacts. Failure to obtain a required pinned artifact does halt staging.

## Phase 0.5: Pre-flight (read-only)

```bash
test "$(hostname -s)" = "$TARGET_HOST"
test "$(uname -m)" = aarch64
test -f "$REPO_DIR/scripts/qwen38-seat-probe.py"
test -f "$REPO_DIR/scripts/qwen38-growing-cache-probe.py"
docker buildx version
sudo -n true
docker info >/dev/null
systemctl --user is-active --quiet llama-swap
test "$(systemctl --user show llama-swap -p LoadState --value)" != masked
test ! -e "$RUNTIME_MASK"
test ! -L "$RUNTIME_MASK"
test -z "$(ss -H -ltn "sport = :$SEAT_PORT")"
test -z "$(docker ps -aq --filter "name=^/${CONTAINER}$")"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
docker ps --format '{{.Names}} {{.Image}}'
systemctl --user list-timers --all --no-pager
python3 - <<'PY'
import os, shutil
assert shutil.disk_usage(os.path.expanduser('~')).free >= int(os.environ['DISK_MIN_GIB']) * 2**30
rows = [line.split() for line in open('/proc/swaps').read().splitlines()[1:]]
assert len(rows) <= 1 and all(row[0] == os.environ['SWAP_FILE'] and row[1] == 'file' for row in rows), 'unexpected swap configuration'
print('PASS first-stage disk margin')
PY
```

Inspect `findmnt -T "$HOME/models"` (or its existing parent) and `lsblk -o NAME,TYPE,TRAN,ROTA,MOUNTPOINTS`: **both model and PLE storage must be local NVMe**, not NFS/SMB or remote storage. Inventory all GPU consumers and scheduled launchers. A DeepSeek, qwen35-122b, another vLLM, training job or unknown scheduled GPU job is a failed exclusivity precondition; resolve its ownership before proceeding. Do not stop unidentified workloads. Record driver, OS, Docker/runtime versions, power/clock settings and free memory; keep those settings fixed during validation.

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
cat /proc/swaps > "$RUN_DIR/swaps-before.txt"
sysctl vm.swappiness vm.overcommit_memory > "$RUN_DIR/vm-policy-before.txt"
git rev-parse HEAD > "$RUN_DIR/runbook-repo-commit.txt"
sha256sum "$REPO_DIR/scripts/qwen38-seat-probe.py" "$REPO_DIR/scripts/qwen38-growing-cache-probe.py" \
  "$REPO_DIR/RUNBOOK-qwen38-flash-next-autoround-seat.md" > "$RUN_DIR/procedure.sha256"
```

**Gate:** the local catalog and recovery snapshots exist, and clients of the fleet have finished their active work before displacement. The Spark's green base is required even though it is about to be drained.

## Phase 2: Stage immutable artifacts (fleet still serving)

Build without GPU access from a fresh, detached source checkout. The upstream Dockerfile uses checksum-pinned remote `ADD` operations and requires BuildKit. Do not run its convenience launcher: it removes an existing container and enables automatic restarts.

```bash
test ! -e "$BUILD_DIR"
git init "$BUILD_DIR"
git -C "$BUILD_DIR" remote add origin "$RECIPE_REPO"
git -C "$BUILD_DIR" fetch --depth 1 origin "$RECIPE_REV"
git -C "$BUILD_DIR" checkout --detach FETCH_HEAD
test "$(git -C "$BUILD_DIR" rev-parse HEAD)" = "$RECIPE_REV"
test -z "$(git -C "$BUILD_DIR" status --porcelain)"
python3 - <<'PY'
import os
from pathlib import Path
s = (Path(os.environ['BUILD_DIR'])/'Dockerfile').read_text()
assert [x for x in s.splitlines() if x.startswith('FROM ')] == ['FROM '+os.environ['BASE_IMAGE']]
assert 'ARG KDET_SHA='+os.environ['KERNEL_REV'] in s
assert s.count('ADD --checksum=sha256:') == 6
print('PASS source/base/kernel pins')
PY
docker pull --platform linux/arm64 "$BASE_IMAGE"
docker image inspect "$BASE_IMAGE" > "$RUN_DIR/base-image.json"
DOCKER_BUILDKIT=1 docker build --platform linux/arm64 \
  --label "org.opencontainers.image.revision=$RECIPE_REV" \
  --iidfile "$RUN_DIR/image-id.txt" "$BUILD_DIR" 2>&1 | tee "$RUN_DIR/build.log"
IMAGE=$(cat "$RUN_DIR/image-id.txt")
export IMAGE
docker image inspect "$IMAGE" > "$RUN_DIR/image.json"
python3 - <<'PY'
import json, os, re
from pathlib import Path
p = Path(os.environ['RUN_DIR'])
base = json.loads((p/'base-image.json').read_text())[0]
d = json.loads((p/'image.json').read_text())[0]
assert base['Architecture'] == d['Architecture'] == 'arm64'
base_digest = os.environ['BASE_IMAGE'].split('@', 1)[1]
assert any(ref.endswith('@'+base_digest) for ref in base['RepoDigests'])
assert re.fullmatch(r'sha256:[0-9a-f]{64}', os.environ['IMAGE'])
assert d['Id'] == os.environ['IMAGE']
assert d['Config']['Labels']['org.opencontainers.image.revision'] == os.environ['RECIPE_REV']
print('PASS locally built ARM64 image identity')
PY
mkdir -p "$MODEL_DIR" "$PLE_DIR"
docker run --rm --network host --entrypoint python3 \
  -v "$MODEL_DIR:/model" -v "$PLE_DIR:/ple-table" "$IMAGE" -c \
  'from huggingface_hub import snapshot_download; import sys; snapshot_download(repo_id=sys.argv[1],revision=sys.argv[2],local_dir="/model"); snapshot_download(repo_id=sys.argv[3],revision=sys.argv[4],local_dir="/ple-table")' \
  "$MODEL_REPO" "$MODEL_REV" "$PLE_REPO" "$PLE_REV"
docker run --rm --network host --entrypoint python3 -i \
  -v "$MODEL_DIR:/model:ro" -v "$PLE_DIR:/ple-table:ro" -v "$RUN_DIR:/evidence" \
  "$IMAGE" - "$MODEL_REPO" "$MODEL_REV" "$PLE_REPO" "$PLE_REV" <<'PY'
import hashlib, json, sys
from pathlib import Path
from huggingface_hub import HfApi
manifest = {}
for mount, repo, rev in (('/model', *sys.argv[1:3]), ('/ple-table', *sys.argv[3:5])):
    info = HfApi().model_info(repo, revision=rev, files_metadata=True)
    assert info.sha == rev
    entries = {}
    for f in info.siblings:
        path = Path(mount)/f.rfilename
        assert path.is_file() and path.stat().st_size == f.size, f.rfilename
        sha256 = hashlib.sha256()
        git_blob = hashlib.sha1(('blob '+str(f.size)+'\0').encode())
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                sha256.update(block)
                git_blob.update(block)
        if f.lfs:
            assert sha256.hexdigest() == f.lfs.sha256, f.rfilename
        else:
            assert git_blob.hexdigest() == f.blob_id, f.rfilename
        entries[f.rfilename] = {'size': f.size, 'sha256': sha256.hexdigest()}
    manifest[mount] = {'repo': repo, 'revision': rev, 'files': entries}
Path('/evidence/artifacts.sha256.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('PASS every checkpoint and external PLE file against pinned upstream hashes')
PY
python3 - <<'PY'
import hashlib, json, os, re, struct
from pathlib import Path
p, ple = Path(os.environ['MODEL_DIR']), Path(os.environ['PLE_DIR'])
checks = {'config.json':'CONFIG_SHA', 'chat_template.jinja':'TEMPLATE_SHA',
          'tokenizer_config.json':'TOKENIZER_CONFIG_SHA', 'generation_config.json':'GENERATION_CONFIG_SHA',
          'model.safetensors.index.json':'INDEX_SHA'}
for name, env in checks.items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest() == os.environ[env], name
index = json.loads((p/'model.safetensors.index.json').read_text())['weight_map']
assert len(set(index.values())) == int(os.environ['SHARD_COUNT'])
assert all((p/f).is_file() for f in set(index.values()))
assert not any('ngram_embedding' in k for k in index)  # external table, deliberately stripped
config = json.loads((p/'config.json').read_text())
c, q = config['text_config'], config['quantization_config']
assert c['max_position_embeddings'] == int(os.environ['CTX'])
assert (c['num_experts'], c['num_experts_per_tok']) == (512, 10)
assert (c['indexer_budget'], c['indexer_compress_ratio']) == (2048, 4)
assert c['rope_parameters']['rope_type'] == 'default'
assert (q['quant_method'], q['bits'], q['group_size']) == ('gptq', 4, 128)
assert q['dynamic']['+:.*lm_head$']['bits'] == 8
assert '<tool_call>' in (p/'chat_template.jinja').read_text()
# The table repository has no index: inspect all safetensors headers without loading weights.
files = sorted(ple.glob('*.safetensors'))
assert len(files) == int(os.environ['PLE_FILE_COUNT'])
parts, scales = set(), []
for f in files:
    with f.open('rb') as stream:
        size = struct.unpack('<Q', stream.read(8))[0]
        assert 0 < size < 64 * 1024 * 1024
        header = json.loads(stream.read(size))
    for name, meta in header.items():
        match = re.search(r'ngram_embedding\.shard_(\d+)\.weight$', name)
        if match:
            part = int(match[1])
            assert part not in parts and meta['dtype'] == 'F8_E4M3'
            parts.add(part)
        if name.endswith('ngram_embedding.weight_scale'):
            scales.append(meta)
assert parts == set(range(c['split_ngram_parts']))
assert len(scales) == 1 and scales[0]['dtype'] == 'BF16'
print('PASS control files, full expert configuration, complete external FP8 PLE and scale')
PY
```

The hash pass reads approximately 116 GiB and retains a manifest for **both** directories, including tokenizer/template and PLE files outside the model index. On an offline re-run, verify every file's size and SHA-256 against that retained manifest, reassert the control-file gates and use the saved image ID. Missing identity evidence halts the run. Never patch downloaded blobs, re-quantize them in place or upgrade runtime packages. Retain the model cards and follow their licence references before production use.

## Phase 3: Drain the Spark and protect the memory envelope

Stop any additional **identified** fleet keepalive/loader timers from Phase 0.5, recording their prior state. The canonical units are below. A runtime mask prevents a dependency such as LiteLLM's `Wants=llama-swap` from reviving the fleet during this attended trial. A unit in `~/.config/systemd/user` outranks the ordinary runtime mask directory; in that case, use the higher-precedence runtime `user.control` directory and record ownership for teardown. Both masks disappear on reboot. If the mask cannot take effect, halt before launching.

```bash
for unit in llama-swap-keepalive.timer llama-swap-keepalive.service; do
  if test "$(systemctl --user show "$unit" -p LoadState --value)" != not-found; then
    systemctl --user stop "$unit"
  fi
done
systemctl --user stop llama-swap.service
systemctl --user mask --runtime llama-swap.service
if test "$(systemctl --user show llama-swap -p LoadState --value)" != masked; then
  test ! -e "$RUNTIME_MASK"
  test ! -L "$RUNTIME_MASK"
  mkdir -p "$(dirname "$RUNTIME_MASK")"
  ln -s /dev/null "$RUNTIME_MASK"
  printf '%s\n' "$RUNTIME_MASK" > "$RUN_DIR/runtime-mask-created.txt"
  systemctl --user daemon-reload
fi
test "$(systemctl --user show llama-swap -p LoadState --value)" = masked
if systemctl --user is-active --quiet llama-swap; then
  echo 'FAIL fleet is still active' >&2
  exit 1
fi
if pgrep -x llama-server; then
  echo 'FAIL llama-server remains after draining the fleet' >&2
  exit 1
fi
python3 - <<'PY'
import os, time
from pathlib import Path
deadline = time.monotonic() + float(os.environ['DRAIN_SETTLE_MAX_S'])
consecutive = 0
while time.monotonic() < deadline:
    m = {k:int(v.split()[0]) for k,v in (s.split(':',1) for s in open('/proc/meminfo'))}
    available = m['MemAvailable']/2**20
    with (Path(os.environ['RUN_DIR'])/'drain-memory.txt').open('a') as output:
        output.write(f'{time.time():.3f} available_gib={available:.3f}\n')
    consecutive = consecutive + 1 if available >= float(os.environ['PRELAUNCH_AVAILABLE_GIB']) else 0
    if consecutive >= 3:
        print(f'PASS drained memory headroom: {available:.3f} GiB, three consecutive samples')
        break
    time.sleep(2)
else:
    raise RuntimeError('drained memory did not reach the pinned headroom within the settling window')
PY
python3 - <<'PY'
import os, subprocess
from pathlib import Path
p = Path(os.environ['RUN_DIR'])
def swaps(text): return [line.split() for line in text.splitlines()[1:]]
before = swaps((p/'swaps-before.txt').read_text())
current = swaps(Path('/proc/swaps').read_text())
def identity(rows): return [(x[0], x[1], x[2], x[4]) for x in rows]
assert identity(current) == identity(before), 'swap configuration changed since snapshot'
assert len(before) <= 1 and all(x[0] == os.environ['SWAP_FILE'] and x[1] == 'file' for x in before)
m = {k:int(v.split()[0])*1024 for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
used = sum(int(row[3])*1024 for row in current)
assert m['MemAvailable'] - used >= float(os.environ['PRELAUNCH_AVAILABLE_GIB'])*2**30, 'insufficient headroom to page swap back into RAM'
if current:
    # Intent is recorded first so teardown also handles an interrupted swapoff.
    (p/'swapoff-requested.txt').write_text(os.environ['SWAP_FILE']+'\n')
    subprocess.run(['sudo', '-n', 'swapoff', os.environ['SWAP_FILE']], check=True)
assert not swaps(Path('/proc/swaps').read_text()), 'swap remains active'
m = {k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
assert m['SwapTotal'] == 0 and m['MemAvailable']/2**20 >= float(os.environ['PRELAUNCH_AVAILABLE_GIB'])
print('PASS swap inactive and drained memory headroom preserved')
PY
systemd-run --user --unit=qwen38-autoround-memory-guard --collect \
  /usr/bin/python3 "$REPO_DIR/scripts/qwen38-seat-probe.py" memory \
  --container "$CONTAINER" --evidence "$RUN_DIR" \
  --min-available-gib "$MEM_AVAILABLE_MIN_GIB" --max-used-gib "$MEM_USED_MAX_GIB"
systemctl --user is-active --quiet qwen38-autoround-memory-guard
```

The guard samples total unified memory and swap counters every two seconds, keeps JSONL, and stops this seat on a breach. This host's first startup produced 69 swap-out pages while approximately 35 GiB remained available. The revised procedure pages existing swap back into RAM **before** the guard's baseline and deactivates the recorded swap file for the seat's lifetime. It preserves fstab, sysctls and the original swap configuration for teardown. No new swap growth or swap I/O is permitted after the guard starts; the RAM limits are unchanged. A swap-preparation failure also requires teardown. Do not use `nvidia-smi` memory/utilisation as the sole GB10 residency gate. Do not drop host caches during serving: this recipe relies on the page cache.

## Phase 4: Launch the seat

The upstream PLE lookup is a CPU gather plus host-to-device copy, so `ple_mmap_lookup` must remain outside CUDA graphs. The separate `/ple-table` mount and environment setting are required. The explicit KV allocation takes precedence over the small memory-utilisation fraction; it does not cap total host memory. The guard remains the total-memory gate.

No automatic restart policy is enabled. After reboot the normal fleet may return; starting this seat again requires its isolation and memory guard. A persistent service needs its own ownership and startup-order procedure.

```bash
docker run -d --name "$CONTAINER" --restart no --gpus all \
  --network host --ipc=host --shm-size 16g \
  -v "$MODEL_DIR:/model:ro" -v "$PLE_DIR:/ple-table:ro" -v "$RUN_DIR/cache:/root/.cache" \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e VLLM_SERVER_DEV_MODE="$DEV_APIS" \
  -e VLLM_PLE_MMAP=1 -e VLLM_PLE_MMAP_DIR=/ple-table \
  -e VLLM_PLE_MMAP_WORKERS=32 -e VLLM_PLE_MMAP_PREWARM="$PREWARM" \
  -e VLLM_PLE_MMAP_PREFETCH=0 -e VLLM_PLE_MMAP_MADV_RANDOM=1 \
  -e VLLM_QSA_EXACT_TOPK="$EXACT_TOPK" -e VLLM_QSA_DET_TOPK="$DET_TOPK" \
  -e VLLM_MTP_DRAFT_VOCAB="$DRAFT_VOCAB" -e VLLM_MARLIN_USE_ATOMIC_ADD=1 \
  -e VLLM_USE_FLASHINFER_SAMPLER=1 -e VLLM_FP8_HYBRID=1 -e VLLM_USE_DEEP_GEMM=0 \
  -e VLLM_ALLOW_LONG_MAX_MODEL_LEN=0 -e VLLM_HIT_DEBUG=0 -e VLLM_STEP_PROFILE=0 \
  -e CUDA_LAUNCH_BLOCKING=0 \
  --entrypoint "" "$IMAGE" \
  vllm serve /model --served-model-name "$SERVED_ID" \
  --host "$SEAT_BIND_HOST" --port "$SEAT_PORT" --load-format "$LOAD_FORMAT" \
  --chat-template /model/chat_template.jinja \
  --max-model-len "$CTX" --max-num-seqs "$SEQS" --gpu-memory-utilization "$GMU" \
  --enable-prefix-caching --enable-chunked-prefill --max-num-batched-tokens "$CHUNK" \
  --compilation-config "$COMPILATION_CONFIG" \
  --no-enable-flashinfer-autotune --kv-cache-dtype "$KV_TYPE" --kv-cache-memory-bytes "$KV_BYTES" \
  --enable-auto-tool-choice --tool-call-parser "$TOOL_PARSER" --reasoning-parser "$REASONING_PARSER" \
  --speculative-config "{\"method\":\"mtp\",\"num_speculative_tokens\":$MTP}"

deadline=$((SECONDS + COLD_START_MAX_S))
until curl -fsS --max-time 3 "localhost:$SEAT_PORT/health" >/dev/null; do
  test "$SECONDS" -lt "$deadline"
  test ! -f "$RUN_DIR/memory.failed"
  systemctl --user is-active --quiet qwen38-autoround-memory-guard
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

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
d = json.loads((Path(os.environ['RUN_DIR'])/'container.json').read_text())[0]
assert d['Image'] == os.environ['IMAGE']
env = dict(x.split('=', 1) for x in d['Config']['Env'] if '=' in x)
assert env['VLLM_QSA_EXACT_TOPK'] == os.environ['EXACT_TOPK'] == '1'
assert env['VLLM_QSA_DET_TOPK'] == os.environ['DET_TOPK'] == '0'
assert env['VLLM_MTP_DRAFT_VOCAB'] == os.environ['DRAFT_VOCAB']
assert env['VLLM_PLE_MMAP_DIR'] == '/ple-table'
assert env.get('VLLM_SERVER_DEV_MODE', '0') == os.environ['DEV_APIS'] in ('0', '1')
args = d['Config']['Cmd']
assert args[args.index('--host')+1] == os.environ['SEAT_BIND_HOST']
assert os.environ['DEV_APIS'] == '0' or os.environ['SEAT_BIND_HOST'] == '127.0.0.1'
assert json.loads(args[args.index('--speculative-config')+1]) == {'method':'mtp', 'num_speculative_tokens':int(os.environ['MTP'])}
assert '--enable-prefix-caching' in args
print('PASS container identity and effective top-k/MTP/cache settings')
PY
```

**Gate:** retain log evidence for the external FP8 PLE table and scale loading, FP8 side-layer dispatch, GPTQ-Marlin head/experts, MTP draft vocabulary, exact top-k, BF16 KV and prefix caching. Record the resolved KV bytes, token capacity, Mamba block size and maximum concurrency at native context; require capacity for one native-context request. Check for ignored tensors, non-finite output, CUDA errors and tracebacks. A **Mamba state-copy guard hit is a failed correctness gate**, even if the process survives: skipping a bad state copy is not proof of a correct continuation. Missing observability is unresolved, not PASS.

Thinking-off is a **request setting**. The probes explicitly send `chat_template_kwargs: {enable_thinking: false}` with the pinned standalone template. Preserve that setting through client/gateway paths. Other reasoning modes, languages and multimodal inputs need their own workload validation; this procedure tests text and tools. Do not substitute the Lance Sharp template or silently switch parsers.

## Phase 5: Serving gates on the isolated engine

The helper uses only Python's standard library. Its tool calls are synthetic; it never runs model-suggested commands. It verifies structured SSE tool calls, JSON arguments, tool-result continuation, unassisted JSON output, and absence of reasoning content/tokens. All failures exit nonzero and keep diagnostic receipts.

```bash
curl -fsS "localhost:$SEAT_PORT/metrics" > "$RUN_DIR/metrics-before.txt"
python3 scripts/qwen38-seat-probe.py protocols --base-url "http://localhost:$SEAT_PORT" \
  --model "$SERVED_ID" --evidence "$RUN_DIR/direct"
for length in $CACHE_TEST_LENGTHS; do
  python3 scripts/qwen38-seat-probe.py cache --base-url "http://localhost:$SEAT_PORT" \
    --model "$SERVED_ID" --prompt-tokens "$length" --warm-ratio "$WARM_RATIO_MAX" \
    --evidence "$RUN_DIR/direct"
  test ! -f "$RUN_DIR/memory.failed"
done
python3 scripts/qwen38-growing-cache-probe.py --base-url "http://localhost:$SEAT_PORT" \
  --model "$SERVED_ID" --lengths $CACHE_TEST_LENGTHS --evidence "$RUN_DIR/growing"
python3 scripts/qwen38-seat-probe.py decode --base-url "http://localhost:$SEAT_PORT" \
  --model "$SERVED_ID" --decode-floor "$DECODE_FLOOR" --max-tokens "$STREAM_MAX_TOKENS" \
  --min-seconds "$LONG_STREAM_MIN_S" --evidence "$RUN_DIR/direct"
curl -fsS "localhost:$SEAT_PORT/metrics" > "$RUN_DIR/metrics-after.txt"
docker logs "$CONTAINER" > "$RUN_DIR/gates-seat.log" 2>&1
systemctl --user is-active --quiet qwen38-autoround-memory-guard
test ! -f "$RUN_DIR/memory.failed"
if systemctl --user is-active --quiet llama-swap; then
  echo 'FAIL fleet revived during seat validation' >&2
  exit 1
fi
```

Cache probes tokenize the actual rendered request, reset the isolated engine's prefix cache, then compare a cold request with its repeat, a changed question on the same prefix, and an unrelated prefix. Expected answers are asserted, not judged by another model. The tests cover a range of prompt lengths through 250K, exercising the native window beyond the historical corruption boundary. **Do not run cache-reset probes once clients use the seat.** A needle smoke does not establish general long-context reasoning quality.

The decode receipt reports native usage tokens, time to first content/tool delta, approximate decode rate `(completion_tokens - 1)/(last_delta - first_delta)` and whole-request rate separately. Stream chunks are not tokens. Do not label `completion_tokens / whole_request_seconds` as decode speed. MTP can emit multiple tokens per stream chunk; this rate remains approximate. The 30 tok/s diagnostic floor is a proposed health threshold, not a model-promotion rule or reproduction of the author's headline. A naturally short reply cannot prove the 90-second timeout gate; record it as inconclusive and exercise a suitable real long generation before proceeding. No `ignore_eos` counting benchmark.

The growing-history helper starts one synthetic conversation, appends real structured tool-call messages and synthetic tool results, then expands it across the pinned lengths **without resetting cache between turns**. It checks older tool-result recall and changing expected answers, records actual rendered/native token counts, and requires a prefix-hit counter increase during each tool continuation. It executes no model-proposed tools. Its one initial cache reset also requires an isolated engine. This targets cache/state errors that repeating one fixed prompt could miss; it does not emulate an entire application harness.

Compare the before/after metrics and logs: require actual speculative draft and accepted-token activity, record acceptance by position if exposed, and report prefix hits/queries, queue time and prefill/decode timing. Retain metric names exactly as emitted by this image. If MTP counters are absent, use its native speculative-decoding log statistics; if neither demonstrates accepted proposals, mark MTP unverified and halt. Review the complete gate log for Mamba guard hits and other runtime errors before declaring PASS.

**Additional capacity characterization:** [qwen38-concurrent-cache-probe.py](./scripts/qwen38-concurrent-cache-probe.py), invoked with `--evidence` pointing to a new directory, submits two independent 250K prompts together and checks their distinct answers and warm repeats. It targets this model on loopback with development cache-reset APIs enabled. This is separate from the single-conversation gates above: the 20 GB trial returned all answers correctly but failed the warm-reuse target for one context, and the test was not repeated at 19 GB. Cold prefills were largely sequential. Do not infer two fully retained fast 250K contexts from the engine's reported cache-token capacity.

## Phase 6: Decision gate

| Gate | Required evidence | Result |
|---|---|---|
| Base and displacement | original local catalog and configuration; private recovery snapshot | NOT RUN |
| Artifact identity | base digest/build source/local image ID/ARM64; both HF revisions and all-file hashes; intact experts/PLE | NOT RUN |
| Exclusivity | Spark fleet and loader timers stopped; mask effective; no other GPU seat | NOT RUN |
| Startup | health within pinned window; GPU/SM121; external PLE/hybrid load; BF16 KV; exact top-k; MTP3/draft vocabulary | NOT RUN |
| Context/cache | measured token lengths through 250K; correct cold/warm/changed/unrelated answers; warm ratio; growing tool history; observed prefix hits | NOT RUN |
| Speculation/state | measured draft acceptance; no Mamba guard hits or CUDA errors | NOT RUN |
| Protocol | auto/required/named tool choice; valid arguments and continuation; JSON; thinking off | NOT RUN |
| Timing | native-usage decode above floor; >90-second direct stream | NOT RUN |
| Memory | swap snapshot/deactivation before guard; every serving phase inside envelope; no new swap or swap I/O; guard active | NOT RUN |
| Optional gateway (Appendix B) | exact row; client access; tools/long stream; existing routes preserved; spend record if persistence configured | NOT RUN / N/A |
| Recovery | restored catalog/config/timers, or retained isolated seat explicitly recorded | NOT RUN |

Phases 1–5 PASS = **serving-ready** at the direct API. Run Appendix B before completing this table if gateway access is part of the deployment; otherwise mark that row N/A. A failed required gate stops dependent work and invokes teardown; preserve logs rather than swapping recipes or raising memory utilisation.

## Phase 7: Cleanup, retention and results

To retain the server after validation, record that disposition, keep the memory guard and fleet mask active, leave the recorded swap file inactive, and keep clients within the measured workload. To end the model session and restore the fleet and swap configuration, execute Appendix A. The container will not auto-restart after reboot. No unattended production service is installed by this runbook.

Write RESULTS once at final disposition, including on a terminal failed run: procedure commit/hashes, all artifact pins, hardware/runtime versions, recon drift, raw receipt locations, every measured gate, failures/retries, min available/max used memory, swap counters, actual KV pool, client/route evidence where applicable, and restored/retained state. Research numbers must remain labelled external. Scrub keys/private prompts from any evidence committed to this public repository; keep private backups in the run directory.

## Appendix A: Teardown / rollback

1. **Clients/gateway:** stop new requests and wait for active ones to finish. If Appendix B added a gateway row or client key grant, remove only this session's additions. Restore the private config backup only if no intervening edits occurred; otherwise apply the inverse row change. Restart the gateway if changed and verify its original catalog and representative existing routes.
2. **Spark:** stop the model container before releasing the fleet mask. Preserve its logs. Run the following in the original pinned shell/run context:

```bash
docker logs "$CONTAINER" > "$RUN_DIR/final-seat.log" 2>&1 || true
docker stop --time 30 "$CONTAINER" || true
test "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" = false
docker rm "$CONTAINER"
systemctl --user stop qwen38-autoround-memory-guard || true
python3 - <<'PY'
import os, subprocess
from pathlib import Path
p = Path(os.environ['RUN_DIR'])
def swaps(text): return [line.split() for line in text.splitlines()[1:]]
before = swaps((p/'swaps-before.txt').read_text())
if (p/'swapoff-requested.txt').exists():
    assert (p/'swapoff-requested.txt').read_text().strip() == os.environ['SWAP_FILE']
    current = swaps(Path('/proc/swaps').read_text())
    for row in before:
        assert row[0] == os.environ['SWAP_FILE'] and row[1] == 'file'
        if row[0] not in {x[0] for x in current}:
            cmd = ['sudo', '-n', 'swapon']
            if int(row[4]) >= 0:
                cmd += ['--priority', row[4]]
            subprocess.run(cmd + [row[0]], check=True)
    current = swaps(Path('/proc/swaps').read_text())
    identity = lambda rows: [(x[0], x[1], x[2], x[4]) for x in rows]
    assert identity(current) == identity(before), 'swap configuration restoration failed'
print('PASS original swap configuration retained/restored')
PY
systemctl --user unmask --runtime llama-swap.service
if test -f "$RUN_DIR/runtime-mask-created.txt"; then
  test "$(cat "$RUN_DIR/runtime-mask-created.txt")" = "$RUNTIME_MASK"
  test "$(readlink "$RUNTIME_MASK")" = /dev/null
  rm -- "$RUNTIME_MASK"
fi
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

Validation binds loopback with development APIs enabled. Before using the network URLs below, perform the normal-mode restart described in v1.4: disable development APIs, select the intended bind address and repeat the health/protocol/memory checks. Do not run cache-reset probes on a seat receiving client traffic.

The direct API is `http://spark-fcf6.local:8888/v1`, model `qwen3.8-flash-next-autoround`. Clients may connect directly, or use an existing LiteLLM gateway for model aliases, keys and accounting. The Dell's existing dashboard/Postgres can record calls to this remote model; installing another database on the Spark is not required. An existing gateway without persistence can route requests but does not provide stored spend records.

After Phase 5 passes, record the selected gateway host/address, its current model catalog and a private config backup. Test Spark connectivity from that host and from the actual client environment. Resolve and record its LAN address if mDNS is unavailable. No tensor-parallel networking is needed.

Add exactly one explicit row to the existing `model_list`, before catch-all mappings. This fragment uses `GATEWAY_ROW`, `SERVED_ID`, `SEAT_PORT` and `ROUTE_TIMEOUT_S` from PINS. An application may choose its own gateway alias without changing the model server.

```yaml
- model_name: qwen3.8-flash-next-autoround
  litellm_params:
    model: openai/qwen3.8-flash-next-autoround
    api_base: http://spark-fcf6.local:8888/v1
    api_key: local-unused
    timeout: 900
```

Validate using the gateway's existing YAML parser. Require exactly one new row and assert that removing it yields the original parsed configuration. Preserve existing model routes and settings, including `fallbacks: []` and `context_window_fallbacks: []`; an unavailable Qwen endpoint must fail visibly. Add the alias to the intended virtual key's allowlist when needed, preserving its existing grants. Use client virtual keys for inference, not the master key.

Restart only the selected gateway through its existing service. Reassert the Spark's fleet remains masked/inactive and the memory guard is active. If the gateway is on the Spark, check its unit dependencies before restarting: `Wants=llama-swap` is the known fleet-revival trap. Do not replace its whole config with the repository's example file; that file includes routes specific to another host.

From the real client environment, run the helper's `protocols` and `decode` modes against the selected gateway URL, using its alias and the pinned thresholds from Phase 5. Set `QWEN38_API_KEY` from the client's existing secret environment if authentication is enabled. Do not run the cache-reset probe through the gateway; those are engine administration routes.

**Gate:** the client can call the exact alias; tool choice, JSON, thinking-off requests and a >90-second stream survive the full path; original routes still work. If that gateway has spend persistence, locate the probe requests in its database. Record the gateway and results, or mark this appendix N/A for direct-only access.

## Appendix C: Retain a normal network endpoint after validation

Run only after the isolated serving gates pass. Preserve the validation container, logs and metrics before replacing it. Keep the fleet masked, swap inactive and the memory guard running throughout; use Appendix A if the restart fails.

```bash
docker inspect "$CONTAINER" > "$RUN_DIR/validation-container.json"
docker logs "$CONTAINER" > "$RUN_DIR/validation-final.log" 2>&1
curl -fsS "localhost:$SEAT_PORT/metrics" > "$RUN_DIR/validation-metrics.txt"
docker stop --timeout 30 "$CONTAINER"
docker rm "$CONTAINER"
export DEV_APIS=0 SEAT_BIND_HOST="$NORMAL_BIND_HOST"
```

Repeat the two Phase 4 Bash blocks using these overrides and the same `IMAGE`, model/table paths, `RUN_DIR` and serving parameters. Preserve earlier phase receipts under `validation-*` names before overwriting startup/identity outputs. Compare the two container inspections: image, mounts and serving arguments must match except for the bind address and disabled development APIs. Verify the normal endpoint:

```bash
python3 scripts/qwen38-seat-probe.py protocols \
  --base-url "http://$TARGET_HOST.local:$SEAT_PORT" --model "$SERVED_ID" \
  --evidence "$RUN_DIR/normal"
python3 - <<'PY'
import os, urllib.request, urllib.error
url = 'http://127.0.0.1:'+os.environ['SEAT_PORT']+'/reset_prefix_cache'
try:
    urllib.request.urlopen(urllib.request.Request(url, data=b'{}',
        headers={'Content-Type':'application/json'}), timeout=10)
except urllib.error.HTTPError as error:
    assert error.code == 404
else:
    raise RuntimeError('development cache-reset endpoint remains exposed')
print('PASS normal mode: development cache-reset endpoint absent')
PY
systemctl --user is-active --quiet qwen38-autoround-memory-guard
test ! -f "$RUN_DIR/memory.failed"
```

These hostname checks run on the Spark; they do not establish connectivity from another client. Record a separate client or gateway check when one is used. A retained seat keeps the original fleet displaced and the swap file inactive until Appendix A is executed. Record that state and the original run directory in RESULTS.
