---
name: live-transit-board
description: Technique for boards driven by live polling APIs — refresh loops that don't drift, honest failure states, and live-data display pitfalls.
---

# Live transit boards — technique

- **One fetch function, one render function**, and a `setInterval`-driven loop that calls
  fetch→map→render; never interleave DOM writes with parsing. Guard against overlapping
  requests (skip the tick if one is in flight) and use an `AbortController` timeout (~10 s)
  so a hung request can't wedge the loop.
- **Honest failure is a feature**: catch *every* rejection path (network, non-200, bad
  JSON, empty array) into one visible state — what failed, when last data was seen. A
  departure board showing stale rows as live is worse than one saying "no data".
- **Live-data display pitfalls**: ETAs drift between refreshes — recompute display minutes
  from the timestamp at render time, don't cache the string. Clamp negatives to "due".
  Sort *after* mapping, not on raw API order (it is not guaranteed sorted).
- **Keep the DOM stable**: rebuild the rows list in place (a fixed table/list container) so
  refreshes don't jump the layout; render the last-updated clock from the contract object
  so the two can't disagree.
- **Test the sad path deliberately**: DevTools offline (or block the API host) and watch
  what the board does — that path is always gated in this genre.
