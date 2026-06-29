# Runbook: LiteLLM `:4000` Front Door — Additive Overlay over a Green llama-swap Fleet

**Status:** Draft (additive **overlay** per [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) §2.1; the second act of the DDD South West demo). Execute once to verify before the talk. Flip to **Verified** after the first green walkthrough on a box already green on the base runbook.

**Purpose:** Add a **LiteLLM `:4000` front door** — one OpenAI/Anthropic-compatible endpoint with `claude-*` wildcard routing, per-agent keys, spend tracking, and a hard **no-cloud-fallback** policy — **on top of** an already-running llama-swap `:9000` fleet. This is **purely additive** (DECISION-DF-005): llama-swap is unchanged underneath, and direct `:9000` stays a documented fallback if LiteLLM is down (DF-001 §3.3). Running this turns the box into a genuine **superset** of the community stack (martinB78 → Dre Dyson → dasroot: `client → LiteLLM → llama-swap → engines`), not a llama-swap-only subset.

```
clients (agents, Claude Code — OpenAI / Anthropic-compatible)
   │
   ▼
LiteLLM :4000             ← THIS overlay adds the front door (control plane: claude-* wildcard · per-agent keys · spend; NO cloud fallback, DF-001)
   │   (LiteLLM-down fallback: clients may hit llama-swap :9000 directly — DF-001 §3.3)
   ▼
llama-swap :9000          ← the base fleet (stood up by RUNBOOK-single-spark-bring-up.md; UNCHANGED — this overlay only pins its CPU affinity)
   └── always-on: workhorse · coach · chat · embed   ·   on-demand: gpt-oss-120b
```

