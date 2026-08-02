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

## Verifying your work

Serve the file (`python3 -m http.server 8043`), open it, and check against the acceptance
list in `TASK.md`. If a browser isn't available to you, at minimum lint the HTML structure,
re-read the two skills' gotcha sections, and state plainly which checks you could not run.
