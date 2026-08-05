# T5 — workspace conventions

You are reorganizing `work/` as specified in `TASK.md` — read it first; it is the complete
spec. Load the `filesystem-hygiene` skill in `.agents/skills/` before acting: it carries
technique (safe move patterns, manifest-first design), not extra requirements.

## Rules

- **Only `work/` and `manifest.json` may be touched.** Never modify `validate/`, the
  skills, or this file. No network.
- A wrong move is recoverable: `cd validate && npm run reset` restores the pristine
  `work/` tree (fixed contents *and* fixed mtimes) — but resets throw away your progress,
  so plan before moving.
- Scripts are fine (this is a scripting task at heart); remove scratch files when done —
  the end-state of the tree is the deliverable.
- **Verify mechanically before claiming done:** `cd validate && npm run validate` (no
  install needed — zero dependencies). Iterate until every gate is green. If you cannot
  run the validator, say so plainly — never claim gates you didn't run.
