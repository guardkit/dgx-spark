#!/usr/bin/env python3
"""showcard LT-0 — drive the likeness test matrix through ComfyUI.

Committable receipt: stdlib + PIL only; all paths + prompts come from a manifest
JSON (no image bytes in this file). Drives POST /prompt, polls /history, fetches
the rendered PNG via /view, and records per-render WALL TIME taken from the
/history status timestamps (execution_start -> execution_success), plus a
client-measured elapsed as a cross-check.

Reuses the proven SC_*-slot injection discipline from scripts/showcard-kr0:
each editable node carries a `_meta.title` (SC_PROMPT / SC_SEED / SC_SIZE /
SC_STEPS / SC_LORA / SC_SUBJECT_IMAGE); the driver finds the node by title and
sets an input ONLY if that field already exists (loud otherwise) so a silent
mis-injection can never pass.

Manifest shape:
  {
    "server": "http://127.0.0.1:8188",
    "renders_dir": "/abs/out",
    "renders": [
      {"name": "a-studio-s42",
       "graph": "/abs/lora_dev_plain.api.json",
       "prompt": "rw0man person, studio portrait ...",
       "seed": 42,
       "width": 1280, "height": 720, "steps": 48,
       "lora": "rw0man_lt0.safetensors", "lora_strength": 1.0,
       "subject": null},
      ...
    ]
  }

For a path-(b) render, set "subject" to an absolute image path: it is uploaded
via POST /upload/image and wired into the SC_SUBJECT_IMAGE (LoadImage) slot.

Each render writes <name>.png + <name>.receipt.json into renders_dir, and the
fully-resolved submitted graph to <name>.submitted.json. A matrix-level summary
is written to renders_dir/render_matrix_receipts.json.

Exit 0 = every render produced an image at the requested size. Nonzero = a
render failed a gate (size mismatch, execution error, or timeout).
"""
import argparse
import hashlib
import io
import json
import mimetypes
import struct
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid
from pathlib import Path


def find(graph, title):
    for nid, node in graph.items():
        if node.get("_meta", {}).get("title") == title:
            return nid, node
    return None, None


def inject(node, title, field, value):
    if field not in node["inputs"]:
        print(f"FAIL: {title} ({node['class_type']}) has no input '{field}'; "
              f"inputs are {sorted(node['inputs'])}")
        return False
    node["inputs"][field] = value
    return True


