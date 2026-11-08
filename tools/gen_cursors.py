# -*- coding: utf-8 -*-
"""
DeepSeek Moe cursor set generator  (v2)

Improvements over v1:
  * outlines are built with a true miter offset polygon, so the arrow tip and
    every arrowhead stay SHARP (v1 rounded them into blobs);
  * slimmer silhouettes, hotspots on the visual point;
  * reworked pen / hand / I-beam glyphs;
  * decorations removed from the pointer tip area.

Everything is drawn at 8x and downsampled, so 32/48/64 look clean.
"""
import math
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 8

NAVY = (16, 22, 52, 255)
WHITE = (255, 255, 255, 255)
BRAND = (77, 107, 254, 255)
BRAND_D = (30, 44, 160, 255)
BRAND_L = (150, 172, 255, 255)
CYAN = (116, 233, 255, 255)
SKIN = (255, 231, 219, 255)
BLUSH = (255, 143, 165, 255)
HAIR = (33, 44, 118, 255)
HAIR_L = (88, 118, 246, 255)
EYE = (44, 198, 255, 255)
GOLD = (255, 205, 120, 255)
CREAM = (255, 249, 245, 255)

# --- whale-girl palette, sampled from the reference art --------------------
GW_HAIR = (96, 154, 222, 255)      # main light-blue hair
GW_HAIR_D = (58, 104, 184, 255)    # hair shadow / side strands
GW_HAIR_L = (168, 206, 248, 255)   # bang highlight
GW_SKIN = (255, 227, 215, 255)
GW_BLUSH = (255, 154, 173, 255)
GW_EYE = (26, 48, 122, 255)
GW_EYE_M = (44, 124, 214, 255)
GW_EYE_L = (108, 206, 255, 255)
GW_FIN = (66, 126, 208, 255)
GW_FIN_L = (128, 178, 236, 255)
GW_NAVY = (24, 46, 104, 255)

SIZES = (32, 48, 64)


# ------------------------------------------------------------- primitives ---
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def norm(v):
    L = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / L, v[1] / L)


def bbox_area(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def offset_poly(pts, d, sign=1, limit=3.5):
    n = len(pts)
    out = []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        e1 = norm(sub(p1, p0))
        e2 = norm(sub(p2, p1))
        n1 = (e1[1] * sign, -e1[0] * sign)
        n2 = (e2[1] * sign, -e2[0] * sign)
        dot = n1[0] * n2[0] + n1[1] * n2[1]
        if 1.0 + dot < 1e-4:
            ox, oy = n1[0] * d, n1[1] * d
        else:
            k = d / (1.0 + dot)
            ox = (n1[0] + n2[0]) * k
            oy = (n1[1] + n2[1]) * k
            L = math.hypot(ox, oy)
            if L > abs(d) * limit:
                s = abs(d) * limit / L
                ox, oy = ox * s, oy * s
        out.append((p1[0] + ox, p1[1] + oy))
    return out


def grow_poly(pts, d):
    """Offset outward by d, auto-detecting winding via bounding-box growth."""
    a = offset_poly(pts, d, 1)
    b = offset_poly(pts, d, -1)
    return a if bbox_area(a) > bbox_area(b) else b


def rot(pts, deg, cx, cy):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca)
            for x, y in pts]


def dilate(mask, r):
    if r < 0.5:
        return mask
    b = mask.filter(ImageFilter.GaussianBlur(r))
    return b.point(lambda v: 255 if v >= 40 else 0)


