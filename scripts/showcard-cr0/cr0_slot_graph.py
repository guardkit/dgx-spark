#!/usr/bin/env python3
"""CR-0: stamp SC_* parameter slots onto a ComfyUI workflow_api JSON.

Takes a workflow exported in **API format** (flat {node_id: {class_type, inputs,
_meta}} — NOT the UI-canvas format with "nodes"/"links" arrays; base_flux.json
as shipped by the playbook is UI-canvas, so export first) and auto-detects the
parameter nodes, stamping reserved titles so downstream tooling injects by
title, never by node id:

  SC_PROMPT    positive text     (CLIPTextEncode | CLIPTextEncodeFlux)
  SC_NEGATIVE  negative text     (ditto, when present)
  SC_SEED      sampler seed      (KSampler.seed | KSamplerAdvanced/RandomNoise.noise_seed)
  SC_SIZE      latent size       (EmptyLatentImage | EmptySD3LatentImage)
  SC_SIZE_MSF  companion size    (ModelSamplingFlux width/height — must track SC_SIZE
                                  or the flux shift schedule silently diverges)
  SC_STEPS     sampler steps     (BasicScheduler | KSampler | KSamplerAdvanced)
  SC_CKPT      model loader      (UNETLoader | CheckpointLoaderSimple)

Positive/negative are resolved by TOPOLOGY: nodes with "positive"/"negative"
link inputs first (KSampler family), then "conditioning" links (BasicGuider /
FluxGuidance — the SamplerCustomAdvanced family the playbook's FLUX graph
uses), following pass-through nodes up to 3 hops. The longest-text heuristic
is the last resort, with a printed warning. Field names that differ per class
(noise_seed, t5xxl) are recorded in _meta (*_field) so cr0_render.py injects
the right key — ComfyUI ignores extra _meta keys.

Prints the proposed map for human ratification; the slotted graph is a
committed artifact, never regenerated silently. Exits 1 if any required slot
(SC_PROMPT, SC_SEED, SC_SIZE) cannot be found.
"""
import argparse
import json
import sys
from pathlib import Path

REQUIRED = ("SC_PROMPT", "SC_SEED", "SC_SIZE")
ENCODE_CLASSES = {"CLIPTextEncode": "text", "CLIPTextEncodeFlux": "t5xxl"}


def is_api_format(graph: dict) -> bool:
    return all(isinstance(v, dict) and "class_type" in v for v in graph.values())


def is_link(v) -> bool:
    return isinstance(v, list) and len(v) == 2 and isinstance(v[0], str)


def resolve_to_encode(graph: dict, node_id: str, hops: int = 3):
    """Follow pass-through nodes (FluxGuidance etc.) until an encode node."""
    for _ in range(hops):
        node = graph.get(node_id)
        if node is None:
            return None
        if node["class_type"] in ENCODE_CLASSES:
            return node_id
        links = [v for v in node["inputs"].values() if is_link(v)]
        if not links:
            return None
        node_id = links[0][0]
    return None


