#!/usr/bin/env python3
"""showcard LT-0 — cut native-resolution face crops and build the identity +
contact sheets Rich judges.

Committable receipt: stdlib + PIL only. All image paths + face boxes come from a
spec JSON (this file holds NO image bytes and NO operator pixels). Face boxes are
authored by viewing each render/reference (no face model is used — and per the
DF-024 standing lesson a model's read is never evidence of likeness anyway; here
a box is only a crop rectangle, not a judgment).

Two artifact classes:
  1. crops/  — the face crop of every render + every reference, cut at NATIVE
     resolution with ZERO resampling (a plain PIL .crop(); references get
     ImageOps.exif_transpose first so the box lands in transposed coords). These
     are the files Rich opens at 100% to judge likeness.
  2. identity-sheet.png / contact-sheet.png — paired + overview composites for
     convenience. For legible side-by-side pairing the crops are scaled to a
     common display height on the SHEET ONLY (LANCZOS); the crops/ files remain
     the zero-resampling 100% originals.

Spec JSON shape:
  {
    "renders_dir": "/abs/renders",
    "crops_dir":   "/abs/crops",
    "out_dir":     "/abs/lt0-20260717",
    "anchor_ref":  "heldout_DSC00044",
    "references": [
      {"label":"heldout_DSC00044","path":"/abs/ref.JPG",
       "box":[0.40,0.10,0.61,0.43],"transpose":true}
    ],
    "renders": [
      {"name":"a-studio-42","path":"/abs/a-studio-42.png",
       "box":[0.33,0.05,0.53,0.52],"label":"path a - studio - seed 42 - 144s",
       "transpose":false}
    ]
  }
Boxes are normalized [left,top,right,bottom] fractions of the (transposed) frame.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw, ImageFont


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def load_frame(path, transpose):
    im = Image.open(path)
    if transpose:
        im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def native_crop(im, box):
    """Zero-resampling crop from normalized [l,t,r,b] fractions."""
    W, H = im.size
    l, t, r, b = box
    px = (max(0, int(l * W)), max(0, int(t * H)),
          min(W, int(r * W)), min(H, int(b * H)))
    return im.crop(px), px


def scaled(img, h):
    w = max(1, int(img.width * h / img.height))
    return img.resize((w, h), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--face-h", type=int, default=440,
                    help="display height of a face crop on the sheets (px)")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    crops_dir = Path(spec["crops_dir"]); crops_dir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(spec["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    fh = args.face_h

    # --- native crops: references ---
    ref_crop = {}
    for r in spec["references"]:
        im = load_frame(r["path"], r.get("transpose", False))
        crop, px = native_crop(im, r["box"])
        outp = crops_dir / f"ref_{r['label']}_face.png"
        crop.save(outp)
        ref_crop[r["label"]] = crop
        print(f"ref crop {r['label']}: native {crop.size} px{px} -> {outp}")

    # --- native crops: renders ---
    rnd_crop = {}
    for r in spec["renders"]:
        im = load_frame(r["path"], r.get("transpose", False))
        crop, px = native_crop(im, r["box"])
        outp = crops_dir / f"{r['name']}_face.png"
        crop.save(outp)
        rnd_crop[r["name"]] = crop
        print(f"render crop {r['name']}: native {crop.size} px{px} -> {outp}")

    fnt = font(20); fnt_s = font(16); pad = 14
    anchor = spec["anchor_ref"]
    anchor_crop = ref_crop[anchor]

    # =============== identity sheet ===============
    # header strip: all reference face crops; then one row per render:
    # [anchor reference face crop | render face crop]
    ref_scaled = [(r["label"], scaled(ref_crop[r["label"]], fh))
                  for r in spec["references"]]
    header_w = pad + sum(c.width + pad for _, c in ref_scaled)
    header_h = fh + 30 + 2 * pad

    a_s = scaled(anchor_crop, fh)
    rows = []
    for r in spec["renders"]:
        rows.append((r, a_s, scaled(rnd_crop[r["name"]], fh)))
    row_w = pad + a_s.width + pad + max(c.width for _, _, c in rows) + pad + 340
    row_h = fh + 2 * pad
    sheet_w = max(header_w, row_w, 900)
    sheet_h = header_h + 30 + len(rows) * (row_h) + pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (22, 22, 25))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 6), "REFERENCE FACES (real photos - held-out + training reps)",
           fill=(255, 210, 90), font=fnt)
    x = pad; y = 34
    for label, c in ref_scaled:
        sheet.paste(c, (x, y))
        d.rectangle([x, y + c.height, x + c.width, y + c.height + 26], fill=(120, 40, 40))
        d.text((x + 4, y + c.height + 4), label, fill=(255, 255, 255), font=fnt_s)
        x += c.width + pad
    d.line([(0, header_h + 14), (sheet_w, header_h + 14)], fill=(80, 80, 90), width=2)
    d.text((pad, header_h + 18),
           f"PAIRS  [ anchor ref {anchor} | render ]  -- judge at 100% in crops/",
           fill=(255, 210, 90), font=fnt_s)

    y = header_h + 44
    for r, aimg, rimg in rows:
        sheet.paste(aimg, (pad, y))
        rx = pad + aimg.width + pad
        sheet.paste(rimg, (rx, y))
        tx = rx + rimg.width + pad
        d.text((tx, y + 6), r["name"], fill=(255, 255, 255), font=fnt)
        d.text((tx, y + 34), r.get("label", ""), fill=(180, 200, 255), font=fnt_s)
        y += row_h
    idp = out_dir / "identity-sheet.png"
    sheet.save(idp)
    print(f"identity-sheet {sheet.size} -> {idp}")

    # =============== contact sheet ===============
    cols = 2
    cw = 620
    ch = int(cw * 9 / 16)
    lh = 60
    n = len(spec["renders"])
    rows_n = (n + cols - 1) // cols
    csheet = Image.new("RGB", (pad + cols * (cw + pad),
                               pad + rows_n * (ch + lh + pad)), (22, 22, 25))
    dd = ImageDraw.Draw(csheet)
    for i, r in enumerate(spec["renders"]):
        im = load_frame(r["path"], r.get("transpose", False))
        th = im.copy(); th.thumbnail((cw, ch))
        cx = pad + (i % cols) * (cw + pad)
        cy = pad + (i // cols) * (ch + lh + pad)
        csheet.paste(th, (cx + (cw - th.width) // 2, cy))
        dd.rectangle([cx, cy + ch, cx + cw, cy + ch + lh], fill=(30, 45, 80))
        dd.text((cx + 6, cy + ch + 4), r["name"], fill=(255, 255, 255), font=fnt)
        dd.text((cx + 6, cy + ch + 32), r.get("label", ""), fill=(190, 205, 255), font=fnt_s)
    cpp = out_dir / "contact-sheet.png"
    csheet.save(cpp)
    print(f"contact-sheet {csheet.size} -> {cpp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