class Canvas:
    def __init__(self, size):
        self.size = size
        self.k = size / 32.0
        self.px = size * SS
        self.img = Image.new("RGBA", (self.px, self.px), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def T(self, p):
        return (p[0] * self.k * SS, p[1] * self.k * SS)

    def TP(self, pts):
        return [self.T(p) for p in pts]

    def tw(self, units):
        return units * self.k * SS

    def mask(self):
        return Image.new("L", (self.px, self.px), 0)

    def md(self, m):
        return ImageDraw.Draw(m)

    # -- gradient ---------------------------------------------------------
    def grad(self, c0, c1, diag=0.0):
        w = h = self.px
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        t = np.clip((yy + xx * diag) / (1.0 + diag), 0, 1)[..., None]
        a = np.array(c0[:3], dtype=np.float32)[None, None, :]
        b = np.array(c1[:3], dtype=np.float32)[None, None, :]
        rgb = (a * (1 - t) + b * t).astype(np.uint8)
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        return Image.fromarray(np.concatenate([rgb, alpha], axis=2), "RGBA")

    # -- painters ---------------------------------------------------------
    def paint_mask(self, m, fill, white=1.1, navy=0.7):
        if navy > 0:
            self.img.paste(Image.new("RGBA", self.img.size, NAVY), (0, 0),
                           dilate(m, self.tw(white + navy)))
        if white > 0:
            self.img.paste(Image.new("RGBA", self.img.size, WHITE), (0, 0),
                           dilate(m, self.tw(white)))
        if isinstance(fill, Image.Image):
            self.img.paste(fill, (0, 0), m)
        else:
            self.img.paste(Image.new("RGBA", self.img.size, fill), (0, 0), m)

    def paint_poly(self, pts, fill, white=1.1, navy=0.7):
        if navy > 0:
            self.d.polygon(self.TP(grow_poly(pts, white + navy)), fill=NAVY)
        if white > 0:
            self.d.polygon(self.TP(grow_poly(pts, white)), fill=WHITE)
        m = self.poly_mask(pts)
        if isinstance(fill, Image.Image):
            self.img.paste(fill, (0, 0), m)
        else:
            self.img.paste(Image.new("RGBA", self.img.size, fill), (0, 0), m)

    # -- shapes -----------------------------------------------------------
    def poly(self, pts, fill):
        self.d.polygon(self.TP(pts), fill=fill)

    def poly_mask(self, pts):
        m = self.mask()
        self.md(m).polygon(self.TP(pts), fill=255)
        return m

    def rrect(self, x0, y0, x1, y1, r, fill):
        self.d.rounded_rectangle([self.T((x0, y0)), self.T((x1, y1))],
                                 radius=max(0.0, r * self.k * SS), fill=fill)

    def rrect_mask(self, x0, y0, x1, y1, r):
        m = self.mask()
        self.md(m).rounded_rectangle([self.T((x0, y0)), self.T((x1, y1))],
                                     radius=max(0.0, r * self.k * SS), fill=255)
        return m

    def ell(self, cx, cy, rx, ry, fill):
        self.d.ellipse([self.T((cx - rx, cy - ry)), self.T((cx + rx, cy + ry))], fill=fill)

    def ell_mask(self, cx, cy, rx, ry):
        m = self.mask()
        self.md(m).ellipse([self.T((cx - rx, cy - ry)), self.T((cx + rx, cy + ry))], fill=255)
        return m

    def cap(self, p0, p1, w, fill):
        a, b = self.T(p0), self.T(p1)
        wp = max(1, int(round(w * self.k * SS)))
        self.d.line([a, b], fill=fill, width=wp)
        r = w * self.k * SS / 2.0
        for c in (a, b):
            self.d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=fill)

    def cap_mask(self, p0, p1, w):
        m = self.mask()
        md = self.md(m)
        a, b = self.T(p0), self.T(p1)
        wp = max(1, int(round(w * self.k * SS)))
        md.line([a, b], fill=255, width=wp)
        r = w * self.k * SS / 2.0
        for c in (a, b):
            md.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=255)
        return m

    def union(self, *masks):
        out = np.array(masks[0])
        for m in masks[1:]:
            out = np.maximum(out, np.array(m))
        return Image.fromarray(out.astype(np.uint8))

    def diff(self, a, b):
        return Image.fromarray(np.where(np.array(b) > 0, 0, np.array(a)).astype(np.uint8))

    def and_(self, a, b):
        return Image.fromarray(np.minimum(np.array(a), np.array(b)))

    def tint(self, m, color):
        self.img.paste(Image.new("RGBA", self.img.size, color), (0, 0), m)

    def sticker(self, drawfn, white=1.25, navy=0.8):
        """Run drawfn on a scratch canvas, then paste it with a die-cut rim."""
        tmp = Canvas(self.size)
        drawfn(tmp)
        alpha = tmp.img.getchannel("A").point(lambda v: 255 if v > 8 else 0)
        if navy > 0:
            self.img.paste(Image.new("RGBA", self.img.size, NAVY), (0, 0),
                           dilate(alpha, self.tw(white + navy)))
        if white > 0:
            self.img.paste(Image.new("RGBA", self.img.size, WHITE), (0, 0),
                           dilate(alpha, self.tw(white)))
        self.img.alpha_composite(tmp.img)

    # -- decorations ------------------------------------------------------
    def heart(self, cx, cy, r, fill=BLUSH):
        pts = []
        for i in range(64):
            t = 2 * math.pi * i / 64
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + x * r / 16.0, cy + y * r / 16.0))
        self.poly(pts, fill)

    def sparkle(self, cx, cy, r, fill=WHITE):
        pts = []
        for i in range(8):
            ang = math.pi / 4 * i - math.pi / 2
            rad = r if i % 2 == 0 else r * 0.30
            pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        self.poly(pts, fill)

    def out(self):
        return self.img.resize((self.size, self.size), Image.LANCZOS)


