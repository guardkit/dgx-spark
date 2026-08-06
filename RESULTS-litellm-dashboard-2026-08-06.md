# RESULTS — LiteLLM Dashboard (2026-08-06) — halt → PINS promotion → **GREEN**

**Two runs, one day, on `promaxgb10-41b1`** over the 2026-08-04 front door. Executed by agent (Claude Code / Fable 5). **First green walkthrough of this overlay — `:4000` is now authenticated with persisted keys + spend.** The arc is the conventions working end-to-end: a gate halted run 1, the fix was a reviewed PINS commit (never a runtime edit), run 2 re-ran from the top and went green.

## Run 1 (halted at Phase 1c, by design)

Fresh mode confirmed (keyless-200, no secrets, no container). **1c FAIL → STOP:** `finproxy-postgres` (postgres:16-alpine, another live project) publishes `0.0.0.0:5432`; `api-test-pg-factory1` and `st-autobuild-pg` hold 5433/5434. No side-effect phase ran. Operator decision: **move OUR bind, leave finproxy alone** → PINS promotion `bind 127.0.0.1:5432 → 127.0.0.1:5435` (commit 18ddf81), demo-box coupling explicitly confirmed cleared by the operator.

## Run 2 — Gate outcomes (Phase 7 table, filled)

| Gate | Result | Note |
|---|---|---|
| P0 drift report emitted + reviewed | **PASS** | [`DRIFT-litellm-dashboard-2026-08-06.md`](./DRIFT-litellm-dashboard-2026-08-06.md) + run-2 addendum — 0 pin drift; `chat` propagation flag |
| P1a front door green (`:4000`) + fleet green (`:9000`) | **PASS (on intent)** | keyless 200 = fresh mode; only the stale `chat` expectation failed (third carrier — see DRIFT) |
| P1b docker usable · P1c `:5435` ours/free | **PASS** | first run of the promoted pin: `:5435` free |
| P1d twin-config invariant | **PASS** | delta = `general_settings` (`master_key` + `database_url`) exactly |
| P3 postgres container healthy (`pg_isready`) | **PASS** | **17.10**, digest `postgres@sha256:7958605b…`, loopback-only `127.0.0.1:5435`, cpuset 0-3, volume `litellm-pgdata` |
| P5.1 keyless `401` **and** master-keyed `200` | **PASS** | auth flip proven both ways (re-confirmed after the F3 fix + restart) |
| P5.2 no-cloud re-asserted on deployed config | **PASS ×2** | DF-001 holds through the config swap |
| P5.3 virtual key: mint → `claude-*` local completion → revoke | **PASS** (after F3 fix) | first attempt FAILed — the gate caught the missing DB schema (below); after `prisma db push`: mint ✓, 417-char local completion ✓, revoke ✓ — supersedes front-door 4.3 on this box |
| P5.4 `:4000/ui` serving | **PASS** | login: `admin` / master key (`grep LITELLM_MASTER_KEY /opt/litellm/litellm.env`) |
| P5.5 spend rows in `LiteLLM_SpendLogs` | **PASS** | 2 rows persisted (the 5.3 completions) |

## Recorded numbers (the validated baselines)

- **litellm 1.95.0** (unchanged from the front-door baseline; PyPI stable at run time)
- **postgres 17.10** (Debian 17.10-1.pgdg13+1), image digest `postgres@sha256:7958605b474b3d264a969cb3a123d6aa00ad1e1fe9da8a69984dabb704d93317`, 68 tables after schema push
- Keyed `:4000` start after the prisma fixes: **~15–20 s**
- Secrets at `/opt/litellm/litellm.env` (0600, never committed); UI reachable at `:4000/ui`

## Drift report

[`DRIFT-litellm-dashboard-2026-08-06.md`](./DRIFT-litellm-dashboard-2026-08-06.md) — 0 upstream pin drift. **Promoted this run: `bind` 5432→5435** (the run-1 gate catch; commit 18ddf81). Nothing else promoted.

## Failures & follow-ups (amendments PR, alongside the earlier family findings)

- **F1 — stale `chat` in Phase 1a** (third carrier across the family; in the DRIFT).
- **F2 — Phase 2's prisma assert is insufficient:** `python3 -c "import prisma"` passes while the **engine binaries are absent**, and litellm 1.95.0 then crash-loops on startup (`Unable to find Prisma binaries. Please run 'prisma generate' first.` — 18 restarts before the fix). Amend Phase 2 to run: `prisma generate --schema="$(python3 -c 'import litellm,os;print(os.path.dirname(litellm.__file__))')/proxy/schema.prisma"`.
- **F3 — Phase 4's "prisma … pushes the schema into Postgres" does not happen** on this install (pip-user litellm 1.95.0 + prisma 0.15.0): the proxy starts and answers keyed-200 with an **empty database**, and the failure surfaces only when gate 5.3's `/key/generate` hits `TableNotFoundError: public.LiteLLM_VerificationToken`. The gate design worked — 5.3 exists precisely to prove the DB write path. Amend Phase 4 to add, after the config deploy: `prisma db push --schema=… --skip-generate` (then restart). Update the Phase 9 prisma triage row with both F2/F3 commands.
- **F4 — Phase 8 evidence command inspects the wrong object:** `docker inspect --format '{{index .RepoDigests 0}}' litellm-postgres` fails (`RepoDigests` lives on the **image**, not the container — Phase 3's variant is correct). Amend to inspect `postgres:17` for the digest.
- **Phase 6 (operator step, open):** nothing was repointed at `:4000` before this overlay, so no client broke — but any future consumer needs a **virtual key** minted per agent (`/key/generate`, budgets). Master key stays UI/admin-only. `:9000` direct remains the documented LiteLLM-down fallback (DF-001 §3.3).
