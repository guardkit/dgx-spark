---
name: filesystem-hygiene
description: Technique for bulk file reorganization tasks — plan-then-execute, hashing, collision handling, and leaving the tree provably clean.
---

# Filesystem hygiene — technique

- **Plan first, move second.** Walk the tree once and build the full source→target mapping
  in memory (with hashes and sizes) *before* touching anything — collision numbering and
  the manifest both need the complete picture, and computing them mid-move is how files
  get eaten. Then execute the plan; the manifest is just the plan serialized.
- **Hash before and after.** Compute each file's digest before moving and verify it at the
  destination — `mv` across the same filesystem shouldn't alter bytes, but the check is
  free and turns "should be fine" into evidence.
- **Dates:** read the spec's precedence rules as a strict cascade and implement them as
  one function you can unit-test against a few names by hand. Use UTC everywhere —
  `stat` mtimes and locale-formatted dates both bite otherwise.
- **Collisions:** deterministic ordering (sort the source paths first) is what makes
  numbering reproducible — iteration order of a directory walk is not a specification.
- **Finish clean:** remove now-empty directories bottom-up (deepest first), then do a
  final walk asserting the invariants yourself — count in == count out, no stragglers —
  before declaring done. Your own final walk is a rehearsal of exactly what any validator
  will do.
