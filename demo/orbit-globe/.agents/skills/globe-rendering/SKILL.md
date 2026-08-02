---
name: globe-rendering
description: globe.gl / three-globe recipes for a fast, good-looking satellite globe — pinned CDN imports, CORS-safe textures, layer choices for thousands of points, ISS highlighting. Load before writing any rendering code.
---

# Globe rendering with globe.gl

## Pinned, known-good CDN imports

```html
<script src="https://cdn.jsdelivr.net/npm/globe.gl@2/dist/globe.gl.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/satellite.js@5/dist/satellite.min.js"></script>
```

globe.gl bundles three.js — do not also import three separately unless you need custom
objects (then use the `three` that globe.gl exposes, or import the matching version).

## CORS-safe textures (the community-standard set)

```js
const globe = Globe()(document.getElementById('globe'))
  .globeImageUrl('https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-blue-marble.jpg')
  .bumpImageUrl('https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-topology.png')
  .backgroundImageUrl('https://cdn.jsdelivr.net/npm/three-globe/example/img/night-sky.png');
```

Hotlinking NASA or threejs.org textures fails CORS intermittently — the jsdelivr three-globe
example images are the safe path. A procedural/canvas texture is an acceptable zero-network
alternative and looks deliberate rather than broken.

## Layers: the right tool per object count

- **Thousands of satellites → `particlesData`/`pointsData`** (GPU points; one material).
  With `pointsData`: `pointAltitude` in globe-radius units (`altKm / 6371`), tiny
  `pointRadius` (~0.08), `pointColor` by constellation.
- **The ISS → its own small `objectsData` entry or a single larger, brighter point + a
  `labelsData` label** ("ISS"), so it pops against the swarm. Consider `ringsData` pulse.
- **Orbit path on hover/click**: propagate ±45 min of the selected satrec into a `pathsData`
  arc. Do this only for the selected satellite — not the whole catalog.
- The official globe.gl `satellites` example (github.com/vasturiano/globe.gl →
  example/satellites) is the proven skeleton for exactly this app: CelesTrak fetch →
  `twoline2satrec` → per-frame propagate → `TIME_STEP` stepping. Reuse its structure.

## Performance + polish checklist

- One `requestAnimationFrame` loop owns simTime; update the data array in place and call
  the layer setter once per frame (globe.gl diffs efficiently).
- `globe.controls().autoRotate = true` with a slow speed for the idle shot.
- HUD: satellite count, sim clock, time-warp factor, ISS lat/lng/alt readout — small
  monospace overlay, top-left; it's what makes the demo legible in a video frame.
- Resize handler (`globe.width(innerWidth).height(innerHeight)`), dark background, no
  scrollbars (`body{margin:0;overflow:hidden}`).
