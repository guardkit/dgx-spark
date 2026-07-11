DRIFT REPORT — RUNBOOK-single-spark-bring-up.md, run 2026-07-11 (UTC)
  host: spark-fcf6 (NVIDIA GB10, aarch64, 20 cores, CUDA 13.0)
  recon: live (api.github.com + web search reachable)

  PIN CHECKS (deterministic)
    [DRIFT] llama-swap        pinned v219, latest release v238. EXPECTED — the runbook
                              deliberately PINS (release cadence is several versions/week,
                              CONVENTIONS §6). Phase 3.1 installs the PIN v219, whose
                              single-dash flag contract + matrix.sets is exactly what
                              examples/llama-swap-config.public.yaml targets. No runtime
                              edit; a pin bump would be a reviewed PR to the PINS block.
    [INFO]  llama.cpp         built from upstream HEAD 13f2b28 (shallow master clone).
                              Upstream latest tag master-fff0e0e. PINS last-verified build
                              b9430 (2026-05-30). We pin a BUILD TARGET (121a-real real
                              Blackwell SM121 kernels), not a git tag — the Phase 2.2
                              GPU-bound gate proves the freshly-built binary. Built
                              `version:` recorded in RESULTS after Phase 2 completes.
    [INFO]  model GGUFs       pins unchanged: unsloth/Qwen3.6-35B-A3B-GGUF (UD-Q4_K_XL),
                              unsloth/gemma-4-26B-A4B-it-GGUF (UD-Q4_K_XL),
                              unsloth/gpt-oss-20b-GGUF (MXFP4), Qwen/Qwen3-Embedding-0.6B
                              (Q8_0). Staged this run into /opt/llama-swap/models/.

  SOURCE SCAN (advisory)
    [INFO]  build flags       -DCMAKE_CUDA_ARCHITECTURES=121a-real matches NVIDIA's current
                              dgx-spark-playbooks llama-cpp recommendation (they additionally
                              pass optional -DGGML_RPC=ON for multi-node RPC — not needed for
                              this single-Spark fleet). No flag-contract regression.
    [INFO]  upstream vs forks Upstream llama.cpp has caught up with / surpassed the DGX SM121
                              forks (croll83/merve) for GB10 as of ~May 2026 — building from
                              upstream HEAD is the correct current path; no fork required.
    [INFO]  llama-swap        no breaking change to the single-dash flag contract or the
                              matrix.sets coexistence schema found affecting the pinned v219.

  VERDICT: 1 drift (llama-swap v219 → v238, EXPECTED — pinned, not floated), 0 flags.
           Procedure unchanged; no pin edit warranted. The gates below prove the
           built/installed components at runtime.
