# DRIFT REPORT — RUNBOOK-litellm-dashboard, run 2026-08-06

Mode: **fresh** (no `litellm.env`, no `litellm-postgres` container; `:4000` keyless-200 = DB-less baseline). Attempted on `promaxgb10-41b1` over the front door greened 2026-08-04. Executed by agent (Claude Code / Fable 5). Recon per CONVENTIONS §4; no step edited, no pin changed.

## PIN CHECKS (deterministic)

```
[OK]    litellm           installed 1.95.0 == PyPI stable 1.95.0 == the front-door validated baseline (2026-08-04) — no float drift
[INFO]  litellm           pre-releases beyond stable: v1.96.0-rc.1 (2026-08-03), v1.97.0-dev.1 (2026-08-05) — pip does not install these
[OK]    postgres image    pin is the MAJOR (postgres:17); current upstream minor 17.10 — a run that reaches Phase 3
                          pulls it fresh and records server_version + digest in RESULTS (none validated yet; this run halted pre-Phase-3)
[OK]    CONFIG            examples/litellm-config.dashboard.yaml present (2026-08-05); twin-config gate 1d run — see RESULTS
```

## SOURCE SCAN (advisory)

```
[INFO] litellm: nothing newer than the PINS date (2026-08-05) on the stable channel touching master_key auth,
       /key/generate, /ui, prisma, DATABASE_URL, or spend logging — 1.95.0 remains the surface this overlay targets
       https://github.com/BerriAI/litellm/releases
[INFO] postgres: 17.x line advancing normally (17.9 → 17.10); within-major float is the pin's design
       https://hub.docker.com/_/postgres
```

## CROSS-RUNBOOK DRIFT (found at execution time)

```
[FLAG] the stale `chat` alias is in THIS overlay's Phase 1a fleet loop too (`for m in chat coach embed workhorse`) —
       propagated from the front-door runbook's Phase 1 into a file authored 2026-08-05, four days after `chat`
       was retired from the base lineup (2026-08-01) and a day after DRIFT-litellm-front-door-2026-08-04 flagged
       the identical bug in the front-door gate. The amendments PR should fix BOTH overlay gates (and the
       front-door topology diagram) in one pass, or the stale list will keep re-propagating into new overlays.
```

## VERDICT

**0 pin drift, 1 cross-runbook flag (the `chat` propagation). Procedure unchanged — the run proceeded on PINS and was then halted by the Phase 1c port gate (`:5432` owned by a foreign Postgres, `finproxy-postgres`) — see [`RESULTS-litellm-dashboard-2026-08-06.md`](./RESULTS-litellm-dashboard-2026-08-06.md).** Resolution of the halt is an operator decision (free the port or a PINS PR changing the bind), not a pin promotion.

---

## RUN 2 ADDENDUM (same day, post-promotion)

Operator chose the PINS route: **bind promoted `127.0.0.1:5432` → `127.0.0.1:5435`** (commit 18ddf81 — the PINS block and every dependent step/gate in one reviewed commit; finproxy untouched). Recon re-asserted before re-run: litellm PyPI stable still 1.95.0 == installed; no new items. Run 2 went green — outcome, recorded baselines (postgres **17.10**, digest `sha256:7958605b…`), and three new execution-caught runbook findings (prisma generate, prisma db push, Phase 8 inspect target) are in the RESULTS file.
