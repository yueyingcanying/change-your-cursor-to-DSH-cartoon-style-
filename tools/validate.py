# -*- coding: utf-8 -*-
"""Structural + sanity validation of the generated .cur/.ani files."""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preview import parse_cur, parse_ani  # noqa: E402

ROLE = [("arrow", "Normal"), ("help", "Help"), ("appstarting", "WorkBkg"), ("busy", "Busy"),
        ("cross", "Precision"), ("ibeam", "Text"), ("pen", "Handwriting"), ("no", "Unavail"),
        ("sizens", "SizeNS"), ("sizewe", "SizeWE"), ("sizenwse", "SizeNWSE"),
        ("sizenesw", "SizeNESW"), ("sizeall", "Move"), ("uparrow", "UpArrow"),
        ("hand", "Link"), ("pin", "Pin")]


def tip_distance(img, hs, thresh=160):
    a = np.array(img.getchannel("A"))
    ys, xs = np.nonzero(a > thresh)
    if len(xs) == 0:
        return None
    d = np.hypot(xs - hs[0], ys - hs[1])
    return float(d.min())


def check_dir(d, verbose=True):
    ok = True
    rows = []
    for key, label in ROLE:
        cp = os.path.join(d, key + ".cur")
        ap = os.path.join(d, key + ".ani")
        if os.path.exists(cp):
            items = parse_cur(open(cp, "rb").read())
            sizes = sorted(im.size[0] for im, hs in items)
            need = [32, 48, 64]
            if sizes != need:
                ok = False
                rows.append((key, "FAIL sizes %s" % sizes))
                continue
            for im, hs in items:
                if not (0 <= hs[0] < im.size[0] and 0 <= hs[1] < im.size[1]):
                    ok = False
                    rows.append((key, "FAIL hotspot outside %s" % (hs,)))
                if im.getchannel("A").getextrema()[1] < 200:
                    ok = False
                    rows.append((key, "FAIL nearly empty %d" % im.size[0]))
            d32 = tip_distance([i for i in items if i[0].size[0] == 32][0][0],
                               [i for i in items if i[0].size[0] == 32][0][1])
            rows.append((key, "cur  32/48/64  hotspot=%s  tip-gap=%.1fpx"
                         % ([i[1] for i in items if i[0].size[0] == 32][0], d32 or -1)))
        elif os.path.exists(ap):
            frames, rates, anih = parse_ani(ap)
            if anih is None:
                ok = False
                rows.append((key, "FAIL no anih"))
                continue
            cb, n, csteps = anih[0], anih[1], anih[2]
            if cb != 36 or n != len(frames):
                ok = False
                rows.append((key, "FAIL anih cb=%d frames=%d/%d" % (cb, n, len(frames))))
            for fi, fr in enumerate(frames):
                if sorted(i[0].size[0] for i in fr) != [32, 48, 64]:
                    ok = False
                    rows.append((key, "FAIL frame %d sizes" % fi))
            rows.append((key, "ani  %d frames @%.0fms  multi-res=yes"
                         % (len(frames), (rates[0] if rates else 5) * 1000 / 60)))
        else:
            ok = False
            rows.append((key, "FAIL missing"))
    if verbose:
        print("== %s" % d)
        for k, msg in rows:
            print("   %-12s %s" % (k, msg))
    return ok, rows


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    allok = True
    for d in ("cursors", "cursors_moe"):
        ok, _ = check_dir(os.path.join(base, d))
        allok = allok and ok
    print("RESULT:", "PASS" if allok else "FAIL")
    sys.exit(0 if allok else 1)