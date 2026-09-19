# Which local model should sit behind a coding agent on our two GB10 boxes?

**Status:** research captured 2026-09-19 from the NVIDIA DGX Spark / GB10 forum, plus read-only checks on `promaxgb10-41b1` (the Dell) and `spark-fcf6` (the Spark). Later the same day, at the owner's request, NVIDIA's kernel fix was installed on both boxes, both were rebooted and verified, and the Spark's Qwen seat was moved from 14 GB of cache back to its documented 19 GB, then to 22 GB, with the same tests run at each size. It is running at 22 GB. See [Concrete next steps](#concrete-next-steps).

**The question:** paid Claude and Codex usage runs out within a day or two when it is used to implement work on the software factory. Can a model running on our own boxes take over the implementation work, leaving the paid models for research, planning and writing specs? This note covers only what we can run on one or both boxes. Choosing and configuring the agent tool (Pi, the DeepSeek harness, opencode) is a separate piece of work.

## The short answer

1. **Fix the kernel on both boxes before any two-box work.** Both boxes were on kernel `7.0.0-1019-nvidia` without NVIDIA's fix. That kernel breaks the memory registration that two-box serving depends on, and holds back 9.3 GiB of memory. The fix is one package and a reboot. It is now applied and verified on both boxes. Details are in [the kernel section](#the-kernel-problem-on-both-boxes).
2. **Start with the model that is already running: Qwen3.8-Flash-Next on the Spark.** It is the only option that can run while the factory runs, because the factory and its model services live on the Dell. The forum rates it the best one-box coding model, and the one like-for-like benchmark on the forum has it level with the bigger two-box models in a fraction of the time. Trying it costs nothing: point the agent at the endpoint we already have.
3. **GLM 5.3 Flash across both boxes is the forum's pick for hard coding work, and it is slow.** About thirteen people who have used both say GLM gets better results than DeepSeek; about five keep DeepSeek as their daily driver because of speed. The pattern most of them settled on is GLM as planner, reviewer and overnight worker, with DeepSeek or Qwen writing the code. Since our plan gives planning and specs to the paid models, the local model's job is the implementer's, which is the job forum users give to the faster models. GLM needs both boxes to itself, so it can only run when the factory is idle. It would be a new runbook.
4. **Keep the DeepSeek 0731 runbook as it is. Do not convert it to the Vision build.** The Vision build is 6–24% slower even on the tuned stacks, needs a new image build, and nobody has shown it writes better code. We already have a separate vision model. Four small fixes found on the forum apply to 0731 and are worth folding in. One of them matters a lot: our seat may have been running with reasoning switched off.
5. **Skip DeepSeek V4.1 Flash.** It is too big for two boxes unless squeezed to about 3 bits, and forum users call it inconsistent.

## Concrete next steps

### 1. Kernel fix on the Spark: done 2026-09-19

Installed `nvidia-spark-grub-kho` 1.0-1 on its own (one new package, nothing else upgraded), confirmed `kho=off` was on the 7.0 boot entry and the boot image was intact, stopped the idle Qwen seat and its guard, and rebooted.

| Check | Before | After |
|---|---|---|
| `kho=off` on the kernel command line | absent | present |
| `/sys/kernel/debug/kho` | present | does not exist |
| Memory available at boot (kernel log) | 117,722,720K | 127,473,180K |
| Memory reserved by the kernel at boot | 16,079,992K | 6,329,464K |
| `CmaFree` | non-zero | 0 |

That is 9.3 GiB handed back. `MemTotal` is the same before and after, which matters for step 3.

The reboot brought back everything the seat's runbook had switched off: `llama-swap` and `litellm` started, two audio model containers started under `llama-swap`, and the 16 GB swap file came on. All were put back as they were: both services stopped and masked through `$XDG_RUNTIME_DIR/systemd/user.control/` (plain `mask --runtime` does not take effect on this box, as the runbook notes), swap off, the memory guard started with the same command and thresholds, and the seat started with `docker start`. It was healthy in about 160 seconds with the same 450,604-token pool, and answered a completion sent from the Dell over the address the gateway uses. The guard's new evidence directory on the Spark is `~/api-factory-resume-20260919T090408Z`, which also holds the container's full pre-reboot configuration as a receipt.

### 2. Kernel fix on the Dell: done 2026-09-19

`nvidia-spark-grub-kho` 1.0-1 was installed the same way, and the owner rebooted the Dell. Checked afterwards:

| Check | Before | After |
|---|---|---|
| `kho=off` on the kernel command line | absent | present |
| `/sys/kernel/debug/kho` | present | does not exist |
| Memory available at boot (kernel log) | 117,659,644K | 127,408,136K |
| Memory reserved by the kernel at boot | 16,143,244K | 6,394,748K |

The same 9.3 GiB came back. `llama-swap`, `litellm` and the two forge sidecars returned on their own, 24 containers are running including `gemma4-adapters` (its restart policy is `no`, so it needs `docker start gemma4-adapters` after any reboot), and the gateway answers its liveness check. One thing not yet done: a request through the gateway to `flash-next` with the factory's key, to confirm a spend record appears.

### 3. Investigate the Spark seat's cache size and memory, aiming to run near 120 GB

The cache was cut from 19 GB to 14 GB on 2026-09-17 because the box ran out of memory and went into swap. The Spark had booted into the broken kernel two days earlier, on 2026-09-15.

**Baseline already recorded.** The guard sampled memory every two seconds for the two days before the reboot, at 14 GB of cache, under real factory traffic:

| Measure | Value |
|---|---|
| Cache pool | 450,604 tokens, 1.72 full conversations |
| Used memory, median | 100.36 GiB |
| Used memory, peak | 100.67 GiB (108.1 GB) |
| Room under the 120 GB ceiling at peak | 11.1 GiB |
| Swap activity | none |
| Shape over time | rose from 96.0 to 100.4 GiB over the first 18 hours, then flat |