def detect(graph: dict) -> dict:
    slots: dict[str, str] = {}
    by_class: dict[str, list[str]] = {}
    for nid, node in graph.items():
        by_class.setdefault(node["class_type"], []).append(nid)

    encodes = [n for cls in ENCODE_CLASSES for n in by_class.get(cls, [])]

    # Topology pass 1: explicit positive/negative links (KSampler family).
    for node in graph.values():
        for role, slot in (("positive", "SC_PROMPT"), ("negative", "SC_NEGATIVE")):
            link = node["inputs"].get(role)
            if slot not in slots and is_link(link):
                enc = resolve_to_encode(graph, link[0])
                if enc is not None:
                    slots[slot] = enc

    # Topology pass 2: "conditioning" links are positive-role (BasicGuider /
    # FluxGuidance — the SamplerCustomAdvanced family in the playbook graph).
    if "SC_PROMPT" not in slots:
        for node in graph.values():
            link = node["inputs"].get("conditioning")
            if is_link(link):
                enc = resolve_to_encode(graph, link[0])
                if enc is not None:
                    slots["SC_PROMPT"] = enc
                    break

    # Last resort: longest baked-in text. Warn loudly.
    if "SC_PROMPT" not in slots and encodes:
        print("WARN: prompt not resolvable by topology — falling back to the "
              "longest-default-text heuristic; VERIFY the map before ratifying.")
        ranked = sorted(encodes, key=lambda n: len(str(
            graph[n]["inputs"].get(ENCODE_CLASSES[graph[n]["class_type"]], ""))),
            reverse=True)
        slots["SC_PROMPT"] = ranked[0]
        if len(ranked) > 1 and "SC_NEGATIVE" not in slots:
            slots["SC_NEGATIVE"] = ranked[1]

    for cls, field in (("KSampler", "seed"), ("KSamplerAdvanced", "noise_seed"),
                       ("RandomNoise", "noise_seed")):
        for nid in by_class.get(cls, []):
            if field in graph[nid]["inputs"]:
                slots["SC_SEED"] = nid
                slots["_seed_field"] = field
                break
        if "SC_SEED" in slots:
            break

    for cls in ("EmptyLatentImage", "EmptySD3LatentImage"):
        if by_class.get(cls):
            slots["SC_SIZE"] = by_class[cls][0]
            break

    if by_class.get("ModelSamplingFlux"):
        slots["SC_SIZE_MSF"] = by_class["ModelSamplingFlux"][0]

    for cls in ("BasicScheduler", "KSampler", "KSamplerAdvanced"):
        for nid in by_class.get(cls, []):
            if "steps" in graph[nid]["inputs"]:
                slots["SC_STEPS"] = nid
                break
        if "SC_STEPS" in slots:
            break

    for cls in ("UNETLoader", "CheckpointLoaderSimple"):
        if by_class.get(cls):
            slots["SC_CKPT"] = by_class[cls][0]
            break

    return slots


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workflow", type=Path, help="workflow_api-format JSON in")
    ap.add_argument("-o", "--out", type=Path, required=True, help="slotted JSON out")
    args = ap.parse_args()

    graph = json.loads(args.workflow.read_text())
    if not is_api_format(graph):
        print("FAIL: not API format. base_flux.json ships in UI-canvas format — "
              "load it in the ComfyUI UI once, enable dev mode, use "
              "'Save (API format)', and slot THAT export.")
        return 1

    slots = detect(graph)
    seed_field = slots.pop("_seed_field", "seed")

    print(f"{'slot':<12} {'node':<6} {'class_type':<22} inject-field")
    for title, nid in sorted(slots.items()):
        node = graph[nid]
        meta = node.setdefault("_meta", {})
        meta["title"] = title
        field = ""
        if title in ("SC_PROMPT", "SC_NEGATIVE"):
            field = ENCODE_CLASSES[node["class_type"]]
            meta["text_field"] = field
            if field != "text":
                field += "  (clip_l stays at its export default)"
        elif title == "SC_SEED":
            field = seed_field
            meta["seed_field"] = seed_field
        elif title in ("SC_SIZE", "SC_SIZE_MSF"):
            field = "width/height"
        elif title == "SC_STEPS":
            field = "steps"
        print(f"{title:<12} {nid:<6} {node['class_type']:<22} {field}")

    if "SC_SIZE_MSF" not in slots and "ModelSamplingFlux" in \
            {n["class_type"] for n in graph.values()}:
        print("WARN: ModelSamplingFlux present but not slotted — its "
              "width/height would stay at export defaults.")
    if "SC_STEPS" not in slots:
        print("WARN: no SC_STEPS slot found — the reduced-steps draft fallback "
              "(--steps) will not be available for this graph.")

    missing = [s for s in REQUIRED if s not in slots]
    if missing:
        print(f"FAIL: could not detect required slot(s): {', '.join(missing)}. "
              "If you title a node manually, ALSO set _meta.text_field / "
              "_meta.seed_field to the node's real input key — cr0_render.py "
              "gates on the field existing, it cannot guess it.")
        return 1

    args.out.write_text(json.dumps(graph, indent=2))
    print(f"PASS: slotted graph written to {args.out} — ratify the map above "
          "(one draft render proves it), then commit the file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
