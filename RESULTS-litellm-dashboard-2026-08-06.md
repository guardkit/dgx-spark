# RESULTS — LiteLLM Dashboard (2026-08-06) — **RUN HALTED at Phase 1c (by design)**

**Mode:** fresh (no `litellm.env`, no container, `:4000` keyless-200). Attempted on `promaxgb10-41b1` over the 2026-08-04 green front door. Executed by agent (Claude Code / Fable 5).
**Outcome:** the **Phase 1c port gate halted the run** — `:5432` is owned by a *foreign* live Postgres. **No side-effect phase ran: no secrets were minted, no container/volume created, no config or unit changed.** The box is exactly as the front-door runbook left it (DB-less, keyless `:4000`). This is the gate doing its job, not a failed deployment.

## Gate outcomes (Phase 7 table, as far as the run reached)

| Gate | Result | Note |
|---|---|---|
| P0 drift report emitted + reviewed | **PASS** | [`DRIFT-litellm-dashboard-2026-08-06.md`](./DRIFT-litellm-dashboard-2026-08-06.md) — 0 pin drift; 1 flag (stale `chat` propagated into this overlay's own 1a) |
| P1a front door green (`:4000`) + fleet green (`:9000`) | **PASS (on intent)** | keyless 200 = fresh mode; verbatim fleet loop FAILs only on `chat` (retired 2026-08-01 — third file carrying the stale list) |
| P1b docker usable | **PASS** | |
| P1c `:5432` ours/free | **FAIL → STOP** | `finproxy-postgres` (postgres:16-alpine, up 41 h, healthy) publishes `0.0.0.0:5432→5432`; also on-box: `api-test-pg-factory1` at 127.0.0.1:**5433**, `st-autobuild-pg` at 127.0.0.1:**5434** |
| P1d twin-config invariant | **PASS** | comment-stripped delta is exactly the `general_settings` block (`master_key` + `database_url`), nothing else |
| P3–P5 (container, auth flip, key lifecycle, UI, spend) | **not reached** | halted before all side effects |

## Recorded numbers

- litellm installed **1.95.0** == PyPI stable (no float drift since the 2026-08-04 baseline)
- postgres:17 upstream minor at recon time: **17.10** (nothing pulled/validated — run halted pre-Phase-3)

## Resolution — an operator decision, per the gate's own text ("free the port or change the bind via a PINS PR")

1. **Free `:5432`** — rebind `finproxy-postgres` off host-port 5432 (it is finproxy's DB; not this runbook's to move), then re-run this overlay; **or**
2. **PINS PR changing this overlay's bind** — e.g. `127.0.0.1:5435` (note **5433 and 5434 are also taken** by the other project DBs above). `DATABASE_URL` is minted in Phase 2 *from* the bind, and no secrets file exists yet, so a bind change now is clean — nothing downstream to migrate.

**Also resolve before re-running — the demo-box coupling (this runbook's own ⚠ header):** [`CAPTURE-single-spark-video.md`](./CAPTURE-single-spark-video.md) still scripts the on-camera *DB-less* beat on this box ("no `/ui` spend dashboard — that's the documented opt-in"), and the 2026-08-06 video roadmap does not record the single-spark video as filmed. Applying this overlay before that shot is captured re-scripts the beat. Confirm filmed-or-rescripted, then re-run.

## Failures & follow-ups

- **F1 — stale `chat` in this overlay's Phase 1a** (third occurrence across the runbook family; flagged in the DRIFT): fix all carriers in the one amendments PR — base 0.1 snippet aside, the alias lists in front-door Phase 1 + its diagram, and dashboard Phase 1a.
- **Side observation (outside this runbook's scope):** `finproxy-postgres` publishes on **`0.0.0.0`** — that Postgres is reachable from the LAN, unlike every other DB container on the box (loopback-bound) and unlike this overlay's own loopback-only pin. Worth a deliberate look from the finproxy side.
