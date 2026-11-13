#!/usr/bin/env python3
"""SongReel engine: customer photos + Suno song + greetings + designed captions -> vertical video.

Usage:
  python3 songreel.py order.json out.mp4 [--preview] [--fps 30]

order.json fields (all optional except photos + audio):
  to, from, occasion, language (en|hi|kn|ta|te), theme (gold|rose|royal|saffron),
  title, subtitle, header, brand,
  photos: [paths], extras: [paths of decor/background images],
  wishes: [short greeting lines inserted as designed cards],
  audio: path, lyrics_lrc: path to .lrc  OR  lyrics: [{"t":12.5,"text":"..."}]  OR  lyrics_text: "line\\nline" (auto-timed, approximate)
"""
import json, sys, os, math, subprocess, argparse, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
FONTS = {
    "en": dict(title=("Pacifico.ttf", 0), body=("Poppins-Bold.ttf", 0), soft=("Poppins-Medium.ttf", 0), wish=("PlayfairDisplay.ttf", 700)),
    "hi": dict(all="NotoSansDevanagari.ttf"), "kn": dict(all="NotoSansKannada.ttf"),
    "ta": dict(all="NotoSansTamil.ttf"), "te": dict(all="NotoSansTelugu.ttf"),
}
THEMES = {
    "gold": dict(c1=(32, 10, 48), c2=(120, 42, 84), accent=(255, 210, 115)),
    "rose": dict(c1=(62, 10, 34), c2=(170, 52, 96), accent=(255, 196, 206)),
    "royal": dict(c1=(10, 20, 64), c2=(46, 66, 150), accent=(255, 226, 150)),
    "saffron": dict(c1=(84, 22, 6), c2=(206, 86, 22), accent=(255, 232, 160)),
}
LATIN_FALLBACK = os.path.join(FD, "Poppins-Bold.ttf")


def ease(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def lerp(a, b, t): return a + (b - a) * t


def font(lang, kind, size):
    f = FONTS.get(lang, FONTS["en"])
    if "all" in f:
        path, w = os.path.join(FD, f["all"]), 700 if kind in ("title", "body", "wish") else 500
    else:
        name, w = f.get(kind, f["body"]); path = os.path.join(FD, name)
    ft = ImageFont.truetype(path, size)
    try:
        axes = ft.get_variation_axes(); vals = []
        for a in axes:
            n = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
            vals.append(min(max(w or a["default"], a["minimum"]), a["maximum"]) if n == "Weight" else a["default"])
        ft.set_variation_by_axes(vals)
    except Exception:
        pass
    return ft


def wrap(text, ft, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if ft.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def text_layer(text, ft, W, color, stroke=0, glow=None, gap=1.3, pad=30):
    lines = []
    for para in text.split("\n"): lines += wrap(para, ft, W - 2 * pad)
    lh = int(ft.size * gap); H = lh * len(lines) + 2 * pad
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        x = (W - ft.getlength(ln)) / 2; y = pad + i * lh
        d.text((x, y), ln, font=ft, fill=color + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
    if glow:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        for i, ln in enumerate(lines):
            gd.text(((W - ft.getlength(ln)) / 2, pad + i * lh), ln, font=ft, fill=glow + (200,))
        g = g.filter(ImageFilter.GaussianBlur(ft.size * 0.28))
        im = Image.alpha_composite(g, im)
    return np.asarray(im).copy()  # RGBA


def blend_rgba(dst, layer, x, y, alpha=1.0):
    """dst BGR uint8 in-place; layer RGBA uint8 (RGB order)."""
    H, W = dst.shape[:2]; h, w = layer.shape[:2]
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0 or alpha <= 0: return
    sub = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = (sub[:, :, 3:4].astype(np.float32) / 255.0) * alpha
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (d * (1 - a) + sub[:, :, 2::-1].astype(np.float32) * a).astype(np.uint8)


def load_photo(p):
    im = ImageOps.exif_transpose(Image.open(p)).convert("RGB"); im.thumbnail((1800, 1800))
    return np.asarray(im)[:, :, ::-1].copy()


_cascade = None
def focus_point(img):
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(os.path.join(HERE, "haarcascade_frontalface_default.xml"))
    h, w = img.shape[:2]; s = 640 / max(h, w)
    g = cv2.cvtColor(cv2.resize(img, None, fx=s, fy=s), cv2.COLOR_BGR2GRAY)
    try:
        f = _cascade.detectMultiScale(g, 1.15, 5, minSize=(40, 40))
    except Exception:
        f = []
    if len(f):
        x0 = min(a[0] for a in f); y0 = min(a[1] for a in f); x1 = max(a[0] + a[2] for a in f); y1 = max(a[1] + a[3] for a in f)
        return ((x0 + x1) / 2 / (g.shape[1]), (y0 + y1) / 2 / (g.shape[0]))
    return (0.5, 0.42)


def crop_to(img, out_w, out_h, zoom, center):
    """Smooth sub-pixel crop of img (cover) zoomed, centered near `center` (px), resized to out."""
    h, w = img.shape[:2]; ca = out_w / out_h
    cw, ch = (h * ca, h) if w / h > ca else (w, w / ca)
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(center[0], cw / 2), w - cw / 2); cy = min(max(center[1], ch / 2), h - ch / 2)
    s = out_w / cw
    M = np.float32([[s, 0, -(cx - cw / 2) * s], [0, s, -(cy - ch / 2) * s]])
    return cv2.warpAffine(img, M, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class Theme:
    def __init__(s, name, W, H):
        t = THEMES.get(name, THEMES["gold"]); s.c1, s.c2, s.accent = t["c1"], t["c2"], t["accent"]
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        c1 = np.array(s.c1[::-1], np.float32); c2 = np.array(s.c2[::-1], np.float32)
        s.grad = np.repeat(c1 + (c2 - c1) * yy, W, axis=1).astype(np.uint8)
        yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xv - W / 2) / (W * 0.75)) ** 2 + ((yv - H / 2) / (H * 0.75)) ** 2)
        s.vig = (1 - 0.55 * np.clip(d - 0.35, 0, 1) ** 1.3)[:, :, None].astype(np.float32)


