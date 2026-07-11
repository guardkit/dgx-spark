#!/usr/bin/env python3
"""CR-0: one headless ComfyUI render through a SC_*-slotted workflow graph.

Injects prompt/seed/size(/model) by SC_* node title, submits via POST /prompt,
polls /history/<id>, downloads the image, and gates on exact output size.
Writes a JSON receipt (timings, params, sha256) beside the image. Stdlib only.

Injection is loud, never silent: every target field must PRE-EXIST in the
node's inputs (ComfyUI ignores unknown input keys, which would otherwise
render a PASS-looking image using the graph's baked-in defaults while the
receipt lied about seed/prompt).

Exit 0 = PASS (image at requested size). Nonzero = a gate failed; the error
is printed, including ComfyUI node_errors when the graph is rejected.
"""
import argparse
import hashlib
import json
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def find(graph: dict, title: str):
    for nid, node in graph.items():
        if node.get("_meta", {}).get("title") == title:
            return nid, node
    return None, None


def inject(node: dict, title: str, field: str, value) -> bool:
    """Set inputs[field] only if the field already exists — loud otherwise."""
    if field not in node["inputs"]:
        print(f"FAIL: {title} node ({node['class_type']}) has no input "
              f"'{field}' — its inputs are {sorted(node['inputs'])}. "
              f"ComfyUI would silently ignore the injection; fix the slot "
              f"(re-run cr0_slot_graph.py or set _meta.*_field).")
        return False
    node["inputs"][field] = value
    return True


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"FAIL: POST {url} -> HTTP {e.code}\n{body[:2000]}")
        sys.exit(1)


def png_size(data: bytes):
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workflow", type=Path, help="SC_*-slotted workflow_api JSON")
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--model", default=None,
                    help="override SC_CKPT model filename (ladder tier)")
    ap.add_argument("--steps", type=int, default=None,
                    help="override SC_STEPS (the reduced-steps draft fallback)")
    ap.add_argument("--timeout", type=int, default=900, help="poll cap, seconds")
    ap.add_argument("-o", "--out", type=Path, required=True, help="output PNG")
    args = ap.parse_args()

    graph = json.loads(args.workflow.read_text())

    _, prompt_node = find(graph, "SC_PROMPT")
    if prompt_node is None:
        print("FAIL: no SC_PROMPT slot — run cr0_slot_graph.py first")
        return 1
    text_field = prompt_node.get("_meta", {}).get("text_field", "text")
    if not inject(prompt_node, "SC_PROMPT", text_field, args.prompt):
        return 1

    _, neg = find(graph, "SC_NEGATIVE")
    if args.negative is not None:
        if neg is None:
            print("FAIL: --negative given but the graph has no SC_NEGATIVE slot")
            return 1
        if not inject(neg, "SC_NEGATIVE",
                      neg.get("_meta", {}).get("text_field", "text"),
                      args.negative):
            return 1

    _, seed_node = find(graph, "SC_SEED")
    if seed_node is None:
        print("FAIL: no SC_SEED slot")
        return 1
    seed_field = seed_node.get("_meta", {}).get("seed_field", "seed")
    if not inject(seed_node, "SC_SEED", seed_field, args.seed):
        return 1

    _, size_node = find(graph, "SC_SIZE")
    if size_node is None:
        print("FAIL: no SC_SIZE slot")
        return 1
    if not (inject(size_node, "SC_SIZE", "width", args.width) and
            inject(size_node, "SC_SIZE", "height", args.height)):
        return 1

    _, msf = find(graph, "SC_SIZE_MSF")
    if msf is not None:
        # ModelSamplingFlux must track the latent size or the flux shift
        # schedule silently diverges from the requested resolution.
        if not (inject(msf, "SC_SIZE_MSF", "width", args.width) and
                inject(msf, "SC_SIZE_MSF", "height", args.height)):
            return 1

    if args.steps is not None:
        _, steps_node = find(graph, "SC_STEPS")
        if steps_node is None:
            print("FAIL: --steps given but the graph has no SC_STEPS slot")
            return 1
        if not inject(steps_node, "SC_STEPS", "steps", args.steps):
            return 1

    if args.model:
        _, ckpt = find(graph, "SC_CKPT")
        if ckpt is None:
            print("FAIL: --model given but no SC_CKPT slot")
            return 1
        if "unet_name" in ckpt["inputs"]:
            field = "unet_name"
        elif "ckpt_name" in ckpt["inputs"]:
            field = "ckpt_name"
        else:
            print(f"FAIL: SC_CKPT node ({ckpt['class_type']}) has neither "
                  f"unet_name nor ckpt_name — inputs are {sorted(ckpt['inputs'])}")
            return 1
        ckpt["inputs"][field] = args.model

    t0 = time.monotonic()
    sub = post_json(f"{args.server}/prompt", {"prompt": graph, "client_id": "cr0"})
    pid = sub.get("prompt_id")
    if not pid:
        print(f"FAIL: no prompt_id in response: {json.dumps(sub)[:500]}")
        return 1
    print(f"submitted prompt_id={pid}")

    images, poll_errors = None, 0
    while time.monotonic() - t0 < args.timeout:
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"{args.server}/history/{pid}",
                                        timeout=30) as r:
                hist = json.loads(r.read()).get(pid)
            poll_errors = 0
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            poll_errors += 1
            print(f"  poll error ({poll_errors}/5): {e}")
            if poll_errors >= 5:
                print("FAIL: ComfyUI unreachable for 5 consecutive polls")
                return 1
            continue
        if not hist:
            continue
        status = hist.get("status", {})
        if status.get("status_str") == "error":
            print(f"FAIL: execution error: {json.dumps(status)[:2000]}")
            return 1
        for node_out in hist.get("outputs", {}).values():
            if node_out.get("images"):
                images = node_out["images"]
                break
        if images:
            break
        if status.get("completed") is True:
            print(f"FAIL: history reports completed with no images: "
                  f"{json.dumps(hist)[:1000]}")
            return 1
    if not images:
        print(f"FAIL: no image within {args.timeout}s (render timeout gate)")
        return 1

    seconds = round(time.monotonic() - t0, 1)
    img = images[0]
    q = urllib.parse.urlencode({"filename": img["filename"],
                                "subfolder": img.get("subfolder", ""),
                                "type": img.get("type", "output")})
    try:
        with urllib.request.urlopen(f"{args.server}/view?{q}", timeout=60) as r:
            data = r.read()
    except (urllib.error.URLError, OSError) as e:
        print(f"FAIL: image download (/view?{q}) failed: {e}")
        return 1

    size = png_size(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    if size != (args.width, args.height):
        print(f"FAIL: got {size}, wanted {(args.width, args.height)} "
              f"(saved to {args.out} for inspection)")
        return 1

    receipt = {
        "workflow": str(args.workflow), "model_override": args.model,
        "steps_override": args.steps,
        "seed": args.seed, "seed_field": seed_field, "text_field": text_field,
        "size": [args.width, args.height], "seconds": seconds,
        "prompt_id": pid, "sha256": hashlib.sha256(data).hexdigest(),
        "out": str(args.out),
    }
    args.out.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2))
    print(f"PASS: {args.out} {size[0]}x{size[1]} in {seconds}s "
          f"(receipt: {args.out.with_suffix('.receipt.json')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
