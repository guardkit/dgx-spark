---
name: satellite-tracking
description: TLE data sources, SGP4 propagation with satellite.js, and the CORS/rate-limit gotchas for browser-side satellite tracking. Load before writing any orbital code.
---

# Satellite tracking in the browser

## Data sources (keyless, HTTPS, CORS-friendly)

- **CelesTrak GP data (bulk TLEs)** — the primary source:
  `https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle`
  Returns three-line elements (name + 2 TLE lines) for ~10k active satellites. Groups worth
  knowing: `GROUP=stations` (includes ISS — small, fast), `GROUP=starlink`, `GROUP=gps-ops`.
  Fetch **once per session**; TLEs are valid for days. Cache in memory.
- **wheretheiss.at** — live ISS position for cross-checking only:
  `https://api.wheretheiss.at/v1/satellites/25544` → `{latitude, longitude, altitude, velocity}`.
  Soft limit ~1 request/second. Do not drive animation from it.
- **ISS NORAD catalog id: 25544** (name in CelesTrak data: "ISS (ZARYA)").
- **Never open-notify.org** — HTTP-only; mixed-content blocked on HTTPS pages.

## SGP4 propagation with satellite.js

CDN: `https://cdn.jsdelivr.net/npm/satellite.js@5/dist/satellite.min.js` (global `satellite`).

```js
const satrec = satellite.twoline2satrec(tleLine1, tleLine2);
const posVel = satellite.propagate(satrec, new Date(simTime));   // ECI km
const gmst   = satellite.gstime(new Date(simTime));
const geo    = satellite.eciToGeodetic(posVel.position, gmst);
const lat = satellite.degreesLat(geo.latitude);   // degrees
const lng = satellite.degreesLong(geo.longitude);
const altKm = geo.height;
```

- `propagate` returns `position: false` for decayed/bad elements — **filter those satrecs
  out at load time** (check one propagation per sat at t0 and drop failures) or the render
  loop throws on NaN.
- Parse the 3-line format defensively: trim names, skip blank trailing lines.

## Time stepping (the smooth-motion pattern)

Keep a `simTime` that advances by `TIME_STEP` per animation frame (e.g. +3000 ms per frame
for a visibly orbiting constellation; 1× real time makes the ISS crawl). Recompute positions
from SGP4 each frame — it is fast enough for thousands of satellites. Offer a small time-warp
control (1× / 60× / 600×) — it reads brilliantly on camera.

## Common failures

- Whole-catalog `eciToGeodetic` per frame is fine; creating new `Date` objects per satellite
  per frame is not — hoist `new Date(simTime)` and `gstime` out of the per-sat loop.
- Longitude from `degreesLong` is already ±180 — don't re-wrap it.
- A "satellites underground" look = you passed radians where degrees were expected (or vice
  versa) to the globe layer. globe.gl wants **degrees** and altitude in globe radii.