# --------------------------------------------------------------- character ---
def girl_head(c, cx, cy, r, blink=0, eyes="open", detail=True):
    """Chibi whale-girl: sky-blue hair, fin 'ears', white whale clip."""
    # whale-fin ears, behind the hair
    for s in (-1, 1):
        fin = [(cx + s * r * 0.46, cy + r * 0.34),
               (cx + s * r * 1.42, cy - r * 0.02),
               (cx + s * r * 1.52, cy + r * 0.46),
               (cx + s * r * 0.78, cy + r * 0.64)]
        c.poly(fin, GW_FIN)
        if detail:
            inner = [(cx + s * r * 0.62, cy + r * 0.40),
                     (cx + s * r * 1.26, cy + r * 0.16),
                     (cx + s * r * 1.30, cy + r * 0.40),
                     (cx + s * r * 0.82, cy + r * 0.56)]
            c.poly(inner, GW_FIN_L)
    # hair mass + long side strands
    c.ell(cx, cy + r * 0.02, r * 1.05, r * 1.03, GW_HAIR)
    for s in (-1, 1):
        c.ell(cx + s * r * 0.94, cy + r * 0.36, r * 0.32, r * 0.62, GW_HAIR_D)
    # face
    c.ell(cx, cy + r * 0.15, r * 0.82, r * 0.79, GW_SKIN)
    # bangs
    for dx, w in ((-0.46, 0.54), (0.0, 0.62), (0.46, 0.54)):
        c.ell(cx + dx * r, cy - r * 0.46, r * w * 0.80, r * 0.46, GW_HAIR)
    c.ell(cx - r * 0.34, cy - r * 0.56, r * 0.30, r * 0.11, GW_HAIR_L)
    c.ell(cx + r * 0.30, cy - r * 0.62, r * 0.18, r * 0.09, GW_HAIR_L)
    c.cap((cx + r * 0.02, cy - r * 1.00), (cx + r * 0.34, cy - r * 1.44),
          max(1.1, r * 0.14), GW_HAIR_L)
    # white whale hair clip
    if detail:
        wx, wy = cx + r * 0.70, cy - r * 0.46
        c.ell(wx, wy, r * 0.17, r * 0.11, WHITE)
        c.poly([(wx - r * 0.12, wy), (wx - r * 0.27, wy - r * 0.12),
                (wx - r * 0.27, wy + r * 0.12)], WHITE)

    ex, ey, er = r * 0.36, cy + r * 0.24, r * 0.29
    if eyes == "closed" or blink:
        for s in (-1, 1):
            c.cap((cx + s * ex - er * 0.95, ey), (cx + s * ex + er * 0.95, ey),
                  max(1.0, r * 0.14), GW_NAVY)
    elif eyes == "happy":
        for s in (-1, 1):
            c.cap((cx + s * ex - er * 0.62, ey + er * 0.34),
                  (cx + s * ex, ey - er * 0.42), max(0.8, r * 0.095), GW_NAVY)
            c.cap((cx + s * ex, ey - er * 0.42),
                  (cx + s * ex + er * 0.62, ey + er * 0.34), max(0.8, r * 0.095), GW_NAVY)
    else:
        for s in (-1, 1):
            c.ell(cx + s * ex, ey, er * 0.84, er * 1.05, GW_EYE)
            c.ell(cx + s * ex, ey + er * 0.16, er * 0.68, er * 0.84, GW_EYE_M)
            c.ell(cx + s * ex, ey + er * 0.30, er * 0.50, er * 0.54, GW_EYE_L)
            c.ell(cx + s * ex - er * 0.32, ey - er * 0.34, er * 0.30, er * 0.34, WHITE)
            c.ell(cx + s * ex + er * 0.28, ey + er * 0.40, er * 0.16, er * 0.16, WHITE)
    for s in (-1, 1):
        c.ell(cx + s * r * 0.64, cy + r * 0.46, r * 0.16, r * 0.10, GW_BLUSH)
    c.ell(cx, cy + r * 0.56, r * 0.13, r * 0.10, GW_NAVY)
    c.ell(cx, cy + r * 0.60, r * 0.09, r * 0.05, (232, 122, 132, 255))