**The likely explanation for the swap at 19 GB.** The guard measures used memory as `MemTotal` minus `MemAvailable`. On the broken kernel the 9.3 GiB reservation was still counted inside both figures, but it could not be used for the pinned memory the GPU needs. So the guard could show several gigabytes of room while the memory the seat could really use was exhausted. If that is right, 19 GB should now fit with the margin the guard always reported. This is a hypothesis to confirm, not a finding.

**First results, 2026-09-19, after both boxes were fixed.** The factory was idle, so the seat was moved back to the documented 19 GB and tested with the repo's own probe scripts.

Where the memory goes, at 14 GB and idle: of 97.9 GiB the guard counted as used, the GPU held 83.5 GiB (67.9 of weights, 14 of cache, about 1.6 of working memory), ordinary process memory 8.0 GiB, and the kernel the rest. Of the 23.75 GiB counted as available, 22.5 GiB was page cache holding the hot rows of the 48 GB lookup table the model reads from disk. So memory given to the conversation cache is taken from that page cache. Generation speed on the capped code stream was 56.4 tok/s at 14 GB and 54.9 tok/s at 19 GB, where the page cache had shrunk to about 15 GiB. Those are single runs and the gap is within noise, but it is the number to watch if the cache grows further.

The seat was relaunched with a command generated from the live container's own configuration, changing only `--kv-cache-memory-bytes` from `14g` to `19g`. The 14 GB container is kept, stopped, as `qwen38-autoround-seat-14g` for a quick way back. The guard stayed active throughout. The pool went from 450,604 to 612,141 tokens, 2.34 full conversations.

| Test at 19 GB | Result | Peak memory | Under the 120 GB ceiling by |
|---|---|---|---|
| Generation speed, 8,192 tokens | 54.9 tok/s | 111.03 GB | 8.97 GB |
| Tool conversation grown in stages to 250K tokens | Pass: right tool call and right recalled value at every stage; a turn on the cached 250K conversation started in 2.1 s | 113.05 GB | 6.95 GB |
| One cold 250K prompt, then repeated | Pass: 159.6 s cold, 2.1 s repeated, correct on a changed question and on an unrelated prompt | 111.86 GB | 8.14 GB |
| Two independent 250K conversations at once, then repeated | **Fail on reuse:** answers correct, but neither was served from cache on the repeat (150 s and 301 s, against 158 s and 316 s cold) | 113.82 GB | 6.18 GB |
| Two independent 130K conversations at once, then repeated | Pass: 3.0 s and 3.4 s on the repeat, against 92 s and 162 s cold | 113.90 GB | 6.10 GB |

No swap, no guard stop, and nothing in the engine log about pre-emption, memory or CUDA errors.

What this establishes:

- **19 GB fits again, with room.** The worst peak was 113.90 GB. On 2026-09-10 the same setting peaked at 118.53 GB, 1.5 GB under the ceiling. The two runs are not identical (that day every test client ran on the Spark itself; today two of the five did), so the 4.6 GB difference should not be credited to the kernel fix alone.
- **The rise over time is a high-water mark, not a leak.** The GPU's memory grew from 88.2 GiB after loading to 92.1 GiB once the long prompts had been through, and stayed there when idle (105.9 GiB used overall). That matches the shape of the 18-hour rise seen at 14 GB: usage climbs as longer conversations arrive, then holds. Today's tests have already pushed the seat to its 250K mark, so factory traffic should not take it higher.
- **Sharing the seat works at the factory's conversation size and not at the extreme.** Two 130K conversations both stay cached. Two 250K conversations do not, even though together they are smaller than the pool, so the limit is in how the engine manages its cache as well as in its size. The 22 GB run below shows more memory helps only partly. For a coding agent sharing this seat with the factory, keep the agent's context compaction well below 250K.

**22 GB, tried the same day at the owner's request.** A bigger cache does not lengthen a single conversation; that limit stays at 262,144 tokens. It raises how much conversation stays cached at once, which is what keeps a long agent session quick from turn to turn. The seat was relaunched the same way with `22g`, giving a pool of 708,497 tokens, 2.70 full conversations, and the same five tests were run in the same order.

| Test | 19 GB | 22 GB |
|---|---|---|
| Pool | 612,141 tokens | 708,497 tokens |
| Tool conversation grown to 250K | Pass; 2.1 s on the cached conversation | Pass; 2.4 s |
| One cold 250K prompt, then repeated | Pass; 159.6 s cold, 2.1 s repeated | Pass; 159.6 s cold, 2.3 s repeated |
| Two 250K conversations at once, repeated | Fail: 150 s and 301 s, neither cached | Still a fail by the probe's rule, but better: 6.6 s (fully cached) and 88.7 s (about half re-read) |
| Two 130K conversations at once, repeated | Pass; 3.0 s and 3.4 s | Pass; 3.4 s and 3.4 s |
| Worst peak memory | 113.90 GB, 6.10 GB under the ceiling | 117.09 GB, 2.91 GB under the ceiling |
| Least memory available | 15.61 GiB | 12.64 GiB (the guard stops the seat below 9.93) |

No swap, no guard stop and no engine errors at either size.

Generation speed needs a note. The first 8,192-token speed test at 22 GB gave 38.4 tok/s, against 54.9 at 19 GB. A repeat straight after the 250K tests gave 40.2, and the repeat after that 59.2. During those two repeats the Spark took 83,000 major page faults and read 0.34 GB from disk. Three prompts the seat had never seen then ran at 56.3, 57.7 and 55.9 tok/s. So steady generation speed is unchanged at 22 GB. What the smaller page cache costs is a short slow patch, about 40 tok/s for a few minutes, after loading and after a very large prompt pushes the lookup table's rows out of memory.

**Where this leaves the seat.** It is running at 22 GB. The stopped containers `qwen38-autoround-seat-19g` and `qwen38-autoround-seat-14g` are the ways back: stop and remove `qwen38-autoround-seat`, rename the one wanted to that name, and `docker start` it. All the evidence, the probes and the relaunch script are on the Spark in `~/api-factory-resume-20260919T090408Z`.

The margin at 22 GB is thin for a seat that runs unattended. The peak sits 2.9 GB under the point where the guard stops the container, and a guard stop takes the factory's Player down. The tests have already driven the seat to its 250K high-water mark, so ordinary traffic should not go higher, but anything else that takes a few gigabytes on the Spark could. If a guard stop during a factory run would be costly, 19 GB is the safer setting and still holds two factory-sized conversations.

