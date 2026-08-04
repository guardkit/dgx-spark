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

**Update 2026-08-04 recon:** maturing fast — thread grew to 31 posts: a published b12x
benchmark (pp2048 prefill 1,832 t/s, tg32 37.6 t/s peak 38.8), bernisse reporting 55+ tok/s
at 2–4 concurrent contexts and **tool-bench 93/100**, a `--load-format safetensors
--safetensors-load-strategy lazy` flag pair that frees KV headroom (candidate for any A/B),
and eugr_nv stating b12x is merged to main with a TP=3 path (2.8M-token KV across three
Sparks). Caveat: eugr/spark-vllm-docker's commit log shows only README-level b12x support —
no visible merge commit or nightly-CI workflow yet, so verify the repo state before ever
re-basing on "main". A/B priority: raised, still later-session.