# ------------------------------------------------------------------- shapes ---
ARROW = [(0, 0), (0, 19.8), (4.1, 15.2), (6.9, 23.5), (10.4, 21.9), (7.6, 13.6), (13.3, 13.6)]


def arrow_pts(s=0.90, org=(2.2, 2.2)):
    return [(p[0] * s + org[0], p[1] * s + org[1]) for p in ARROW]


def dbl_arrow_pts(L=22.0, hl=6.2, hw=5.3, bw=1.95, cx=16.0, cy=16.0, deg=0.0):
    h = L / 2.0
    pts = [(0, 0), (hl, -hw), (hl, -bw), (L - hl, -bw), (L - hl, -hw), (L, 0),
           (L - hl, hw), (L - hl, bw), (hl, bw), (hl, hw)]
    pts = [(x - h + cx, y + cy) for x, y in pts]
    return rot(pts, deg, cx, cy)


def move_pts(R=13.6, hl=5.4, hw=5.3, b=2.15, cx=16.0, cy=16.0):
    pts = [
        (0, -R), (hw, -R + hl), (b, -R + hl), (b, -b), (R - hl, -b), (R - hl, -hw),
        (R, 0), (R - hl, hw), (R - hl, b), (b, b), (b, R - hl), (hw, R - hl),
        (0, R), (-hw, R - hl), (-b, R - hl), (-b, b), (-R + hl, b), (-R + hl, hw),
        (-R, 0), (-R + hl, -hw), (-R + hl, -b), (-b, -b), (-b, -R + hl), (-hw, -R + hl),
    ]
    return [(x + cx, y + cy) for x, y in pts]


# ---------------------------------------------------------------------- art ---
def art_arrow(c):
    pts = arrow_pts()
    c.paint_poly(pts, c.grad(BRAND_L, BRAND_D, 0.5), white=1.15, navy=0.72)
    m = c.poly_mask(pts)
    gloss = c.poly_mask([(0.9, 4.2), (0.9, 14.6), (2.5, 12.2), (3.5, 4.2)])
    c.tint(c.and_(m, gloss), (255, 255, 255, 74))


def art_moe_arrow(c):
    """Moe variant: chibi head riding a slim blade, tip on the hotspot."""
    tip = (2.2, 2.2)

    def head(d):
        girl_head(d, 17.6, 18.8, 7.9, detail=d.size >= 48)

    c.sticker(head, white=1.25, navy=0.82)
    blade = [tip, (10.0, 12.8), (8.9, 14.0), (1.4, 8.2)]
    c.paint_poly(blade, c.grad(BRAND_L, BRAND_D, 0.5), white=1.05, navy=0.7)
    c.heart(5.2, 7.4, 1.45, (255, 255, 255, 205))


def art_help(c):
    c.paint_poly(arrow_pts(s=0.82, org=(2.0, 2.0)),
                 c.grad(BRAND_L, BRAND_D, 0.5), white=1.1, navy=0.7)
    c.heart(7.3, 8.4, 1.5, (255, 255, 255, 230))
    bx, by, br = 23.4, 23.4, 7.2
    c.paint_mask(c.ell_mask(bx, by, br, br), c.grad(BRAND_L, BRAND, 0.35),
                 white=1.2, navy=0.72)
    c.cap((bx - 2.5, by - 2.3), (bx + 0.2, by - 3.5), 1.85, WHITE)
    c.cap((bx + 0.2, by - 3.5), (bx + 2.3, by - 2.0), 1.85, WHITE)
    c.cap((bx + 2.3, by - 2.0), (bx + 0.5, by + 0.8), 1.85, WHITE)
    c.cap((bx + 0.5, by + 0.8), (bx + 0.5, by + 2.1), 1.85, WHITE)
    c.ell(bx + 0.5, by + 4.2, 1.1, 1.1, WHITE)