class Sparkles:
    def __init__(s, W, H, color, n=26, seed=1):
        r = random.Random(seed); s.W, s.H, s.n = W, H, n
        s.p = [(r.random(), r.random(), r.uniform(0.02, 0.07), r.uniform(0, 6.28), r.choice([0, 1, 1, 2]), r.uniform(0.5, 1.0)) for _ in range(n)]
        s.sprites = []
        for rad in (7, 14, 26):
            R = int(rad * W / 720); k = np.zeros((2 * R + 1, 2 * R + 1), np.float32)
            yy, xx = np.mgrid[-R:R + 1, -R:R + 1]; k = np.exp(-(xx ** 2 + yy ** 2) / (2 * (R / 2.2) ** 2))
            s.sprites.append((k[:, :, None] * np.array(color[::-1], np.float32)[None, None, :] / 255.0, R))

    def draw(s, frame, t, boost=0.0):
        f = frame.astype(np.float32)
        for (x, y, sp, ph, sz, br) in s.p:
            px = int((x + 0.03 * math.sin(t * 0.6 + ph)) * s.W); py = int(((y - sp * t) % 1.0) * s.H)
            k, R = s.sprites[sz]
            tw = 0.55 + 0.45 * math.sin(t * 2.2 + ph) + boost * 0.6
            x0, y0 = px - R, py - R; x1, y1 = px + R + 1, py + R + 1
            cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, s.W), min(y1, s.H)
            if cx1 <= cx0 or cy1 <= cy0: continue
            f[cy0:cy1, cx0:cx1] += k[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0] * (255 * 0.8 * br * max(tw, 0.1))
        np.clip(f, 0, 255, out=f); return f.astype(np.uint8)


class Ctx:
    def __init__(s, o, W, H, fps, total):
        s.o, s.W, s.H, s.fps, s.total = o, W, H, fps, total
        s.lang = o.get("language", "en"); s.theme = Theme(o.get("theme", "gold"), W, H)
        s.scale = W / 1080.0
        s.spark = Sparkles(W, H, s.theme.accent)
        occ = (o.get("occasion") or "birthday").lower()
        default_fx = dict(birthday=["balloons", "confetti"], anniversary=["hearts", "petals"], wedding=["hearts", "petals"], diwali=["petals"],
                          devotional=["petals"], love=["hearts"], festival=["confetti", "petals"]).get(occ, ["confetti"])
        s.fx = FX(s, o.get("fx", default_fx))
        s.header = None
        if o.get("header"):
            s.header = text_layer(o["header"], font(s.lang, "soft", int(38 * s.scale)), W, s.theme.accent, stroke=0, glow=s.theme.accent, pad=int(10 * s.scale))

    def F(s, kind, px): return font(s.lang, kind, max(8, int(px * s.scale)))


def blurred_bg(img, W, H, dark=0.5, tint=None, tint_a=0.25):
    big = crop_to(img, int(W * 1.18), int(H * 1.18), 1.0, (img.shape[1] / 2, img.shape[0] / 2))
    big = cv2.GaussianBlur(big, (0, 0), W / 22)
    big = (big.astype(np.float32) * dark)
    if tint is not None: big = big * (1 - tint_a) + np.array(tint[::-1], np.float32) * tint_a
    return np.clip(big, 0, 255).astype(np.uint8)


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255); return np.asarray(m) > 127



# ------------------------------------------------------------------ v2 graphics
def _rot_variants(im, n=8):
    return [np.asarray(im.rotate(i * 360 / n, resample=Image.BICUBIC, expand=True)).copy() for i in range(n)]


def sprite_heart(size, col):
    S = size * 4; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); pts = []
    for i in range(240):
        t = i / 240 * 2 * math.pi; x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((S / 2 + x * S / 38, S / 2.15 - y * S / 38))
    d.polygon(pts, fill=col + (235,)); d.ellipse([S * .26, S * .2, S * .4, S * .3], fill=(255, 255, 255, 120))
    return im.resize((size, size), Image.LANCZOS)


