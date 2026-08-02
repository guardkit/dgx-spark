# Task: the whole-sky constellation globe (ISS highlighted)

> The on-camera prompt can be one sentence — the environment (AGENTS.md + skills) carries
> the rest. Canonical phrasing:
>
> **"Build the constellation globe described in TASK.md — follow the workspace conventions."**

## The brief

A single-file browser app: an interactive 3D Earth showing **every active satellite** as a
live, propagated point cloud — Starlink, GPS, the lot — with **the ISS highlighted and
labelled**, orbit path on selection, and time-warp controls.

This is the ISS-tracker genre, 2026 edition: strictly harder than the classic single-dot
tracker (which is training-data-saturated), visually spectacular, and still instantly
legible to anyone watching.

## Acceptance checklist

1. Loads from one `index.html` with no build step, no keys, no backend.
2. Fetches CelesTrak active-catalog TLEs once; **all positions come from in-browser SGP4
   propagation** (smooth motion — no per-second API polling).
3. Thousands of satellites render at interactive frame rates; decayed/invalid elements are
   filtered, not crashed on.
4. The ISS is visually distinct (color/size/label) and shows a live lat/lng/alt readout.
5. Clicking/hovering a satellite shows its name and orbit path (±45 min).
6. Time-warp control (1× / 60× / 600×) works and the HUD shows sim time + satellite count.
7. TLE-fetch failure shows a visible error state, not a blank globe.
8. Zero console errors.
9. The `window.__orbitGlobe` testability contract (AGENTS.md) is live and accurate, the
   sim **boots at 1× real time**, and `validate/` reports **all gates green** — including
   the physics oracle (your ISS position vs an independent SGP4 propagation and the live
   wheretheiss.at API).

## Warm-up variant (optional first take)

The classic: single ISS tracker — one globe, one moving ISS marker with ground-track trail,
position cross-checked once against wheretheiss.at. Same conventions apply. Good as a quick
first take to verify the harness/endpoint wiring before the full constellation run.
