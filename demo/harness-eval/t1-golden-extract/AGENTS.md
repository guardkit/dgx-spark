# T1 — workspace conventions

You are producing `extract.json` in this workspace root. Read `TASK.md` for the brief —
it is the complete spec. Load the `log-forensics` skill in `.agents/skills/` before writing
code: it carries technique (parsing strategy, normalization pitfalls), not extra requirements.

## Rules

- **No network access needed or allowed** — everything is in `input/server.log`.
- Work however you like (a throwaway script is fine), but the deliverable is the JSON file,
  not the script. Remove scratch files when done.
- **Verify mechanically before claiming done:** `cd validate && npm run validate` (no
  install needed — zero dependencies). Iterate until every gate is green. If you cannot run
  the validator, say so plainly — never claim gates you didn't run.
