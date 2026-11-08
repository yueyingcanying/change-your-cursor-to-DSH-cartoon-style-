# -*- coding: utf-8 -*-
"""Zoom sheet: render selected cursors at native size, upscaled with NEAREST."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview import parse_cur, parse_ani, NAMES  # noqa: E402


def load(curdir, key, frame=4):
    p = os.path.join(curdir, key + ".cur")
    if os.path.exists(p):
        return parse_cur(open(p, "rb").read()), False
    p = os.path.join(curdir, key + ".ani")
    frames, rates, _ = parse_ani(p)
    return frames[frame % len(frames)], True


def main(curdir, outpng, keys, sizes=(32, 64), zoom=8):
    cell = max(sizes) * zoom + 24
    W = cell * len(keys) * 2 + 20
    H = 40 + (max(sizes) * zoom + 40) * len(sizes) + 20
    sheet = Image.new("RGB", (W, H), (243, 245, 250))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("segoeuib.ttf", 14)
    except Exception:
        f = ImageFont.load_default()

    for ki, k in enumerate(keys):
        items, anim = load(curdir, k)
        m = {im.size[0]: (im, hs) for im, hs in items}
        d.text((10 + ki * cell * 2, 8), k + (" (ani)" if anim else ""), font=f, fill=(20, 24, 48))
        for bi, bg in enumerate(((247, 249, 255), (26, 30, 44))):
            bx = 10 + ki * cell * 2 + bi * cell
            for si, size in enumerate(sizes):
                if size not in m:
                    continue
                im, (hx, hy) = m[size]
                big = im.resize((size * zoom, size * zoom), Image.NEAREST)
                canvas = Image.new("RGB", big.size, bg)
                canvas.paste(big, (0, 0), big)
                dd = ImageDraw.Draw(canvas)
                dd.line([hx * zoom - zoom // 2, hy * zoom - zoom * 2,
                         hx * zoom - zoom // 2, hy * zoom + zoom * 2], fill=(255, 60, 60))
                dd.line([hx * zoom - zoom * 2, hy * zoom - zoom // 2,
                         hx * zoom + zoom * 2, hy * zoom - zoom // 2], fill=(255, 60, 60))
                sheet.paste(canvas, (bx + 6, 30 + si * (max(sizes) * zoom + 40)))
    sheet.save(outpng)
    print(outpng, sheet.size)


if __name__ == "__main__":
    cdir = sys.argv[1]
    out = sys.argv[2]
    ks = sys.argv[3].split(",") if len(sys.argv) > 3 else ["arrow", "hand", "pen", "busy", "ibeam"]
    z = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    main(cdir, out, ks, zoom=z)