def art_cross(c):
    cx = cy = 16.0
    m = c.union(
        c.cap_mask((cx, 4.6), (cx, 12.6), 1.95),
        c.cap_mask((cx, 19.4), (cx, 27.4), 1.95),
        c.cap_mask((4.6, cy), (12.6, cy), 1.95),
        c.cap_mask((19.4, cy), (27.4, cy), 1.95),
    )
    c.paint_mask(m, c.grad(BRAND_L, BRAND_D, 0.4), white=1.05, navy=0.68)
    c.paint_mask(c.ell_mask(cx, cy, 2.3, 2.3), BRAND, white=0.95, navy=0.65)



def art_ibeam(c):
    cx = 16.0
    top, bot = 5.4, 26.6
    sw = 4.15
    m = c.union(
        c.cap_mask((cx, top + 2.0), (cx, bot - 2.0), 1.9),
        c.cap_mask((cx - sw, top), (cx + sw, top), 2.05),
        c.cap_mask((cx - sw, bot), (cx + sw, bot), 2.05),
        c.cap_mask((cx - sw, top + 0.8), (cx - sw, top + 3.0), 1.65),
        c.cap_mask((cx + sw, top + 0.8), (cx + sw, top + 3.0), 1.65),
        c.cap_mask((cx - sw, bot - 0.8), (cx - sw, bot - 3.0), 1.65),
        c.cap_mask((cx + sw, bot - 0.8), (cx + sw, bot - 3.0), 1.65),
    )
    c.paint_mask(m, c.grad(BRAND_L, BRAND_D, 0.2), white=1.05, navy=0.68)


def art_pen(c):
    """Tapered 45-degree pen with a proud clip, tip at (2.6, 2.6)."""
    ux, uy = 0.7071, 0.7071
    tip = (2.7, 2.7)
    L = 25.2
    wn, wb = 1.45, 2.10      # half width near nib / at back

    def P(t, s):
        return (tip[0] + ux * t - uy * s, tip[1] + uy * t + ux * s)

    def lerp_w(t):
        f = max(0.0, min(1.0, (t - 5.0) / (L - 5.0)))
        return wn + (wb - wn) * f

    pts_r, pts_l = [], []
    for i in range(13):
        t = 5.0 + (L - 5.0) * i / 12.0
        w = lerp_w(t)
        pts_r.append(P(t, -w))
        pts_l.append(P(t, w))
    body = pts_r + [P(L + 1.1, 0.0)] + pts_l[::-1]
    c.paint_poly(body, c.grad(BRAND_L, BRAND_D, 0.35), white=1.05, navy=0.68)

    # clip standing proud on the upper side
    clip = [P(16.2, -lerp_w(16.2) - 0.30), P(L - 1.6, -wb - 0.70),
            P(L - 1.6, -wb - 0.10), P(16.2, -lerp_w(16.2) + 0.42)]
    c.paint_poly(clip, c.grad((240, 246, 255), (158, 178, 238), 0.3), white=0.8, navy=0.55)

    # gold ring
    c.poly([P(9.4, -lerp_w(9.4)), P(12.0, -lerp_w(12.0)), P(12.0, lerp_w(12.0)),
            P(9.4, lerp_w(9.4))], GOLD)
    # nib
    c.poly([P(0.0, 0.0), P(5.2, -wn * 1.02), P(5.2, wn * 1.02)], NAVY)
    c.poly([P(1.1, 0.0), P(4.6, -wn * 0.42), P(4.6, wn * 0.42)], (58, 76, 138, 255))


def art_hand(c):
    """Pointing hand. Fingertip at (13.0, 2.8)."""
    fx = 13.0
    m = c.union(
        c.cap_mask((fx, 3.4), (fx, 13.2), 4.4),             # index finger
        c.cap_mask((10.2, 16.8), (5.9, 13.0), 4.0),         # thumb
        c.rrect_mask(16.2, 10.6, 22.6, 16.8, 2.6),          # knuckles
        c.rrect_mask(9.6, 12.8, 22.2, 26.4, 4.4),           # palm
    )
    c.paint_mask(m, c.grad(CREAM, (203, 217, 255), 0.35), white=1.2, navy=0.78)
    cuff = c.rrect_mask(9.0, 24.6, 22.8, 31.6, 2.4)
    c.paint_mask(cuff, c.grad(BRAND_L, BRAND_D, 0.35), white=1.2, navy=0.8)
    c.heart(15.9, 28.2, 2.3, BLUSH)


