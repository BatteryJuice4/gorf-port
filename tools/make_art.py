#!/usr/bin/env python3
"""Generate the game pack artwork (icon.png, banner.png) for this repo.

The images are original, procedurally drawn art (space scene and a generic flying
saucer). They contain nothing from the original game. Output is deterministic.

usage: python3 tools/make_art.py [output_dir]   (default: gamepacks/gorf)
"""
import math
import os
import struct
import sys
import zlib

SS = 2  # supersampling factor for smooth edges


def write_png(path, w, h, rgba):
    rows = b"".join(b"\0" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(rows, 9)))
        f.write(chunk(b"IEND", b""))


def blend(dst, src):
    """src-over blend of RGBA floats (0..1)."""
    a = src[3] + dst[3] * (1 - src[3])
    if a <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    return tuple((src[i] * src[3] + dst[i] * dst[3] * (1 - src[3])) / a for i in range(3)) + (a,)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def saucer(x, y):
    """Saucer in unit coordinates (centered at 0,0, about 2 wide). Returns RGBA or None."""
    col = None
    # glow under the saucer
    g = math.exp(-((x / 0.9) ** 2 + ((y - 0.25) / 0.35) ** 2) * 3)
    if g > 0.02:
        col = (0.4, 0.9, 1.0, 0.35 * g)
    # dome
    if x * x / 0.16 + (y + 0.18) ** 2 / 0.12 < 1 and y < -0.05:
        shine = max(0.0, 1 - math.hypot(x + 0.12, y + 0.35) * 3)
        col = blend(col or (0, 0, 0, 0), (0.55 + 0.4 * shine, 0.85 + 0.15 * shine, 1.0, 0.92))
    # body: flattened ellipse with a darker rim
    e = x * x / 1.0 + y * y / 0.06
    if e < 1:
        t = (y + 0.25) / 0.5
        base = lerp((0.85, 0.87, 0.92), (0.35, 0.37, 0.45), max(0.0, min(1.0, t)))
        if e > 0.82:
            base = lerp(base, (0.15, 0.15, 0.2), 0.6)
        col = blend(col or (0, 0, 0, 0), base + (1.0,))
        # row of lights
        for i in range(-3, 4):
            lx = i * 0.24
            if math.hypot(x - lx, y - 0.02) < 0.05:
                col = (1.0, 0.75 if i % 2 else 0.35, 0.2, 1.0)
    return col


def banner(w, h):
    W, H = w * SS, h * SS
    # deterministic stars (simple LCG)
    seed = 12345
    stars = []
    for _ in range(170):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        sx = seed % W
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        sy = seed % H
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        stars.append((sx, sy, 0.4 + (seed % 100) / 160.0, 1 + (seed % 3)))
    star_map = {}
    for sx, sy, b, r in stars:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d = math.hypot(dx, dy)
                if d <= r:
                    k = (sx + dx, sy + dy)
                    star_map[k] = max(star_map.get(k, 0), b * (1 - d / (r + 0.5)))
    px = [None] * (W * H)
    planet_c, planet_r = (W * 0.84, H * 0.95), H * 0.55
    for Y in range(H):
        for X in range(W):
            t = Y / H
            c = lerp((0.03, 0.02, 0.10), (0.20, 0.05, 0.25), t) + (1.0,)
            s = star_map.get((X, Y))
            if s:
                c = blend(c, (1.0, 1.0, 0.95, s))
            # ringed planet
            dx, dy = X - planet_c[0], Y - planet_c[1]
            d = math.hypot(dx, dy)
            if d < planet_r:
                light = max(0.0, 1 - math.hypot(dx + planet_r * 0.5, dy + planet_r * 0.6) / (planet_r * 1.6))
                band = 0.5 + 0.5 * math.sin(dy / (planet_r * 0.09))
                pc = lerp((0.35, 0.12, 0.10), (0.95, 0.55, 0.25), light * (0.8 + 0.2 * band))
                c = blend(c, pc + (1.0,))
            ring = (dx / (planet_r * 1.7)) ** 2 + (dy / (planet_r * 0.32)) ** 2
            if 0.82 < ring < 1.0 and (dy > -planet_r * 0.05 or d > planet_r):
                c = blend(c, (0.95, 0.8, 0.55, 0.75))
            # saucer, left of center
            sx = (X - W * 0.30) / (H * 0.32)
            sy = (Y - H * 0.45) / (H * 0.32)
            sc = saucer(sx, sy)
            if sc:
                c = blend(c, sc)
            # laser beam from the saucer
            if W * 0.30 + H * 0.36 < X < W * 0.70 and abs(Y - (H * 0.47 + (X - W * 0.3) * 0.08)) < SS * 1.2:
                c = blend(c, (1.0, 0.3, 0.4, 0.9))
            px[Y * W + X] = c
    return downsample(px, W, H, w, h)


def icon(size):
    W = size * SS
    px = [None] * (W * W)
    for Y in range(W):
        for X in range(W):
            x = (X - W / 2) / (W / 2)
            y = (Y - W / 2) / (W / 2)
            d = math.hypot(x, y)
            c = (0.0, 0.0, 0.0, 0.0)
            if d < 0.97:
                c = lerp((0.22, 0.06, 0.30), (0.04, 0.02, 0.12), d) + (1.0,)
                if d > 0.90:
                    c = (0.95, 0.55, 0.25, 1.0)
            sc = saucer(x / 0.72, y / 0.72)
            if sc and d < 0.97:
                c = blend(c, sc)
            px[Y * W + X] = c
    return downsample(px, W, W, size, size)


def downsample(px, W, H, w, h):
    out = bytearray(w * h * 4)
    n = SS * SS
    for y in range(h):
        for x in range(w):
            acc = [0.0, 0.0, 0.0, 0.0]
            for dy in range(SS):
                for dx in range(SS):
                    c = px[(y * SS + dy) * W + x * SS + dx]
                    acc[0] += c[0] * c[3]
                    acc[1] += c[1] * c[3]
                    acc[2] += c[2] * c[3]
                    acc[3] += c[3]
            a = acc[3] / n
            i = (y * w + x) * 4
            if acc[3] > 0:
                out[i:i + 3] = bytes(min(255, int(acc[k] / acc[3] * 255 + 0.5)) for k in range(3))
            out[i + 3] = min(255, int(a * 255 + 0.5))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "gamepacks", "gorf")
    os.makedirs(out, exist_ok=True)
    write_png(os.path.join(out, "icon.png"), 256, 256, icon(256))
    write_png(os.path.join(out, "banner.png"), 600, 150, banner(600, 150))
    print("wrote", os.path.join(out, "icon.png"), "and banner.png")


if __name__ == "__main__":
    main()
