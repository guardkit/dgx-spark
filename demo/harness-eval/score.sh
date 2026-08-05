#!/usr/bin/env bash
# Score one cell: run the task's validator against the run directory. OPERATOR-RUN —
# this is the receipt; the agent's own validator runs count for nothing in the grid.
#
#   ./score.sh <t1|t2|t3|t4|t5> <h1|h2|h3>
set -euo pipefail
cd "$(dirname "$0")"

TASK="${1:?usage: ./score.sh <t1|t2|t3|t4|t5> <h1|h2|h3>}"
TIER="${2:?usage: ./score.sh <t1|t2|t3|t4|t5> <h1|h2|h3>}"
RUN="runs/${TASK}-${TIER}"
[ -d "$RUN" ] || { echo "$RUN not found — run ./cell.sh $TASK $TIER first" >&2; exit 1; }

case "$TASK" in
  t1) node t1-golden-extract/validate/validate.mjs  "$RUN" ;;
  t2) node t2-chess-stockfish/validate/validate.mjs "$RUN" ;;   # needs: cd t2-chess-stockfish/validate && npm run setup (once)
  t3) node t3-next-bus/validate/validate.mjs        "$RUN" ;;   # needs: cd t3-next-bus/validate && npm run setup (once)
  t5) node t5-tool-effects/validate/validate.mjs    "$RUN" ;;
  t4)
    # T4's validator lives in demo/orbit-globe and assumes its own workspace shape:
    # score by dropping the run's index.html into a scratch copy of that workspace.
    WS="$RUN/.score-ws"
    rm -rf "$WS"; mkdir -p "$WS"
    rsync -a --exclude runs ../orbit-globe/ "$WS/"               # includes validate/node_modules if setup was run
    cp "$RUN/index.html" "$WS/index.html"
    ( cd "$WS/validate" && node validate.mjs )
    ;;
  *) echo "unknown task: $TASK" >&2; exit 1 ;;
esac