def art_pin(c):
    m = c.union(
        c.ell_mask(16, 12.2, 8.7, 8.7),
        c.poly_mask([(8.4, 15.4), (23.6, 15.4), (16, 30.8)]),
    )
    c.paint_mask(m, c.grad(BRAND_L, BRAND_D, 0.35), white=1.35, navy=0.8)
    c.ell(16, 12.0, 3.2, 3.2, WHITE)
    c.ell(16, 12.0, 1.6, 1.6, BRAND)


def art_no(c):
    m = c.ell_mask(16, 16, 11.8, 11.8)
    slash = c.cap_mask((8.4, 8.4), (23.6, 23.6), 3.1)
    c.paint_mask(c.diff(m, slash), c.grad(BRAND_L, BRAND_D, 0.4), white=1.35, navy=0.8)
    c.cap((8.4, 8.4), (23.6, 23.6), 2.5, WHITE)


def art_resize(c, deg):
    c.paint_poly(dbl_arrow_pts(deg=deg), c.grad(BRAND_L, BRAND_D, 0.35),
                 white=1.1, navy=0.7)


def art_move(c):
    c.paint_mask(c.poly_mask(move_pts()), c.grad(BRAND_L, BRAND_D, 0.3),
                 white=1.05, navy=0.65)
    c.ell(16, 16, 1.9, 1.9, WHITE)


def art_uparrow(c):
    pts = [(16, 3.2), (24.6, 12.6), (19.3, 12.6), (19.3, 27.0),
           (12.7, 27.0), (12.7, 12.6), (7.4, 12.6)]
    c.paint_poly(pts, c.grad(BRAND_L, BRAND_D, 0.3), white=1.1, navy=0.7)



def arc_mask(c, cx, cy, R, w, phase, n, span=0.74, ccw=False):
    steps = 30
    segs = []
    for i in range(steps):
        frac = i / steps
        if frac > span:
            continue
        t0 = 2 * math.pi * frac + phase * (2 * math.pi / n) * (-1 if ccw else 1)
        t1 = 2 * math.pi * (i + 1) / steps + phase * (2 * math.pi / n) * (-1 if ccw else 1)
        segs.append(c.cap_mask((cx + math.cos(t0) * R, cy + math.sin(t0) * R),
                               (cx + math.cos(t1) * R, cy + math.sin(t1) * R), w))
    m = segs[0]
    for s in segs[1:]:
        m = c.union(m, s)
    return m


def art_busy(c, phase, n=10):
    m = arc_mask(c, 16, 16, 12.9, 1.95, phase, n, span=0.72)
    c.paint_mask(m, c.grad(BRAND_L, BRAND, 0.5), white=1.0, navy=0.66)
    eyes = "open"
    blink = 0
    if phase in (6, 7):
        blink = 1
    elif phase in (3, 4):
        eyes = "happy"
    girl_head(c, 16, 16, 7.9, blink=blink, eyes=eyes, detail=c.size >= 48)


def art_appstarting(c, phase, n=8):
    c.paint_poly(arrow_pts(s=0.78, org=(1.7, 1.7)),
                 c.grad(BRAND_L, BRAND_D, 0.5), white=1.0, navy=0.64)
    m = arc_mask(c, 23.2, 23.2, 6.1, 1.95, phase, n, span=0.55, ccw=True)
    c.paint_mask(m, c.grad(BRAND_L, BRAND, 0.4), white=1.0, navy=0.64)


# --------------------------------------------------------------- containers ---
def to_cur_image(img, hx, hy):
    w, h = img.size
    px = img.load()
    rows = []
    for y in range(h - 1, -1, -1):
        row = bytearray()
        for x in range(w):
            r, g, b, a = px[x, y]
            row += bytes((b, g, r, a))
        rows.append(bytes(row))
    xor = b"".join(rows)
    stride = ((w + 31) // 32) * 4
    and_mask = b"\x00" * (stride * h)
    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0,
                         len(xor) + len(and_mask), 0, 0, 0, 0)
    data = header + xor + and_mask
    entry = struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, hx, hy, len(data), 0)
    return entry, data


