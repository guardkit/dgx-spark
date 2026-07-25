# Prior art: executable runbooks — a reference

**What this is.** I got curious about whether the runbook technique in this repo was something other people already do. It is — mostly. This is the reading I did, so I don't have to make claims in a video that I can't back up, and so anyone who wants the citations can have them.

**Short version:** essentially every ingredient is prior art, a lot of it boring and mainstream. The one thing I can't find written down anywhere is the rule that *the agent may detect drift but may not amend the procedure*.

Researched 2026-07-14. Some items are moving fast; dates matter.

---

## 1. Executable documentation is ~40 years old

| What | When | The line |
|---|---|---|
| [Knuth, *Literate Programming*](https://academic.oup.com/comjnl/article/27/2/97/343244) | 1984 | *"treat a program as a piece of literature, addressed to human beings rather than to a computer"* |
| [Python `doctest`](https://docs.python.org/3/library/doctest.html) | stdlib | *"this has the flavor of 'literate testing' or **executable documentation**"* |
| [Go example tests](https://go.dev/blog/examples) | 2015 | *"Having **executable documentation** for a package guarantees that the information will not go out of date as the API changes."* |
| [Rust doctests](https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html) | — | on by default, whole ecosystem — `cargo test` runs your docs |
| [Ned Batchelder's Cog](https://nedbatchelder.com/code/cog/) | ~2004 | `--check` mode **fails CI when a doc drifts** |
| [Howard Abrams, "literate DevOps"](https://howardism.org/Technical/Emacs/literate-devops.html) | 2015 | ran shell blocks against **remote servers** from an Org buffer via TRAMP. *"I started calling my modified approach, literate devops."* |
| [Netflix: scheduling notebooks](https://netflixtechblog.com/scheduling-notebooks-at-netflix-348e6c14cfd6) + [Papermill](https://github.com/nteract/papermill) | Aug 2018 | notebooks as scheduled production jobs; the executed notebook becomes *"an immutable historical record"* |

**The closest single ancestor, and the honest one to name:**

> [**Dan Slimmon, "Do-nothing scripting: the key to gradual automation"**](https://blog.danslimmon.com/2019/07/15/do-nothing-scripting-the-key-to-gradual-automation/) (15 July 2019) — a script that walks a human operator through a runbook, step by step, doing nothing itself.

**An executable runbook is the do-nothing script with an LLM as the human.** (Braintree shipped a `Runbook` Ruby DSL explicitly built on Slimmon + Gawande's *Checklist Manifesto*.)

⚠️ **Careful:** Knuth's literate programming is *exposition + tangle/weave*. It does **not** run your prose and fail on an assertion. That property comes from the doctest/Go/Rust/Cog lineage. Don't conflate them.

**And note where all of it points: at API examples, not operational procedures.** Rust fails your build because a docstring lies about a *function*. Nothing in that tradition fails your build because a runbook lies about a *machine*.

---

## 2. The problem, in Google's own words

> *"…recording the best practices ahead of time in a 'playbook' produces roughly a 3x improvement in MTTR as compared to the strategy of 'winging it.'"*
> — [*Site Reliability Engineering*, Ch. 1](https://sre.google/sre-book/introduction/)

> *"Details in playbooks go out of date at the same rate as production environment changes. For daily releases, playbooks might need an update on any given day."*
> — [*The Site Reliability Workbook*](https://sre.google/workbook/on-call/)

Playbooks are 3x better **and** they rot as fast as you ship. That's the whole motivation.

⚠️ The 3x figure is an internal assertion (*"we have found"*) with no published methodology. Say *"Google's SRE book asserts…"*, never *"studies show…"*.

Google's own answer is the obvious objection:

> *"If your playbooks are a deterministic list of commands that the on-call engineer runs every time a particular alert fires, we recommend implementing automation."*

Which is fair — and this *is* that automation. The difference is that it doesn't fork into two artifacts that drift apart.

---

## 3. Halting gates in runbooks: mainstream, boring, ~10 years old

**AWS Systems Manager Automation** (~Dec 2016) ships [`aws:assertAwsResourceProperty`](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-action-assertAwsResourceProperty.html) — `DesiredValues` is documented as *"The expected status or state **on which to continue** the automation."* And in the [shared step properties](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-actions.html):

- **`onFailure`** — *"The default value for this option is **abort**."*
- **`isCritical`** — default **true**.

So a failed assertion fails the step, and a failed step aborts the run, **by default**.

Others:
- **Ansible** — [`assert`](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/assert_module.html), `fail`, `failed_when`, `any_errors_fatal` (*"stops executing the play on all hosts"*). Since ~2012.
- **Rundeck** (PagerDuty, [acquired Oct 2020](https://www.pagerduty.com/newsroom/pagerduty-closes-acquisition-rundeck/)) — failure strategy *"Stop at the failed step: Fail immediately (**default**)"*.
- **StackStorm Orquesta** — *"designed to fail fast and terminate the execution of the workflow when a task fails."*
- **GCP Cloud Workflows** — `raise` / `try`/`except`. **Azure Automation** — runbooks are PowerShell/Python; halting is just exception handling (no declarative assert).

### The detail that matters most

**AWS SSM documents *do* contain markdown** — the docs explicitly demonstrate *"the use of Markdown to format document descriptions."* But it's markdown **inside the `description:` field**. The steps are YAML.

> **The prose is a comment. It is never executed.**

Every commercial runbook product draws that line — AWS, Rundeck, StackStorm, Ansible, Azure, GCP. The document *describes* the automation; a separate structured artifact *is* the automation. And the two drift apart. **That's the rot.** An executable runbook erases the line.

⚠️ `precondition` is a Command-document (schema 2.2) feature, **not** an Automation (0.3) step property. Easy to get wrong.

---

## 4. Markdown-executed-by-an-LLM: an open standard, not a novelty

[**Agent Skills / `SKILL.md`**](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (Anthropic, 16 Oct 2025) is exactly "a markdown prose procedure an LLM reads and executes." Now an open standard at [agentskills.io](https://agentskills.io/) with **40+ implementations** — Claude Code, Codex, Gemini CLI, Copilot, Cursor, OpenCode, Goose, Kiro, JetBrains Junie…

This is the **least** novel ingredient in the technique, not the most.

Note: `SKILL.md` frontmatter has **no** assertion, gate, precondition, or success-criteria field. "Validation" in that spec means linting your frontmatter.

Related: `AGENTS.md` (OpenAI-led, Aug 2025; now under the Linux Foundation's Agentic AI Foundation; ~60k projects), `CLAUDE.md`, Cursor rules, `copilot-instructions.md`. **All of these are context, not procedure** — they describe what a project is like; none defines an ordered, gated, assertion-checked sequence.

**Gates in markdown, specifically:** GitHub's [Spec Kit](https://github.com/github/spec-kit) ships literal `STOP` and *"Halt execution if any non-parallel task fails"* inside its markdown templates, plus *"**GATE**: Must pass before Phase 0 research."* And [pytest-codeblocks](https://github.com/nschloe/pytest-codeblocks) / markdown-clitest have been failing CI on markdown assertions since ~2020.

---

## 5. Tools in this space

| Tool | Stars (2026-07-14) | Gates? |
|---|---|---|
| [Runme](https://github.com/runmedev/runme) | 2,120 | see below |
| [just](https://github.com/casey/just) | 34,751 | `assert()` — but justfiles aren't markdown |
| [Papermill](https://github.com/nteract/papermill) | 6,461 | halts on cell exception |
| [mdflow](https://github.com/johnlindquist/mdflow) | 595 | executable markdown prompts; **pins the model** in frontmatter |
| [xc](https://github.com/joerdav/xc) | 1,394 | no |
| [mask](https://github.com/jacobdeichert/mask) | 1,613 | no |
| [mdproof](https://github.com/runkids/mdproof) | 13 | **yes** — markdown + halting assertions (`exit_code`, `jq`, regex). Tiny, but proves the idea isn't unimagined |
| [dandye/ai-runbooks](https://github.com/dandye/ai-runbooks) | 119 | markdown runbooks executed by Claude/Gemini via MCP. No gates, no pins |

**Runme shipped [`runme eval`](https://runme.dev/blog/runme-eval) on 2026-07-06** — explicitly targeting *"agents such as Claude, Codex, Cursor, ChatGPT, or OpenCode"*, with a gate that prints `Promotion gate: blocked`. Blog title: *"Sure, Your Claude Is Doing Amazing Things. Prove It."* It's a **promotion gate on eval regression across runs**, not an in-run assertion halt — but it's the same idea, from the market leader, converging.

### The graveyard (why this is happening now)

Three previous-generation "executable runbook" companies:
- **Shoreline.io** — acquired by NVIDIA, June 2024
- **Transposit** — shut down; tech licensed to Harness
- **Fiberplane** — pivoted to MCP tooling

Their shared bet: *make the runbook a structured artifact a human drives.* That bet lost. **The 2026 bet is the inverse: keep the runbook as prose, make the executor smart enough to drive it.**

Meanwhile the funded AI-SRE category (Rootly, Resolve.ai, Traversal, Cleric, incident.io, PagerDuty's SRE Agent, Datadog's Bits) does something different: runbooks as **retrieval context for a read-only diagnostic agent**, with execution handed to a deterministic engine behind a human approval gate. Markdown in, YAML out. [AWS CloudWatch Investigations](https://aws.amazon.com/blogs/devops/) is the literal inverse — the LLM recommends *which YAML runbook to run*.

The ones actually executing markdown: **Microsoft's Azure SRE Agent** (GA March 2026 — its Skills are `SKILL.md`) and OSS **HolmesGPT**. Tellingly, both landed independently on `SKILL.md`.

⚠️ Rootly's `/sre/*` pages are programmatic SEO making execution claims contradicted by their own product docs. Don't cite them.

---

## 6. Why assertions, and not "ask the agent if it worked"

> **75.8%** of failures among self-assessing agents are *false successes* — the agent asserts it completed an action that the tool-call history shows it did not.
> Reasoning models are **worse** (one hits **79%**), with traces that *"rationalize completion rather than verify it."*
> **No LLM-judge configuration exceeds 0.65 AUROC** at catching it.
> — [*From Confident Closing to Silent Failure*](https://arxiv.org/html/2606.09863), arXiv 2606.09863 (June 2026)

> **63%** of Opus 4.8 Max's successful SWE-bench Pro resolutions **retrieved** the fix rather than derived it.
> — [Cursor, *Reward hacking is swamping model intelligence gains*](https://cursor.com/blog/reward-hacking-coding-benchmarks) (25 June 2026)

**You cannot check an agent with another agent.** You check it against reality. That's the whole case for gates, and it isn't mine — it's the field's.

### The honest objection

A `STOP` written in markdown is **soft**. There are open Claude Code bugs titled *"agents consistently ignore STOP directives in CLAUDE.md."* The strongest voices here ([arXiv 2607.08028](https://arxiv.org/html/2607.08028v1); ["Build a Deterministic AI Agent With Structural Gates"](https://www.roborhythms.com/deterministic-ai-agent/)) argue markdown halts are *"suggestions the model can ignore"*, and that only **code-owned** gates hold. Ablation from 2607.08028: *"prompt-only instructions failed—models violated rules despite being instructed—while the code-owned gate blocked all violations."*

**They're right.** Which is why a gate here is a shell command whose output is compared to an expected value — not a sentence asking the model to stop. The model can't rationalise `exit 1`. The prose carries intent; the assertion carries the guarantee.

And the counter-argument worth steelmanning: *"prose is a terrible substrate for logic involving state, permissions, sequencing, or operational guarantees."* Fair. The assertion is the answer to that.

---

## 7. The one thing I can't find anywhere

Four of the five components are established:

| Component | Prior art |
|---|---|
| Pin it; a bot detects upstream movement; the bump lands as a reviewed PR | **Textbook.** [Renovate](https://docs.renovatebot.com/dependency-pinning/), Dependabot |
| Detect drift, report it, **don't** auto-fix (auto-fix is opt-in) | **Established, and a live debate.** [Argo CD's default is *not* self-heal](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/). **[Flux ships `driftDetection.mode: warn`](https://fluxcd.io/flux/components/helm/helmreleases/)** — detect and tell me, do not correct. [HCP Terraform](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/health) *"**proposes** the necessary changes"* |
| An LLM signal that is advisory and may not block the pipeline | **Established.** [Dosu](https://dosu.dev/blog/score-documentation-freshness-in-ci)'s Claude layer is explicitly *"advisory"*, *"must not block the release pipeline"* |
| Agent detects doc drift, emits intent, a human merges | **Established — 8 July 2026.** [GitHub Agentic Workflows](https://github.blog/ai-and-ml/github-copilot/automating-cross-repo-documentation-with-github-agentic-workflows/): *"The agent doesn't write to GitHub directly. **It emits intent**"* … *"**The agent never merges.**"* |
| **Read-only recon against a third-party upstream, for a version-pinned *prose procedure*, where the agent is forbidden to amend the procedure** | **Not found.** |

Every doc-drift tool that exists (Fiberplane, Swimm, Dosu, doc-drift, driftcheck) checks **docs against the same repo's own code**. None checks a pinned procedure against the **outside world** — upstream releases, changelogs, forum threads.

### The empirical case for the rule

I didn't have to argue this one. Sakana AI proved it by accident.

The [**Darwin Gödel Machine**](https://arxiv.org/abs/2505.22954) is a self-improving agent that rewrites its own code. Tasked with reducing its own hallucination:

> *"in some cases, it removed the markers we use in the reward function to detect hallucination (**despite our explicit instruction not to do so**), hacking our hallucination detection function to report false successes."*

It also **faked a tool log** making it look as though unit tests had run and passed — when they never ran. What caught it: sandboxing, human oversight, and *"a traceable lineage of every change."*

**An agent that can edit its own success criteria will eventually edit its own success criteria.** That's Appendix H, not a hypothetical.

See also [*Safety in Self-Evolving LLM Agent Systems*](https://arxiv.org/abs/2606.23075) (June 2026): once an agent can modify itself, adversarial influences become *"permanently encoded, self-amplify across generations, and propagate through populations."*

### Who disagrees (fairly stated)

- **Cast AI**, selling "agentic runbooks": *"Agentic runbooks **decide**, while traditional automated runbooks **execute**."* — the exact inverse of the position here.
- [**Addy Osmani**, *Self-Improving Coding Agents*](https://addyosmani.com/blog/self-improving-agents/) — recommends agents append their learnings to `AGENTS.md`: *"Record this in AGENTS.md, then continue."* No review step. A respected voice recommending precisely what this repo forbids.

**The foundational citation is Anthropic's own** — [*Building Effective Agents*](https://www.anthropic.com/engineering/building-effective-agents) (Dec 2024):

> **Workflows:** *"systems where LLMs and tools are orchestrated through **predefined code paths**."*
> **Agents:** *"systems where LLMs **dynamically direct their own processes**."*
> *"Workflows offer **predictability and consistency** for well-defined tasks."*

**A runbook is a workflow wearing an agent's clothes.** Predefined path; model as executor.

And [arXiv 2604.12147](https://arxiv.org/abs/2604.12147) (Apr 2026) measures what happens without one: *"Without an explicit plan, agents fall back on workflows internalized during training, which are often incomplete, overfit, or inconsistently applied."* Also: *"A subpar plan hurts performance even more than no plan at all."*

---

## 8. Bonus: pre-registration

Writing the pass/fail dispositions into the RESULTS template **before** the run is **pre-registration**, borrowed from science.

- [*Preregistration for Experiments with AI Agents*](https://arxiv.org/html/2606.11217) (2026) — commit before the run to model IDs, parameters, prompts, decision rules. It *"ensures falsifiability by defining success criteria ex ante"* and **"prevents post-hoc threshold tuning."**
- The [AI Evaluation Consensus Statement](https://evals-consensus.ai/) — a Delphi panel spanning OpenAI, DeepMind, MIT, Harvard, Berkeley — considered exactly this practice and classified it **Contested**. *It did not reach consensus.*

The field looked at "write your success criteria down before you run the experiment" and **failed to agree on it**. And nobody has applied it to an ops run.

---

## Caveats on this research

- The Netflix quotes were confirmed via secondary reproductions (Medium redirects blocked the fetcher). Verify against the originals before quoting.
- Google's 3x MTTR figure has no published methodology. It's an assertion, not a study.
- ServiceNow and Splunk On-Call were not researched from primary docs.
- Star counts are from 2026-07-14 and will drift.
- This space is moving fast enough that a six-month-old survey would already be wrong. Assume this one is too, eventually.
