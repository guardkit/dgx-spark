#!/usr/bin/env bash
# llama-swap-keepalive.sh — PUBLIC FLEET variant (deployed by RUNBOOK-single-spark-bring-up.md)
#
# Probes llama-swap's admin endpoint and revives any configured-but-not-running
# always-on model with a single one-shot request that returns immediately.
# Designed to run from a systemd timer every ~5 minutes.
#
# MODEL_PROBE_KIND MUST equal hooks.on_startup.preload in
# /opt/llama-swap/config/config.yaml. For the PUBLIC config that is the four
# always-on models: workhorse, coach, chat, embed (NOT the operator's personal
# qwen-graphiti/nomic-embed/coach-ft-v3 lineup — see repo scripts/ copy).
#
# Exit codes: 0 all running (revived where needed) · 1 admin unreachable ·
#   2 unexpected response shape · 3 one or more revival attempts failed

set -u
set -o pipefail

LLAMA_SWAP_URL="${LLAMA_SWAP_URL:-http://localhost:9000}"
REVIVE_TIMEOUT="${REVIVE_TIMEOUT:-300}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-5}"
LOCK_FILE="${LOCK_FILE:-/var/lock/llama-swap-keepalive.lock}"
LOG_TAG="llama-swap-keepalive"

# Per-model probe shape: chat | embed. Keys = the PUBLIC always-on preload set.
declare -A MODEL_PROBE_KIND=(
    [workhorse]=chat
    [coach]=chat
    [chat]=chat
    [embed]=embed
)

log() { echo "[$LOG_TAG] $*"; }

exec 9>"$LOCK_FILE" 2>/dev/null || { log "WARN: cannot open lock file $LOCK_FILE; running without lock"; }
if [[ -e /proc/$$/fd/9 ]]; then
    if ! flock -n 9; then log "Another keep-alive run is in progress; exiting."; exit 0; fi
fi

running_json=$(curl -sS --max-time "$PROBE_TIMEOUT" "$LLAMA_SWAP_URL/running") || { log "ERROR: cannot reach $LLAMA_SWAP_URL/running"; exit 1; }
configured_json=$(curl -sS --max-time "$PROBE_TIMEOUT" "$LLAMA_SWAP_URL/v1/models") || { log "ERROR: cannot reach $LLAMA_SWAP_URL/v1/models"; exit 1; }

ALWAYS_ON="${!MODEL_PROBE_KIND[*]}"

mapfile -t TO_REVIVE < <(python3 - "$running_json" "$configured_json" "$ALWAYS_ON" <<'PY'
import json, sys
running_raw, configured_raw, allow_raw = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    running = json.loads(running_raw).get("running", [])
    configured = json.loads(configured_raw).get("data", [])
except (ValueError, AttributeError) as e:
    print(f"ERROR: parse: {e}", file=sys.stderr); sys.exit(2)
allow = set(allow_raw.split())
ready = {entry["model"] for entry in running if entry.get("state") == "ready"}
for m in configured:
    mid = m["id"]
    if mid in allow and mid not in ready:
        print(mid)
PY
) || { rc=$?; log "ERROR: admin endpoint returned unexpected JSON shape (python rc=$rc)"; exit 2; }

if [[ ${#TO_REVIVE[@]} -eq 0 ]]; then log "All configured models are ready; nothing to revive."; exit 0; fi
log "Reviving: ${TO_REVIVE[*]}"

declare -a PIDS=() NAMES=()
for model in "${TO_REVIVE[@]}"; do
    kind="${MODEL_PROBE_KIND[$model]:-chat}"
    if [[ "$kind" == "embed" ]]; then
        body=$(printf '{"model":"%s","input":"keepalive"}' "$model"); endpoint="$LLAMA_SWAP_URL/v1/embeddings"
    else
        body=$(printf '{"model":"%s","max_tokens":1,"messages":[{"role":"user","content":"k"}]}' "$model"); endpoint="$LLAMA_SWAP_URL/v1/chat/completions"
    fi
    ( curl -sS --max-time "$REVIVE_TIMEOUT" -H "Content-Type: application/json" -d "$body" -o /dev/null -w "%{http_code}" "$endpoint" > "/tmp/llama-keepalive-$model.code" 2>"/tmp/llama-keepalive-$model.err" ) &
    PIDS+=("$!"); NAMES+=("$model")
done

fail=0
for i in "${!PIDS[@]}"; do
    wait "${PIDS[$i]}" || true
    code=$(cat "/tmp/llama-keepalive-${NAMES[$i]}.code" 2>/dev/null || echo "")
    err=$(cat "/tmp/llama-keepalive-${NAMES[$i]}.err" 2>/dev/null || echo "")
    rm -f "/tmp/llama-keepalive-${NAMES[$i]}.code" "/tmp/llama-keepalive-${NAMES[$i]}.err"
    if [[ "$code" =~ ^2 ]]; then log "  ${NAMES[$i]}: revived (HTTP $code)"; else log "  ${NAMES[$i]}: revive FAILED (HTTP ${code:-none}; err=${err:-none})"; fail=1; fi
done
(( fail )) && exit 3
exit 0
