# -*- coding: utf-8 -*-
"""Independent reader + preview sheet.  Does not reuse the generator's code."""
import io
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

NAMES = {
    "arrow": "Normal Select",
    "help": "Help Select",
    "appstarting": "Working in Background",
    "busy": "Busy",
    "cross": "Precision Select",
    "ibeam": "Text Select",
    "pen": "Handwriting",
    "no": "Unavailable",
    "sizens": "Vertical Resize",
    "sizewe": "Horizontal Resize",
    "sizenwse": "Diagonal Resize 1",
    "sizenesw": "Diagonal Resize 2",
    "sizeall": "Move",
    "uparrow": "Alternate Select",
    "hand": "Link Select",
    "pin": "Location Select",
}


def parse_cur(blob):
    """-> list of (PIL RGBA, (hx,hy))"""
    rsv, typ, cnt = struct.unpack_from("<HHH", blob, 0)
    if rsv != 0 or typ not in (1, 2):
        raise ValueError("bad ICONDIR type=%d" % typ)
    out = []
    for i in range(cnt):
        off = 6 + 16 * i
        w, h, cc, r, hx, hy, nbytes, ioff = struct.unpack_from("<BBBBHHII", blob, off)
        w = w or 256
        h = h or 256
        data = blob[ioff:ioff + nbytes]
        hdr = struct.unpack_from("<IiiHHIIiiII", data, 0)
        bw, bh, bit, comp = hdr[1], hdr[2], hdr[4], hdr[5]
        if bit != 32 or comp != 0:
            raise ValueError("unsupported bpp=%d comp=%d" % (bit, comp))
        hp = bh // 2
        stride = bw * 4
        px = data[40:40 + stride * hp]
        img = Image.new("RGBA", (bw, hp), (0, 0, 0, 0))
        p = img.load()
        for y in range(hp):
            rowoff = (hp - 1 - y) * stride
            for x in range(bw):
                b, g, rr, a = px[rowoff + x * 4:rowoff + x * 4 + 4]
                p[x, y] = (rr, g, b, a)
        out.append((img, (hx, hy)))
    return out


def parse_ani(path):
    blob = open(path, "rb").read()
    if blob[:4] != b"RIFF" or blob[8:12] != b"ACON":
        raise ValueError("not an ACON")
    frames, rates, anih = [], [], None
    i = 12
    end = len(blob)
    while i + 8 <= end:
        tag = blob[i:i + 4]
        size = struct.unpack_from("<I", blob, i + 4)[0]
        body = blob[i + 8:i + 8 + size]
        if tag == b"anih":
            anih = struct.unpack("<9I", body[:36])
        elif tag == b"rate":
            rates = list(struct.unpack("<%dI" % (size // 4), body))
        elif tag == b"LIST" and body[:4] == b"fram":
            j = 4
            while j + 8 <= len(body):
                t = body[j:j + 4]
                sz = struct.unpack_from("<I", body, j + 4)[0]
                if t == b"icon":
                    frames.append(parse_cur(body[j + 8:j + 8 + sz]))
                j += 8 + sz + (sz & 1)
        i += 8 + size + (size & 1)
    return frames, rates, anih


def checker(w, h, c1=(255, 255, 255), c2=(232, 236, 244), s=8):
    im = Image.new("RGBA", (w, h), c1)
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=c2)
    return im


def main(curdir, outpng, frame_pick=None):
    light = (247, 249, 255, 255)
    dark = (26, 30, 44, 255)
    keys = ["arrow", "help", "appstarting", "busy", "cross", "ibeam", "pen", "no",
            "sizens", "sizewe", "sizenwse", "sizenesw", "sizeall", "uparrow", "hand", "pin"]

    cols = [32, 48, 64]
    pad = 18
    label_w = 190
    cell_w = 32 + 48 + 64 + 40
    row_h = 78
    W = label_w + cell_w * 2 + pad * 2
    H = pad * 2 + 34 + row_h * len(keys)

    sheet = Image.new("RGBA", (W, H), (243, 245, 250, 255))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("segoeui.ttf", 15)
        fb = ImageFont.truetype("segoeuib.ttf", 17)
        fs = ImageFont.truetype("segoeui.ttf", 12)
    except Exception:
        f = fb = fs = ImageFont.load_default()

    # section headers
    d.rectangle([pad + label_w, pad, pad + label_w + cell_w - 8, pad + 28], fill=light)
    d.rectangle([pad + label_w + cell_w, pad, pad + label_w + cell_w * 2 - 8, pad + 28], fill=dark)
    d.text((pad + label_w + 10, pad + 5), "on light UI", font=fb, fill=(20, 26, 50))
    d.text((pad + label_w + cell_w + 10, pad + 5), "on dark UI", font=fb, fill=(240, 244, 255))

    y = pad + 34
    for k in keys:
        path = os.path.join(curdir, k + ".cur")
        if not os.path.exists(path):
            path = os.path.join(curdir, k + ".ani")
        if not os.path.exists(path):
            continue
        if path.endswith(".ani"):
            frames, rates, anih = parse_ani(path)
            pick = 4 if frame_pick is None else frame_pick
            items = frames[pick % len(frames)]
            anim = " .ani %df @%dms" % (len(frames), (rates[0] if rates else 5) * 1000 // 60)
        else:
            items = parse_cur(open(path, "rb").read())
            anim = ""
        size_map = {im.size[0]: (im, hs) for im, hs in items}

        d.text((pad, y + 24), NAMES.get(k, k), font=fb, fill=(24, 30, 55))
        d.text((pad, y + 44), "%s%s" % (k, anim), font=fs, fill=(110, 120, 150))

        for bi, bg in enumerate((light, dark)):
            bx = pad + label_w + bi * cell_w
            d.rounded_rectangle([bx, y, bx + cell_w - 10, y + row_h - 10], 8, fill=bg)
            xo = bx + 8
            for size in cols:
                if size not in size_map:
                    continue
                im, (hx, hy) = size_map[size]
                im = im.copy()
                # hotspot marker
                dd = ImageDraw.Draw(im)
                dd.line([hx - 0.5, hy - 3, hx - 0.5, hy + 3], fill=(255, 40, 40, 255))
                dd.line([hx - 3, hy - 0.5, hx + 3, hy - 0.5], fill=(255, 40, 40, 255))
                sheet.alpha_composite(im, (xo, y + 10))
                d.text((xo + size // 2 - 8, y + 10 + 46), str(size), font=fs,
                       fill=(60, 70, 100) if bi == 0 else (170, 180, 210))
                xo += size + 14
        y += row_h

    sheet.convert("RGB").save(outpng)
    print("preview ->", outpng, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])