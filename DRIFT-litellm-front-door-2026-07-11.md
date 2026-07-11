DRIFT REPORT — RUNBOOK-litellm-front-door.md, run 2026-07-11T15:29:04+0000 (UTC)
  host: spark-fcf6 (GB10, aarch64, 20 cores)
  recon: live (pypi.org reachable; docs.litellm.ai search OK)

  PIN CHECKS (deterministic)
    [DRIFT] litellm[proxy]   PINS baseline 1.89.4 (2026-06-25); latest STABLE on PyPI is
                             1.91.2 (uploaded 2026-07-11). Intervening stable releases:
                             1.89.6, 1.90.2, 1.90.3, 1.91.0, 1.91.1, 1.91.2.
                             Pre-releases present but EXCLUDED by pip default resolution:
                             1.92.0rc1/rc2, 1.93.0.dev1/dev2/dev3, 1.92.0.dev2.
                             `pip install --user 'litellm[proxy]'` would land 1.91.2.
                             This drift is EXPECTED — litellm is float-with-baseline
                             (CONVENTIONS §3). Not a pin edit; the Phase 4 gates prove
                             whatever release installs.

  SOURCE SCAN (advisory)
    [INFO]  proxy config surface UNCHANGED across 1.89 → 1.91 for the fields this overlay
            uses: model_list (model: openai/<alias> + api_base), router_settings.fallbacks,
            router_settings.context_window_fallbacks, --port/--host, /v1/*. No breaking
            change surfaced in docs.litellm.ai (proxy/configs, routing) or release notes.
    [INFO]  [proxy] extra remains pure-Python / wheels-only on aarch64 — no ARM64 wheel
            regression indicated. (Baseline install ~16 s.)
    [INFO]  BerriAI/litellm#15114 "fallback when receiving a completely unknown model" is a
            FEATURE REQUEST, not shipped-breaking — no impact on our empty-fallback,
            no-cloud-target DF-001 posture.

  VERDICT: 1 drift (expected float 1.89.4 → 1.91.2), 0 flags. Procedure unchanged; no pin
           edit warranted (CONVENTIONS §3 — the gates prove the installed release).

  ⚠ RUN OUTCOME — HALTED AT PHASE 1 (precondition NOT met, independent of the drift above):
    The base llama-swap :9000 fleet is NOT green on this box — no `llama-swap` user unit
    exists, nothing is listening on :9000, no llama-swap binary/config/process, linger=no.
    Per RUNBOOK-litellm-front-door.md Phase 1 (FAIL → halt): the front door has nothing to
    route to. Phases 2–6 were NOT executed (nothing installed, no unit written, :9000 not
    touched). Fix: execute RUNBOOK-single-spark-bring-up.md to green first, then re-run this
    overlay. This drift report is the sole artifact of the 2026-07-11 run.
