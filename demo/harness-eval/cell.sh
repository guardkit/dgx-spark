#!/usr/bin/env bash
# Prepare (and for H1: fully run) one cell of the harness-eval grid.
#
#   ./cell.sh <t1|t2|t3|t4|t5> <h1|h2|h3> [--force]
#
# Creates runs/<task>-<tier>/ containing exactly what that tier is allowed to have:
#   h1  one-shot: assembles the prompt, calls the endpoint, saves the deliverable. Done.
#   h2  bare agent: TASK.md + task inputs only -> you run pi in it.
#   h3  full environment: the whole workspace (AGENTS.md, skills, validator) -> you run pi.
# Then score with ./score.sh <task> <tier>.  Endpoint overrides: EVAL_URL, EVAL_MODEL.
set -euo pipefail
cd "$(dirname "$0")"

TASK="${1:?usage: ./cell.sh <t1|t2|t3|t4|t5> <h1|h2|h3> [--force]}"
TIER="${2:?usage: ./cell.sh <t1|t2|t3|t4|t5> <h1|h2|h3> [--force]}"
FORCE="${3:-}"

case "$TASK" in
  t1) DIR="t1-golden-extract";  DELIV="extract.json" ;;
  t2) DIR="t2-chess-stockfish"; DELIV="index.html" ;;
  t3) DIR="t3-next-bus";        DELIV="index.html" ;;
  t4) DIR="../orbit-globe";     DELIV="index.html" ;;
  t5) DIR="t5-tool-effects";    DELIV="" ;;
  *) echo "unknown task: $TASK" >&2; exit 1 ;;
esac
case "$TIER" in h1|h2|h3) ;; *) echo "unknown tier: $TIER" >&2; exit 1 ;; esac

RUN="runs/${TASK}-${TIER}"
if [ -e "$RUN" ]; then
  [ "$FORCE" = "--force" ] || { echo "$RUN exists — pass --force to redo (old run is deleted)" >&2; exit 1; }
  rm -rf "$RUN"
fi
mkdir -p "$RUN"

copy_inputs() {           # what the TASK itself provides, tier-independent
  cp "$DIR/TASK.md" "$RUN/"
  case "$TASK" in
    t1) mkdir -p "$RUN/input" && cp "$DIR/input/server.log" "$RUN/input/" ;;
    t3) cp "$DIR/config.json" "$RUN/" ;;
    t5) node "$DIR/validate/setup.mjs" "$RUN" >/dev/null ;;
  esac
}

case "$TIER" in
  h3)
    rsync -a --exclude node_modules --exclude runs --exclude '.score-ws' "$DIR/" "$RUN/"
    rm -f "$RUN/README.md" "$RUN/opencode.json" 2>/dev/null || true
    [ "$TASK" = "t5" ] && node "$RUN/validate/setup.mjs" "$RUN" >/dev/null
    echo "== $RUN ready (full environment)."
    echo "   cd $RUN && pi"
    echo '   prompt:  Do the task in TASK.md — follow the workspace conventions.'
    ;;
  h2)
    copy_inputs
    echo "== $RUN ready (bare agent: brief + inputs, no environment)."
    echo "   cd $RUN && pi"
    echo '   prompt:  Complete the task described in TASK.md.'
    ;;
  h1)
    copy_inputs
    if [ "$TASK" = "t5" ]; then
      cat > "$RUN/NOTE.md" <<'EOF'
T5 under H1 fails BY CONSTRUCTION: a one-shot chat completion cannot touch a filesystem.
This run dir holds the untouched fixtures; score it to record the 0 honestly.
EOF
      echo "== $RUN ready. T5/H1 is the by-construction fail — score it as-is (see NOTE.md)."
    else
      node lib/h1-oneshot.mjs "$RUN" "$DELIV"
      echo "== $RUN done (one-shot). Artifact: $RUN/$DELIV — now: ./score.sh $TASK $TIER"
    fi
    ;;
esac
