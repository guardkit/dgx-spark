# DRIFT: granite-vision-seat runbook — `huggingface-cli` deprecated

**Found:** 2026-07-11 on `spark-fcf6` during `RUNBOOK-granite-vision-seat.md` Phase 3.
**Kind:** upstream tooling drift — affects **every future run** of this runbook (and any other that shells `huggingface-cli`).

## What drifted

The runbook pins the weight-staging command (Phase 3, path b) as:

```bash
~/gvseat-venv/bin/huggingface-cli download ibm-granite/granite-vision-4.1-4b
```

`huggingface-cli` is now **deprecated and does nothing** — it exits printing:

```
Warning: `huggingface-cli` is deprecated and no longer works. Use `hf` instead.
Hint: `hf` is already installed! Use it directly.
```

(`huggingface_hub` CLI renamed to `hf`; observed `hf` v1.23.0.)

## What worked instead

```bash
hf download ibm-granite/granite-vision-4.1-4b
```

Ungated model → no token required for the pull (an unauthenticated-rate warning is expected and harmless). Landed the full snapshot (7.5G) in `~/.cache/huggingface/hub/models--ibm-granite--granite-vision-4.1-4b`.

## Suggested runbook edit (next revision)

- Phase 2 (a): `huggingface-cli login` → `hf auth login`.
- Phase 3 (b): `huggingface-cli download …` → `hf download …`.
- Drop the `~/gvseat-venv` bootstrap if `hf` is already on PATH (it was here, `~/.local/bin/hf`); keep a venv fallback only for boxes without it.

Not fixed in-runbook during this run (house rule: never edit steps mid-run). Recorded here per Phase 0 drift convention; committed alongside `RESULTS-granite-vision-seat-spark-fcf6.md`.
