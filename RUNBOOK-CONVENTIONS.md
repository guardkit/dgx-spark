# Runbook Conventions

How runbooks are written and executed in this repo. This is the method the DGX Spark work is built on, and the thing that distinguishes a runbook here from "paste the blog into Claude Code."

---

## 1. What a runbook is here

A runbook is an **executable specification**, not a tutorial. It is written to be run by an **agent** (Claude Code, Codex, or OpenCode) against a target machine, and it must hold three properties:

1. **Deterministic** — steps are version-pinned. The same runbook produces the same procedure today and in three months. No step says "install the latest X"; it says "install X pinned at `<version>`, and a gate asserts you got it."
2. **Self-verifying** — the hard-won knowledge is encoded as **gates** (assertions that fail loudly and halt), not as prose warnings the operator might skim past. A blog says "watch out for the ARM64 CPU-fallback"; a runbook *asserts the server is GPU-bound and stops if it isn't*.
3. **Reproducible** — it produces a `RESULTS-*.md` / `VALIDATION-*.md` artifact, and any change to the procedure is a reviewed commit, never a mid-run mutation.

**The anti-goal.** An LLM that searches the web and then *rewrites its own steps* mid-run is an improviser, not a runbook. It throws away determinism and reproducibility — the exact properties that make a runbook worth more than an ad-hoc "set up my Spark" prompt. We deliberately do **not** do that. Research *informs*; gates *decide*; a human *ratifies* changes to the procedure.

---

## 2. Anatomy (house structure)

Every runbook follows the shape proven in `RUNBOOK-v3-production-deployment`:

```
# Runbook <n>: <title>
**Purpose / Machine / Predecessors / Execution-results link / Expected duration**
**Target architecture:** <ASCII diagram>

## Phase 0: Recon            ← read-only; emits a drift report (see §4). NEW.
## Phase 0.5: Pre-flight     ← environment checks, no side effects yet
## Phase 1..N                ← pinned steps, each ending in an inline PASS/FAIL check
## Phase N: Decision Gate    ← the gate table: every check, with a result column
## Phase N+1: Cleanup & Harden
## Appendix: Rollback
```

Inline checks live *in* the step (a `curl … | python3 -c "… print('PASS' if … else 'FAIL')"` or a `grep -q … && echo PASS`). The Decision Gate table at the end is the single place to read whether the run is green.

---

## 3. Pins live in one block

Each runbook opens with a **`PINS`** block — the single source of truth for every version, tag, commit, model repo, and threshold the runbook depends on. Steps reference the pins; gates assert them; recon checks them. Example (real, from the current stack):

```
PINS (runbook vN, set 2026-06-19)
  llama-swap            v208            (single-dash flags; matrix coexistence)
  llama.cpp             build SM121 121a-real   (PR #17570 Anthropic Messages API)
  graphiti fork         v0.29.5-guardkit.6
  workhorse GGUF        Qwen3.6-35B-A3B-Instruct UD-Q4_K_XL
  gpt-oss-120b GGUF     sowilow/gpt-oss-120b-DGX-Spark-GGUF (Blackwell-tuned)
  MEM_CEILING_GB        115     (121 usable; freeze observed at 114)
  KV_CACHE_TYPE         q8_0
```

When recon flags drift on a pin, the fix is a **PR that edits this block** (see §6) — not an edit the agent makes to itself at runtime.

---

## 4. Phase 0 — Recon (read-only, advisory)

Before any step with a side effect runs, the agent performs recon against a **fixed source list** and emits a **drift report**. Recon has no side effects: it only reads and reports.

Two tiers:

**(a) Deterministic checks** — where an API exists, compare the pin to upstream with a plain query, no LLM judgment:

```bash
# llama-swap: pinned vs latest release tag
PINNED=v208
LATEST=$(curl -s https://api.github.com/repos/mostlygeek/llama-swap/releases/latest | jq -r .tag_name)
[ "$PINNED" = "$LATEST" ] && echo "llama-swap: pinned == latest ($PINNED)" \
                          || echo "DRIFT: llama-swap pinned $PINNED, latest $LATEST"
```

Repeat for: llama.cpp HEAD vs the built commit, the graphiti fork tag, HF model-repo revisions. These results are exact and reproducible.

**(b) LLM-judgment scan** — for prose sources where there's no API, the executing LLM searches a fixed topic list and summarises *new* items since the pin date into the drift report. Fixed sources, tightly scoped — never "search the web and adapt":

```
RECON SOURCES (fixed)
  - NVIDIA DGX Spark / GB10 forum  (topics: llama-swap, llama.cpp SM121 build,
    CX-7 firmware, gpu-memory-utilization, memory freeze, vLLM aarch64 images)
  - github.com/mostlygeek/llama-swap  releases + open issues
  - github.com/ggml-org/llama.cpp     releases + SM121-tagged issues
  - Dre Dyson blog                    (new posts since pin date)
RECON TASK
  "For each source, report only items newer than the PINS date that affect a
   pinned component or a known gotcha. Output a drift report. Do NOT propose
   edited steps. Do NOT change any pin."
```

**Output is a drift report, not new steps.** Format in §5.

**Graceful degradation (DF-001).** Recon is *additive*, never on the critical path. If search is unavailable or a source is down, the runbook **still executes the pinned procedure** and records `recon: skipped (source unreachable)`. A setup runbook that can't run without live internet to the forum is a worse artifact, not a better one.

---

## 5. Drift report format

