# T2 — workspace conventions

You are building the chess board described in `TASK.md` — read it first; it is the complete
spec, including the testability contract. Load the `chess-move-generation` skill in
`.agents/skills/` before writing code: it carries technique (movegen structure, the classic
legality traps), not extra requirements.

## Rules

- **Self-contained means self-contained**: the validator loads the page with all network
  requests blocked. Any external `src`/`href` fails a gate.
- Engine first, UI second — the gates interrogate `window.__chess`, and a pretty board
  wrapped around a wrong move generator scores zero.
- **Verify mechanically before claiming done:** `cd validate && npm run setup` (once —
  installs Playwright Chromium + Stockfish), then `npm run validate`. Iterate until every
  gate is green. If you cannot run the validator, say so plainly — never claim gates you
  didn't run.
