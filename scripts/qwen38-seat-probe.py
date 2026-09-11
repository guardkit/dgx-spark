#!/usr/bin/env python3
"""Gates for RUNBOOK-qwen38-flash-next-seat.md; Python standard library only.

Sends synthetic requests, never executes model-proposed tools. Memory mode can
stop only the explicitly named container. No benchmarks are uploaded.
"""

import argparse
import json
import os
from pathlib import Path
import random
import re
import subprocess
import time
import urllib.request


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_repetition(content):
    # Ordinary Python section comments are not a generation loop. Keep this
    # exception bounded and specific; long runs in prose/code still fail.
    screened = re.sub(r"(?m)^[ \t]*#[ \t]*(?:={64,120}|-{64,120})[ \t]*$", "", content)
    require(not re.search(r"(!{16,}|(.)\2{63,})", screened), "repetitive output")


class Probe:
    def __init__(self, args):
        self.args = args
        self.base = args.base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        key = os.environ.get(args.key_env)
        if key:
            self.headers["Authorization"] = "Bearer " + key
        self.records = []

    def request(self, path, body=None):
        return urllib.request.Request(
            self.base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers=self.headers,
        )

    def json_request(self, path, body=None):
        with urllib.request.urlopen(self.request(path, body), timeout=900) as response:
            return json.load(response)

    def reset_prefix_cache(self):
        with urllib.request.urlopen(self.request("/reset_prefix_cache", {}), timeout=30) as response:
            require(response.status == 200, "cache reset failed")
            body = response.read()
            if body.strip():
                require(json.loads(body).get("success") is True, "engine refused cache reset")

    def chat(self, messages, label, max_tokens=512, **extra):
        body = {
            "model": self.args.model, "messages": messages,
            "temperature": 0, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "stream": True, "stream_options": {"include_usage": True}, **extra,
        }
        start = time.monotonic()
        first = last = None
        content, reasoning, calls, usage, finish = "", "", {}, {}, None
        response_models = set()
        done = False
        with urllib.request.urlopen(self.request("/v1/chat/completions", body), timeout=900) as response:
            for raw in response:
                line = raw.decode().strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    done = True
                    break
                event = json.loads(data)
                require("error" not in event, "error in SSE stream")
                if event.get("model"):
                    response_models.add(event["model"])
                if event.get("usage"):
                    usage = event["usage"]
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    chunk = delta.get("content") or ""
                    thought = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    if chunk or thought or delta.get("tool_calls"):
                        now = time.monotonic()
                        first = now if first is None else first
                        last = now
                    content += chunk
                    reasoning += thought
                    for call in delta.get("tool_calls", []):
                        item = calls.setdefault(call["index"], {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                        if call.get("id"):
                            item["id"] = call["id"]
                        for field in ("name", "arguments"):
                            item["function"][field] += call.get("function", {}).get(field) or ""
                    finish = choice.get("finish_reason") or finish
        elapsed = time.monotonic() - start
        # Retain the actual response before assertions, including failed streams,
        # so a content heuristic cannot discard the evidence needed to diagnose it.
        self.args.evidence.mkdir(parents=True, exist_ok=True)
        raw = {"label": label, "elapsed_s": elapsed,
               "first_delta_s": first - start if first is not None else None,
               "last_delta_s": last - start if last is not None else None,
               "done": done, "finish_reason": finish, "usage": usage,
               "content": content, "reasoning": reasoning,
               "response_models": sorted(response_models),
               "tool_calls": [calls[k] for k in sorted(calls)]}
        (self.args.evidence / (label + "-raw-" + str(time.time_ns()) + ".json")).write_text(
            json.dumps(raw, indent=2) + "\n")
        require(done and first is not None and finish is not None, "incomplete/empty SSE response")
        require(not reasoning and "<think>" not in content, "thinking-off gate failed")
        require(usage.get("completion_tokens", 0) > 0, "missing native completion-token usage")
        require(not (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0), "nonzero reasoning usage")
        check_repetition(content)
        record = {
            "label": label, "ttft_s": first - start, "elapsed_s": elapsed,
            "decode_tok_s": (usage["completion_tokens"] - 1) / (last - first) if last > first else None,
            "e2e_tok_s": usage["completion_tokens"] / elapsed,
            "usage": usage, "finish_reason": finish, "content": content,
            "response_models": sorted(response_models),
            "tool_calls": [calls[k] for k in sorted(calls)],
        }
        self.records.append(record)
        print(json.dumps({k: v for k, v in record.items() if k not in ("content", "tool_calls")}), flush=True)
        return record

    def protocols(self):
        models = self.json_request("/v1/models")
        require(self.args.model in {m["id"] for m in models["data"]}, "model ID absent")
        tools = [{"type": "function", "function": {
            "name": "lookup_test_key", "description": "Read a synthetic test value by key.",
            "parameters": {"type": "object", "properties": {"key": {"type": "string"}},
                           "required": ["key"], "additionalProperties": False},
        }}]
        for name, choice in (("auto", "auto"), ("required", "required"),
                             ("named", {"type": "function", "function": {"name": "lookup_test_key"}})):
            messages = [{"role": "user", "content": "Use lookup_test_key with key gate-alpha. After its result, answer with only the value returned by the tool."}]
            result = self.chat(messages, "tool-" + name, tools=tools, tool_choice=choice)
            # vLLM's named-tool path deliberately returns "stop" even when it
            # streams a structured tool call. Auto/required still use "tool_calls".
            allowed_finish = {"stop", "tool_calls"} if name == "named" else {"tool_calls"}
            require(result["finish_reason"] in allowed_finish, "tool finish reason missing")
            require(len(result["tool_calls"]) == 1, "expected one tool call")
            call = result["tool_calls"][0]
            require(call["id"] and call["function"]["name"] == "lookup_test_key", "wrong tool name/id")
            require(json.loads(call["function"]["arguments"]) == {"key": "gate-alpha"}, "invalid tool arguments")
            messages += [{"role": "assistant", "content": result["content"] or None, "tool_calls": result["tool_calls"]},
                         {"role": "tool", "tool_call_id": call["id"], "content": '{"value":"cobalt-731"}'}]
            answer = self.chat(messages, "tool-result-" + name, tools=tools, tool_choice="none")
            require(answer["content"].strip() == "cobalt-731", "tool-result continuation incorrect")
        result = self.chat([{"role": "user", "content": 'Return only this JSON object, no fences: {"ok":true,"files":[],"count":3}'}], "json-without-grammar")
        require(json.loads(result["content"]) == {"ok": True, "files": [], "count": 3}, "JSON contract smoke failed")

    def cache(self):
        # /tokenize and /reset_prefix_cache are engine administration routes.
        # Run this mode directly against the isolated engine, before routing.
        rng = random.Random(3808)
        words = "ledger invoice payroll contract clause annex schedule amount date vendor total net gross tax due paid".split()
        target = self.args.prompt_tokens
        filler = " ".join(rng.choice(words) + str(rng.randrange(10000)) for _ in range(target))
        def messages(question):
            return [{"role": "user", "content": prefix + "\n" + question}]
        question = "What is alpha in the test record? Reply only with its value."
        # Keep the full source text: destructive proportional trimming can
        # undershoot, after which slicing cannot grow the prompt back.
        low, high = 0, len(filler)
        for _ in range(24):
            size = (low + high) // 2
            prefix = "Test record. alpha=cobalt-731.\n" + filler[:size] + "\nTest record. beta=amber-942."
            count = self.json_request("/tokenize", {"model": self.args.model, "messages": messages(question),
                                                      "add_generation_prompt": True,
                                                      "chat_template_kwargs": {"enable_thinking": False}})["count"]
            if target <= count <= target + 128:
                break
            if count < target:
                low = size + 1
            else:
                high = size - 1
        require(target <= count <= target + 128, "could not construct requested token length")
        self.reset_prefix_cache()
        cold = self.chat(messages(question), "cold-" + str(target), max_tokens=64)
        warm = self.chat(messages(question), "warm-" + str(target), max_tokens=64)
        for result in (cold, warm):
            actual = result["usage"].get("prompt_tokens", 0)
            require(actual >= target and abs(actual - count) <= 128, "served prompt length differs from tokenized request")
        require(cold["content"].strip() == warm["content"].strip() == "cobalt-731", "cold/warm answer mismatch")
        require(warm["ttft_s"] <= cold["ttft_s"] * self.args.warm_ratio, "no adequate prefix-cache speedup")
        changed = self.chat(messages("What is beta in the test record? Reply only with its value."), "changed-suffix", max_tokens=64)
        require(changed["content"].strip() == "amber-942", "cached state ignored changed suffix")
        clean = self.chat([{"role": "user", "content": "An unrelated record has alpha=jade-563. Reply only with this record's alpha value."}], "unrelated-prefix", max_tokens=64)
        require(clean["content"].strip() == "jade-563", "state leaked between requests")

    def decode(self):
        prompt = (
            "Write a complete Python module containing 100 independent string validation functions. "
            "Each function needs a descriptive docstring, implementation, and three assert examples. "
            "Cover identifiers, dates, paths, invoice codes, URLs, email addresses, and whitespace. "
            "Give the code directly. Do not abbreviate or replace functions with placeholders."
        )
        result = self.chat([{"role": "user", "content": prompt}], "code-decode", max_tokens=self.args.max_tokens)
        require(result["usage"]["completion_tokens"] >= 128, "generation too short to measure decode")
        require(result["decode_tok_s"] is not None and result["decode_tok_s"] >= self.args.decode_floor, "decode below diagnostic floor")
        require(result["elapsed_s"] >= self.args.min_seconds, "long-stream duration not exercised; gate inconclusive")


def memory(args):
    def sample():
        mem = {k: int(v.split()[0]) * 1024 for k, v in (line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())}
        vm = dict(line.split() for line in Path("/proc/vmstat").read_text().splitlines())
        return {"time": time.time(), "available_gib": mem["MemAvailable"] / 2**30,
                "used_gib": (mem["MemTotal"] - mem["MemAvailable"]) / 2**30,
                "swap_used": mem["SwapTotal"] - mem["SwapFree"],
                "pswpin": int(vm["pswpin"]), "pswpout": int(vm["pswpout"])}
    baseline = sample()
    with (args.evidence / "memory.jsonl").open("a") as output:
        while True:
            state = sample()
            output.write(json.dumps(state) + "\n")
            output.flush()
            if (state["available_gib"] < args.min_available_gib or state["used_gib"] > args.max_used_gib
                    or state["swap_used"] > baseline["swap_used"]
                    or state["pswpin"] > baseline["pswpin"] or state["pswpout"] > baseline["pswpout"]):
                (args.evidence / "memory.failed").write_text(json.dumps(state) + "\n")
                subprocess.run(["docker", "stop", "--time", "10", args.container], check=False, timeout=30)
                raise RuntimeError("memory envelope breached; seat stop requested")
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["protocols", "cache", "decode", "memory"])
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--key-env", default="QWEN38_API_KEY")
    parser.add_argument("--prompt-tokens", type=int, default=20000)
    parser.add_argument("--warm-ratio", type=float, default=0.5)
    parser.add_argument("--decode-floor", type=float, default=18)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--min-seconds", type=float, default=90)
    parser.add_argument("--container")
    parser.add_argument("--min-available-gib", type=float)
    parser.add_argument("--max-used-gib", type=float)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    if args.mode == "memory":
        require(args.container and args.min_available_gib and args.max_used_gib, "memory mode requires container and both limits")
        memory(args)
        return
    require(args.base_url and args.model, "API mode requires base URL (without /v1) and model")
    probe = Probe(args)
    status = "FAIL"
    try:
        getattr(probe, args.mode)()
        status = "PASS"
    finally:
        path = args.evidence / (args.mode + "-" + str(time.time_ns()) + ".json")
        path.write_text(json.dumps({"status": status, "model": args.model,
                                    "base_url": args.base_url, "records": probe.records}, indent=2) + "\n")
        print(status, args.mode, str(path), flush=True)


if __name__ == "__main__":
    main()
