# Runbook: LiteLLM Virtual Keys + Spend Dashboard (Postgres) — Additive Overlay over the `:4000` Front Door

**Status:** **Verified** (additive **overlay** per [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) §2.1 — an overlay **over the front-door overlay**). First green walkthrough 2026-08-06 on `promaxgb10-41b1`, over the 2026-08-04-green front door — a full halt→promotion→re-run arc: the 1c port gate stopped run 1, the bind moved 5432→5435 by a reviewed PINS commit, run 2 passed every Phase 7 gate ([`RESULTS-litellm-dashboard-2026-08-06.md`](./RESULTS-litellm-dashboard-2026-08-06.md); that run's findings — prisma generate, prisma db push, evidence inspect target, stale `chat` — are folded in below).

**Purpose:** Add the **opt-in control-plane persistence** the front-door runbook deliberately skips ([its "does NOT cover" list](./RUNBOOK-litellm-front-door.md)): a **master key** on `:4000`, **per-agent virtual keys** (`POST /key/generate`, budgets), and the **spend dashboard** at `:4000/ui` — backed by a **containerized Postgres**. Routing is untouched: the DF-001 no-cloud guard, the `claude-*` wildcard, and llama-swap `:9000` underneath are byte-identical policy. **Auth changes WHO may call `:4000`, never WHERE a request can route.**

```
clients (agents, Claude Code — now each holding a VIRTUAL KEY)
   │  Authorization: Bearer sk-…      ← THIS overlay flips :4000 from open to authenticated
   ▼
LiteLLM :4000  ──────────────► Postgres :5435 (docker, loopback-only)   ← keys · spend · dashboard state
   │   (unchanged: claude-* wildcard · DF-001 no-cloud · x-litellm-response-cost)
   ▼
llama-swap :9000               ← the fleet (UNCHANGED — this overlay never touches it)
```

**Prereq (hard, asserted in Phase 1):** the box is **GREEN** on [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) (its Phase 5 table) — LiteLLM serving on `:4000` under its user unit, fleet on `:9000`. This overlay does not re-run any front-door phase; it adds a secrets file, a Postgres container, a config variant, and a unit **drop-in** (the front-door unit file itself is untouched).
**Conventions:** [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) §2.1 (overlay = precondition gate) · §3 (pins; the Postgres note below) · §8 (LiteLLM gate rows).
**One-time box setup:** passwordless sudo; agent runs as the operator user — see [README → Running a runbook](./README.md#one-time-box-setup-passwordless-sudo). Docker must be usable by that user (DGX OS ships it; gate in Phase 1).
**Decision record:** [`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md) — LiteLLM as the single-Spark control plane; this overlay turns on the persistence half of that control plane.
**Expected wall-clock:** ~10 min (image pull + LiteLLM's first DB start — prisma engine download + schema push — dominate; needs network once).
**Outputs:** `RESULTS-litellm-dashboard-<YYYY-MM-DD>.md`, committed `DRIFT-litellm-dashboard-<YYYY-MM-DD>.md`, the live `/opt/litellm/config.yaml` (dashboard variant), and `/opt/litellm/litellm.env` (**never committed**).

---

## PINS (this overlay's block — additive to the front-door overlay's PINS)

```
PINS (set 2026-08-05)
  postgres image   postgres:17                docker library, linux/arm64. MAJOR is the pin (on-disk format);
                                              minors float within 17.x (upstream guarantees drop-in minors) —
                                              record server_version + image digest in RESULTS each run;
                                              promote a digest here by PR only if a minor ever bites.
  container        litellm-postgres           supervised by dockerd (--restart unless-stopped), NOT a user unit
                                              (a user systemd unit cannot order After= a system service; see Phase 3)
  volume           litellm-pgdata             named docker volume — keys + spend history live here; survives
                                              container recreate; destroyed ONLY by the Appendix full-removal step
  bind             127.0.0.1:5435             loopback only — never 0.0.0.0; the DB is reachable from this box only.
                                              PROMOTED 5432→5435 2026-08-06 (run 1's 1c gate caught 5432 held by
                                              finproxy-postgres; 5433/5434 also taken by api-test/st-autobuild DBs
                                              on the reference box — host port only; in-container stays 5432)
  db / user        litellm / litellm
  cpuset           0-3                        same cores as the litellm unit — the control plane stays off the
                                              fleet's cores 4-19 (front-door Phase 4.2 philosophy)
  secrets          /opt/litellm/litellm.env   0600. LITELLM_MASTER_KEY (sk-…) + POSTGRES_PASSWORD + DATABASE_URL.
                                              Created once (Phase 2); re-runs REUSE it — never rotated silently;
                                              NEVER committed (evidence capture excludes it by construction).
  CONFIG           examples/litellm-config.dashboard.yaml   (public config + general_settings — the ONLY value
                                              delta, asserted by the Phase 1 twin-config gate)
  litellm          (no separate pin — float-with-baseline inherited from the front-door PINS; validated 1.95.0)
```

When recon flags drift, the fix is a **PR editing this block** — never a runtime edit.

---

## Execution modes

```
Execution modes (CONVENTIONS §2.2):
  fresh    — first flip to authenticated + persisted, on a box green on the front-door overlay
  re-run   — same file again; secrets are reused (not rotated), container/volume/config writes are
             skip-if-present or overwrite-safe, the gates re-verify
  update   — Phase 0 recon flags a LiteLLM release or a Postgres 17.x minor; re-run — pip pulls latest
             litellm (front-door Phase 2 owns that), docker pull refreshes 17.x; gates re-prove; RESULTS
             records the new baselines. A Postgres MAJOR (18+) is a pin edit + migration plan, NOT a re-run.
```

---

## What this overlay does NOT cover

- **The front door itself** (install, unit, CPU pins, `claude-*` routing) — that is [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md), already green underneath.
- **Any routing change.** The dashboard config's `model_list`/`router_settings` are value-identical to the public config (gate-asserted). Want a routing change? Edit the **public** config first, mirror here, re-run both overlays.
- **Cloud-LLM escalation.** Still zero cloud on the critical path (DF-001) — the no-cloud gate re-asserts on the deployed dashboard config in Phase 5.2.
- **Postgres backups/HA.** The named volume persists across container recreates and reboots; dump/restore discipline beyond that is future work (a `pg_dump` cron is the obvious follow-up once spend history matters).

---

## Phase 0: Recon (read-only, advisory) — emits the drift report

No side effects. Degrades gracefully (DF-001): network down → record `recon: skipped` and proceed on the PINS.

```
RECON SOURCES (fixed)
  - github.com/BerriAI/litellm  releases since the front-door PINS date — ONLY items touching the
    surfaces this overlay adds: master_key auth, /key/generate, /ui, prisma schema/migrations,
    DATABASE_URL handling, spend logging
  - hub.docker.com/_/postgres   17.x tags — new minor within 17, or a 17→18 major bump
TASK: "Report only items newer than the PINS date affecting the DB/auth/UI surface above, or the
       postgres 17.x line. Emit a drift report. Do NOT propose edited steps. Do NOT change any pin."
```

Write `DRIFT-litellm-dashboard-<timestamp>.md` (conventions §5) and commit it next to the RESULTS file. **▶ GATE (advisory):** review `[DRIFT]`/`[FLAG]` before promoting anything; the run proceeds on the current PINS regardless.

---

## Phase 1: Pre-flight — **▶ GATE: front door green, docker usable, twin configs in sync**

### 1a — the front door is green on `:4000` (and which mode this run is)

The overlay asserts the front-door runbook's **output state** (CONVENTIONS §2.1). A keyless `200` proves the DB-less baseline (fresh mode); a keyless `401` **with our secrets file present** proves a previous run of *this* overlay (re-run mode). Anything else → the front door isn't green — **stop**.

```bash
MISS=
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:4000/v1/models)
if [ "$CODE" = "200" ]; then
  echo "GATE PASS: :4000 serving, keyless — DB-less baseline (fresh mode)"
elif [ "$CODE" = "401" ] && [ -f /opt/litellm/litellm.env ]; then
  echo "GATE PASS: :4000 serving, authenticated — this overlay already applied (re-run mode)"
else
  echo "GATE FAIL: :4000 gave HTTP ${CODE:-<no answer>} — front door not green. Run RUNBOOK-litellm-front-door.md to green first. STOP."; MISS=1
fi
# the fleet underneath (the front door's own precondition — cheap to re-assert):
ALIASES=$(curl -sf http://localhost:9000/v1/models | jq -r '.data[].id' 2>/dev/null | sort | tr '\n' ' ')
for m in coach embed workhorse; do   # the three always-on aliases (chat retired from the base lineup 2026-08-01)
  echo " $ALIASES " | grep -q " $m " || { echo "GATE FAIL: alias '$m' not on :9000 — base fleet not green. STOP."; MISS=1; }
done
[ -z "$MISS" ] && echo "GATE PASS: preconditions green — proceed."
```
**FAIL → halt.** Flipping auth on a broken front door just hides the breakage behind 401s.

### 1b — docker daemon usable by the operator user

```bash
docker info >/dev/null 2>&1 \
  && echo "GATE PASS: docker daemon reachable as $USER" \
  || { echo "GATE FAIL: docker unusable as $USER."; \
       echo "  fix: sudo systemctl enable --now docker && sudo usermod -aG docker $USER   # then log out/in and re-run"; }
```
**FAIL → halt** (fix is one-time box setup, then re-run this overlay).

### 1c — `:5435` is free, or already ours

```bash
if docker inspect litellm-postgres >/dev/null 2>&1; then
  echo "GATE PASS: container litellm-postgres exists (re-run mode) — Phase 3 will reuse it"
elif ss -ltn 2>/dev/null | grep -q ':5435 '; then
  echo "GATE FAIL: something else is listening on :5435 — reusing a foreign Postgres is out of scope; free the port or change the bind via a PINS PR. STOP."
else
  echo "GATE PASS: :5435 free"
fi
```

### 1d — **▶ GATE: twin-config invariant** — the dashboard config is the public config + `general_settings`, nothing else

The two example configs are the drift risk this overlay introduces (CONVENTIONS' partition principle can't apply — the deployed file must be one file). So the invariant is machine-checked: **comments stripped, the only diff is additions, and they are the `general_settings` block.**

```bash
DELTA=$(diff <(sed 's/#.*//;/^[[:space:]]*$/d' examples/litellm-config.public.yaml) \
             <(sed 's/#.*//;/^[[:space:]]*$/d' examples/litellm-config.dashboard.yaml) | grep -E '^[<>]')
echo "$DELTA"
if [ -n "$(echo "$DELTA" | grep '^<')" ]; then
  echo "GATE FAIL: the dashboard config DROPS lines the public config has — routing drift. Re-mirror from public. STOP."
elif echo "$DELTA" | grep -q 'general_settings' && echo "$DELTA" | grep -q 'master_key' && echo "$DELTA" | grep -q 'database_url' \
     && [ -z "$(echo "$DELTA" | grep '^>' | grep -vE 'general_settings|master_key|database_url')" ]; then
  echo "GATE PASS: dashboard config = public config + general_settings block, nothing else"
else
  echo "GATE FAIL: unexpected delta between the twin configs (above) — re-mirror before deploying. STOP."
fi
```
**FAIL → halt.** This is what keeps "auth changes WHO, never WHERE" true by construction.

---

## Phase 2: Secrets — mint once, reuse forever &nbsp;·&nbsp; **▶ the agent runs this step**

One 0600 file holds all three values; the systemd drop-in (Phase 4) feeds it to LiteLLM, `docker run` (Phase 3) reads the DB password from it. **Idempotent: if the file exists it is reused — a re-run never silently rotates the master key** (rotating it invalidates every minted virtual key's parent and the UI login; rotation is a deliberate operator act, not a side effect).

```bash
ENVF=/opt/litellm/litellm.env
if [ ! -f "$ENVF" ]; then
  umask 177
  MK="sk-$(openssl rand -hex 24)"
  PGPW="$(openssl rand -hex 16)"
  cat > "$ENVF" <<EOF
LITELLM_MASTER_KEY=${MK}
POSTGRES_PASSWORD=${PGPW}
DATABASE_URL=postgresql://litellm:${PGPW}@127.0.0.1:5435/litellm
EOF
  echo "[secrets] minted $ENVF"
else
  echo "[secrets] $ENVF exists — REUSED (re-runs never rotate keys)"
fi
chmod 600 "$ENVF"; ls -l "$ENVF"
# prisma: LiteLLM's DB layer. TWO steps, both idempotent — the pip package alone is NOT enough:
# `import prisma` succeeds while the engine binaries are still absent, and litellm then
# crash-loops on start with "Unable to find Prisma binaries. Please run 'prisma generate'
# first." (18 restarts observed 2026-08-06 before the generate).
python3 -c "import prisma" 2>/dev/null || pip install --user --break-system-packages prisma
PATH="$HOME/.local/bin:$PATH" prisma generate \
  --schema="$(python3 -c 'import litellm,os;print(os.path.dirname(litellm.__file__))')/proxy/schema.prisma"
```

The UI login is then **username `admin`, password = `LITELLM_MASTER_KEY`** (LiteLLM's default; `UI_USERNAME`/`UI_PASSWORD` env vars can split them later if wanted — add them to this same env file).

---

## Phase 3: Postgres container — pinned image, named volume, loopback-only

Supervision note: the container is supervised by **dockerd** (`--restart unless-stopped`), not a user systemd unit — a user unit cannot `After=` the system-level docker service, so wrapping `docker run` in one buys ordering problems, not robustness. The VS Code-cgroup trap (CONVENTIONS §8) doesn't apply: containerd owns the process tree. LiteLLM's own `Restart=on-failure` (already in its unit) absorbs the boot race: if it starts before Postgres is up it fails and retries every 5 s until the DB answers.

```bash
set -a; . /opt/litellm/litellm.env; set +a
docker volume create litellm-pgdata >/dev/null
if docker inspect litellm-postgres >/dev/null 2>&1; then
  docker start litellm-postgres >/dev/null 2>&1 || true
  echo "[postgres] container exists — reused (data in litellm-pgdata untouched)"
else
  docker run -d --name litellm-postgres \
    --restart unless-stopped \
    --cpuset-cpus 0-3 \
    --shm-size 256m \
    -e POSTGRES_DB=litellm -e POSTGRES_USER=litellm \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -p 127.0.0.1:5435:5432 \
    -v litellm-pgdata:/var/lib/postgresql/data \
    postgres:17
fi
# ▶ GATE — DB answers (pg_isready via the container; retry: first boot runs initdb)
for i in $(seq 1 24); do
  docker exec litellm-postgres pg_isready -U litellm -d litellm >/dev/null 2>&1 && break
  sleep 5
done
docker exec litellm-postgres pg_isready -U litellm -d litellm \
  && echo "GATE PASS: postgres accepting connections on 127.0.0.1:5435" \
  || { echo "GATE FAIL: postgres not ready after 120s — docker logs litellm-postgres. STOP."; }
# [record in RESULTS] the actual minor + digest this run validated:
docker exec litellm-postgres psql -U litellm -d litellm -tAc "show server_version;"
docker inspect --format '{{index .RepoDigests 0}}' postgres:17
```
**FAIL → halt.** Everything after this needs the DB.

---

## Phase 4: Deploy the dashboard config + env drop-in, restart LiteLLM

The front-door unit file stays untouched — the env feed is a **drop-in** (`20-dashboard.conf`), the same mechanism the front door uses for llama-swap's CPU pin. The config deploy mirrors the front door's own overwrite-safe pattern (backup, then install).

```bash
LCFG=/opt/litellm/config.yaml
[ -f "$LCFG" ] && cp -a "$LCFG" "$LCFG.bak-$(date +%Y%m%d-%H%M%S)" && echo "[backup] $LCFG.bak-* saved (this is also the rollback artifact)"
sudo install -D -m644 examples/litellm-config.dashboard.yaml "$LCFG"

mkdir -p ~/.config/systemd/user/litellm.service.d
cat > ~/.config/systemd/user/litellm.service.d/20-dashboard.conf <<'EOF'
[Service]
EnvironmentFile=/opt/litellm/litellm.env
EOF

systemctl --user daemon-reload

# Push the schema BEFORE the authenticated start — litellm 1.95.0 (pip-user install) does NOT
# do this itself: it comes up keyed-200 over an EMPTY database and the failure only surfaces
# at gate 5.3's /key/generate (TableNotFoundError: LiteLLM_VerificationToken — caught 2026-08-06).
# Engine binaries were generated in Phase 2; Postgres is up from Phase 3; needs DATABASE_URL:
set -a; . /opt/litellm/litellm.env; set +a
PATH="$HOME/.local/bin:$PATH" prisma db push --skip-generate \
  --schema="$(python3 -c 'import litellm,os;print(os.path.dirname(litellm.__file__))')/proxy/schema.prisma"

systemctl --user restart litellm

# First authenticated start: poll with the MASTER key until the surface answers (with the
# generate + db push above already done, this is seconds, not the old first-run stall):
for i in $(seq 1 36); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://localhost:4000/v1/models)
  [ "$CODE" = "200" ] && break
  sleep 5
done
[ "$CODE" = "200" ] \
  && echo "PASS: :4000 answering with master-key auth (took ~$((i*5))s)" \
  || { echo "FAIL: :4000 not answering keyed after 180s — tail /opt/litellm/litellm.log (prisma engine download is the usual first-run stall). STOP."; }
```

> **The coupling to know (self-healing, same shape as the front door's affinity drop-in):** a **front-door re-run overwrites `/opt/litellm/config.yaml` with the PUBLIC (DB-less) config** — auth and persistence silently revert (the drop-in and env file survive; env vars without `general_settings` in the config are inert). The heal is: **re-run this overlay** (Phase 4 redeploys the dashboard config; secrets and DB are reused untouched). Gate 5.1 is what catches the reverted state: keyless requests answering `200` on a box that has this overlay's env file is the tell.

---

## Phase 5: Trust gates

```bash
# all gates below assume:  set -a; . /opt/litellm/litellm.env; set +a
```

### 5.1 **▶ GATE — auth actually flipped: keyless 401, master-keyed 200**

Half of this gate is proving a *negative* — the old open door is closed. A keyless `200` here means the config on disk is not the dashboard config (see the Phase 4 coupling note).

```bash
ANON=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:4000/v1/models)
AUTH=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://localhost:4000/v1/models)
{ [ "$ANON" = "401" ] || [ "$ANON" = "403" ]; } && [ "$AUTH" = "200" ] \
  && echo "GATE PASS: keyless ${ANON}, master-keyed 200 — auth is live" \
  || echo "GATE FAIL: keyless=${ANON} keyed=${AUTH} — expected 401/403 + 200. If keyless=200: the PUBLIC config is deployed (front-door re-run reverted it) — re-run Phase 4. STOP."
```

### 5.2 **▶ GATE — no cloud fallback, re-asserted on the DEPLOYED config (DF-001)** &nbsp;·&nbsp; (registry: CONVENTIONS §8 "LiteLLM auto cloud-fallback")

Same assertion as the front door's 4.1 — re-run because the config file *changed* in Phase 4, and the invariant belongs to the file on disk, not to a file we once deployed:

```bash
CFG=/opt/litellm/config.yaml
grep -qE '^\s*fallbacks:\s*\[\]' "$CFG" && grep -qE '^\s*context_window_fallbacks:\s*\[\]' "$CFG" \
  && echo "GATE PASS: both fallback lists empty" \
  || echo "GATE FAIL: a fallback list is populated — DF-001 risk. STOP."
! sed 's/#.*//' "$CFG" | grep -qiE 'fallback.*(claude|gemini|anthropic|vertex|bedrock|openai/gpt)' \
  && echo "GATE PASS: no cloud model named as a fallback target" \
  || echo "GATE FAIL: a cloud model appears in a fallback chain — DF-001 violation. STOP."
```
**FAIL → halt.** Persistence must never smuggle in escalation.

### 5.3 **▶ GATE — a virtual key mints, routes `claude-*` to the local workhorse, and is revoked**

The full key lifecycle in one gate: mint (proves the DB write path), complete (proves a *virtual* key routes exactly like the keyless baseline did — the front door's 4.3, now keyed), revoke (proves cleanup; also keeps re-runs from accreting gate keys).

```bash
VK=$(curl -sf -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d '{"key_alias":"gate-check-'"$(date +%s)"'","max_budget":1.0}' | jq -r '.key // empty')
[ -n "$VK" ] && echo "PASS: /key/generate minted a virtual key" \
             || echo "GATE FAIL: /key/generate returned no key — DB write path broken (litellm log + docker logs litellm-postgres). STOP."
RESP=$(curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $VK" -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-6","max_tokens":128,"messages":[{"role":"user","content":"In one short sentence, say hello and name yourself."}]}')
GEN=$(echo "$RESP" | jq -r '(.choices[0].message.content // "") + (.choices[0].message.reasoning_content // "")')
[ -n "$GEN" ] \
  && echo "GATE PASS: claude-* under a VIRTUAL key → local model (${#GEN} chars; supersedes front-door 4.3 on this box)" \
  || { echo "GATE FAIL: no completion under the virtual key. STOP."; echo "$RESP" | head -c 400; }
curl -sf -X POST http://localhost:4000/key/delete \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d '{"keys":["'"$VK"'"]}' >/dev/null && echo "PASS: gate key revoked"
```

### 5.4 **▶ GATE — the dashboard answers**

```bash
UI=$(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:4000/ui)
{ [ "$UI" = "200" ]; } \
  && echo "GATE PASS: :4000/ui serving (login: admin / LITELLM_MASTER_KEY from /opt/litellm/litellm.env)" \
  || echo "GATE FAIL: /ui gave ${UI} — the UI ships in the wheel; a non-200 usually means the proxy started without the DB (see Phase 4 poll). STOP."
```

### 5.5 **▶ GATE — spend actually persists (the point of all this)**

Spend rows are written **batched** (~10 s flush), so retry before judging. The 5.3 completion above is the row we expect.

```bash
N=0
for i in $(seq 1 12); do
  N=$(docker exec litellm-postgres psql -U litellm -d litellm -tAc 'SELECT count(*) FROM "LiteLLM_SpendLogs";' 2>/dev/null | tr -d '[:space:]')
  [ -n "$N" ] && [ "$N" -gt 0 ] && break
  sleep 5
done
[ -n "$N" ] && [ "$N" -gt 0 ] \
  && echo "GATE PASS: ${N} spend row(s) persisted in Postgres" \
  || echo "GATE FAIL: no spend rows after 60s — proxy is up but not writing spend (litellm log: look for DB connect errors). STOP."
```

### 5.6 Operator hand-off — print the login card (info, not a gate)

All gates green → tell the operator how to get in. **The password IS the master key** — this echoes it to the **terminal only**; it must never be pasted into `RESULTS-*`, `DRIFT-*`, or `evidence/` (the Phase 8 rule).

```bash
set -a; . /opt/litellm/litellm.env; set +a
HOSTIP=$(hostname -I 2>/dev/null | awk '{print $1}')
cat <<CARD

  ┌─ LiteLLM spend dashboard — how to log in ──────────────────────────────
  │  URL        http://localhost:4000/ui    (LAN: http://${HOSTIP:-<box-ip>}:4000/ui)
  │  Username   admin
  │  Password   ${LITELLM_MASTER_KEY}
  │
  │  Retrieve it any time:   grep LITELLM_MASTER_KEY /opt/litellm/litellm.env
  │  Re-runs NEVER rotate it (Phase 2) — this login stays stable.
  └─ master key = UI + admin API only. Agents get VIRTUAL keys → Phase 6.

CARD
```

---

## Phase 6: Client migration — the operator step this overlay creates

Everything that pointed at `:4000` keyless now gets `401`. That is the *feature*, not a regression — but it needs an operator pass:

1. **Mint one virtual key per agent/client** (alias it meaningfully; set budgets — this is the per-agent spend story):
   ```bash
   set -a; . /opt/litellm/litellm.env; set +a
   curl -s -X POST http://localhost:4000/key/generate \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
     -d '{"key_alias":"claude-code-main","max_budget":25.0}' | jq -r .key
   ```
2. **Update each client** to send it (`api_key`/`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` pointing at `:4000` — whichever the client uses). The `api_key: "none"` placeholders *inside* `/opt/litellm/config.yaml` are the proxy's upstream credentials to llama-swap — they are **not** affected and stay `"none"`.
3. **The master key is for the UI + admin API only** — never hand it to an agent.
4. **`:9000` direct stays open** (DF-001 §3.3): llama-swap has no auth; the documented LiteLLM-down fallback is unchanged. Loopback/LAN exposure of `:9000` is the same as before this overlay — auth on `:4000` is spend governance, not network security.

---

## Phase 7: Decision Gate

| Gate | Result | Note |
|---|---|---|
| P0 drift report emitted + reviewed | | committed `DRIFT-litellm-dashboard-*` |
| P1a front door green (`:4000`) + fleet green (`:9000`) | | precondition — FAIL→STOP |
| P1b docker usable · P1c `:5435` ours/free | | one-time box setup if FAIL |
| P1d twin-config invariant (delta = `general_settings` only) | | routing-drift guard — FAIL→STOP |
| P3 postgres container healthy (`pg_isready`) | | version + digest recorded in RESULTS |
| P5.1 keyless `401` **and** master-keyed `200` | | auth flip proven both ways — FAIL→STOP |
| P5.2 no-cloud re-asserted on deployed config | | DF-001 — FAIL→STOP |
| P5.3 virtual key: mint → `claude-*` local completion → revoke | | supersedes front-door 4.3 on this box |
| P5.4 `:4000/ui` serving | | login: `admin` / master key |
| P5.5 spend rows in `LiteLLM_SpendLogs` | | the persistence claim, proven in the DB |

---

## Phase 8: Evidence capture → RESULTS

```bash
mkdir -p evidence/litellm-dashboard
cp /opt/litellm/config.yaml evidence/litellm-dashboard/litellm-config-$(date +%F).yaml          # env-indirected: contains NO secrets
systemctl --user cat litellm.service > evidence/litellm-dashboard/litellm.service-$(date +%F).txt  # includes the drop-in; references the env file PATH only
# RepoDigests lives on the IMAGE object, not the container — the container-inspect form
# template-errors ("map has no entry for key RepoDigests"; caught 2026-08-06):
{ docker inspect --format '{{.Config.Image}}' litellm-postgres; \
  docker inspect --format '{{index .RepoDigests 0}}' postgres:17; \
  docker exec litellm-postgres psql -U litellm -d litellm -tAc "show server_version;"; } \
  > evidence/litellm-dashboard/postgres-image-$(date +%F).txt
# NEVER capture /opt/litellm/litellm.env — the config's os.environ indirection exists precisely so
# that every committable artifact is secret-free by construction.
```

Then write `RESULTS-litellm-dashboard-<YYYY-MM-DD>.md`:

```
# RESULTS — LiteLLM Dashboard (<YYYY-MM-DD>)
## Gate outcomes        (the Phase 7 table, filled)
## Recorded numbers     litellm version · postgres server_version + image digest (the validated baselines)
## Drift report         link to DRIFT-litellm-dashboard-<date>.md + what was promoted (if anything)
## Failures & follow-ups
```

---

## Phase 9: Failure modes — fast triage

| Symptom | Likely cause | Fix |
|---|---|---|
| LiteLLM restart-loops after Phase 4; log shows "Unable to find Prisma binaries" | engine binaries not generated (the pip package alone is not enough), or the download is blocked (needs network once) | Phase 2's `prisma generate --schema=<litellm>/proxy/schema.prisma`; tail `/opt/litellm/litellm.log` |
| `/key/generate` 500s `TableNotFoundError` while keyed `/v1/models` is `200` | schema never pushed — litellm does not run `db push` itself on this install | Phase 4's `prisma db push --skip-generate --schema=…`, then `systemctl --user restart litellm` |
| Keyless requests suddenly `200` again on an authed box | a front-door re-run redeployed the PUBLIC config (the documented coupling) | re-run this overlay — Phase 4 redeploys the dashboard config; secrets/DB untouched (gate 5.1 is the detector) |
| Every existing client `401`s | expected — auth flipped | Phase 6: mint virtual keys, update clients; interim escape hatch: `:9000` direct (DF-001 §3.3) |
| `pg_isready` never passes | first-boot `initdb` still running, or a volume/permissions issue | `docker logs litellm-postgres`; if the volume is from a different PG major, see the Appendix major-upgrade note |
| `:5435` already bound at Phase 1c | another Postgres on the box | free it, or change this overlay's bind via a PINS PR — silently reusing a foreign DB is out of scope (this pin already moved once: 5432→5435, 2026-08-06) |
| UI loads, `admin` login rejected | password ≠ current master key (stale shell env, or key rotated by hand) | use the live value: `grep LITELLM_MASTER_KEY /opt/litellm/litellm.env`; confirm the drop-in is applied: `systemctl --user show litellm -p EnvironmentFiles` |
| 5.5 finds zero spend rows | batched flush not elapsed, or proxy started before DB and never reconnected | wait/retry; `systemctl --user restart litellm` once the DB is up (Restart= absorbs this at boot) |
| Box offline at first run of Phase 4 | prisma engines + docker pull need network once | this overlay is opt-in and network-dependent on FIRST run only; re-runs after a green run are offline-safe |

---

## Appendix A: Rollback — back to the validated DB-less baseline

One step returns `:4000` to the front-door runbook's green state (keyless, DB-less); the data survives for a later re-apply:

```bash
sudo install -D -m644 examples/litellm-config.public.yaml /opt/litellm/config.yaml   # or restore the Phase 4 .bak-*
rm -f ~/.config/systemd/user/litellm.service.d/20-dashboard.conf
systemctl --user daemon-reload && systemctl --user restart litellm
curl -s -o /dev/null -w 'keyless :4000 -> %{http_code}\n' http://localhost:4000/v1/models   # expect 200 again
docker stop litellm-postgres        # optional: park the DB (data intact in litellm-pgdata)
```

**Full removal** (destroys keys + spend history — deliberate, irreversible):
```bash
docker rm -f litellm-postgres && docker volume rm litellm-pgdata && rm -f /opt/litellm/litellm.env
```

**Postgres major upgrade (17 → 18+, future):** never a re-run — `pg_dump` out of the 17 container, pin edit by PR, fresh volume, restore. The named volume's on-disk format is major-specific; pointing an 18 image at a 17 volume fails at boot by design.

---

## Appendix B: See also

- [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) — the overlay underneath: install, unit, CPU pins, routing, no-cloud gate. Its keyless gate 4.3 is **superseded by 5.3 here** once this overlay is applied.
- [`examples/litellm-config.dashboard.yaml`](./examples/litellm-config.dashboard.yaml) — the config this overlay deploys (public + `general_settings`; twin-config gate 1d).
- [`examples/litellm-config.public.yaml`](./examples/litellm-config.public.yaml) — the DB-less baseline config (and the rollback target).
- [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) · [`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md)
