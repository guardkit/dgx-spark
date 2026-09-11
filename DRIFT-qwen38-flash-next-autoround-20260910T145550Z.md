# Drift report — AutoRound seat, 20260910T145550Z

## Pin checks

- **OK:** Saren HEAD `1633d4bc11701c04d7cbd633994421466d1eff1d` matched the recipe pin.
- **OK:** checkpoint HEAD `19f9710c8f6600a32e15fb98bc77613ee8ec369b` and PLE HEAD `50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14` matched their pins.
- **OK:** digest-pinned base image pulled and verified for ARM64; local source build succeeded.
- **INFO:** blazux HEAD `bd60fcb1b492ca920f74df7462f05da7b6d98f73`; Tony HEAD `6ad1c8f15cbab1ababd2048e8e5f94094dbfc4a0`, consistent with the reassessment.

## Source scan

- [vLLM #54173](https://github.com/vllm-project/vllm/issues/54173) remained open, last updated September 9.
- The [September 10 custom top-k failure](https://github.com/jschmied/qwen38-flash-next-gb10/commit/7fede41fc726) was already reflected in the exact-top-k selection. This startup failure occurred before a context test, so it neither reproduces nor clears that kernel issue.
- The [NVIDIA comparison thread](https://forums.developer.nvidia.com/t/which-single-spark-qwen3-8-flash-next-thread-is-the-best/382522) and [shared Arena reference](https://spark-arena.com/benchmark/7ec7eaf7-a10c-403d-be52-c44c0fc64539) were reachable. The retrieved comparison posts were last updated September 7; no change to the selected pins followed.
- Browser access to several metadata APIs failed; direct HTTPS API reads succeeded and are retained privately in `recon-summary.json` and `recon-*.txt`.

**Verdict:** selected software/model pins unchanged. Local execution required documented mask-precedence and drain-settling corrections, then failed the no-swap startup gate. See [execution results](RESULTS-qwen38-flash-next-autoround-seat-20260910T145550Z.md).
