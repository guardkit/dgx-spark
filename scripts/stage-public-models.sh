#!/usr/bin/env bash
# stage-public-models.sh — one-shot pre-record staging for the PUBLIC llama-swap config.
#
# The public config (examples/llama-swap-config.public.yaml) needs two GGUFs that are NOT
# part of the personal/reference lineup, so they're missing on the reference box:
#   chat  → gpt-oss-20b           (unsloth/gpt-oss-20b-GGUF, MXFP4, ~12 GB)
#   embed → Qwen3-Embedding-0.6B  (Qwen/Qwen3-Embedding-0.6B-GGUF, Q8_0, ~0.6 GB)
# (workhorse + coach are shared with the personal lineup and assumed already staged.)
#
# This downloads them into the served dir and makes the on-disk filename match the config's
# `--model` path (Unsloth often ships uppercase e.g. *-MXFP4.gguf — we symlink to the exact
# name the config expects so it resolves). Idempotent: re-running skips what's present.
#
# Run on the TARGET box before RUNBOOK-single-spark-bring-up Phase 3.2 (deploy config).
#   MODELS_DIR=/opt/llama-swap/models ./scripts/stage-public-models.sh
set -euo pipefail

MODELS_DIR="${MODELS_DIR:-/opt/llama-swap/models}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

if command -v hf >/dev/null 2>&1; then            HF=(hf download)
elif command -v huggingface-cli >/dev/null 2>&1; then HF=(huggingface-cli download)
else echo "ERROR: HF CLI not found — pip install -U 'huggingface_hub[hf_transfer]'"; exit 1; fi

# stage <repo> <target-subdir> <expected-filename> <include-glob>...
stage() {
  local repo="$1" sub="$2" want="$3"; shift 3
  local dir="$MODELS_DIR/$sub" incs=()
  for g in "$@"; do incs+=(--include "$g"); done
  echo "── ${repo}  →  ${dir}/${want}"
  if [ -e "$dir/$want" ]; then echo "   present — skip"; return 0; fi
  mkdir -p "$dir"
  "${HF[@]}" "$repo" "${incs[@]}" --local-dir "$dir"
  local got; got=$(find "$dir" -iname '*.gguf' ! -lname '*' 2>/dev/null | sort | head -1)
  [ -n "$got" ] || { echo "   ERROR: no .gguf downloaded from $repo"; exit 1; }
  if [ "$(basename "$got")" != "$want" ]; then
    ( cd "$dir" && ln -sf "$(basename "$got")" "$want" )   # relative symlink → config path resolves
    echo "   linked ${want} → $(basename "$got")"
  fi
  echo "   OK: $(readlink -f "$dir/$want")"
}

# chat — gpt-oss-20b (MXFP4-native). Case-tolerant include (Unsloth ships *MXFP4*).
stage "unsloth/gpt-oss-20b-GGUF"        "gpt-oss-20b" "gpt-oss-20b-mxfp4.gguf"        "*mxfp4*" "*MXFP4*"
# embed — Qwen3-Embedding-0.6B (Q8_0).
stage "Qwen/Qwen3-Embedding-0.6B-GGUF"  "qwen3-embed" "Qwen3-Embedding-0.6B-Q8_0.gguf" "*Q8_0*" "*q8_0*"

echo
echo "── verify (these are the paths the public config's --model lines expect):"
ok=1
for p in "$MODELS_DIR/gpt-oss-20b/gpt-oss-20b-mxfp4.gguf" "$MODELS_DIR/qwen3-embed/Qwen3-Embedding-0.6B-Q8_0.gguf"; do
  if [ -e "$p" ]; then echo "   OK       $p"; else echo "   MISSING  $p"; ok=0; fi
done
[ "$ok" = 1 ] && echo "✅ public chat + embed staged. (workhorse + coach are shared with the personal lineup.)" \
             || { echo "❌ something missing — check the HF download output above"; exit 1; }
