# DRIFT REPORT — RUNBOOK-litellm-front-door, run 2026-08-04

Mode: **fresh** add of the overlay on `promaxgb10-41b1`, immediately after the base runbook's first green walkthrough ([`RESULTS-single-spark-bring-up-2026-08-04.md`](./RESULTS-single-spark-bring-up-2026-08-04.md)). Executed by agent (Claude Code / Fable 5). Recon per CONVENTIONS §4; no step edited, no pin changed.

## PIN CHECKS (deterministic)

```
[DRIFT] litellm           validated baseline 1.89.4 (2026-06-25) → PyPI latest 1.95.0 (2026-08-03)
                          EXPECTED drift — litellm is float-with-baseline (CONVENTIONS §3); this run
                          installs latest and, if the Phase 4 gates prove it, records 1.95.0 as the
                          new validated baseline. No pin edit unless a gate fails.
[INFO]  litellm           GH pre-releases beyond stable: v1.96.0-rc.1 (2026-08-03) — not installed by pip
[OK]    litellm 1.95.0    release notes show no breaking change to the surface this overlay uses
                          (model_list → openai/<model> + api_base, --port, /v1/*, fallbacks);
                          proxy-related entries are fixes + a Codex drop_params convenience
[OK]    GB10_CORES        20 (10x X925 + 10x A725) — unchanged hardware fact
[OK]    CONFIG            examples/litellm-config.public.yaml present; routes ONLY live fleet aliases
                          (workhorse/coach/embed/gpt-oss-120b + claude-* wildcard); names no cloud model
```

## SOURCE SCAN (advisory — fixed source: BerriAI/litellm releases since 2026-06-25)

```
[INFO] litellm: steady weekly cadence 1.89.4 → 1.95.0 (~6 stable releases in the gap) — consistent with
       the float-not-freeze rationale; nothing in the gap renames the [proxy] extra or drops aarch64 wheels
       https://github.com/BerriAI/litellm/releases
```

## CROSS-RUNBOOK DRIFT (found at execution time)

```
[FLAG] overlay Phase 1 gate + topology diagram still assert a `chat` alias — `chat`/gpt-oss-20b was
       RETIRED from the base lineup 2026-08-01 (base PINS + public config). The base's green output
       state is now workhorse/coach/embed (+ gpt-oss-120b on-demand). The overlay's precondition gate
       as written FAILs against a CORRECT base. Fix by PR: drop `chat` from the Phase 1 loop and the
       diagram. (examples/litellm-config.public.yaml is already correct — it names no `chat` route.)
```

## VERDICT

**1 expected float drift (1.89.4 → 1.95.0), 1 cross-runbook flag (stale `chat` in the overlay's Phase 1 gate). Procedure unchanged — run proceeds; the Phase 4 gates decide whether 1.95.0 becomes the new validated baseline.** The `chat` fix goes in the same amendments PR as the base runbook's F1–F3.