def sprite_balloon(size, col):
    W, Hh = size * 4, int(size * 1.7) * 4; im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    bw, bh = W, int(W * 1.18); d.ellipse([0, 0, bw - 1, bh - 1], fill=col + (240,))
    d.polygon([(W / 2, bh - 2), (W / 2 - W * .07, bh + W * .1), (W / 2 + W * .07, bh + W * .1)], fill=col + (240,))
    d.ellipse([W * .18, W * .14, W * .38, W * .4], fill=(255, 255, 255, 110))
    d.line([(W / 2, bh + W * .1), (W / 2 + W * .05, Hh - 1)], fill=(255, 255, 255, 150), width=max(2, W // 60))
    return im.resize((size, int(size * 1.7)), Image.LANCZOS)


def sprite_petal(size, col):
    S = size * 4; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([S * .1, S * .3, S * .9, S * .7], fill=col + (240,)); d.ellipse([S * .25, S * .4, S * .8, S * .6], fill=tuple(min(255, c + 45) for c in col) + (200,))
    return im.resize((size, size), Image.LANCZOS)


def sprite_confetti(size, col):
    S = size * 3; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([S * .1, S * .35, S * .9, S * .65], fill=col + (245,)); return im.resize((size, size), Image.LANCZOS)


FX_PAL = {"confetti": [(255, 90, 120), (255, 200, 60), (90, 200, 255), (160, 120, 255), (120, 230, 150)],
          "balloons": [(255, 90, 120), (255, 190, 50), (80, 190, 255), (170, 120, 255), (90, 220, 140)],
          "hearts": [(255, 90, 130), (255, 140, 170), (230, 50, 90), (255, 190, 205)],
          "petals": [(255, 150, 20), (255, 190, 40), (240, 110, 20), (255, 215, 90)]}
FX_COUNT = {"confetti": 30, "balloons": 8, "hearts": 13, "petals": 22}


class FX:
    def __init__(s, ctx, kinds, seed=3):
        r = random.Random(seed); s.W, s.H = ctx.W, ctx.H; s.items = []; s.sc = ctx.scale
        for kind in kinds:
            if kind not in FX_PAL: continue
            for i in range(FX_COUNT[kind]):
                col = r.choice(FX_PAL[kind]); sz = int(r.uniform(34, 70) * ctx.scale) if kind != "confetti" else int(r.uniform(22, 36) * ctx.scale)
                if kind == "balloons": sz = int(r.uniform(70, 120) * ctx.scale)
                fn = dict(hearts=sprite_heart, balloons=sprite_balloon, petals=sprite_petal, confetti=sprite_confetti)[kind]
                im = fn(sz, col); vars_ = [np.asarray(im).copy()] if kind in ("balloons", "hearts") else _rot_variants(im)
                xx = r.random()
                if kind in ("balloons", "hearts"): xx = r.choice([0.02 + 0.1 * r.random(), 0.88 - 0.02 + 0.1 * r.random()])
                s.items.append(dict(kind=kind, vars=vars_, x=xx, y=r.random(), sp=r.uniform(.04, .12) if kind != "confetti" else r.uniform(.12, .26),
                                    ph=r.uniform(0, 6.28), rs=r.uniform(.6, 1.6), up=kind in ("balloons", "hearts"), sw=r.uniform(.01, .03) if kind in ("balloons", "hearts") else r.uniform(.02, .06)))

    def draw(s, frame, t, pulse=0.0):
        for it in s.items:
            v = it["vars"]; im = v[int((t * it["rs"] * 2 + it["ph"]) * 2) % len(v)] if len(v) > 1 else v[0]
            h, w = im.shape[:2]; k = (it["y"] + (-1 if it["up"] else 1) * it["sp"] * t) % 1.0
            y = int(k * (s.H + 2 * h) - h); x = int((it["x"] + it["sw"] * math.sin(t * .9 + it["ph"])) * s.W - w / 2)
            blend_rgba(frame, im, x, y, 0.95)


_rays_cache = {}
def rays_layer(ctx, S, color, n=14):
    key = (S, color, n)
    if key not in _rays_cache:
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = S / 2
        for i in range(n):
            a0 = i * 2 * math.pi / n; a1 = a0 + math.pi / n * 0.85
            d.polygon([(c, c), (c + S * math.cos(a0), c + S * math.sin(a0)), (c + S * math.cos(a1), c + S * math.sin(a1))], fill=color + (95,))
        arr = np.asarray(im).copy(); yy, xx = np.mgrid[0:S, 0:S]; r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / c
        arr[:, :, 3] = (arr[:, :, 3] * np.clip(1 - r, 0, 1) ** 0.55).astype(np.uint8); _rays_cache[key] = arr
    return _rays_cache[key]


def draw_rays(frame, ctx, cx, cy, t, pulse=0.0, alpha=1.0):
    S = int(ctx.H * 1.15); R = rays_layer(ctx, S, ctx.theme.accent)
    M = cv2.getRotationMatrix2D((S / 2, S / 2), t * 7.0, 1.0 + 0.04 * pulse); M[0, 2] += cx - S / 2; M[1, 2] += cy - S / 2
    w = cv2.warpAffine(R, M, (ctx.W, ctx.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    blend_rgba(frame, w, 0, 0, alpha)


def make_card(ctx, cw, ch):
    c = ctx; m = int(46 * c.scale); b = int(16 * c.scale); tw, th = cw + 2 * b + 2 * m, ch + 2 * b + 2 * m
    sh = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
    d.rounded_rectangle([m, m + int(14 * c.scale), tw - m, th - m + int(14 * c.scale)], int(26 * c.scale), fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(m * 0.45)); d = ImageDraw.Draw(sh)
    d.rounded_rectangle([m, m, tw - m, th - m], int(22 * c.scale), fill=(255, 250, 240, 255), outline=c.theme.accent + (255,), width=max(2, int(4 * c.scale)))
    return dict(tpl=np.asarray(sh).copy(), inner=rounded_mask(cw, ch, int(12 * c.scale)), m=m, b=b, tw=tw, th=th, cw=cw, ch=ch)


def place_card(frame, K, ph, cx, cy, ang, sc, alpha=1.0):
    card = K["tpl"].copy(); m, b, cw, ch = K["m"], K["b"], K["cw"], K["ch"]
    reg = card[m + b:m + b + ch, m + b:m + b + cw]; reg[K["inner"], :3] = ph[:, :, ::-1][K["inner"]]; reg[K["inner"], 3] = 255
    tw, th = K["tw"], K["th"]; rad = math.radians(abs(ang)); bw = int((tw * math.cos(rad) + th * math.sin(rad)) * sc) + 4; bh = int((tw * math.sin(rad) + th * math.cos(rad)) * sc) + 4
    M = cv2.getRotationMatrix2D((tw / 2, th / 2), ang, sc); M[0, 2] += bw / 2 - tw / 2; M[1, 2] += bh / 2 - th / 2
    w = cv2.warpAffine(card, M, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    blend_rgba(frame, w, int(cx - bw / 2), int(cy - bh / 2), alpha)


def karaoke_layer(text, ft, W, col, hi, stroke, pad):
    """returns base RGBA, highlight RGBA, word boxes [(x0,y0,x1,y1)] in reading order."""
    lines = []
    for para in text.split("\n"): lines += wrap(para, ft, W - 2 * pad)
    lh = int(ft.size * 1.3); H = lh * len(lines) + 2 * pad
    mk = lambda c: Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base, high, glow = mk(0), mk(0), mk(0); db, dh, dg = ImageDraw.Draw(base), ImageDraw.Draw(high), ImageDraw.Draw(glow); boxes = []
    for i, ln in enumerate(lines):
        x0 = (W - ft.getlength(ln)) / 2; y = pad + i * lh; ws = ln.split(" ")
        for j, w in enumerate(ws):
            pre = (" ".join(ws[:j]) + (" " if j else "")); x = x0 + ft.getlength(pre); wl = ft.getlength(w)
            db.text((x, y), w, font=ft, fill=col + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 210))
            dh.text((x, y), w, font=ft, fill=hi + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 210)); dg.text((x, y), w, font=ft, fill=hi + (230,))
            boxes.append((int(x) - stroke - 4, y - 6, int(x + wl) + stroke + 4, y + lh))
    glow = glow.filter(ImageFilter.GaussianBlur(ft.size * 0.25)); high = Image.alpha_composite(glow, high)
    return np.asarray(base).copy(), np.asarray(high).copy(), boxes


# ------------------------------------------------------------------ slides
class PhotoSlide:
    kind = "photo"

    def __init__(s, ctx, img, idx, focus):
        s.c, s.img, s.idx, s.focus = ctx, img, idx, focus; s.ready = False

    def prepare(s):
        c = s.c; W, H = c.W, c.H; h, w = s.img.shape[:2]; a = w / h
        s.bleed = a <= 0.62
        s.bg = blurred_bg(s.img, W, H, 0.55, c.theme.c2, 0.28)
        s.rev = s.idx % 2 == 1; s.angle = (-2.2, 2.0, -1.4, 2.6)[s.idx % 4]
        if not s.bleed:
            ca = min(max(a, 0.74), 1.22); s.cw = int(W * 0.84); s.ch = int(s.cw / ca)
            maxh = int(H * 0.60)
            if s.ch > maxh: s.ch = maxh; s.cw = int(s.ch * ca)
            m = int(46 * c.scale); b = int(16 * c.scale); s.m, s.b = m, b
            tw, th = s.cw + 2 * b + 2 * m, s.ch + 2 * b + 2 * m
            sh = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
            d.rounded_rectangle([m, m + int(14 * c.scale), tw - m, th - m + int(14 * c.scale)], int(26 * c.scale), fill=(0, 0, 0, 150))
            sh = sh.filter(ImageFilter.GaussianBlur(m * 0.45))
            d = ImageDraw.Draw(sh)
            d.rounded_rectangle([m, m, tw - m, th - m], int(22 * c.scale), fill=(255, 250, 240, 255), outline=c.theme.accent + (255,), width=max(2, int(4 * c.scale)))
            s.tpl = np.asarray(sh).copy()
            s.inner = rounded_mask(s.cw, s.ch, int(12 * c.scale))
            s.tw, s.th = tw, th

    def release(s): s.bg = None; s.tpl = None; s.ready = False

    def render(s, t, dur, pulse):
        if not s.ready: s.prepare(); s.ready = True
        c = s.c; W, H = c.W, c.H; u = t / max(dur, 1e-6)
        uu = 1 - u if s.rev else u
        zoom = lerp(1.0, 1.14, ease(uu)); fx, fy = s.focus; h, w = s.img.shape[:2]
        cen = (lerp(w / 2, fx * w, ease(uu)), lerp(h / 2, fy * h, ease(uu)))
        # moving blurred bg
        bw, bh = s.bg.shape[1], s.bg.shape[0]
        ox = int((bw - W) * (0.5 + 0.5 * math.sin(u * 2.0 + s.idx))); oy = int((bh - H) * u)
        frame = s.bg[oy:oy + H, ox:ox + W].copy()
        if s.bleed:
            ph = crop_to(s.img, W, H, zoom * (1 + 0.012 * pulse), cen)
            grad = np.linspace(1.0, 0.42, H, dtype=np.float32)[:, None, None]
            grad[:int(H * 0.55)] = 1.0; grad[int(H * 0.55):, :, :] = np.linspace(1.0, 0.45, H - int(H * 0.55), dtype=np.float32)[:, None, None]
            frame = np.clip(ph.astype(np.float32) * grad, 0, 255).astype(np.uint8)
        else:
            ph = crop_to(s.img, s.cw, s.ch, zoom, cen)
            card = s.tpl.copy()
            reg = card[s.m + s.b:s.m + s.b + s.ch, s.m + s.b:s.m + s.b + s.cw]
            reg[s.inner, :3] = ph[:, :, ::-1][s.inner]; reg[s.inner, 3] = 255
            e = ease(t / 0.8)
            sc = (0.86 + 0.14 * e) * (1 + 0.018 * pulse)
            ang = s.angle * (1 + 1.8 * (1 - e)) + 0.5 * math.sin(t * 1.1)
            cx = W / 2; cy = H * 0.455 + (1 - e) * H * 0.07 + 6 * c.scale * math.sin(t * 1.3)
            M = cv2.getRotationMatrix2D((s.tw / 2, s.th / 2), ang, sc); M[0, 2] += cx - s.tw / 2; M[1, 2] += cy - s.th / 2
            warped = cv2.warpAffine(card, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            a = warped[:, :, 3:4].astype(np.float32) / 255.0
            frame = (frame.astype(np.float32) * (1 - a) + warped[:, :, 2::-1].astype(np.float32) * a).astype(np.uint8)
        return frame


class CardSlide:
    kind = "card"

    def __init__(s, ctx, text, bg_img=None, big=True, medallion=None, sub=None, brand=None, title_font="wish"):
        s.c, s.text, s.bg_img, s.medal, s.sub, s.brand, s.tf = ctx, text, bg_img, medallion, sub, brand, title_font; s.ready = False
        s.big = big

    def prepare(s):
        c = s.c; W, H = c.W, c.H; acc = c.theme.accent
        if s.bg_img is not None: s.bg = blurred_bg(s.bg_img, W, H, 0.5, c.theme.c1, 0.45)[:H, :W].copy()
        else: s.bg = c.theme.grad.copy()
        size = 92 if s.big else 70
        if len(s.text) > 40: size = int(size * 0.8)
        s.tl = text_layer(s.text, c.F(s.tf, size), W, (255, 255, 255), stroke=int(2 * c.scale), glow=acc, pad=int(W * 0.1))
        s.sl = text_layer(s.sub, c.F("soft", 44), W, acc, glow=acc, pad=int(10 * c.scale)) if s.sub else None
        s.bl = text_layer(s.brand, c.F("soft", 36), W, (255, 255, 255), pad=int(10 * c.scale)) if s.brand else None
        s.mimg = None
        if s.medal is not None:
            D = int(W * 0.50); ph = crop_to(s.medal[0], D, D, 1.05, (s.medal[0].shape[1] * s.medal[1][0], s.medal[0].shape[0] * s.medal[1][1]))
            m = Image.new("L", (D, D), 0); ImageDraw.Draw(m).ellipse([0, 0, D - 1, D - 1], fill=255)
            pad = int(24 * c.scale); R = Image.new("RGBA", (D + 2 * pad, D + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(R)
            d.ellipse([0, 0, D + 2 * pad - 1, D + 2 * pad - 1], fill=acc + (255,)); d.ellipse([int(8 * c.scale)] * 2 + [D + 2 * pad - 1 - int(8 * c.scale)] * 2, fill=(60, 20, 40, 255))
            R.paste(Image.fromarray(ph[:, :, ::-1]), (pad, pad), m)
            s.mimg = np.asarray(R).copy()

    def release(s): s.bg = None; s.ready = False

    def render(s, t, dur, pulse):
        if not s.ready: s.prepare(); s.ready = True
        c = s.c; W, H = c.W, c.H
        zs = 1.0 + 0.06 * (t / max(dur, 1e-6)); M = np.float32([[zs, 0, W * (1 - zs) / 2], [0, zs, H * (1 - zs) / 2]])
        frame = cv2.warpAffine(s.bg, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        ytxt = 0.40 if s.mimg is None else 0.57
        e0 = ease(t / 0.9)
        draw_rays(frame, c, W / 2, H * 0.40 if s.mimg is None else H * 0.12 + s.mimg.shape[0] / 2, t, pulse, 0.55 * e0)
        if s.mimg is not None:
            e = ease(t / 0.9); mh = s.mimg.shape[0]
            blend_rgba(frame, s.mimg, (W - s.mimg.shape[1]) // 2, int(H * 0.12 + (1 - e) * 40), alpha=e)
        e1 = ease((t - 0.2) / 0.8); th = s.tl.shape[0]
        blend_rgba(frame, s.tl, 0, int(H * ytxt - th / 2 + (1 - e1) * 40), alpha=e1 * (1 + 0.0 * pulse))
        if s.sl is not None:
            e2 = ease((t - 0.7) / 0.8); blend_rgba(frame, s.sl, 0, int(H * ytxt + th / 2 + 10 * c.scale + (1 - e2) * 30), alpha=e2)
        if s.bl is not None:
            e3 = ease((t - 1.3) / 0.8); blend_rgba(frame, s.bl, 0, int(H * 0.90), alpha=e3 * 0.9)
        return frame



class MedalSlide:
    kind = "photo"

    def __init__(s, ctx, img, idx, focus): s.c, s.img, s.idx, s.focus, s.ready = ctx, img, idx, focus, False

    def prepare(s):
        c = s.c; W, H = c.W, c.H; D = int(W * 0.80); s.D = D; pad = int(26 * c.scale); s.bg = c.theme.grad.copy()
        mi = Image.new("L", (D, D), 0); ImageDraw.Draw(mi).ellipse([0, 0, D - 1, D - 1], fill=255); s.m = np.asarray(mi) > 127
        n = D + 2 * pad; R = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(R); g = int(10 * c.scale)
        d.ellipse([0, 0, n - 1, n - 1], fill=c.theme.accent + (255,)); d.ellipse([pad - g, pad - g, n - 1 - pad + g, n - 1 - pad + g], fill=(0, 0, 0, 0))
        s.ring = np.asarray(R).copy(); s.pad = pad

    def release(s): s.bg = None; s.ready = False

    def render(s, t, dur, pulse):
        if not s.ready: s.prepare(); s.ready = True
        c = s.c; W, H = c.W, c.H; D = s.D; u = t / max(dur, 1e-6); h, w = s.img.shape[:2]; fx, fy = s.focus
        frame = s.bg.copy(); cy = H * 0.46
        draw_rays(frame, c, W / 2, cy, t + s.idx * 3, pulse, 0.9)
        zoom = lerp(1.0, 1.18, ease(u)); ph = crop_to(s.img, D, D, zoom, (lerp(w / 2, fx * w, ease(u)), lerp(h / 2, fy * h, ease(u))))
        e = ease(t / 0.9); sc = (0.7 + 0.3 * e) * (1 + 0.025 * pulse); n = D + 2 * s.pad
        disc = np.zeros((n, n, 4), np.uint8); inner = disc[s.pad:s.pad + D, s.pad:s.pad + D]
        inner[s.m, :3] = ph[:, :, ::-1][s.m]; inner[s.m, 3] = 255
        ra = s.ring[:, :, 3:4] > 0; disc[:, :, :3] = np.where(ra, s.ring[:, :, :3], disc[:, :, :3]); disc[:, :, 3] = np.maximum(disc[:, :, 3], s.ring[:, :, 3])
        M = cv2.getRotationMatrix2D((n / 2, n / 2), 4 * math.sin(t * 0.8) * (1 - 0.5 * e), sc); M[0, 2] += W / 2 - n / 2; M[1, 2] += cy - n / 2
        w_ = cv2.warpAffine(disc, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)); blend_rgba(frame, w_, 0, 0, e)
        return frame


class CollageSlide:
    kind = "photo"
    SPOTS = [(0.36, 0.28, -6.0, (-1.0, 0.0)), (0.64, 0.47, 5.0, (1.0, 0.0)), (0.40, 0.66, -3.0, (0.0, 1.0))]

    def __init__(s, ctx, imgs, foci, idx): s.c, s.imgs, s.foci, s.idx, s.ready = ctx, imgs, foci, idx, False

    def prepare(s):
        c = s.c; cw = int(c.W * 0.56); ch = int(cw * 1.2); s.K = make_card(c, cw, ch); s.bg = blurred_bg(s.imgs[0], c.W, c.H, 0.5, c.theme.c2, 0.3)[:c.H, :c.W].copy()

    def release(s): s.bg = None; s.ready = False

    def render(s, t, dur, pulse):
        if not s.ready: s.prepare(); s.ready = True
        c = s.c; W, H = c.W, c.H; frame = s.bg.copy(); u = t / max(dur, 1e-6)
        for i, (img, f) in enumerate(zip(s.imgs, s.foci)):
            x, y, ang, (dx, dy) = s.SPOTS[i]; e = ease((t - 0.35 * i) / 0.8)
            h, w = img.shape[:2]; z = lerp(1.0, 1.12, ease(u))
            ph = crop_to(img, s.K["cw"], s.K["ch"], z, (lerp(w / 2, f[0] * w, ease(u)), lerp(h / 2, f[1] * h, ease(u))))
            cx = x * W + dx * (1 - e) * W * 0.9; cy = y * H + dy * (1 - e) * H * 0.5
            place_card(frame, s.K, ph, cx, cy + 5 * c.scale * math.sin(t * 1.2 + i), ang * (1 + (1 - e) * 2), (0.9 + 0.1 * e) * (1 + 0.012 * pulse))
        return frame


# ------------------------------------------------------------------ audio / lyrics
def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "22050", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32), 22050


def analyse(y, sr, fps, nframes):
    hop = sr // fps; n = len(y) // hop
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(axis=1)); rms /= rms.max() + 1e-9
    avg = np.convolve(rms, np.ones(12) / 12, mode="same"); on = np.clip(rms - avg, 0, None); on /= on.max() + 1e-9
    p = np.zeros(nframes); v = 0.0
    for i in range(nframes):
        v = max(v * 0.86, on[i] if i < len(on) else 0.0); p[i] = v
    return p, on


def parse_lrc(path):
    out = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if ln.startswith("[") and "]" in ln:
            tag, txt = ln[1:].split("]", 1)
            try: mm, ss = tag.split(":"); out.append({"t": int(mm) * 60 + float(ss), "text": txt.strip()})
            except ValueError: pass
    return [x for x in out if x["text"]]


def lyric_events(o, start, end):
    ev = []
    if o.get("lyrics_lrc") and os.path.exists(o["lyrics_lrc"]): ev = parse_lrc(o["lyrics_lrc"])
    elif o.get("lyrics"): ev = [dict(x) for x in o["lyrics"]]
    elif o.get("lyrics_text"):
        lines = [l.strip() for l in o["lyrics_text"].split("\n") if l.strip() and not l.strip().startswith("[")]
        wts = np.array([max(len(l), 12) for l in lines], float); wts /= wts.sum(); t = start
        for l, w in zip(lines, wts): ev.append({"t": t, "text": l}); t += w * (end - start)
    for i, e in enumerate(ev): e["end"] = ev[i + 1]["t"] if i + 1 < len(ev) else min(e["t"] + 5, end)
    return ev


# ------------------------------------------------------------------ build + render
def build(o, W, H, fps):
    y, sr = load_audio(o["audio"]); total = min(len(y) / sr, 300.0)
    nframes = int(total * fps); pulse, onset = analyse(y, sr, fps, nframes)
    ctx = Ctx(o, W, H, fps, total); lang = ctx.lang
    photos = [load_photo(p) for p in o["photos"]]; focus = [focus_point(p) for p in photos]
    extras = [load_photo(p) for p in o.get("extras", [])]
    to, frm = o.get("to", ""), o.get("from", "")
    title = o.get("title") or ((f"Happy {o.get('occasion', 'Birthday').title()}\n{to}") if to else "A Song For You")
    intro = CardSlide(ctx, title, bg_img=photos[0], medallion=(photos[0], focus[0]), sub=o.get("subtitle", "A song made just for you"), title_font="title")
    outro = CardSlide(ctx, o.get("outro_title") or (("With love,\n" + frm) if frm else "With love"), bg_img=photos[-1], medallion=(photos[-1], focus[-1]),
                      sub=(f"A song made for {to}" if to else None), brand=o.get("brand"), title_font="title")
    t_in, t_out, fade = 4.2, 6.0, 0.7
    mid = max(total - t_in - t_out, 6.0)
    wishes = list(o.get("wishes", [])); target = 4.6
    n_photo_slots = max(1, round(mid / target))
    seq = []
    pi = 0; wi = 0; layouts = ["frame", "medal", "frame", "collage"]
    for k in range(n_photo_slots):
        lay = layouts[k % 4]; n = len(photos)
        if lay == "collage" and n >= 3:
            ids = [(pi + j) % n for j in range(3)]; seq.append(CollageSlide(ctx, [photos[i] for i in ids], [focus[i] for i in ids], k)); pi += 3
        elif lay == "medal":
            seq.append(MedalSlide(ctx, photos[pi % n], k, focus[pi % n])); pi += 1
        else:
            seq.append(PhotoSlide(ctx, photos[pi % n], k, focus[pi % n])); pi += 1
        if wishes and (k + 1) % 3 == 0 and k + 1 < n_photo_slots:
            seq.append(CardSlide(ctx, wishes[wi % len(wishes)], bg_img=extras[wi % len(extras)] if extras else None)); wi += 1
    # slide durations (photo slots weigh 1.0, cards 0.8), boundaries snapped to beats
    wts = np.array([1.35 if isinstance(x, CollageSlide) else (1.0 if x.kind == "photo" else 0.8) for x in seq]); wts = wts / wts.sum() * (mid + fade * len(seq))
    starts = [0.0]; durs = [t_in + fade]
    t = t_in
    for sl, d in zip(seq, wts):
        starts.append(t); durs.append(d); t += d - fade
    starts.append(t); durs.append(total - t)
    # snap boundaries to onsets (+-0.35s)
    on = onset
    for i in range(1, len(starts)):
        c0 = int(starts[i] * fps); lo, hi = max(c0 - 10, 0), min(c0 + 10, len(on) - 1)
        if hi > lo and on[lo:hi].max() > 0.35: starts[i] = (lo + int(np.argmax(on[lo:hi]))) / fps
    slides = [intro] + seq + [outro]
    for i, sl in enumerate(slides): sl.trans = ["fade", "push", "zoom", "flash"][i % 4]
    for i in range(len(slides)): durs[i] = (starts[i + 1] - starts[i] + fade) if i + 1 < len(starts) else total - starts[i]
    return ctx, slides, starts, durs, pulse, nframes, total, lyric_events(o, t_in, total - t_out)


def caption_layers(ctx, ev):
    ft = ctx.F("body", 64); out = []
    for e in ev:
        base, hi, boxes = karaoke_layer(e["text"], ft, ctx.W, (255, 255, 255), ctx.theme.accent, int(3 * ctx.scale), int(14 * ctx.scale))
        words = e["text"].split(); wl = np.array([len(w) + 2 for w in words], float); span = max(e["end"] - e["t"] - 0.35, 0.8)
        edges = e["t"] + np.concatenate([[0], np.cumsum(wl / wl.sum())]) * span
        out.append((e["t"], e["end"], base, hi, boxes[:len(words)], edges))
    return out


def draw_caption(fr, cap, t, ctx):
    a, b, base, hi, boxes, edges = cap
    e_in = ease((t - a) / 0.3); e_out = ease((b - t) / 0.3); al = min(e_in, e_out)
    lay = base.copy(); k = int(np.searchsorted(edges, t, side="right")) - 1
    for j, (x0, y0, x1, y1) in enumerate(boxes):
        if j <= k: lay[max(y0, 0):y1, max(x0, 0):x1] = hi[max(y0, 0):y1, max(x0, 0):x1]
    blend_rgba(fr, lay, 0, int(ctx.H * 0.855 - lay.shape[0] / 2 + (1 - e_in) * 22 * ctx.scale), al)


def render(o, outp, preview=False, fps=30, frame_at=None):
    W, H = (540, 960) if preview else (1080, 1920)
    ctx, slides, starts, durs, pulse, nframes, total, ev = build(o, W, H, fps)
    caps = caption_layers(ctx, ev); fade = 0.7
    def make(i):
        t = i / fps; pl = float(pulse[min(i, len(pulse) - 1)])
        # active slides
        act = [k for k in range(len(slides)) if starts[k] <= t < starts[k] + durs[k]]
        k = act[0]
        fr = slides[k].render(t - starts[k], durs[k], pl)
        if len(act) > 1:
            k2 = act[-1]; a = min(max((t - starts[k2]) / fade, 0), 1); a = a * a * (3 - 2 * a)
            fr2 = slides[k2].render(t - starts[k2], durs[k2], pl); tr = slides[k2].trans
            if tr == "push":
                sh = int(W * a); out = fr2.copy(); out[:, :W - sh] = fr[:, sh:]; out[:, W - sh:] = fr2[:, :sh]; fr = out
            elif tr == "zoom":
                zs = 1 + 0.5 * a; M = np.float32([[zs, 0, W * (1 - zs) / 2], [0, zs, H * (1 - zs) / 2]])
                fr = cv2.addWeighted(cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT), 1 - a, fr2, a, 0)
            else:
                fr = cv2.addWeighted(fr, 1 - a, fr2, a, 0)
                if tr == "flash":
                    w_ = 0.75 * (1 - abs(2 * a - 1)); fr = cv2.addWeighted(fr, 1 - w_, np.full_like(fr, 255), w_, 0)
        for kk in range(len(slides)):
            if t >= starts[kk] + durs[kk] and slides[kk].ready: slides[kk].release()
        fr = (fr.astype(np.float32) * (ctx.theme.vig * (1 + 0.06 * pl))).clip(0, 255).astype(np.uint8)
        fr = ctx.spark.draw(fr, t, pl); ctx.fx.draw(fr, t, pl)
        if ctx.header is not None and 4.0 < t < total - 5.5: blend_rgba(fr, ctx.header, 0, int(H * 0.035), 0.9)
        for cap in caps:
            if cap[0] <= t < cap[1]: draw_caption(fr, cap, t, ctx)
        return fr
    if frame_at is not None: return make(int(frame_at * fps))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", o["audio"],
           "-map", "0:v", "-map", "1:a", "-af", f"afade=t=in:d=0.5,afade=t=out:st={total - 2.5:.2f}:d=2.5", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", outp]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(nframes):
        pr.stdin.write(make(i).tobytes())
        if i % (fps * 10) == 0: print(f"  {i / fps:5.1f}s / {total:.1f}s", flush=True)
    pr.stdin.close(); pr.wait()
    return outp


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("order"); ap.add_argument("out"); ap.add_argument("--preview", action="store_true")
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--frame", type=float, help="render a single PNG at this second")
    a = ap.parse_args(); o = json.load(open(a.order, encoding="utf-8")); base = os.path.dirname(os.path.abspath(a.order))
    for k in ("photos", "extras"): o[k] = [p if os.path.isabs(p) else os.path.join(base, p) for p in o.get(k, [])]
    for k in ("audio", "lyrics_lrc"):
        if o.get(k) and not os.path.isabs(o[k]): o[k] = os.path.join(base, o[k])
    if a.frame is not None:
        cv2.imwrite(a.out, render(o, a.out, a.preview, a.fps, frame_at=a.frame)); print("wrote", a.out)
    else:
        print("rendered", render(o, a.out, a.preview, a.fps))
