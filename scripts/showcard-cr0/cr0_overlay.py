#!/usr/bin/env python3
"""CR-0: deterministic typography offline — Pillow headline over a render.

Proves the text-never-via-diffusion path: stroked headline in the upper-right
region, auto-fitted so the bbox stays inside the canvas AND clear of the
badge safe-area (both gated — a clipped headline would silently invalidate
the Phase 6 discrimination probe). Headline bbox emitted as metadata (the
showcard Tier-1 pattern: mobile-readability is bbox arithmetic, not pixel
inspection).

--variants additionally writes two deliberately-degraded copies for the VLM
probe: a low-contrast headline (same fitted size, no stroke, grey) and a tiny
headline. If the VLM can't score these lower than the good composite on
headline_legibility, that is the score-clumping finding, recorded honestly.

Requires Pillow (pinned in the runbook pre-flight). Exit 0 = PASS.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SAFE_BADGE = (0.82, 0.85, 1.0, 1.0)  # bottom-right duration-badge region (fracs)
ORIGIN = (0.48, 0.10)                # headline anchor (fracs)
MIN_PX, MAX_PX = 40, 120


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    print("FAIL: no bold TTF found (install fonts-dejavu-core)")
    sys.exit(1)


def rects_overlap(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def fit_headline(img: Image.Image, text: str, badge) -> tuple[int, tuple]:
    """Largest px in [MIN_PX, MAX_PX] whose bbox fits the canvas and misses
    the badge safe-area. Measurement only — nothing is drawn."""
    d = ImageDraw.Draw(img)
    xy = (int(img.width * ORIGIN[0]), int(img.height * ORIGIN[1]))
    for px in range(MAX_PX, MIN_PX - 1, -5):
        font = load_font(px)
        bbox = d.textbbox(xy, text, font=font, stroke_width=max(2, px // 14))
        inside = (bbox[0] >= 0 and bbox[1] >= 0 and
                  bbox[2] <= img.width and bbox[3] <= img.height)
        if inside and not rects_overlap(bbox, badge):
            return px, bbox
    print(f"FAIL: headline cannot fit canvas + badge safe-area even at "
          f"{MIN_PX}px — shorten --text")
    sys.exit(1)


def draw_headline(img: Image.Image, text: str, px: int,
                  fill: str, stroke: str | None):
    d = ImageDraw.Draw(img)
    xy = (int(img.width * ORIGIN[0]), int(img.height * ORIGIN[1]))
    kw = {"stroke_width": max(2, px // 14), "stroke_fill": stroke} if stroke else {}
    d.text(xy, text, font=load_font(px), fill=fill, **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("render", type=Path, help="background PNG from cr0_render.py")
    ap.add_argument("--text", default="LOCAL AI\nTHUMBNAILS")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--variants", action="store_true",
                    help="also write -lowcontrast and -tinytext probe variants")
    args = ap.parse_args()

    base = Image.open(args.render).convert("RGB")
    if base.size != (1280, 720):
        print(f"FAIL: expected 1280x720 render, got {base.size}")
        return 1

    badge = (int(SAFE_BADGE[0] * base.width), int(SAFE_BADGE[1] * base.height),
             int(SAFE_BADGE[2] * base.width), int(SAFE_BADGE[3] * base.height))
    px, bbox = fit_headline(base, args.text, badge)

    good = base.copy()
    draw_headline(good, args.text, px, fill="#FFFFFF", stroke="#111111")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    good.save(args.out)

    meta = {"headline_px": px,
            "headline_bbox_1280": list(bbox),
            "height_at_168w_px": round((bbox[3] - bbox[1]) * 168 / 1280, 1),
            "badge_safe_area": list(badge)}
    args.out.with_suffix(".bbox.json").write_text(json.dumps(meta, indent=2))
    written = [str(args.out)]

    if args.variants:
        # Same fitted size, grey, strokeless: contrast is the ONLY difference.
        low = base.copy()
        draw_headline(low, args.text, px, fill="#8a8a8a", stroke=None)
        p = args.out.with_stem(args.out.stem + "-lowcontrast")
        low.save(p); written.append(str(p))

        tiny = base.copy()  # 22px: unreadable at mobile scale, trivially inside
        draw_headline(tiny, args.text.replace("\n", " "), 22,
                      fill="#FFFFFF", stroke="#111111")
        p = args.out.with_stem(args.out.stem + "-tinytext")
        tiny.save(p); written.append(str(p))

    print(f"PASS: {', '.join(written)}")
    print(f"      fitted {px}px; headline height at 168px width = "
          f"{meta['height_at_168w_px']}px (bbox {bbox})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
