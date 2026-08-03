# eugr B12X 0731 recipe — archived A/B candidate (NOT the lane of record)

Two attachments from bernisse's post (NVIDIA forum t/376220 post 18, 2026-08-03), archived
2026-08-03 while the forum S3 links were live:

- `dsv4.txt` — the recipe (vLLM serving `deepseek-ai/DeepSeek-V4-Flash-0731` on dual Sparks
  via the B12X docker stack; fp8 KV, DSpark nst=5, full tool-calling).
- `run.txt` — the 0731 reasoning-effort fix.

**Status per the 2026-08-03 keep-or-pivot assessment:** fully shareable provenance (better
than our manual Patch-4 mount), fixes a reasoning-effort bug, **but** ~36 h old with one
independent reproducer, fp8 KV (half nvfp4_ds_mla's density — 1M ctx unverified), and no
published acceptance/decode numbers. Verdict: the tonyd2wild pin stays the lane of record
(three independent reproductions); this stack runs as a **measured A/B in a later session**.
Its bar to displace the pin: match ~60% draft acceptance AND verify 1M ctx at fp8 KV.
