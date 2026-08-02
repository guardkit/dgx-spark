# Orbit Globe — workspace conventions

You are building a small, visually impressive, browser-only satellite-tracking app in this
workspace. Read `TASK.md` for the brief. Two skills in `.agents/skills/` carry the domain
knowledge — load them before writing code: `satellite-tracking` (TLE/SGP4/data sources) and
`globe-rendering` (globe.gl/three.js recipes and safe asset URLs).

## Deliverable shape (non-negotiable)

- **One self-contained `index.html`.** No build step, no bundler, no backend, no npm install.
  Libraries come from CDN via pinned versions (the rendering skill lists known-good pins).
- **No API keys, ever.** Only the approved endpoints below — they are keyless and CORS-safe.
- Opening the file in a browser (or via `python3 -m http.server`) is the entire deployment.

## Approved network endpoints (anything else: assume blocked)

| Purpose | Endpoint |
|---|---|
| TLE sets (bulk, all active sats) | `https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle` |
| ISS position spot-check | `https://api.wheretheiss.at/v1/satellites/25544` (~1 req/s max) |
| Globe textures / lib assets | `https://cdn.jsdelivr.net/npm/three-globe/example/img/*` |
| Libraries | `https://cdn.jsdelivr.net/npm/*`, `https://unpkg.com/*` |

**Never use open-notify.org** — it is HTTP-only and silently dies to mixed-content blocking
on any HTTPS page. This is the single most common failure in this genre.

## Engineering rules

- **Propagate, don't poll.** Fetch TLEs once, run SGP4 in-browser (satellite.js), and step
  time locally for smooth motion. Position-polling APIs are for a one-time sanity cross-check
  at most — a dot that jumps once a second reads as broken on camera.
- Target 60fps with thousands of objects: use point/instanced rendering for the constellation,
  a distinct highlighted object + label for the ISS.
- Zero console errors or unhandled promise rejections in the final artifact.
- Degrade gracefully: if the TLE fetch fails, say so visibly in the UI — never a blank globe.
- Vanilla JS. Comment only what is non-obvious (frame stepping, coordinate conversions).

## Testability contract (required — the validator depends on it)

The app must expose a small machine-readable status object, updated **every frame**:

```js
window.__orbitGlobe = {
  satCount: 0,          // satellites currently rendered (post-filtering)
  simTime: Date.now(),  // current sim clock, ms epoch
  timeWarp: 1,          // current warp factor (MUST boot at 1× real time, simTime = now)
  iss: { lat: 0, lng: 0, altKm: 0 },   // degrees; the highlighted ISS position
  errors: []            // human-readable strings for any fetch/parse failure shown in the UI
};
```

This is part of the spec, not test scaffolding — it is also what drives your HUD, so build
the HUD *from* this object and both stay honest together.

## Verifying your work

Mechanical first: `cd validate && npm run setup` (once) `&& npm run validate` — a
three-tier gate suite (static checks · headless runtime checks against the contract above ·
an independent SGP4 + live-API physics oracle for the ISS position). **Iterate until every
gate is green**; the suite prints a PASS/FAIL table and exits non-zero on any FAIL.
Then the human check: serve the file (`python3 -m http.server 8043`), open it, and walk the
acceptance list in `TASK.md`. If you cannot run the validator, say so plainly — never claim
gates you didn't run.