Recon emits one artifact, human-readable and diffable:

```
DRIFT REPORT — <runbook>, run <timestamp>
  PIN CHECKS (deterministic)
    [OK]    llama-swap        v208 == latest
    [DRIFT] llama.cpp         built <commit>; HEAD is 3 weeks newer
    [OK]    graphiti fork     v0.29.5-guardkit.6
  SOURCE SCAN (advisory)
    [FLAG]  forum: new thread "CX-7 firmware regression on DGX OS 7.x" (4d ago)
    [INFO]  llama-swap: issue #NNN — matrix eviction edge case under load
  VERDICT: 1 drift, 1 flag. Procedure unchanged. Review before promoting pins.
```

The report is committed alongside the `RESULTS-*` artifact. It is *also* the best live-demo material: show it on stage, then watch a gate catch the regression it predicted.

---

## 6. Promotion = PR, not runtime

When recon flags real drift:

1. A human reads the drift report.
2. If the change is wanted, it's a **commit to the `PINS` block** (and any step/gate that follows from it), reviewed, with a changelog line.
3. The runbook re-runs against the new pins.

The runbook never edits itself mid-run. The repo stays the source of truth; the runbook is a **living artifact** — recon *surfaces* staleness, a PR *resolves* it. This is what keeps "self-updating" from collapsing into "non-deterministic."

---

## 7. Gates vs research (the split that matters)

| | Research (Phase 0 recon) | Gate (in-step) |
|---|---|---|
| When | Before side effects | At the relevant step |
| Reads | Forum, upstream repos | The live machine |
| Output | A drift report | PASS / FAIL → halt on FAIL |
| Authority | Advisory — informs a human | Decisive — stops the run |
| Mutates the procedure? | **Never** | Never (it asserts, doesn't edit) |

Recon tells you a value *might* need changing *before* you hit the gate. The gate enforces the invariant *regardless* of what recon said. They are independent safety nets.

---

## 8. Gotcha → gate registry

The reusable core: GB10 traps we've hit (ours + the community's), each with the assertion that catches it. New runbooks pull the relevant rows in as gates. This table is the talk's "receipts."

| Gotcha | Why it bites | Gate (assertion) | Source |
|---|---|---|---|
| `mmap` on unified memory | Severe slowdown on GB10 | every `llama-server` cmd contains `--no-mmap` | setup §5 |
| f16 KV cache | Quality degradation on Qwen3.x / SM121 | KV type is `q8_0` (`--cache-type-k/v q8_0`) | setup §5 |
| `-np` splits ctx across slots | per-slot ctx = ctx/np; large chunks 400 | `ctx_size / np ≥ expected_max_chunk_tokens` | findings §9.1, v3 §5.2 |
| 121 GB memory ceiling | Freeze observed at 114 GB / 7 GB free | projected `resident + KV < MEM_CEILING_GB (115)` before load | README §9.4 |
| `pkill -f llama-server` | Matches the running script → self-kill | use `pkill -x llama-server` | v3 §4.2 |
| `find -name "*Q8*"` | Misses lowercase files on disk | use `-iname` | v3 §0.1 |
| llama-swap `--config` | GNU double-dash silently rejected (v208) | flags are single-dash `-config` / `-listen` | v3 §5.3 |
| No `matrix.sets` block | Cross-model requests → load→kill→load thrash | coexistence set declared in config | v3 §5.2 |
| Process under VS Code cgroup | Editor lifecycle reaps the tree, bypasses `Restart=` | `/proc/$(pgrep -x llama-swap)/cgroup` is the systemd unit, not a `chromium`/`app-` scope | v3 §10.2 |
| `CLAUDE_CODE_ATTRIBUTION_HEADER` unset | KV-cache busting on every turn | env var `= 0` | setup §8 |
| `ANTHROPIC_API_KEY` unset (not empty) | SDK auth path misbehaves | env var is the empty string, explicitly | setup §8 |
| Generic ARM64 binary | Silent CPU-only fallback (~2 tok/s) | `llama-server` appears in `nvidia-smi` compute-apps; built `121a-real` | Dre Dyson; setup §3 |
| `gpu-memory-utilization` | CUDA sees 121.69 GiB ≠ 128; util fails after a swap (VRAM not freed yet) | dynamic launcher computes util from *actual* free VRAM at launch | setup §12 |
| Embedding dims 1024 | Actual nomic model is 768 | Graphiti config `dimensions: 768` | v3 §7.1 |
| llama-swap child crash | Parent `Restart=` doesn't revive children; `matrix` only on traffic | keep-alive timer present + firing | v3 §5.6 |
| Cold-load 504 | `healthCheckTimeout` too short for 120B load | `healthCheckTimeout ≥ 600` | setup §10 |

---

## 9. Naming & files

| Pattern | Use |
|---|---|
| `RUNBOOK-<topic>.md` | An executable runbook. |
| `RESULTS-<topic>.md` | Execution record (numbers, what passed). |
| `VALIDATION-<id>-results.md` | Gate outcomes for a specific task/gap. |
| `DECISION-<id>.md` | ADR (or a pointer to the canonical one in `guardkit/docs/decisions/`). |
| `DRIFT-<runbook>-<date>.md` | A committed recon drift report. |

First exemplar to build under these conventions: **`RUNBOOK-single-spark-bring-up.md`** — unboxed GB10 → a trusted multi-model endpoint on `:9000`, with the Phase 0 recon block and the registry rows above wired in as gates. Prove the one exemplar, then extract the template.