**What to do next.**

1. Leave the seat on factory traffic for at least a day, then read the guard's samples in `memory.jsonl`. It passes if the peak stays near 117 GB with no swap. Also compare the seat's own generation-speed counters with the 44.6 tok/s measured at 14 GB, since real traffic is the true test of the smaller page cache. Then remove the rollback containers that are no longer wanted.
2. To widen the margin without giving cache back, boot the Spark without a desktop. It starts at about 5 GiB used with the desktop; forum users report about 3 without.
3. Do not go past 22 GB on this build. If a larger pool is still wanted, the routes are a smaller `--max-num-batched-tokens` (8192 today; lower frees working memory and slows prompt reading) or an 8-bit cache if this build accepts it, each tested the same way.
4. Done the same day: the owner chose 22 GB, and the runbook now pins `KV_BYTES=22g` (its v1.8 note), with 19 GB as the tested fallback and 20 or 21 GB allowed once tested. The run is recorded in [RESULTS-qwen38-flash-next-kv-ceiling-20260919T090408Z.md](./RESULTS-qwen38-flash-next-kv-ceiling-20260919T090408Z.md) and its [drift report](./DRIFT-qwen38-flash-next-kv-ceiling-20260919T090408Z.md), which also give the fallback commands. The README and the factory evaluation note were updated to match. The protocol gate (tool calls and JSON) was run at 22 GB and passed.

### 4. After both boxes are fixed: prove two-box serving again

