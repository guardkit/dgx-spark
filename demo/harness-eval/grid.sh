#!/usr/bin/env bash
# Show the results table — built automatically from every runs/*/SCORE.txt that
# ./score.sh has saved. No hand-editing, ever.
#
#   ./grid.sh          print the table
#   ./grid.sh --save   also write it to results/GRID-<today>.md (commit that; it renders
#                      on GitHub and is the on-screen graphic for the video)
set -euo pipefail
cd "$(dirname "$0")"

cell() {  # cell <task> <tier> -> PASS / n-of-m / · (not scored yet)
  local f="runs/$1-$2/SCORE.txt"
  [ -f "$f" ] || { printf '·'; return; }
  local last; last=$(tail -n1 "$f")
  case "$last" in
    *"gates green"*) printf 'PASS' ;;
    *"gates FAILED"*)
      # last line reads: "K/N gates FAILED" -> show passed/total
      local k n; k=${last%%/*}; n=${last#*/}; n=${n%% *}
      printf '%d/%d' "$((n - k))" "$n" ;;
    *) printf '?' ;;
  esac
}

row() {  # row <task> <label>
  printf '| %s | %s | %s | %s |\n' "$2" "$(cell "$1" h1)" "$(cell "$1" h2)" "$(cell "$1" h3)"
}

TABLE=$(
  echo '| Task | H1 one-shot | H2 bare agent | H3 full environment |'
  echo '|---|---|---|---|'
  row t1 'T1 log extraction'
  row t2 'T2 chess vs Stockfish'
  row t3 'T3 next-bus board'
  row t4 'T4 satellite globe'
  row t5 'T5 file reorganizing'
)

echo "$TABLE"
echo
echo "PASS = every gate green · n/m = gates passed / total · '·' = not scored yet"

if [ "${1:-}" = "--save" ]; then
  OUT="results/GRID-$(date +%F).md"
  mkdir -p results
  {
    echo "# Harness-eval results — $(date +%F)"
    echo
    echo "Model: DeepSeek-V4-Flash-0731 (two-Spark seat) · scored by \`./score.sh\` (operator-run) · n=1 per cell."
    echo
    echo "$TABLE"
    echo
    echo "Per-cell gate detail: \`runs/<task>-<tier>/SCORE.txt\` (copy alongside this file to publish)."
  } > "$OUT"
  echo
  echo "written: $OUT"
fi
