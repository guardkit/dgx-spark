# Harness-eval grid — <YYYY-MM-DD>

Model: DeepSeek-V4-Flash-0731 (two-Spark seat, `:8888`) · endpoint gates green incl. tool-calling · n=1 per cell unless noted.

Score = gates green / total gates (from `./score.sh`, operator-run). A cell **passes** only all-green.

| Task | H1 one-shot | H2 bare agent | H3 full environment |
|---|---|---|---|
| T1 golden extraction | | | |
| T2 chess vs Stockfish | | | |
| T3 next-bus board | | | |
| T4 constellation globe | | | |
| T5 tool-effects | 0 (by construction) | | |
| **Cells passed** | | | |

**Tokens** (from the LiteLLM spend dashboard, per tier if keyed): …
**Wall-clock per tier:** …
**Notes / honest caveats** (first-pass greens, oracle flakes, skipped cells): …

Attach: every cell's validator output under `results/<date>/` + the identical brief texts.