Launch the DeepSeek 0731 seat from its runbook, stop it, and launch it again without rebooting, since the kernel fault showed on relaunch. On the first request, require non-empty `reasoning_content` (see [the runbook changes](#changes-worth-making-to-the-0731-runbook)).

### 5. First agent trial against the Qwen seat

Add a separate gateway alias for the agent that pins thinking at `medium`, point the chosen agent tool at it, and run one real piece of factory work. Record the cache hit rate for that alias and any turn that ends without a tool call.

## Why the factory's location decides so much

The Dell hosts the factory: the forge, the specialist agents, the office manager, the LiteLLM front door, and the vLLM server that holds the tuned Gemma adapters. On 2026-09-19 it had 83 GB of its 121 GB in use. The Spark runs one thing, the Qwen3.8-Flash-Next seat.

Every two-box recipe on the forum wants each box almost empty. The best-documented GLM recipe asks for 118 GiB free on each node, and one careful tester had 2.3 GiB and 4.3 GiB spare at a 512K context. That is the same operating pattern as our DeepSeek seat: drain the model services on both boxes, bring the big model up for a session, tear it down afterwards.

So there are two different situations:

- **Driving features through the factory.** The factory needs the Dell's model services, so only the Spark is free. That means a one-box model.
- **Working on the factory's own code with a coding agent while the factory is stopped.** Both boxes are free, so a two-box model is possible for that session.

## What the forum says about each model for real coding work

Speeds are single-request generation speed in tokens per second (tok/s). "Prefill" is how fast the model reads the prompt; it matters for coding agents because every turn re-sends a growing history.

| Model | Boxes | Generation speed | What people who use it for software work say |
|---|---|---|---|
| Qwen3.8-Flash-Next (125B, 6B active per token) | 1 | On our seat, 58.8 tok/s in a capped code-stream test and 44.6 on real factory traffic; forum users report 45–57 in daily coding | Good at taking a ticket and working it end to end. Output has "a lot of silly mistakes" and is wordy. Fast prefill. |
| GLM 5.3 Flash (320B, 18B active) | 2 | 33–37 on prose, 37–50 on code with the best recipe; 25–32 is typical | The smartest of the three on hard problems. Slow, thinks for a long time, does not stop to ask. Weak at HTML/CSS. Drifts once a task's context passes about 260K tokens. |
| DeepSeek V4 Flash 0731 (284B, 13B active) | 2 | 83.8 structured / 77.6 code / 30.3 prose on our seat | Fast, stable for weeks, pleasant to work with interactively. Tends to brute-force, and hits a ceiling on hard problems where it "circles around the problem". |
| DeepSeek V4 Flash Vision Exp | 2 | 6–24% slower than 0731 on the same hardware with tuned stacks; 30–40% slower on the early ones | Same character as 0731 plus image input. Tool calling slightly more robust. |
| DeepSeek V4.1 Flash (552B) | 2, at about 3 bits | 25–40 | "A hot mess", "inconsistent", confabulates. Several people went back to 0731. |

### The one like-for-like benchmark

One poster (tsarihan) ran all three models on the same pair of Sparks with the same scripts, using a 40-task subset of SWE-bench Pro, a benchmark of real repository bug fixes ([thread 382697](https://forums.developer.nvidia.com/t/382697)):

| Model and build | Tasks solved | Time for the 40 |
|---|---|---|
| Qwen3.8-Flash-Next, NVIDIA 4-bit, 1M context | 38 of 40 | about 2 hours |
| Qwen3.8-Flash-Next, 8-bit | 36 of 40 | |
| GLM 5.3 Flash, 4-bit | 36 of 40 | about four times Qwen's |
| DeepSeek V4 Flash 0731, reasoning on at max | 33 of 40 | about 5.7 hours |
| DeepSeek V4 Flash 0731, reasoning silently off | 22 of 40 | |

Treat this as one person's result. Forty tasks is small, a gap of two or three tasks is within noise, and nobody has reproduced it. What it does support is that Qwen on cheaper hardware is in the same band as the two-box models, and that DeepSeek with reasoning off is much worse.

The same poster measured how long each model takes to read a 131K-token prompt on two boxes: Qwen 51 seconds, GLM 67 seconds, DeepSeek 115 seconds.

### The anecdotes, and how they split

The main comparison thread is ["So for Dual Spark what is the choice now"](https://forums.developer.nvidia.com/t/382628), 67 replies.

People who moved to GLM for coding:

- peter.h177, after two weeks of near-continuous heavy use (a C++ server for a 3D application, embedded back ends): "way more capable than ds4f in my tests… if you leave it for a day and come back, it will get things done." He keeps reasoning effort at High, because Max "will quickly fill the context window with reasoning tokens, even on trivial tasks", and runs it as an orchestrator handing subtasks to GLM subagents with an end-to-end test loop.
- squawksquack, 2 billion input tokens in: GLM is "like a Harbor Freight's Opus 4.x", DeepSeek 0731 "feels like Harbor Freight Sonnet". GLM is "more thoughtful / less wasteful with changes, especially on architecture level changes"; DeepSeek "will bruteforce its way thru".
- 0rand switched to GLM on the Sparks for unattended work. He describes DeepSeek as needing "baby-sitting", and GLM as something that "does not stop and talk to you, report, ask anything, just pushes through".
- phyo.arkarlwin started out with garbage output from GLM, fixed it by changing checkpoint, and ended up preferring it for long, complex tasks. His example of the cost: a simple document edit took GLM more than 17 minutes of thinking.

People who stayed with DeepSeek:

- stu.miller runs four Sparks around the clock: "ds4flash 0731 beats everything… up for almost 6 weeks flawlessly." He tried GLM for two days: "slightly better than ds4flash but slow as hell."
- co-le uses 0731 for software engineering with "almost zero sessions that annoyed me".
- OllieO tried GLM on a real task: "finished in 25m, end result was bad… Back to Vision Exp."

One person compared Qwen and DeepSeek directly for coding (Zambonilli, using Claude Code and opencode as the agent tools): Qwen is "better at agentic coding", DeepSeek "better at mechanical coding… the code it produces, while verbose, usually doesn't need a ton of rework."

The pattern is consistent. GLM wins when the task is hard and nobody is waiting. DeepSeek wins when someone is sitting at the keyboard. Qwen is the one-box option that gets closest to both.

## The kernel problem on both boxes

**What is wrong.** Kernel `7.0.0-1019-nvidia` turns on a feature (Kexec HandOver, KHO) that reserves about 9.3 GiB at boot in a way the kernel then mis-accounts. When a two-box job tries to pin memory for the network link while the GPU holds a lot of memory, the pin fails with `ibv_reg_mr_iova2 failed with error Cannot allocate memory` and the job dies or hangs. NVIDIA staff confirmed the cause in [thread 383023](https://forums.developer.nvidia.com/t/383023) and posted an [update advisory](https://forums.developer.nvidia.com/t/383254).

**When it bites.** One poster tested it directly: with 85 GB of GPU memory in use per box it passed, at 90 GB it flipped between passing and failing across boots, and at 100 GB it failed every time. On the older 6.17 kernel it passed at every size up to 110 GB. Others found the first launch after a reboot works and every relaunch fails. Our DeepSeek seat has not been launched since this kernel arrived. The same reservation also explains the [7 GiB drop in available memory](https://forums.developer.nvidia.com/t/383222) people saw after the update, which matters for the fixed memory guard on our Qwen seat.

**Checked on our boxes, 2026-09-19, before the fix.** Both reported the same thing (both have since been fixed; see [Concrete next steps](#concrete-next-steps)):

```
kernel: 7.0.0-1019-nvidia
/proc/cmdline: no kho=off
CmaTotal: 0 kB, CmaFree: non-zero      (the forum's signature of the broken state)
nvidia-spark-grub-kho: Installed: (none), Candidate: 1.0-1
GRUB_DEFAULT=0, no apt holds
driver 580.173.02
```

**The fix.** NVIDIA shipped a package on 2026-09-17, `nvidia-spark-grub-kho`, which adds `kho=off` to the kernel command line. A normal `sudo apt update && sudo apt upgrade` installs it; a reboot applies it. If the package does not appear, `sudo apt clean all` first. Afterwards `cat /proc/cmdline` should contain `kho=off`, and `sudo ls /sys/kernel/debug/kho` should say the path does not exist. The original reporter and several others confirmed two-box serving works again after this.

**Side effects and fallback.** Two people needed to lower the GPU memory setting slightly afterwards (one went from 0.84 to 0.82), and one saw out-of-memory errors he had not seen before. Three people said adding `kho=off` by hand did not help them and went back to the older kernel. The forum's known-good kernels are `6.17.0-1031` and `6.17.0-1032`. Neither box has those installed; the newest older kernel on both is `6.17.0-1029`, which one working setup on the forum uses but nobody has formally validated. If a rollback is ever needed, set the kernel by its full menu path in `GRUB_DEFAULT`; several people found `grub-set-default` silently does nothing on DGX OS.

**Test after fixing.** Launch the two-box seat, stop it, and launch it again without rebooting. The failure shows on the relaunch.

A related report: another Dell Pro Max GB10 owner had this kernel update install without its boot image, leaving the machine unable to boot ([thread 383505](https://forums.developer.nvidia.com/t/383505)). Both our boxes already boot this kernel and both have non-empty boot images for it and for `6.17.0-1029`, so we got through that. After the upgrade and before the reboot, check again that `/boot/initrd.img-7.0.0-1019-nvidia` exists and is not empty. The thread has a recovery procedure that keeps the disk contents; NVIDIA's own recovery image wipes the disk.

## Qwen3.8-Flash-Next on one box

We run the Saren build: 4-bit weights (Intel AutoRound Int4), all ten experts per token, three-token speculative decoding, prefix caching on, 58.79 tok/s measured on 2026-09-10. That is still a sound choice. What has changed on the forum since then ([main thread](https://forums.developer.nvidia.com/t/381228), [Int4 thread](https://forums.developer.nvidia.com/t/382733), [NVIDIA 4-bit thread](https://forums.developer.nvidia.com/t/382957)):

- **A faster build exists, at some cost in quality.** azampatti's build halves the experts used per token from ten to five and retrains the shared expert to compensate. On the author's own tests it runs about 72 tok/s against about 57 for the ten-expert build. Independent users report 45–57 tok/s in daily coding. One independent coding benchmark, run before the author's 2026-09-18 quality update, put it behind the full model: C++ 87.0% against 89.4%, Rust 80.8% against 87.8%, a HumanEval-style set 57.9% against 64.6%. Read that with care: the full model in that test was NVIDIA's 4-bit checkpoint on a different serving stack, not our build, so it compares whole stacks; it was one person on one box with few trials; and the Python test was adapted for chat with a short output limit, so it is not the standard HumanEval score. Our runbook already treats fewer experts as a separate quality experiment, and that still looks right.
- **NVIDIA's own 4-bit checkpoint is slower on one box** (28–31 tok/s on the latest image) and scores about the same on tool-calling tests. Several 4-bit builds on the forum ran without prefix caching, which means re-reading the whole history every turn. Ours has it on.
- **Running it at 8 bits across two boxes is slower for a single request** (35–45 tok/s) and nobody measured better tool calling from it. There is no reason to spend both boxes on Qwen.
- **A new failure to watch for in agent use.** One user logged the model ending a turn with text like "Let me…" and no tool call, on about 3.5% of turns (219 of 6,257) under the OpenHands agent on the five-expert build. Swapping back to the stock chat template did not fix it. It is unresolved. A second, harmless oddity: the model occasionally remarks that "the user hasn't asked a question yet" after a tool result and then carries on ([thread 383593](https://forums.developer.nvidia.com/t/383593)).
- **Memory creeps up on very long agent runs.** One user saw a 262K-context session climb close to the 128 GB limit from a nearly empty box; at 200K with 20 GB of cache it stayed flat at about 108 GB. Our 19 GB cache under a 120 GB guard is in the same territory. Applying the kernel fix should hand some memory back.
- **Reasoning level.** The stock template defaults to the highest level. The Int4 author suggests medium for daily work and the highest for bug review or overnight runs. One measurement: more than 12,000 reasoning tokens with thinking on against about 2,100 with it off for the same task.

### Should the recipe change when a coding agent uses this seat?

No. Keep the recipe; change how the agent is connected to it. The seat works well as the factory's code-writing model, and the things an interactive agent needs most are things this build already has: prefix caching that works on a growing conversation, fast prompt reading, and the fastest generation of any full-quality one-box build on the forum.

The live seat's own counters show why the cache matters more than generation speed. Between its relaunch on 2026-09-17 and 2026-09-19 it served 759 factory requests:

| Measure | Value |
|---|---|
| Average prompt | 45,788 tokens |
| Average output | 807 tokens |
| Prompt tokens to generated tokens | 57 to 1 (34.8M against 0.61M) |
| Prompt tokens served from cache | 91% |
| Average wait for the first token | 2.56 seconds |
| Generation speed on real work | 44.6 tok/s |
| Speculative guesses accepted | 62.6%, 1.88 extra tokens per step |

Generation on real work is 44.6 tok/s, not the 58.8 of the capped code-stream test, because the speculative guesses are accepted 62.6% of the time on real work against 91.7% in that test. An average request spends about 18 seconds generating and 2.6 seconds waiting to start. Without the cache it would first have to read 45,788 tokens, about 30 seconds at the prompt-reading speed we measured, which would more than double the request. A coding agent's traffic has the same shape: a large growing prompt and short outputs each turn. So a recipe without working prefix caching would be slower in practice even if it generated at the same speed, and a recipe that generates 20% faster saves only three or four seconds a request.

The alternatives, and why none is a better fit for an agent:

| Alternative | What it would gain | Why not |
|---|---|---|
| azampatti's five-expert Int4 build | About 72 tok/s on the author's tests | Independent users report 45–57 tok/s, which is what we already get. It reads prompts more slowly (about 1,000 tok/s against about 1,550 measured on our seat at 250K). It scored lower on the one independent coding benchmark, and it is the build where the "Let me…" stall was logged. |
| NVIDIA's or local-inference-lab's 4-bit checkpoints on the MiaAI-Lab or PILCOTHINK recipes | The highest tool-calling test score on the forum (95), and an 8-bit cache that roughly doubles the number of tokens held (one recipe reports 995K on one box) | Generation is 28–37 tok/s, about 40% slower than ours. As of 2026-09-11 these stacks ran without prefix caching, so every turn re-reads the whole history. The score gap is within the test's run-to-run spread. |
| The Lance build we keep as a fallback | Prefix caching on a newer vLLM | 22–24 tok/s with speculative decoding off. |

What does need attention, all of it configuration:

- **Thinking level.** Checked on the live seat: the chat template turns thinking on by default at `xhigh`, and accepts only `xhigh`, `medium` and `low`. Any other value is rejected with an error, which is the "400 Unexpected reasoning effort high" a forum user hit from Claude Code. The factory never sees this because the Player sends thinking off. An agent tool that sends `high` or `max` will fail on every request; one that sends nothing will think at the slowest level. The build's author suggests `medium` for daily work. Give the agent its own alias at the LiteLLM front door that pins `medium` and removes or maps whatever effort value the tool sends. A separate alias also keeps the agent's usage apart from the Player's in the accounting.
- **The cache is shared.** The seat ran with 14 GB of cache from 2026-09-17, after the box ran out of memory and went into swap, and was moved to 19 GB and then 22 GB on 2026-09-19 once the kernel was fixed. At 22 GB that is a pool of 708,497 tokens, 2.70 full-length conversations. At 14 GB the factory traffic was served from cache 91% of the time (31.7M of 34.8M prompt tokens). Tests on 2026-09-19 showed two independent 130K-token conversations both stay cached at either size. Two 250K-token conversations do not both stay cached even though they fit in the pool; at 22 GB one did and the other was about half re-read. So a factory feature and an agent session can share the seat as long as the agent's context is compacted well below 250K; 150K is a sensible setting. If an agent turn that normally starts in a second or two takes a minute, its conversation has been pushed out. Measure the cache hit rate per client before judging how the agent feels.
- **The memory guard protects the box by stopping the container.** A long agent session that trips the 120 GB guard takes the factory's Player down with it. One forum user saw a 262K-token agent run climb close to the 128 GB limit from an almost empty box. On our seat the worst test peaked at 113.9 GB with 19 GB of cache and 117.1 GB with 22 GB; see step 3 of [Concrete next steps](#concrete-next-steps).

If sharing does turn out to be the problem, the one recipe-level change worth testing is an 8-bit cache, which would roughly double the pool. The recipes that have it use different checkpoints and generate more slowly, so measure the contention first.

### How this squares with the 18 September Codex review

That review (`video-plans/2026-09-18-qwen38-runbook-forum-review.md` in the youtube-channel repo) examined the Hybrid Sharp runbook and treated Hybrid Sharp, with speculative decoding off, as the working factory deployment at 36–37 tok/s. The live system says otherwise:

- The Dell's gateway routes both factory aliases, `flash-next` and `flash-next-t06`, to `qwen3.8-flash-next-autoround` on the Spark.
- The only Qwen container on the Spark, running or stopped, is `qwen38-autoround-seat`, created 2026-09-15, with three-token speculative decoding on.
- Hybrid Sharp measures 22–24 tok/s on the forum. A whole-request rate of 36–37 tok/s is what the AutoRound seat's counters predict: 807 tokens in about 18 seconds of generating plus 2.6 seconds of waiting is about 39 tok/s.

So the 36–37 figure most likely came from the AutoRound seat, and the review's main recommendation, to trial a full-expert AutoRound build with speculative decoding, describes what is already in production. It was executed and recorded on 2026-09-10 in `RUNBOOK-qwen38-flash-next-autoround-seat.md` and its results files. Whether Hybrid Sharp ever served the factory cannot be told from the boxes today.

The rest of the review holds and agrees with this note: record the live configuration as a receipt (the 14 GB cache setting the seat ran with from 17 to 19 September is in neither runbook); treat the five-expert build as a modified model and judge its capability as well as its speed; compare recipes on the same factory tasks by time to accepted work, not by tok/s; and keep testing prefix reuse on growing tool conversations, since the upstream vLLM issue (#54173) was still open.

A newer one-box engine, [DGPP](https://forums.developer.nvidia.com/t/383406), reports 42.6–50.3 tok/s for the NVIDIA 4-bit Qwen checkpoint on one box and 62–75 on two. It is a few days old. Early users found it rejects requests that combine tools with a JSON response format, and it shipped with a 256-token default output limit. Worth watching, not worth adopting yet.

## GLM 5.3 Flash on two boxes

There are three families of build ([main thread](https://forums.developer.nvidia.com/t/381350), [optimisation thread](https://forums.developer.nvidia.com/t/382939), [Intel thread](https://forums.developer.nvidia.com/t/382041), [EXL3 thread](https://forums.developer.nvidia.com/t/382486)). The two big threads favour different ones: the optimisation thread is built around NVIDIA's checkpoint, while the people in the main thread doing agent work day to day have mostly moved to Intel's.

| Build | Generation speed | Strengths | Weaknesses |
|---|---|---|---|
| Intel's 4-bit checkpoint (`Intel/GLM-5.3-Flash-W4A16-AutoRound`) with the model's built-in three-token speculative decoding. Recipes: `taoofshawn/spark-recipes` (`glm-v53-flash-intel-w4a16`), and florianbrede's forum thread "GLM 5.3 Flash Intel AutoQuant W4A16 TP2 MTP3 - Concurrent Agentic Use" | 23–34 for one request (52 on code in one test), about 98 in total across eight requests | The main thread's consensus for agent work on two boxes; at least six people run it. Cache of 1.75–2.4M tokens. A cached 32K-token turn came back in 0.7 seconds against 3.7–4.5 for the others, which is what a coding agent feels most. One overnight Claude Code run: 7.5 hours, 360M prompt tokens submitted, 97.7% served from cache. Another user: several billion input tokens across 4–6 parallel agents. Everything in the chain is reported as MIT or Apache licensed. | Older recipes had to rewrite the checkpoint's config file before it would load. A zero-point bug in vLLM needs a small fix (`mods/fix-autogptq-sym-qzeros`). The fast external drafter does not work well with it. |
| NVIDIA's 4-bit checkpoint (`nvidia/GLM-5.3-Flash-NVFP4`) on PILCOTHINK's vLLM image with 0rand's tuning. Repo: `0rand/glm-5.3-flash-nvidia-nvfp4-dflash-2x-dgx-sparks` | 33–37 prose, 37–50 code | Fastest single request. At least four other people reproduced it. Context up to 1M. | Its speed comes from an external drafter model, DFlash2, which forum posts and one installer's own output describe as CC BY-NC-ND, a non-commercial licence. Without it the speed falls to about 24–27. Needs about 118 GiB free per box for the 1M setting. Two to four concurrent requests at most. One user who tested both found it scored below Intel's and left less room for cache. |
| EXL3 4-bit (`Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw`) on Entrpi's or MiaAI-Lab's engine | 20–37 | Closest to the original model by the forum's measurements, and the most consistent across repeated test runs. | Both engines also lean on the DFlash2 drafter. Entrpi's engine caches in blocks of 4,608 tokens, so an agent making many short turns reuses very little (one user measured 3.8%); MiaAI-Lab's is effectively one request at a time. Upgrades of Entrpi's image have been painful. |

If we build a GLM runbook, start from the Intel build. It has the strongest evidence for the thing we would use it for, long agent sessions with a growing history, and it avoids the drafter's licence question. We use these boxes commercially, so read the licences of the model and the drafter ourselves before relying on forum summaries; the thread does not state the model's own licence.

Two settings matter more than the choice of build:

- **Reasoning effort.** The model's chat template only recognises `low` and `high`. Anything else, including sending nothing, `medium`, `max` or `xhigh`, is treated as max. At max the model writes monologues of up to 30,000 tokens between tool calls, and one user timed 45 minutes for a single turn. Switching to `high` "cut reasoning output by 90%… it's like 4 times faster now", and the model maker's own figures show only a slight quality drop. A good share of the "GLM is unbearably slow" reports were made at max. Send `high` explicitly.
- **Whether thinking is on at all.** Entrpi's launcher starts with thinking off by default, and one user measured a science benchmark at 70% that way against 91.2% with it on. Some chat templates ignore the switch entirely. As with DeepSeek, check that a response actually contains reasoning.

Things that will catch us:

- **Garbage output and repetition loops in agent runs** came from one specific checkpoint (`LibertAIDAI/GLM-5.3-Flash-NVFP4`), which emits occasional corrupt tokens that wreck a tool call. The NVIDIA and RedHat checkpoints do not have the fault. Use the model maker's agent sampling settings, temperature 0.95 and top_p 1.0, set on the server; low temperature makes any loop worse.
- **A second kind of breakdown is unresolved.** One user, in a Pi session on Entrpi's EXL3 image, saw the model's thinking collapse into an endless stream of "!!!" at about 100K tokens of context, and gave up and let DeepSeek finish the job. It matches an open SGLang bug report (#36669) about multi-tool agent prompts. He had reached 400K on the same setup before without trouble.
- **The boxes have to be nearly empty.** People who got it running had 5 GB or less in use on each box before loading, and sat at 117–121 GB of 122 GB afterwards. Both our boxes boot to a desktop and the Dell runs the factory. Fitting the settings to our boxes will take a session of its own, as it did for DeepSeek.
- **The first box can run out of memory while loading weights.** The fix that worked is `--load-format instanttensor`, which also cuts loading from 13–30 minutes to about 4. Do not try to cap the container's memory with Docker instead: one user's box "wedged hard for hours and needed a reboot".
- **`--gpu-memory-utilization 0.9` fails to start** on a box with 108 GiB free; 0.85 passes.
- **Prefix caching is fragile and decides how usable an agent feels.** Measured hit rates ranged from 3.8% to 97% depending on the stack and its flags. With Claude Code as the client, one user went from 47.7% to 97.7% by passing the chat template explicitly and turning off the attribution header Claude Code adds to each request. Measure the hit rate with our actual agent tool before judging the speed.
- **vLLM merged support for the model around 2026-09-04,** but every working two-box recipe still carries patches. Pin the image.
- **The checkpoints are 165–204 GB and must be on both boxes.** Intel's is the smallest at 165 GiB. The Dell has 376 GB free on a disk that is 90% full. The Spark has 2.4 TB free.
- **Reading a long prompt is slow.** With 0rand's recipe the wait before the first token grows in step with the prompt: about 70 seconds at 64K tokens, 136 seconds at 128K, 270 seconds at 256K. Prefix caching hides this on later turns of the same conversation, but a cold start or a context compaction pays it in full.
- **One unexplained report** of a two-box cluster freezing within a day after the DGX OS 7.6.0 update brought driver 580.178.04. Both our boxes are on 580.173.02, the driver NVIDIA documents.

GLM 5.3 Flash on one box means squeezing it to about 2 bits. One such build reports 64 tok/s on structured output and 25 on prose, and its own measurements show the damage: it picks the same next token as the original only 88.9% of the time. There is also a 2-bit llama.cpp recipe. Forum opinion is that quantising this hard wrecks these models for agent work.

## DeepSeek: keep 0731, and what to change in the runbook

### Why not move the runbook to the Vision build

The [Vision Exp thread](https://forums.developer.nvidia.com/t/381911) runs to 393 replies. What it establishes:

- **It is slower.** Six people compared it with 0731 on the same hardware. On the early stacks the gap was large: 26 against 45 tok/s under heavy agent work, 31.6 against 44.8 on code. On the tuned stacks at the end of the thread it narrowed: 45 against 48 on coding, 36.5 against 44.0 on a standard benchmark, 38–41 against 50.5 on mixed real prompts. The cause is the built-in draft head that does the speculative decoding (the model guesses several tokens ahead and checks them in one step). On 0731 the guesses are accepted 49–74% of the time; on Vision Exp 21–35%. No recipe fixes that; it is in the checkpoint.
- **It is not a drop-in swap.** The 0731 images have no image processor. Every Vision recipe either patches one in or moves to a newer vLLM build, so it means a new image build on both boxes (two hours for one poster, seven and a half for another). Most Vision stacks also require the speculative setting to be a multiple of three, six by default, where our runbook pins five; two recipes patch around that.
- **The code quality case is unproven.** Tool-calling test averages were 91 against 89.2 for 0731, inside the test's own noise. One user reported noticeably sturdier function calling. Another, doing software work, went back to 0731 plus a separate vision model after Vision Exp twice tried to act on production instead of development.
- **We already have the separate vision model.** The Granite vision seat covers image input. "0731 plus a vision sidecar" is where that user ended up, and it is what we have.

If image input inside the coding model becomes a real need, add it as a separate overlay runbook and leave 0731 as the pinned lane. Two starting points. The closest to what we run is `tonyd2wild/DeepSeek-v4-Flash-Vision-Exp-DSpark-1M-NVFP4-KV-2x-DGX-Spark`, by the author of the recipe we already pin: it keeps our five-token speculative setting and our `nvfp4_ds_mla` cache type, and adds a vision patch and an architecture override. One forum user measured a 2.72M-token cache on it. The other is OllieO's `oselivanov/ollie-gb10-serving-stacks`, which was the most recommended by the end of the thread. OllieO's stack replaces the `b12x` kernels with `marlin`, because he traced corrupted numbers under concurrent requests to the `b12x` expert kernels on the newer images. Our runbook depends on `b12x` for its speed. Nobody has reported that fault on the older image we pin, and we have not tested for it.

### Changes worth making to the 0731 runbook

1. **Check that reasoning is actually on.** Our live launch file has `--default-chat-template-kwargs '{"thinking":false}'`, so any client that does not ask for thinking gets none. Worse, our own first-run results recorded that with thinking requested at max effort, `reasoning_content` still came back empty and the token count matched the visible text. The forum poster who found this problem gives exactly that as the sign reasoning is off, whatever the launch line says. His scores were 22 of 40 with it off and 33 of 40 with it on, and the "format errors" he first blamed on the parser disappeared once the model could think. DeepSeek's own settings for coding agents are reasoning effort max, temperature 1.0, top_p 0.95. Our launch file also has `--generation-config vllm`, which he notes makes vLLM ignore the checkpoint's sampling defaults. The runbook should gain a gate: send one request, require non-empty `reasoning_content`.
2. **Add a kernel gate to the pre-flight phase:** `kho=off` present on both boxes, and a relaunch-without-reboot test.
3. **Cap how much of a long prompt is read before other requests get a turn:** `--long-prefill-token-threshold 1024`. Measured on the forum: the next turn in another session dropped from 153.6 seconds to 2.17 seconds while a long prompt was being read.
4. **A prefix-cache gap that affects 0731 too.** Prompts ending 1–64 tokens past a 256-token boundary were never cached, about one request in four. The fix is `stujmiller/dsv4-prefix-replay-tail-fix`, confirmed by a second user. For a coding agent that re-sends its history every turn, this is a real saving.
5. **A newer parser fix,** vLLM PR #55954, handles tool calls where the model omits the wrapper. It sits alongside the #573 fix we already mount, and is worth checking against our image.

### DeepSeek V4.1 Flash

552B parameters and 510 GB on disk ([thread 382725](https://forums.developer.nvidia.com/t/382725)). Two community recipes squeeze it onto two boxes at about 3 bits per weight, with 25–40 tok/s, a GPU memory setting of 0.92, both boxes headless and nothing else running ([thread 383583](https://forums.developer.nvidia.com/t/383583)). Verdicts from people who have used it, locally and through the paid API: "a hot mess", "inconsistent", "bad about confabulating", and two to three times the thinking tokens of 0731. The people running it well have four or eight Sparks.

One side finding from that recipe is useful to us: on a box with no desktop session, the 2 GB reserved for the display can be given to CUDA. Both our boxes boot to a desktop today.

## Other models that came up

- **Qwen3.8-27B (dense, one box):** about 50 tok/s with a tuned SGLang recipe. The same poster's benchmark had it at 75% against 90% for the big models. A reasonable fast helper, not the main coder.
- **MiniMax M3:** liked as an agent "voice", rated less solid at coding, and its licence restricts commercial use.
- **MiMo V2.6 Flash (309B, 15B active):** announced, not released. The previous version took a long time to get working in the serving engines.
- **Ling 3.0 Flash (124B, 5B active):** mentioned as a decent one-box daily driver. No coding reports.

## What the forum says about agent tools

This is outside the scope of this note, so only what came up in passing. The tools people pair with these models are Hermes, opencode, Claude Code pointed at a local endpoint, the DeepSeek harness, Qwen Code and OpenHands. Pi appears a handful of times. One user runs "pi subagents + hermes + LiteLLM proxy" across his boxes with Qwen3.8-Flash-Next and GLM 5.3 Flash and calls it "the workhorse so far. No hiccup." That is close to our own layout, since we already have the LiteLLM front door. The "!!!" breakdown described in the GLM section happened in a Pi session. Two others run the oh-my-pi variant, one with Qwen at about 29 tok/s. Two more posts are relevant to us: one user found DeepSeek and GLM "work very well" on the DeepSeek harness and finished a bug-fix job with GLM that an older Qwen had failed; another found the DeepSeek harness repeated every message back to Qwen3.8-27B in each thinking cycle, which a reply put down to the chat template. Several people said the harness makes as much difference as the model.

## What this research does not establish

- Nothing here was run on our boxes. Every speed and score is someone else's, on their stack, with their prompts.
- The forum's favourite tool-calling test has a run-to-run spread of about four points. Most of the differences people argue over are smaller than that.
- Several long forum posts were written by the posters' own models and pasted in. One was caught in a factual error by another member.
- Whether any of these models can do the factory work to the standard Claude does is the real question, and only a trial on our own tasks answers it. The cheapest such trial is an agent pointed at the Qwen seat we already run.

## Sources

All on `forums.developer.nvidia.com`, read in full on 2026-09-19.

| Thread | Subject |
|---|---|
| [382628](https://forums.developer.nvidia.com/t/382628) | GLM 5.3 Flash or DeepSeek V4 Flash for two Sparks |
| [382697](https://forums.developer.nvidia.com/t/382697) | Three models on two Sparks: prefill, first-token time, SWE-bench Pro |
| [381832](https://forums.developer.nvidia.com/t/381832) | DeepSeek, GLM and Qwen compared, and one-box advice |
| [382939](https://forums.developer.nvidia.com/t/382939) | Optimising NVIDIA's GLM 5.3 Flash checkpoint for two Sparks |
| [381350](https://forums.developer.nvidia.com/t/381350) | GLM 5.3 Flash main thread |
| [382041](https://forums.developer.nvidia.com/t/382041), [382486](https://forums.developer.nvidia.com/t/382486), [383673](https://forums.developer.nvidia.com/t/383673), [383674](https://forums.developer.nvidia.com/t/383674) | GLM builds: Intel 4-bit, EXL3, four-Spark recipes, vision complaints |
| [381911](https://forums.developer.nvidia.com/t/381911) | DeepSeek V4 Flash Vision Exp |
| [382725](https://forums.developer.nvidia.com/t/382725), [383583](https://forums.developer.nvidia.com/t/383583), [383242](https://forums.developer.nvidia.com/t/383242), [383539](https://forums.developer.nvidia.com/t/383539) | DeepSeek V4.1 Flash |
| [382026](https://forums.developer.nvidia.com/t/382026), [382584](https://forums.developer.nvidia.com/t/382584) | DeepSeek 0731 in NVIDIA 4-bit; Vision Exp on one Spark |
| [381228](https://forums.developer.nvidia.com/t/381228), [382733](https://forums.developer.nvidia.com/t/382733), [382957](https://forums.developer.nvidia.com/t/382957), [382476](https://forums.developer.nvidia.com/t/382476), [383593](https://forums.developer.nvidia.com/t/383593) | Qwen3.8-Flash-Next |
| [383023](https://forums.developer.nvidia.com/t/383023), [383222](https://forums.developer.nvidia.com/t/383222), [383254](https://forums.developer.nvidia.com/t/383254), [383505](https://forums.developer.nvidia.com/t/383505) | Kernel 7.0.0-1019 regression, memory loss, NVIDIA's advisory, Dell boot failure |
| [383406](https://forums.developer.nvidia.com/t/383406) | DGPP inference engine |
