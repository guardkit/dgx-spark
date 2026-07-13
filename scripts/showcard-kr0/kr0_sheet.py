#!/usr/bin/env python3
"""KR-0: build a labelled likeness contact sheet for the fidelity verdict.

Layout: one row per subject photo. The reference photo is leftmost (labelled
REFERENCE); the subject-conditioned renders follow as columns, each labelled
with its prompt-style and seed. The operator eyeballs this sheet to judge
whether Kontext holds the likeness across prompts and seeds (DF-024 §3).

Input is a manifest JSON:
  {"subjects": [
     {"reference": "/abs/ref.jpg",
      "renders": [{"path": "/abs/r.png", "label": "studio · s42"}, ...]},
     ...]}

Pillow only (already staged on the render box per CR-0).
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit(img: Image.Image, cw: int, ch: int) -> Image.Image:
    img = img.convert("RGB")
    scale = min(cw / img.width, ch / img.height)
    w, h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    return img.resize((w, h), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path, help="sheet manifest JSON")
    ap.add_argument("-o", "--out", type=Path, required=True, help="sheet PNG")
    ap.add_argument("--cell", type=int, default=384, help="cell width px")
    args = ap.parse_args()

    man = json.loads(args.manifest.read_text())
    subjects = man["subjects"]

    cw = args.cell
    ch = int(cw * 9 / 16)          # 16:9 render cells
    label_h = 34
    pad = 12
    ncols = 1 + max(len(s["renders"]) for s in subjects)

    cell_h = ch + label_h
    sheet_w = pad + ncols * (cw + pad)
    sheet_h = pad + len(subjects) * (cell_h + pad)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (24, 24, 27))
    draw = ImageDraw.Draw(sheet)
    font = load_font(16)

    def place(col, row, img, label, accent):
        x = pad + col * (cw + pad)
        y = pad + row * (cell_h + pad)
        draw.rectangle([x, y, x + cw, y + cell_h], fill=(15, 15, 17))
        thumb = fit(img, cw, ch)
        sheet.paste(thumb, (x + (cw - thumb.width) // 2,
                            y + (ch - thumb.height) // 2))
        draw.rectangle([x, y + ch, x + cw, y + cell_h], fill=accent)
        draw.text((x + 8, y + ch + 8), label[:48], fill=(255, 255, 255), font=font)

    for row, s in enumerate(subjects):
        ref = Image.open(s["reference"])
        place(0, row, ref, f"REFERENCE  {Path(s['reference']).name}", (120, 40, 40))
        for i, r in enumerate(s["renders"]):
            img = Image.open(r["path"])
            place(1 + i, row, img, r.get("label", Path(r["path"]).name), (40, 60, 110))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"PASS: contact sheet {sheet_w}x{sheet_h} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
