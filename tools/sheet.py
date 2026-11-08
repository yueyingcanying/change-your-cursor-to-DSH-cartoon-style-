# -*- coding: utf-8 -*-
"""Readable contact sheet: 4 x 4 grid, 32px cursors at 3x on light and dark."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview import parse_cur, parse_ani, NAMES  # noqa: E402

ROLE = ["arrow", "help", "appstarting", "busy", "cross", "ibeam", "pen", "no",
        "sizens", "sizewe", "sizenwse", "sizenesw", "sizeall", "uparrow", "hand", "pin"]

Z = 3
PAD = 14
CELL_W = 32 * Z * 2 + 26
CELL_H = 32 * Z + 34


def load(d, key):
    p = os.path.join(d, key + ".cur")
    if os.path.exists(p):
        return {im.size[0]: (im, hs) for im, hs in parse_cur(open(p, "rb").read())}
    frames, rates, _ = parse_ani(os.path.join(d, key + ".ani"))
    return {im.size[0]: (im, hs) for im, hs in frames[3]}


def main(src, outpng, title):
    cols = 4
    rows = (len(ROLE) + cols - 1) // cols
    W = PAD * 2 + cols * CELL_W
    H = 54 + PAD + rows * CELL_H
    sheet = Image.new("RGB", (W, H), (245, 247, 252))
    d = ImageDraw.Draw(sheet)
    try:
        fb = ImageFont.truetype("segoeuib.ttf", 19)
        fr = ImageFont.truetype("segoeui.ttf", 13)
        fs = ImageFont.truetype("segoeui.ttf", 12)
    except Exception:
        fb = fr = fs = ImageFont.load_default()

    d.text((PAD, 14), title, font=fb, fill=(22, 28, 52))
    d.text((PAD, 36), "32 px shown at 3x  ·  red cross = click hotspot", font=fr,
           fill=(120, 130, 160))

    for i, key in enumerate(ROLE):
        m = load(src, key)
        if 32 not in m:
            continue
        im, hs = m[32]
        cx = PAD + (i % cols) * CELL_W
        cy = 54 + PAD + (i // cols) * CELL_H
        card = Image.new("RGB", (CELL_W - 8, CELL_H - 8), (255, 255, 255))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, card.size[0] - 1, card.size[1] - 1], 10,
                             fill=(255, 255, 255), outline=(228, 232, 244))
        for bi, bg in enumerate(((250, 251, 255), (27, 32, 48))):
            tile = Image.new("RGB", (32 * Z, 32 * Z), bg)
            big = im.resize((32 * Z, 32 * Z), Image.NEAREST)
            tile.paste(big, (0, 0), big)
            td = ImageDraw.Draw(tile)
            td.line([hs[0] * Z - Z // 2, hs[1] * Z - 2 * Z,
                     hs[0] * Z - Z // 2, hs[1] * Z + 2 * Z], fill=(255, 70, 70))
            td.line([hs[0] * Z - 2 * Z, hs[1] * Z - Z // 2,
                     hs[0] * Z + 2 * Z, hs[1] * Z - Z // 2], fill=(255, 70, 70))
            card.paste(tile, (5 + bi * (32 * Z + 6), 4))
        cd.text((5, 32 * Z + 7), NAMES.get(key, key), font=fs, fill=(60, 70, 100))
        sheet.paste(card, (cx, cy))

    sheet.save(outpng)
    print(outpng, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "DeepSeek Moe")