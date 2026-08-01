#!/usr/bin/env bash
# stage-public-models.sh — stage the THREE public-config model GGUFs. Idempotent.
#
# This is invoked BY the runbook as an execution step (RUNBOOK-single-spark-bring-up Phase 1.5) —
# it is NOT a manual prerequisite. Run it directly only if you want to pre-warm the downloads.
#
# Downloads the three models the public config (examples/llama-swap-config.public.yaml) serves,
# into the served dir, and makes each on-disk filename match the config's `--model` path
# (upstream filenames differ in case — we symlink to the exact expected name).
# Models already on disk are skipped (so on the reference box only embed downloads).
set -euo pipefail

MODELS_DIR="${MODELS_DIR:-/opt/llama-swap/models}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

if command -v hf >/dev/null 2>&1; then               HF=(hf download)
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

# workhorse — Qwen3.6-35B-A3B (Player, ~22 GB)
stage "unsloth/Qwen3.6-35B-A3B-GGUF"      "qwen36-35b"   "Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf"       "*UD-Q4_K_XL*"
# coach — stock Gemma-4-26B-A4B-it (~17 GB)
stage "unsloth/gemma-4-26B-A4B-it-GGUF"   "gemma4-coach" "gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf"    "*UD-Q4_K_XL*"
# (gpt-oss-20b `chat` RETIRED from the lineup 2026-08-01 — redundant beside the two
#  2026 MoEs. Its hard-won lesson STAYS: include-globs MUST match files the repo
#  actually ships — a non-matching glob downloads nothing and aborts the whole
#  staging under `set -e` before later models run (observed 2026-07-11: unsloth's
#  gpt-oss repo had no *mxfp4* file). When adding a model, check the repo's file
#  list against the glob first.)
# embed — Qwen3-Embedding-0.6B (Q8_0, ~0.6 GB)
stage "Qwen/Qwen3-Embedding-0.6B-GGUF"    "qwen3-embed"  "Qwen3-Embedding-0.6B-Q8_0.gguf"        "*Q8_0*" "*q8_0*"

echo
echo "── verify (the paths the public config's --model lines expect):"
ok=1
for p in \
  "$MODELS_DIR/qwen36-35b/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf" \
  "$MODELS_DIR/gemma4-coach/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf" \
  "$MODELS_DIR/qwen3-embed/Qwen3-Embedding-0.6B-Q8_0.gguf"; do
  if [ -e "$p" ]; then echo "   OK       $p"; else echo "   MISSING  $p"; ok=0; fi
done
[ "$ok" = 1 ] && echo "✅ all three public models staged." || { echo "❌ something missing — check the HF download output above"; exit 1; }

# NOTE: if a workhorse/coach repo ever ships SHARDED (…00001-of-000NN.gguf), point the config
# --model at the 00001 shard instead of symlinking a single name (llama.cpp auto-loads the rest).