def write_cur(path, items):
    head = struct.pack("<HHH", 0, 2, len(items))
    entries, blobs = b"", []
    offset = 6 + 16 * len(items)
    for img, (hx, hy) in items:
        entry, data = to_cur_image(img, hx, hy)
        entry = entry[:12] + struct.pack("<I", offset) + entry[16:]
        entries += entry
        blobs.append(data)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(head + entries + b"".join(blobs))


def chunk(tag, payload):
    out = tag + struct.pack("<I", len(payload)) + payload
    return out + (b"\x00" if len(payload) & 1 else b"")


def write_ani(path, frames, rates=None, name="DeepSeek Moe"):
    """RIFF/ACON container.

    cSteps MUST equal cFrames: with cSteps = 0 Windows rejects the whole file
    (LoadCursorFromFile returns NULL) and silently falls back to the stock
    pointer.  cBitCount / cPlanes must also be filled in (32 / 1), matching
    what C:\\Windows\\Cursors\\aero_busy.ani ships.
    """
    tmp = os.path.join(os.path.dirname(path), "_f.tmp.cur")
    blobs = []
    for items in frames:
        write_cur(tmp, items)
        blobs.append(open(tmp, "rb").read())
    os.remove(tmp)
    n = len(blobs)
    rates = rates or [5] * n
    jif = int(round(np.mean(rates)))
    anih = struct.pack("<IIIIIIIII", 36, n, n, 0, 0, 32, 1, jif, 1)
    fram = b"".join(chunk(b"icon", b) for b in blobs)
    list_fram = b"LIST" + struct.pack("<I", 4 + len(fram)) + b"fram" + fram
    body = chunk(b"anih", anih) + chunk(b"rate", struct.pack("<%dI" % n, *rates)) + list_fram
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(body)) + b"ACON" + body)


# ------------------------------------------------------------------- build ---
HOTSPOT = {
    "arrow": (2, 2), "help": (2, 2), "appstarting": (2, 2), "busy": (16, 16),
    "cross": (16, 16), "ibeam": (16, 16), "pen": (2, 2), "no": (16, 16),
    "sizens": (16, 16), "sizewe": (16, 16), "sizenwse": (16, 16),
    "sizenesw": (16, 16), "sizeall": (16, 16), "uparrow": (16, 2),
    "hand": (12.8, 2.8), "pin": (16, 30),
}

STATIC = {
    "arrow": art_arrow, "help": art_help, "cross": art_cross, "ibeam": art_ibeam,
    "pen": art_pen, "no": art_no,
    "sizens": lambda c: art_resize(c, 90), "sizewe": lambda c: art_resize(c, 0),
    "sizenwse": lambda c: art_resize(c, 45), "sizenesw": lambda c: art_resize(c, 135),
    "sizeall": art_move, "uparrow": art_uparrow, "hand": art_hand, "pin": art_pin,
}


def hs(key, size):
    hx, hy = HOTSPOT[key]
    k = size / 32.0
    return (int(round(hx * k)), int(round(hy * k)))


def build(outdir, moe=False):
    os.makedirs(outdir, exist_ok=True)
    made = []
    for key, fn in STATIC.items():
        if moe and key == "arrow":
            fn = art_moe_arrow
        items = []
        for size in SIZES:
            c = Canvas(size)
            fn(c)
            items.append((c.out(), hs(key, size)))
        p = os.path.join(outdir, key + ".cur")
        write_cur(p, items)
        made.append(p)

    for name, nf, rate in (("busy", 10, 5), ("appstarting", 8, 6)):
        frames = []
        for ph in range(nf):
            items = []
            for size in SIZES:
                c = Canvas(size)
                if name == "busy":
                    art_busy(c, ph, nf)
                    hx, hy = size // 2, size // 2
                else:
                    art_appstarting(c, ph, nf)
                    hx, hy = hs("arrow", size)
                items.append((c.out(), (hx, hy)))
            frames.append(items)
        p = os.path.join(outdir, name + ".ani")
        write_ani(p, frames, rates=[rate] * nf)
        made.append(p)
    return made


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for d, moe in (("cursors", False), ("cursors_moe", True)):
        files = build(os.path.join(base, d), moe=moe)
        print("%-12s %d files" % (d, len(files)))