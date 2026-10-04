#!/usr/bin/env python3
"""
Turn a photo into the profile's dithered header: two-tone Floyd–Steinberg
dots in the site's gold, one PNG for GitHub's dark theme and one for light.

    python3 tools/dither_header.py PHOTO [--top 0.40] [--ratio 3] [--dot 2]

Needs Pillow. Writes assets/header-dark.png and assets/header-light.png.
"""

import argparse
import os

from PIL import Image, ImageEnhance, ImageOps

GOLD = (232, 196, 106)        # #E8C46A, the site's accent
DARK_BG = (13, 17, 23)        # GitHub dark canvas
LIGHT_INK = (150, 110, 30)    # deeper gold that reads on white
LIGHT_BG = (255, 255, 255)


def dither(img, ink, bg):
    """1-bit Floyd–Steinberg, then paint the two levels in our colours."""
    bw = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    return Image.composite(Image.new("RGB", bw.size, ink), Image.new("RGB", bw.size, bg), bw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo")
    ap.add_argument("--top", type=float, default=0.40, help="crop start, as a fraction of height")
    ap.add_argument("--ratio", type=float, default=3.0, help="banner width / height")
    ap.add_argument("--width", type=int, default=600, help="dot grid width before scaling")
    ap.add_argument("--dot", type=int, default=2, help="pixels per dot in the output")
    ap.add_argument("--contrast", type=float, default=1.15)
    ap.add_argument("--gamma", type=float, default=1.8,
                    help=">1 darkens midtones, so gold is kept for highlights")
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()

    im = Image.open(args.photo).convert("RGB")
    w, h = im.size
    bh = int(w / args.ratio)
    y = min(int(args.top * h), h - bh)
    band = im.crop((0, y, w, y + bh))
    grid = band.resize((args.width, int(args.width / args.ratio)), Image.LANCZOS)
    gray = ImageOps.autocontrast(grid.convert("L"), cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(args.contrast)
    # Dark theme darkens midtones (gold only on highlights); light theme does
    # the reverse before inverting, so it isn't a wall of ink.
    dark_src = gray.point(lambda v: round(255 * (v / 255) ** args.gamma))
    light_src = gray.point(lambda v: round(255 * (v / 255) ** (1 / args.gamma)))

    os.makedirs(args.out, exist_ok=True)
    size = (grid.width * args.dot, grid.height * args.dot)
    # Dark theme: light parts of the photo become gold dots.
    dither(dark_src, GOLD, DARK_BG).resize(size, Image.NEAREST).save(
        os.path.join(args.out, "header-dark.png"), optimize=True)
    # Light theme: dark parts become ink, so the image isn't a negative.
    dither(ImageOps.invert(light_src), LIGHT_INK, LIGHT_BG).resize(size, Image.NEAREST).save(
        os.path.join(args.out, "header-light.png"), optimize=True)
    for n in ("header-dark.png", "header-light.png"):
        p = os.path.join(args.out, n)
        print("%s  %dx%d  %.0f KB" % (p, size[0], size[1], os.path.getsize(p) / 1e3))


if __name__ == "__main__":
    main()
