# T3 — workspace conventions

You are building the departure board described in `TASK.md` — read it first; it is the
complete spec, including the endpoint, field mapping, and testability contract. Load the
`live-transit-board` skill in `.agents/skills/` before writing code: it carries technique
(refresh loops, failure handling, live-data pitfalls), not extra requirements.

## Rules

- **Only two requests are legal**: `./config.json` and the configured TfL endpoint. Any
  other external `src`/`href`/fetch fails a gate. No libraries, no fonts, no images.
- The contract object must describe **what is actually rendered** — the validator compares
  both against its own independent API fetch; a board that renders one thing and reports
  another fails.
- **Verify mechanically before claiming done:** `cd validate && npm run setup` (once —
  installs Playwright Chromium), then `npm run validate`. Iterate until every gate is
  green. Note the oracle is a **live API**: at very quiet hours it can legitimately return
  no arrivals — the gates account for that, your board must too. If you cannot run the
  validator, say so plainly — never claim gates you didn't run.
