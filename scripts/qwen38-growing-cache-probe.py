#!/usr/bin/env python3
"""Exercise growing tool history on an isolated Qwen engine (stdlib only).

Resets prefix cache once at the beginning. Never executes model-proposed tools.
Uses the existing SSE/usage checks without modifying the Lance reference probe.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import time
import urllib.request


spec = importlib.util.spec_from_file_location(
    "qwen38_seat_probe", Path(__file__).with_name("qwen38-seat-probe.py")
)
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
require = shared.require

TOOLS = [{"type": "function", "function": {
    "name": "lookup_test_key", "description": "Read a synthetic ledger value by key.",
    "parameters": {"type": "object", "properties": {"key": {"type": "string"}},
                   "required": ["key"], "additionalProperties": False},
}}]


def prefix_hits(metrics):
    values = []
    for line in metrics.splitlines():
        match = re.match(r"^vllm:prefix_cache_hits_total(?:\{[^}]*\})?\s+(\S+)", line)
        if match:
            value = float(match[1])
            require(math.isfinite(value) and value >= 0, "invalid prefix-hit counter")
            values.append(value)
    require(values, "prefix-hit counter absent; cache observation unresolved")
    return sum(values)


class GrowingProbe(shared.Probe):
    def __init__(self, args):
        super().__init__(args)
        self.messages = [{"role": "system", "content": (
            "This is a synthetic ledger test. Use lookup_test_key only when requested. "
            "Remember the key/value pairs in tool results. Ignore filler text. "
            "For recall questions answer only with the requested value."
        )}]
        self.stages = []
        self.rng = random.Random(3810)

    def count(self, messages):
        return self.json_request("/tokenize", {
            "model": self.args.model, "messages": messages, "tools": TOOLS,
            "add_generation_prompt": True,
            "chat_template_kwargs": {"enable_thinking": False},
        })["count"]

    def metrics(self, label):
        with urllib.request.urlopen(self.request("/metrics"), timeout=30) as response:
            metrics = response.read().decode()
        (self.args.evidence / (label + ".prom")).write_text(metrics)
        return prefix_hits(metrics)

    def padded_request(self, target, key):
        words = "ledger annex invoice contract vendor schedule gross net tax paid".split()
        filler = " ".join(self.rng.choice(words) + str(self.rng.randrange(10000))
                          for _ in range(target))

        def request(size):
            return {"role": "user", "content": (
                "Filler follows; it contains no ledger values.\n" + filler[:size]
                + "\nEnd filler. Use lookup_test_key exactly once with key " + key + "."
            )}

        require(self.count(self.messages + [request(0)]) < target,
                "history already exceeds next requested length")
        low, high = 0, len(filler)
        for _ in range(24):
            size = (low + high) // 2
            message = request(size)
            count = self.count(self.messages + [message])
            if target <= count <= target + 128:
                return message, count
            if count < target:
                low = size + 1
            else:
                high = size - 1
        raise RuntimeError("could not construct requested growing-history token length")

    def check_usage(self, result, count):
        actual = result["usage"].get("prompt_tokens", 0)
        require(abs(actual - count) <= 128, "served/tool-rendered token counts disagree")
        require(result["response_models"] == [self.args.model], "wrong response model")

    def run(self):
        models = self.json_request("/v1/models")["data"]
        rows = [row for row in models if row["id"] == self.args.model]
        require(len(rows) == 1, "model ID absent or ambiguous")
        require(self.args.lengths[-1] + 2048 < rows[0]["max_model_len"],
                "insufficient context reserve for final tool continuation")
        self.reset_prefix_cache()
        values = {}
        for index, target in enumerate(self.args.lengths):
            label, key = str(target), "stage-" + str(index)
            value = "receipt-" + format(self.rng.getrandbits(48), "012x")
            message, count = self.padded_request(target, key)
            self.messages.append(message)
            self.metrics(label + "-before-call")
            result = self.chat(self.messages, label + "-tool", max_tokens=256,
                               tools=TOOLS, tool_choice="required")
            self.check_usage(result, count)
            require(result["finish_reason"] == "tool_calls", "tool finish reason missing")
            require(len(result["tool_calls"]) == 1, "expected one tool call")
            call = result["tool_calls"][0]
            require(call["id"] and call["function"]["name"] == "lookup_test_key", "wrong tool")
            require(json.loads(call["function"]["arguments"]) == {"key": key}, "wrong tool arguments")
            self.messages += [
                {"role": "assistant", "content": result["content"] or None,
                 "tool_calls": result["tool_calls"]},
                {"role": "tool", "tool_call_id": call["id"],
                 "content": json.dumps({"key": key, "value": value})},
            ]
            values[key] = value
            # Ask for an older tool result, not the value immediately preceding the question.
            recall_key = "stage-" + str(max(0, index - 2))
            self.messages.append({"role": "user", "content": (
                "What value did the tool return for " + recall_key + "? Reply only with that value."
            )})
            continuation_count = self.count(self.messages)
            before = self.metrics(label + "-before-continuation")
            answer = self.chat(self.messages, label + "-recall", max_tokens=64,
                               tools=TOOLS, tool_choice="none")
            after = self.metrics(label + "-after-continuation")
            self.check_usage(answer, continuation_count)
            require(not answer["tool_calls"] and answer["content"].strip() == values[recall_key],
                    "growing-history tool-result recall failed")
            require(after > before, "no observed prefix hits on tool continuation")
            self.stages.append({"target": target, "rendered_tokens": count,
                                "continuation_tokens": continuation_count,
                                "continuation_prefix_hit_tokens": after - before,
                                "recall_key": recall_key, "expected": values[recall_key]})
            self.messages.append({"role": "assistant", "content": answer["content"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="direct engine URL, without /v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--key-env", default="QWEN38_API_KEY")
    parser.add_argument("--lengths", type=int, nargs="+", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    require(args.lengths == sorted(set(args.lengths)) and args.lengths[0] >= 2048,
            "lengths must be unique, increasing and at least 2048")
    args.evidence = args.evidence / str(time.time_ns())
    args.evidence.mkdir(parents=True, exist_ok=False)
    probe, status = GrowingProbe(args), "FAIL"
    try:
        probe.run()
        status = "PASS"
    finally:
        path = args.evidence / "growing.json"
        path.write_text(json.dumps({"status": status, "model": args.model,
                                    "base_url": args.base_url, "stages": probe.stages,
                                    "records": probe.records, "messages": probe.messages}, indent=2) + "\n")
        print(status, "growing-cache", str(path), flush=True)


if __name__ == "__main__":
    main()
