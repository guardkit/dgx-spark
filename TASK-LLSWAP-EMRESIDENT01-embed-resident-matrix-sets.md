# TASK-LLSWAP-EMRESIDENT01 — keep qwen3 `embed` resident across all fleet coexistence matrix-sets

**Status:** live change actioned on the box (2026-06-27); **runbook rule added +
committed**; persistence into the canonical tracked *config* still pending (gated
on `MIGRATION.md` bringing the personal config into this repo).
**Priority:** high (blocks reliable fleet-memory harvest/RAG; caused the
FEAT-HARV recovery stall).
**Related:** `RUNBOOK-single-spark-bring-up.md`, `MIGRATION.md`, fleet-memory
`TASK-FIX-RELAYACKTMO01`, `TASK-HARV-007`.

## Context

The fleet-memory relay embeds against `embed` (Qwen3-Embedding-0.6B → 1024 dims)
on the shared `:9000` llama-swap. In the live personal config
(`/opt/llama-swap/config/config.yaml`), `em` (the `embed` alias) was a member of
**only** the `all` matrix-set:

```
all: "qg & ne & qw & cfv3 & dl & em"
```

Every **other** coexistence set omitted it, so requesting any of them evicted
`embed`:

```
lpa:    "gv & qw & ne"        # finproxy / granite-vision (LPA POC) — the active thrash source
lpa_v3: "gv33 & qw & ne"
tutor:  "gt & qw"             # study-tutor
arch:   "aa & qw"             # architect-agent
```

finproxy continuously drives the `lpa` set (granite-vision), so `embed` was
evicted constantly. The relay's next embed request then **cold-started at
85–181s**, which (with the relay's old 10s timeout) DLQ'd recoverable timeouts
and stalled the FEAT-HARV harvest recovery (167→447 episodes).

## Change actioned live (2026-06-27)

Edited `/opt/llama-swap/config/config.yaml` (backup:
`config.yaml.bak.20260626-harv`); `-watch-config` hot-reloaded it. Added `& em`
to the four non-exclusive coexistence sets:

```
lpa:    "gv & qw & ne & em"
lpa_v3: "gv33 & qw & ne & em"
tutor:  "gt & qw & em"
arch:   "aa & qw & em"
```

`em` (Qwen3-Embedding-0.6B Q8, ctx 32768) is ~1–2 GB resident — verified it fits
with ~29 GB headroom under the 121 GB ceiling, even with the `lpa` set's
granite-vision (~56 GB) loaded. After the reload the full preload fleet came
back and `embed` is resident + warm (~20 ms).

**Deliberately left alone:** the memory-maxed *exclusive* sets `coach31`
(`qw & g31`), `autobuild_go` (`go & gc`), `coder_30b` (`qc`). These intentionally
evict the whole fleet and already require manually pausing the keepalive timer;
`em` should follow the same fate there (a long 31B/120B/coder run does not need
the relay's RAG embed resident).

## The general rule this encodes

> Any model that an **always-on service depends on** (here: the fleet-memory
> relay's RAG `embed`) MUST be a member of **every** non-exclusive coexistence
> matrix-set, not just `all` — otherwise a cross-set request evicts it and the
> dependent service eats a cold-start (or, with a tight client timeout, a hard
> failure). Membership in `all` alone is necessary but not sufficient.

The public example config (`examples/llama-swap-config.public.yaml`) trivially
satisfies this — it has a single `all: "wh & co & ch & em"` set, so `embed` is
always resident. The defect is specific to the **personal** config's richer
set structure (lpa/tutor/arch), which `MIGRATION.md` is bringing into this repo.

## To do (persist the change)

- [ ] **AC-1** Reflect the change in the canonical personal config as it lands in
  this repo per `MIGRATION.md`: `em` in `lpa`, `lpa_v3`, `tutor`, `arch`
  (excluded from `coach31`, `autobuild_go`, `coder_30b`).
- [x] **AC-2** Added the "always-on dependency must be in every coexistence set"
  rule to `RUNBOOK-single-spark-bring-up.md` (2026-06-27) — §3.2 matrix bullet, a
  new gotcha-table row, and an Appendix B migration-reality note pinning `embed`
  resident across `all`/`lpa`/`lpa_v3`/`tutor`/`arch`.
- [ ] **AC-3** Confirm the keepalive allowlist / preload set
  (`scripts/llama-swap-keepalive.sh` `MODEL_PROBE_KIND`,
  `hooks.on_startup.preload`) includes `embed` (the live preload already does).
- [ ] **AC-4** Verify on a fresh bring-up: drive the `lpa` set (a granite-vision
  request) and confirm `embed` stays resident (`/running` shows `embed:ready`
  throughout, no cold-start on the next relay embed).

## Note

This is the infra half of the FEAT-HARV embed-cold-start fix. The relay half —
making the relay robust even when `embed` *is* evicted (raised/settings-driven
timeouts) — is fleet-memory `TASK-FIX-RELAYACKTMO01`. Both were actioned during
the 2026-06-27 recovery; this file tracks persisting the config change so it
survives a rebuild/bring-up.
