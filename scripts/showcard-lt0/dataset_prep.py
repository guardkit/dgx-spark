#!/usr/bin/env python3
"""showcard LT-0 dataset prep — crop/resize the operator's source photos into the
flux-finetuning DreamBooth training layout.

Committable receipt: stdlib + PIL only, all paths as CLI args, no image bytes.

Pipeline per selected photo (order matters):
  1. open source JPG
  2. ImageOps.exif_transpose  -- the Sony DSC JPGs carry an EXIF orientation tag;
     this bakes it in so the crop box (authored in transposed coords) lands right.
  3. crop to the box from crops.json  (box = [left, top, right, bottom], transposed coords)
  4. resize so the LONGEST side == --longest (default 1024), Lanczos
  5. save JPEG quality 95 into --out

The source library is READ-ONLY: this script only reads from --src and writes to --out.

Usage:
  dataset_prep.py --src <source_dir> --crops <crops.json> --out <output_dir> \
                  [--longest 1024] [--quality 95]

crops.json shape:
  { "crops": { "DSC00042.JPG": [left, top, right, bottom], ... }, ... }
Any other top-level keys (comments, source dims) are ignored.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageOps


def load_crops(path):
    with open(path) as fh:
        doc = json.load(fh)
    crops = doc.get("crops")
    if not isinstance(crops, dict) or not crops:
        sys.exit(f"crops.json {path!r} has no non-empty 'crops' object")
    return crops


def process_one(src_path, box, out_path, longest, quality):
    with Image.open(src_path) as im:
        im = ImageOps.exif_transpose(im)  # step 2 — MUST precede the crop
        im = im.convert("RGB")
        w, h = im.size
        left, top, right, bottom = box
        # Validate the box lands inside the transposed frame.
        if not (0 <= left < right <= w and 0 <= top < bottom <= h):
            raise ValueError(
                f"crop box {box} out of bounds for {w}x{h} image {src_path!r}"
            )
        cropped = im.crop((left, top, right, bottom))  # step 3
        cw, ch = cropped.size
        scale = longest / float(max(cw, ch))            # step 4
        new_size = (max(1, round(cw * scale)), max(1, round(ch * scale)))
        resized = cropped.resize(new_size, Image.LANCZOS)
        resized.save(out_path, "JPEG", quality=quality)  # step 5
        return resized.size


def main():
    ap = argparse.ArgumentParser(description="showcard LT-0 dataset prep")
    ap.add_argument("--src", required=True, help="source photo dir (READ-ONLY)")
    ap.add_argument("--crops", required=True, help="crops.json path")
    ap.add_argument("--out", required=True, help="output dir (flux_data/rw0man)")
    ap.add_argument("--longest", type=int, default=1024,
                    help="longest-side pixels after resize (default 1024)")
    ap.add_argument("--quality", type=int, default=95,
                    help="JPEG quality (default 95)")
    args = ap.parse_args()

    crops = load_crops(args.crops)
    os.makedirs(args.out, exist_ok=True)

    ok = 0
    for fname, box in sorted(crops.items()):
        src_path = os.path.join(args.src, fname)
        if not os.path.isfile(src_path):
            sys.exit(f"missing source photo: {src_path}")
        out_name = os.path.splitext(fname)[0] + ".jpg"
        out_path = os.path.join(args.out, out_name)
        size = process_one(src_path, box, out_path, args.longest, args.quality)
        print(f"{fname} -> {out_name}  {size[0]}x{size[1]}")
        ok += 1

    print(f"wrote {ok} images to {args.out}")


if __name__ == "__main__":
    main()
