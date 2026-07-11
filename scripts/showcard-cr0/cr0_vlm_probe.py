#!/usr/bin/env python3
"""CR-0: the two load-bearing VLM probes against llama-swap.

Probe 1 — guided decoding on the VISION endpoint: send each image with
`response_format: json_schema` (never proven on a vision model in this estate;
the reference pipeline used it on the text extractor only). PASS = every
response parses against the schema. On failure, rerun with --no-schema to
demonstrate the fallback wire (prompt-JSON + parse-retry), and record which
wire showcard's evaluator must use.

Probe 2 — score discrimination: the image set includes deliberately-degraded
variants (from cr0_overlay.py --variants). PASS = the degraded variants score
LOWER on headline_legibility than the good composite by >= --spread. A clump
(everything ~0.7) is a valid, recorded outcome — it means Tier-1 gates + the
human pick carry showcard's sessions, and the finding is filed, not hidden.

Decoding pinned t=0/seed for reproducibility; max_tokens capped (the
max-tokens-ceiling guard ported from the reference pipeline — an uncapped
vision call has looped for 164s before). Stdlib only. Writes probe.json.
"""
import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CRITERIA = ["headline_legibility", "focal_clarity", "contrast"]

SCHEMA = {
    "name": "thumb_scores",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {c: {"type": "number", "minimum": 0, "maximum": 1}
                       for c in CRITERIA},
        "required": CRITERIA,
        "additionalProperties": False,
    },
}

PROMPT = (
    "You are scoring a YouTube thumbnail candidate. Answer by perception, not "
    "opinion. headline_legibility: could you read the headline text if this "
    "image were 168 pixels wide? (transcribe it mentally first; 0 = unreadable, "
    "1 = effortless). focal_clarity: how many distinct focal points compete? "
    "(1 clear subject = high, cluttered = low). contrast: does the text "
    "separate cleanly from its backdrop? Respond with JSON only: "
    '{"headline_legibility": x, "focal_clarity": x, "contrast": x}, each 0..1.'
)


def score(endpoint: str, model: str, image: Path, use_schema: bool,
          seed: int, max_tokens: int):
    b64 = base64.b64encode(image.read_bytes()).decode()
    body = {
        "model": model,
        "temperature": 0.0,
        "seed": seed,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    }
    if use_schema:
        body["response_format"] = {"type": "json_schema", "json_schema": SCHEMA}
    req = urllib.request.Request(
        f"{endpoint}/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.loads(r.read())["choices"][0]["message"]["content"] or ""
    m = re.search(r"\{.*\}", text, re.S)  # tolerate prose around JSON in fallback mode
    parsed = json.loads(m.group(0) if m else text)
    if set(CRITERIA) - set(parsed):
        raise ValueError(f"missing criteria in: {text[:300]}")
    out = {c: float(parsed[c]) for c in CRITERIA}
    bad = {c: v for c, v in out.items() if not 0.0 <= v <= 1.0}
    if bad:
        # Structured-output backends (llama.cpp grammars, vLLM xgrammar/
        # outlines — the fleet seat is vLLM) don't reliably enforce numeric
        # min/max — gate client-side.
        raise ValueError(f"scores out of 0..1 range: {bad}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("images", nargs="+", type=Path,
                    help="good composite first, then degraded variants")
    ap.add_argument("--endpoint", default="http://127.0.0.1:9000/v1")
    ap.add_argument("--model", default="granite-vision-4-1-4b")
    ap.add_argument("--no-schema", action="store_true",
                    help="fallback wire: no response_format, parse from text")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--spread", type=float, default=0.15,
                    help="required good-vs-degraded gap on headline_legibility")
    ap.add_argument("-o", "--out", type=Path, default=Path("probe.json"))
    args = ap.parse_args()

    results, wire = {}, ("prompt-json" if args.no_schema else "json_schema")
    for img in args.images:
        try:
            results[img.name] = score(args.endpoint, args.model, img,
                                       not args.no_schema, args.seed,
                                       args.max_tokens)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            # OSError covers HTTPError, URLError (server down/refused) and
            # socket timeouts — all must land on the FAIL line, not a traceback.
            detail = e.read().decode(errors="replace")[:500] \
                if isinstance(e, urllib.error.HTTPError) else str(e)[:500]
            print(f"FAIL (probe 1, wire={wire}): {img.name}: {detail}")
            if not args.no_schema:
                print("  -> rerun with --no-schema to demonstrate the fallback "
                      "wire; record the outcome either way.")
            return 1

    print(f"PASS (probe 1): all {len(results)} responses parsed via {wire}\n")
    header = f"{'image':<34}" + "".join(f"{c:>22}" for c in CRITERIA)
    print(header)
    for name, s in results.items():
        print(f"{name:<34}" + "".join(f"{s[c]:>22.2f}" for c in CRITERIA))

    good = results[args.images[0].name]["headline_legibility"]
    degraded = [results[i.name]["headline_legibility"] for i in args.images[1:]]
    spread_ok = bool(degraded) and all(good - d >= args.spread for d in degraded)
    verdict = ("DISCRIMINATES" if spread_ok else
               "CLUMPED" if degraded else "N/A (no variants supplied)")
    print(f"\nprobe 2 (score discrimination): {verdict} "
          f"(good={good:.2f}, degraded={[f'{d:.2f}' for d in degraded]}, "
          f"required gap >= {args.spread})")
    if not spread_ok and degraded:
        print("  Recorded as a finding, not a failure: Tier-1 gates + the human "
              "pick carry showcard sessions if the VLM clumps.")

    args.out.write_text(json.dumps(
        {"wire": wire, "model": args.model, "seed": args.seed,
         "max_tokens": args.max_tokens, "scores": results,
         "discrimination": verdict}, indent=2))
    print(f"receipt: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
