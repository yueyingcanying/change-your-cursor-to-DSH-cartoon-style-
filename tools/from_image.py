# -*- coding: utf-8 -*-
"""Build cursors straight from the reference artwork (no redrawing)."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_cursors import (  # noqa: E402
    SS, WHITE, NAVY, BRAND, BRAND_L, BRAND_D, Canvas, dilate, hs, write_cur, write_ani,
)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ref.png")
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEAD_CROP = (176, 4, 700, 516)
FACE_CROP = (252, 100, 660, 508)  # square, so it nests inside a round badge


def cutout(path, thresh=26):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    key = (255, 0, 255)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(im, seed, key, thresh=thresh)
    a = np.array(im)
    bg = (a[:, :, 0] == 255) & (a[:, :, 1] == 0) & (a[:, :, 2] == 255)
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    rgb = np.array(Image.open(path).convert("RGB"))
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def trim(im):
    a = np.array(im.getchannel("A"))
    ys, xs = np.nonzero(a > 8)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def tip_hotspot(im):
    """Hotspot = tip of the ahoge: centroid x of the topmost opaque row."""
    a = np.array(im.getchannel("A"))
    for y in range(a.shape[0]):
        xs = np.nonzero(a[y] > 120)[0]
        if len(xs):
            return (int(round(float(xs.mean()))), y)
    return (0, 0)


def paste_photo(c, photo, box, white=1.15, navy=0.72, clip_circle=None):
    """Place a raster cut-out (aspect preserved, top-left aligned) with a rim."""
    px0, py0 = c.T((box[0], box[1]))
    avail_w = (box[2] - box[0]) * c.k * SS
    avail_h = (box[3] - box[1]) * c.k * SS
    sw, sh = photo.size
    r = min(avail_w / sw, avail_h / sh)
    w, h = max(1, int(round(sw * r))), max(1, int(round(sh * r)))
    im = photo.resize((w, h), Image.LANCZOS)

    layer = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
    layer.paste(im, (int(round(px0)), int(round(py0))))
    a = layer.getchannel("A")
    if clip_circle is not None:
        cm = c.ell_mask(clip_circle[0], clip_circle[1], clip_circle[2], clip_circle[3])
        layer.putalpha(Image.fromarray(np.minimum(np.array(a), np.array(cm))))
    a = layer.getchannel("A").point(lambda v: 255 if v > 8 else 0)
    if navy > 0:
        c.img.paste(Image.new("RGBA", c.img.size, NAVY), (0, 0),
                    dilate(a, c.tw(white + navy)))
    if white > 0:
        c.img.paste(Image.new("RGBA", c.img.size, WHITE), (0, 0), dilate(a, c.tw(white)))
    c.img.alpha_composite(layer)


def art_arrow_photo(c, head):
    """Girl owns the tile (~90%); the arrow is a small accent on her corner."""
    from gen_cursors import arrow_pts
    paste_photo(c, head, (3.4, 4.0, 31.8, 31.4), white=0.80, navy=0.50)
    c.paint_poly(arrow_pts(s=0.50, org=(2.0, 2.0)),
                 c.grad(BRAND_L, BRAND_D, 0.5), white=0.85, navy=0.52)


def art_help_photo(c, face):
    from gen_cursors import art_arrow
    art_arrow(c)
    bx, by, br = 23.2, 23.2, 7.8
    c.paint_mask(c.ell_mask(bx, by, br, br), WHITE, white=1.1, navy=0.7)
    paste_photo(c, face, (bx - br + 0.9, by - br + 0.9, bx + br - 0.9, by + br - 0.9),
                white=0.0, navy=0.0, clip_circle=(bx, by, br - 0.85, br - 0.85))


def art_busy_photo(c, face, phase, n=10):
    from gen_cursors import arc_mask
    m = arc_mask(c, 16, 16, 13.4, 1.75, phase, n, span=0.72)
    c.paint_mask(m, c.grad(BRAND_L, BRAND, 0.5), white=0.95, navy=0.62)
    R = 11.3
    c.paint_mask(c.ell_mask(16, 16, R + 0.85, R + 0.85), WHITE, white=0.95, navy=0.58)
    paste_photo(c, face, (16 - R, 16 - R, 16 + R, 16 + R), white=0.0, navy=0.0,
                clip_circle=(16, 16, R, R))


def art_app_photo(c, face, phase, n=8):
    """Small arrow on the corner, big face badge with a thin spinning arc."""
    from gen_cursors import arc_mask, arrow_pts
    c.paint_poly(arrow_pts(s=0.55, org=(1.8, 1.8)),
                 c.grad(BRAND_L, BRAND_D, 0.5), white=0.90, navy=0.55)
    cx = cy = 21.2
    Rr = 8.2
    m = arc_mask(c, cx, cy, Rr, 1.7, phase, n, span=0.55, ccw=True)
    c.paint_mask(m, c.grad(BRAND_L, BRAND, 0.4), white=0.90, navy=0.58)
    R = 7.0
    c.paint_mask(c.ell_mask(cx, cy, R + 0.8, R + 0.8), WHITE, white=0.90, navy=0.55)
    paste_photo(c, face, (cx - R, cy - R, cx + R, cy + R), white=0.0, navy=0.0,
                clip_circle=(cx, cy, R, R))


def main():
    full = cutout(SRC)
    head = trim(full.crop(HEAD_CROP))
    face = trim(full.crop(FACE_CROP))
    head.save(os.path.join(OUT, "whale_girl_head.png"))
    print("head:", head.size, " face:", face.size)

    d = os.path.join(OUT, "cursors_moe")
    sizes = (32, 48, 64)

    items = []
    for s in sizes:
        c = Canvas(s)
        art_arrow_photo(c, head)
        items.append((c.out(), hs("arrow", s)))
    write_cur(os.path.join(d, "arrow.cur"), items)
    print("arrow hotspots:", [hs_ for _, hs_ in items])

    items = []
    for s in sizes:
        c = Canvas(s)
        art_help_photo(c, face)
        items.append((c.out(), hs("arrow", s)))
    write_cur(os.path.join(d, "help.cur"), items)

    frames = []
    for ph in range(10):
        fr = []
        for s in sizes:
            c = Canvas(s)
            art_busy_photo(c, face, ph, 10)
            fr.append((c.out(), (s // 2, s // 2)))
        frames.append(fr)
    write_ani(os.path.join(d, "busy.ani"), frames, rates=[5] * 10)

    frames = []
    for ph in range(8):
        fr = []
        for s in sizes:
            c = Canvas(s)
            art_app_photo(c, face, ph, 8)
            fr.append((c.out(), hs("arrow", s)))
        frames.append(fr)
    write_ani(os.path.join(d, "appstarting.ani"), frames, rates=[6] * 8)
    print("wrote photo arrow/help/busy/appstarting ->", d)


if __name__ == "__main__":
    main()