def upload_image(server, path):
    data = Path(path).read_bytes()
    ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    boundary = f"----lt0{uuid.uuid4().hex}"
    buf = io.BytesIO()

    def w(s):
        buf.write(s.encode() if isinstance(s, str) else s)

    w(f"--{boundary}\r\n")
    w(f'Content-Disposition: form-data; name="image"; filename="{Path(path).name}"\r\n')
    w(f"Content-Type: {ctype}\r\n\r\n")
    w(data)
    w("\r\n")
    w(f"--{boundary}\r\n")
    w('Content-Disposition: form-data; name="overwrite"\r\n\r\n')
    w("true\r\n")
    w(f"--{boundary}--\r\n")
    req = urllib.request.Request(
        f"{server}/upload/image", data=buf.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    name = resp.get("name")
    if not name:
        raise RuntimeError(f"/upload/image returned no name: {resp}")
    sub = resp.get("subfolder", "")
    return f"{sub}/{name}" if sub else name


def post_json(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def png_size(data):
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def server_walltime(hist):
    """Wall seconds from /history status messages (execution_start->success)."""
    msgs = hist.get("status", {}).get("messages", [])
    start = end = None
    for ev in msgs:
        if not isinstance(ev, list) or len(ev) < 2:
            continue
        name, payload = ev[0], ev[1]
        ts = payload.get("timestamp") if isinstance(payload, dict) else None
        if name == "execution_start" and ts is not None:
            start = ts
        elif name in ("execution_success", "execution_error") and ts is not None:
            end = ts
    if start is not None and end is not None:
        return round((end - start) / 1000.0, 1)
    return None


def run_one(server, job, out_dir):
    graph = json.loads(Path(job["graph"]).read_text())

    _, p = find(graph, "SC_PROMPT")
    if p is None or not inject(p, "SC_PROMPT",
                              p.get("_meta", {}).get("text_field", "text"),
                              job["prompt"]):
        return None
    _, s = find(graph, "SC_SEED")
    if s is None or not inject(s, "SC_SEED",
                              s.get("_meta", {}).get("seed_field", "noise_seed"),
                              int(job["seed"])):
        return None
    _, sz = find(graph, "SC_SIZE")
    if sz is None or not (inject(sz, "SC_SIZE", "width", int(job["width"]))
                          and inject(sz, "SC_SIZE", "height", int(job["height"]))):
        return None
    if "steps" in job:
        _, st = find(graph, "SC_STEPS")
        if st is None or not inject(st, "SC_STEPS", "steps", int(job["steps"])):
            return None
    if job.get("lora"):
        _, lo = find(graph, "SC_LORA")
        if lo is None or not inject(lo, "SC_LORA", "lora_name", job["lora"]):
            return None
        if "lora_strength" in job:
            inject(lo, "SC_LORA", "strength_model", float(job["lora_strength"]))

    uploaded = None
    if job.get("subject"):
        uploaded = upload_image(server, job["subject"])
        _, subj = find(graph, "SC_SUBJECT_IMAGE")
        if subj is None or not inject(
                subj, "SC_SUBJECT_IMAGE",
                subj.get("_meta", {}).get("image_field", "image"), uploaded):
            return None

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{job['name']}.submitted.json").write_text(json.dumps(graph, indent=2))

    t0 = time.monotonic()
    sub = post_json(f"{server}/prompt", {"prompt": graph, "client_id": "lt0"})
    pid = sub.get("prompt_id")
    if not pid:
        print(f"FAIL[{job['name']}]: no prompt_id: {sub}")
        return None
    print(f"[{job['name']}] submitted prompt_id={pid} seed={job['seed']}")

    timeout = int(job.get("timeout", 1200))
    images, hist, poll_err = None, None, 0
    while time.monotonic() - t0 < timeout:
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"{server}/history/{pid}", timeout=30) as r:
                hist = json.loads(r.read()).get(pid)
            poll_err = 0
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            poll_err += 1
            print(f"  poll error ({poll_err}/5): {e}")
            if poll_err >= 5:
                print(f"FAIL[{job['name']}]: ComfyUI unreachable for 5 polls")
                return None
            continue
        if not hist:
            continue
        status = hist.get("status", {})
        if status.get("status_str") == "error":
            print(f"FAIL[{job['name']}]: execution error: "
                  f"{json.dumps(status)[:1500]}")
            return None
        for node_out in hist.get("outputs", {}).values():
            if node_out.get("images"):
                images = node_out["images"]
                break
        if images:
            break
        if status.get("completed") is True:
            print(f"FAIL[{job['name']}]: completed with no images")
            return None
    if not images:
        print(f"FAIL[{job['name']}]: timeout {timeout}s")
        return None

    client_secs = round(time.monotonic() - t0, 1)
    img = images[0]
    q = urllib.parse.urlencode({"filename": img["filename"],
                                "subfolder": img.get("subfolder", ""),
                                "type": img.get("type", "output")})
    with urllib.request.urlopen(f"{server}/view?{q}", timeout=120) as r:
        data = r.read()

    size = png_size(data)
    out_png = out_dir / f"{job['name']}.png"
    out_png.write_bytes(data)
    server_secs = server_walltime(hist)

    ok = size == (int(job["width"]), int(job["height"]))
    receipt = {
        "name": job["name"], "graph": job["graph"], "prompt": job["prompt"],
        "seed": job["seed"], "width": job["width"], "height": job["height"],
        "steps": job.get("steps"), "lora": job.get("lora"),
        "lora_strength": job.get("lora_strength"),
        "subject": job.get("subject"), "uploaded_as": uploaded,
        "prompt_id": pid, "size": list(size) if size else None,
        "server_walltime_s": server_secs, "client_elapsed_s": client_secs,
        "sha256": hashlib.sha256(data).hexdigest(), "out": str(out_png),
        "size_gate": "PASS" if ok else "FAIL",
    }
    (out_dir / f"{job['name']}.receipt.json").write_text(json.dumps(receipt, indent=2))
    print(f"{'PASS' if ok else 'FAIL'}[{job['name']}]: {size} "
          f"server={server_secs}s client={client_secs}s -> {out_png}")
    return receipt if ok else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--only", default=None,
                    help="run only renders whose name contains this substring")
    args = ap.parse_args()

    man = json.loads(args.manifest.read_text())
    server = man.get("server", "http://127.0.0.1:8188")
    out_dir = Path(man["renders_dir"])
    jobs = man["renders"]
    if args.only:
        jobs = [j for j in jobs if args.only in j["name"]]

    receipts, failures = [], []
    for job in jobs:
        try:
            rec = run_one(server, job, out_dir)
        except Exception as e:  # noqa: BLE001 - report + continue the batch
            print(f"FAIL[{job['name']}]: exception {type(e).__name__}: {e}")
            rec = None
        if rec:
            receipts.append(rec)
        else:
            failures.append(job["name"])

    summary = {"total": len(jobs), "passed": len(receipts),
               "failed": failures, "receipts": receipts}
    (out_dir / "render_matrix_receipts.json").write_text(json.dumps(summary, indent=2))
    print(f"\nMATRIX: {len(receipts)}/{len(jobs)} passed; "
          f"failed={failures or 'none'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
