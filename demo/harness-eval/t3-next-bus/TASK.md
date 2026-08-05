# Task T3: a live next-bus departure board

> This brief is identical in every harness tier. Deliverable: `index.html` in the
> workspace root (for the one-shot tier: reply with only that file's contents).

## The brief

A single-file browser departure board for one bus stop, driven by TfL's live Arrivals API.
The board must show what the API says **right now** — the validator independently queries
the same API and cross-checks your rows, and the human check is standing at the stop.

## Data source (keyless)

- Read `./config.json` (sits next to `index.html`): `{ "stopId", "stopName", "apiBase" }`.
- Fetch `${apiBase}/StopPoint/${stopId}/Arrivals` — a JSON array of predictions; the fields
  you need: `lineName`, `destinationName`, `expectedArrival` (ISO 8601), `timeToStation`
  (seconds).

## Rules

1. Map each prediction to a row: **line** (`lineName`), **destination**
   (`destinationName`), **etaMin** (`round(timeToStation / 60)`, shown as "due" when 0),
   **expectedIso** (`expectedArrival`). Sort ascending by `etaMin`; show at most 10.
2. Refresh automatically every ≤ 30 s; show the stop name and a last-updated clock.
3. Fetch failure (or empty response) shows a **visible, honest state** on the board — never
   a blank page, never stale rows presented as live; record the reason in `errors`.
4. Zero uncaught errors, ever — including while the API is unreachable.

## Testability contract (required — the validator drives it)

```js
window.__busBoard = {
  stopId: "",           // from config.json
  departures: [],       // [{ line, destination, etaMin, expectedIso }] as rendered, sorted
  lastFetchIso: "",     // ISO time of the last successful fetch
  errors: [],           // human-readable strings for any fetch/parse failure shown in the UI
};
```

## Acceptance checklist

1. Single `index.html` + the provided `config.json`; no other assets, no libraries, no keys.
2. Board renders live rows matching the API (line, destination, minutes), sorted, ≤ 10.
3. Auto-refresh ≤ 30 s; stop name + last-updated shown.
4. Blocked API ⇒ visible error state + `errors` populated, no uncaught errors.
5. The contract above is live and matches what is rendered.