**Prereq (hard, asserted in Phase 1):** the box is **GREEN** on [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) — the llama-swap `:9000` fleet is serving the four always-on aliases under its user systemd unit. This overlay does **nothing** to the llama-swap config; it adds the LiteLLM unit and pins llama-swap's CPU affinity via a drop-in.
**Conventions:** [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) §2.1 (overlay = precondition gate, not transclusion) · §3 (float-with-baseline) · §8 (the two LiteLLM gate rows this overlay cites).
**One-time box setup:** passwordless sudo for the operator user; run the agent **as that user** — see [README → Running a runbook](./README.md#one-time-box-setup-passwordless-sudo).
**Decision record:** [`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md) — why LiteLLM `:4000` is the single-Spark front door (and the single-node precursor to the two-Spark front door, DF-004).
**Expected wall-clock:** ~5 min (`litellm[proxy]` is pure-Python wheels-only on aarch64, ~16 s; the rest is config + unit + a fleet restart to pick up the affinity drop-in).
**Outputs:** `RESULTS-litellm-front-door-<YYYY-MM-DD>.md`, the committed `DRIFT-litellm-front-door-<YYYY-MM-DD>.md`, and the live `/opt/litellm/config.yaml`.

---

## PINS (this overlay's block — additive to the base runbook's PINS)

```
PINS (set 2026-06-25)
  litellm    PyPI       litellm[proxy]  (latest)   pip --user --break-system-packages  (front door :4000; floated not frozen — stable interface + gate-protected, CONVENTIONS §3; validated at 1.89.4 on GB10 2026-06-25, wheels-only ~16s)
  GB10_CORES           20                           10x Cortex-X925 + 10x Cortex-A725 (NOT 72-core Grace) — for the CPUAffinity ranges below
  ENDPOINT             LiteLLM :4000 (clients)      llama-swap :9000 remains a direct-port fallback (DF-001 §3.3)
  CONFIG               examples/litellm-config.public.yaml   (this overlay's canonical target)
```

These are genuinely the overlay's own pins — only its steps and gates reference them, so they live here, not split out of the base runbook's block (CONVENTIONS §3, single-PINS-per-runbook). When recon flags drift, the fix is a **PR editing this block** — never a runtime edit.

---

## Execution modes

```
Execution modes (CONVENTIONS §2.2):
  fresh    — first add of the front door, on a box already green on the base runbook
  re-run   — same file again; the config/unit writes are overwrite-safe, the gates re-verify
  update   — Phase 0 recon flags a LiteLLM release; re-run (pip pulls latest), the gates re-prove it,
             record the new validated baseline in RESULTS. litellm is float-with-baseline (CONVENTIONS §3),
             so "update LiteLLM" IS "re-run this overlay" — no pin edit unless a gate fails.
```

Because the base (frozen SM121 build / GGUF pins) and this overlay (weekly-floating LiteLLM) are separate files, they have **independent re-run cadences** — bumping LiteLLM never makes you touch the fragile build pins.

---

## What this overlay does NOT cover

- **The llama-swap fleet itself.** That is [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) (the base) — already green; not re-run here.
- **vLLM backends / cross-node TP behind LiteLLM.** That is the two-Spark runbook ([`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md)) — DF-005 (single node) is the precursor to DF-004 (two nodes).
- **Persisted virtual keys + the spend dashboard (`:4000/ui`).** Opt-in; needs Postgres (`DATABASE_URL` + `master_key`) — see the bottom of [`examples/litellm-config.public.yaml`](./examples/litellm-config.public.yaml). DB-less (the default here) still routes, still enforces the no-cloud guard, and still returns per-request cost in the `x-litellm-response-cost` header.
- **Cloud-LLM escalation.** Zero cloud on the critical path (DF-001) — enforced by the Phase 4 no-cloud gate. The public config names **no** cloud model at all.

---

## Phase 0: Recon (read-only, advisory) — emits the drift report

No side effects. Degrades gracefully (DF-001): network down → record `recon: skipped` and proceed on the PINS.

```
RECON SOURCES (fixed)
  - github.com/BerriAI/litellm   releases (proxy extra / ARM64 wheel) since the PINS date
TASK: "Report only LiteLLM releases newer than the PINS date that affect the proxy install
       (the [proxy] extra, the aarch64 wheel) or the config surface this overlay uses
       (model_list → openai/<model> + api_base, --port, /v1/*, fallbacks). Emit a drift report.
       Do NOT propose edited steps. Do NOT change any pin."
```

Write `DRIFT-litellm-front-door-<timestamp>.md` (conventions §5) and commit it next to the RESULTS file. **▶ GATE (advisory):** review any `[DRIFT]`/`[FLAG]` before promoting the pin; the run proceeds on the current PINS regardless. (LiteLLM is float-with-baseline — drift here is *expected*; the gates below prove the installed release works.)

---

## Phase 1: Pre-flight — **▶ GATE: the base fleet is green on `:9000`** (the overlay precondition)

This overlay asserts the base runbook's **output state** (CONVENTIONS §2.1) — it does not re-run any base phase. If `:9000` isn't serving the fleet under its user unit, **stop and run the base runbook first**.

```bash
# (a) the four always-on aliases are served on :9000
ALIASES=$(curl -sf http://localhost:9000/v1/models | jq -r '.data[].id' 2>/dev/null | sort | tr '\n' ' ')
echo "llama-swap :9000 aliases: ${ALIASES:-<none reachable>}"
MISS=
for m in chat coach embed workhorse; do
  echo " $ALIASES " | grep -q " $m " || { echo "GATE FAIL: alias '$m' not served on :9000."; MISS=1; }
done
# (b) llama-swap is supervised as a USER unit (so the CPU-affinity drop-in in Phase 3 takes effect)
systemctl --user is-active --quiet llama-swap \
  && echo "GATE PASS: llama-swap user unit active" \
  || { echo "GATE FAIL: llama-swap user unit not active."; MISS=1; }
[ -z "$MISS" ] \
  && echo "GATE PASS: base fleet green on :9000 — proceed with the front door." \
  || echo "STOP: stand the base fleet up first — execute RUNBOOK-single-spark-bring-up.md to green (Decision Gate 5.4)."
```
**FAIL → halt.** The front door has nothing to route to without the fleet; the empty-target case is exactly what this gate prevents.

---

## Phase 2: Install LiteLLM &nbsp;·&nbsp; **▶ the agent runs this step** (pure-Python, ARM64; not a manual prerequisite)

> **Update mode:** re-running this phase pulls the latest `litellm[proxy]`. The gates in Phase 4 re-prove the new release; record the version in RESULTS as the new validated baseline (CONVENTIONS §3). No pin edit unless a gate fails.

```bash
pip install --user --break-system-packages 'litellm[proxy]'   # latest; [proxy] extra is pure-Python, wheels-only on aarch64 (~16s; validated baseline 1.89.4)
hash -r
LITELLM_BIN=$(command -v litellm || echo ~/.local/bin/litellm)
VER=$("$LITELLM_BIN" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
echo "[record in RESULTS] litellm ${VER}   (validated baseline: 1.89.4 on GB10 2026-06-25)"
# Deliberately NOT version-frozen (CONVENTIONS §3): litellm's surface here (model_list/openai-prefix/api_base,
# --port, /v1/*) is stable and the no-cloud + routes gates below prove THIS release works at runtime. Recon flags
# BerriAI/litellm drift; if a future release ever breaks a run, pin it THEN via a PR to the PINS block.
```

---

## Phase 3: Deploy the config + start under a USER systemd unit — CPU-pinned disjoint from llama-swap

Mirror the llama-swap supervision model (user unit + linger; never a VS Code terminal — the same Chromium-cgroup trap as the base runbook's Phase 4.2 applies equally). The unit's `CPUAffinity=` is pinned to a **disjoint** core range from llama-swap so the two never contend under concurrent multi-model load (the WARN gate in Phase 4). GB10 is a **20-core** CPU (PINS `GB10_CORES`) — here LiteLLM takes `0-3`, llama-swap takes `4-19` via a drop-in (keeps the base Phase 4.1 unit untouched):

```bash
sudo mkdir -p /opt/litellm && sudo chown -R $USER:$USER /opt/litellm
sudo install -D -m644 examples/litellm-config.public.yaml /opt/litellm/config.yaml
LITELLM_BIN=$(command -v litellm || echo ~/.local/bin/litellm)

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/litellm.service <<EOF
[Unit]
Description=LiteLLM front door (:4000) -> llama-swap :9000
After=network-online.target llama-swap.service
Wants=llama-swap.service
[Service]
Type=simple
CPUAffinity=0-3
ExecStart=${LITELLM_BIN} --config /opt/litellm/config.yaml --port 4000 --host 0.0.0.0
Restart=on-failure
RestartSec=5
StandardOutput=append:/opt/litellm/litellm.log
StandardError=append:/opt/litellm/litellm.log
[Install]
WantedBy=default.target
EOF

# Pin llama-swap onto the COMPLEMENTARY cores via a drop-in (the base Phase 4.1 unit untouched):
mkdir -p ~/.config/systemd/user/llama-swap.service.d
cat > ~/.config/systemd/user/llama-swap.service.d/10-cpu-affinity.conf <<'EOF'
[Service]
CPUAffinity=4-19
EOF

systemctl --user daemon-reload
systemctl --user restart llama-swap        # picks up the affinity drop-in (no config/model change) — see the note below
systemctl --user enable --now litellm
sudo loginctl enable-linger "$USER"         # boots without a login (same model as llama-swap)
```
Manage it with `systemctl --user … litellm` (note the `--user`). `:9000` is unchanged — only its CPU affinity is pinned.

> **The one coupling to know (self-healing):** this overlay applies the `CPUAffinity=4-19` drop-in to llama-swap and re-applies it **every run** (the heredoc is overwrite-safe), so a base re-run that restarts llama-swap and drops the affinity is healed the next time you run this overlay. **The `restart llama-swap` above bounces the resident fleet** (a cold reload of the ~65 GB preload) — schedule it, don't treat it as free. If you only need to add LiteLLM without re-pinning affinity, you can skip the drop-in, but then the Phase 4 CPU-pin gate WARNs.

---

## Phase 4: Trust gates

### 4.1 **▶ GATE — no cloud fallback (DF-001)** &nbsp;·&nbsp; (registry: CONVENTIONS §8 "LiteLLM auto cloud-fallback")

The robust invariant is *no cloud model is reachable as a fallback target* — assert BOTH fallback lists are empty **AND** no cloud model is named in a fallback chain. (LiteLLM's own documented `context_window_fallbacks` example escalates to `claude-opus` on context overflow — the exact unattended-spend footgun. The empty-list "disable" is an undocumented inference, so we also assert the absence of any cloud target.)

```bash
CFG=/opt/litellm/config.yaml
grep -qE '^\s*fallbacks:\s*\[\]' "$CFG" && grep -qE '^\s*context_window_fallbacks:\s*\[\]' "$CFG" \
  && echo "GATE PASS: both fallback lists empty" \
  || echo "GATE FAIL: a fallback list is populated — DF-001 risk. STOP."
# The `^\s*` anchor is load-bearing: without it an empty `context_window_fallbacks: []`
# line satisfies the first grep's `fallbacks: []` substring even when `fallbacks:` is populated.
! sed 's/#.*//' "$CFG" | grep -qiE 'fallback.*(claude|gemini|anthropic|vertex|bedrock|openai/gpt)' \
  && echo "GATE PASS: no cloud model named as a fallback target" \
  || echo "GATE FAIL: a cloud model appears in a fallback chain — DF-001 violation. STOP."
# `sed 's/#.*//'` strips comments FIRST — the in-file note "…escalates to claude-opus on overflow"
# is prose, not a route, and must not false-FAIL the gate. The check is on YAML values only.
```
**FAIL → halt.** This is the on-camera "the one community feature I deliberately disable" beat. Cloud models may be *named* only for the attended DF-003 path (the public box names none at all).

### 4.2 **▶ GATE — CPU-pin LiteLLM disjoint from llama-swap (WARN, not STOP)** &nbsp;·&nbsp; (registry: CONVENTIONS §8 "LiteLLM ↔ llama-swap CPU contention")

Under concurrent multi-model load, LiteLLM and llama-swap sharing a core can yield LiteLLM 504s + flaky llama-swap health checks. The disjointness check is sound and self-verifying; the 504s rationale is community-sourced and **not** authoritative (see DF-005's verification note), so this **WARNs, it does not halt**:

```bash
LSW=$(systemctl --user show llama-swap.service -p CPUAffinity --value 2>/dev/null)
LIT=$(systemctl --user show litellm.service   -p CPUAffinity --value 2>/dev/null)
python3 - "$LSW" "$LIT" <<'PY'
import sys
def expand(s):
    out=set()
    for tok in (s or "").replace(',',' ').split():
        if '-' in tok:
            a,b=tok.split('-'); out|=set(range(int(a),int(b)+1))
        elif tok.isdigit(): out.add(int(tok))
    return out
lsw, lit = expand(sys.argv[1]), expand(sys.argv[2])
if not lsw or not lit:
    print("GATE WARN: CPUAffinity not set on both units — pin them disjoint (e.g. litellm 0-3, llama-swap 4-19 on the 20-core GB10).")
elif lsw & lit:
    print(f"GATE WARN: CPUAffinity overlaps on cores {sorted(lsw & lit)} — make the two units' core sets disjoint (re-derive for 20 cores).")
else:
    print("GATE PASS: litellm and llama-swap CPUAffinity are disjoint.")
PY
```
> Why WARN, not STOP: a full-page fetch of dredyson.com refuted the "Dre Dyson's #1 mistake / 72-core" framing an early draft used (his actual #1 is `gpu-memory-utilization`; the community deploys via Docker `cpuset`, so `CPUAffinity=` is *our* systemd remedy). The pin is still worth doing; it just isn't a hard gate.

### 4.3 **▶ GATE — front door answers + `claude-*` routes to a local model**

```bash
# (a) the front door lists the fleet via :4000
curl -sf http://localhost:4000/v1/models | jq -r '.data[].id' | sort
# (b) a claude-* request lands on the LOCAL workhorse (no cloud — there is no cloud model in the config to reach).
#     max_tokens is generous so workhorse (--reasoning auto) emits real text; accept content OR reasoning_content
#     — a reasoning model can put its answer in reasoning_content and leave content empty (verified on GB10).
RESP=$(curl -s http://localhost:4000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-6","max_tokens":128,"messages":[{"role":"user","content":"In one short sentence, say hello and name yourself."}]}')
GEN=$(echo "$RESP" | jq -r '(.choices[0].message.content // "") + (.choices[0].message.reasoning_content // "")')
SERVED=$(echo "$RESP" | jq -r '.model // "?"')
[ -n "$GEN" ] \
  && echo "GATE PASS: claude-* routed to a local model via :4000 (served=${SERVED}, ${#GEN} chars generated)" \
  || { echo "GATE FAIL: no local completion for claude-* via :4000. STOP."; echo "$RESP" | head -c 400; }
```
**Routing safety is structural:** because the public config names **no** cloud model and ships empty fallback lists (4.1), a `claude-*` request *cannot* reach a cloud API — there is no target. If the literal `claude-*` wildcard doesn't resolve in your installed LiteLLM version, add explicit `claude-sonnet-4-6` / `claude-opus-4-7` rows mapping to `openai/workhorse` (see the config's note).

---

## Phase 5: Decision Gate

| Gate | Result | Note |
|---|---|---|
| P0 Drift report emitted + reviewed | | committed `DRIFT-litellm-front-door-*` |
| P1 base fleet green on `:9000` (four aliases + llama-swap user unit active) | | precondition — FAIL→STOP, run the base runbook first |
| P4.1 LiteLLM no-cloud fallback (both lists empty + no cloud target) | | DF-001 — FAIL→STOP |
| P4.2 LiteLLM ↔ llama-swap CPUAffinity disjoint | | **WARN** (not hard-gated) |
| P4.3 front door `:4000` answers + `claude-*` → local | | no outbound cloud (structural) |

---

## Phase 6: Evidence capture → RESULTS

```bash
mkdir -p evidence/litellm-front-door
cp /opt/litellm/config.yaml evidence/litellm-front-door/litellm-config-$(date +%F).yaml
systemctl --user cat litellm.service > evidence/litellm-front-door/litellm.service-$(date +%F).txt
# the DRIFT report from Phase 0 lives at the repo root, committed
```
Then write `RESULTS-litellm-front-door-<YYYY-MM-DD>.md`:

```
# RESULTS — LiteLLM Front Door (<YYYY-MM-DD>)
## Gate outcomes        (the Phase 5 table, filled)
## Recorded numbers     installed litellm version (the validated baseline this run proved)
## Drift report         link to DRIFT-litellm-front-door-<date>.md + what was promoted (if anything)
## Failures & follow-ups
```

---

## Phase 7: Failure modes — fast triage

| Symptom | Likely cause | Fix |
|---|---|---|
| Phase 1 gate FAILs: `:9000` not serving | the base fleet isn't up | execute [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) to green first (its Decision Gate 5.4) |
| LiteLLM 504s / flaky health under concurrent load | LiteLLM & llama-swap sharing a CPU core | Phase 4.2 — set disjoint `CPUAffinity=` (litellm 0-3 / llama-swap 4-19; re-derive for the 20-core GB10) |
| `:4000` refused but `:9000` works | LiteLLM down | use llama-swap `:9000` directly (documented DF-001 §3.3 fallback); `systemctl --user status litellm`; tail `/opt/litellm/litellm.log` |
| `claude-*` request errors / not routed | the `claude-*` wildcard isn't matched in your LiteLLM version | Phase 4.3 — add explicit `claude-sonnet-4-6` / `claude-opus-4-7` → `openai/workhorse` rows |
| `claude-*` reaches a cloud API | a cloud model was added to the config / a fallback chain | Phase 4.1 no-cloud gate; the public config names NO cloud model (DF-001) |
| llama-swap lost its CPU affinity after a base re-run | a base-runbook restart dropped the drop-in | re-run this overlay (Phase 3 re-applies the `10-cpu-affinity.conf` drop-in — self-healing) |

---

## Appendix: See also

- [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md) — the **base** this overlay sits on (the llama-swap `:9000` fleet). Run it to green first.
- [`examples/litellm-config.public.yaml`](./examples/litellm-config.public.yaml) — the canonical LiteLLM (`:4000`) config this overlay deploys.
- [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) — §2.1 (overlay = precondition gate), §3 (float-with-baseline), §8 (the two LiteLLM gate rows cited here).
- [`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md) — why LiteLLM `:4000` is the single-Spark front door (single-node precursor to DF-004).
- [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) — the two-node superset; its Phase 7 reuses this overlay's install/unit/CPU-pin mechanism.
