"""Five Geeth Upahar motion themes. Usage: python3 themes.py THEME out.html [audio.m4a start dur]
THEME in: royal, rangoli, romantic, devotional, party"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from shape import text_paths
import geom as G
D = os.path.dirname(__file__); W, H = 540, 960
F = lambda n: os.path.join(D, "fonts", n + ".ttf")
def T(s, font, size, y, t0, dur, x=W/2, **k):
    r = text_paths(s, F(font), size)
    return dict(type="text", glyphs=r["glyphs"], w=r["width"], x=x, y=y, t0=t0, dur=dur, align="center", **k)
def P(d, t0, dur, **k): return dict(type="path", d=d, t0=t0, dur=dur, **k)
def bursts(beat, fps, t_from, t_to, spots, colors, gap=1.3):
    out, last, j = [], -9, 0
    for i, b in enumerate(beat):
        t = i / fps
        if t_from <= t <= t_to and b > .8 and t - last >= gap:
            x, y = spots[j % len(spots)]; out.append(dict(t=t, x=x, y=y, c=colors[j % len(colors)], n=34, s=95 + 25 * (j % 3))); last = t; j += 1
    return out
STAR = "M0 -9 L2.4 -2.8 L9 -2.8 L3.8 1.2 L5.8 7.6 L0 3.8 L-5.8 7.6 L-3.8 1.2 L-9 -2.8 L-2.4 -2.8Z"
SPARK = "M0 -9 L2 -2 L9 0 L2 2 L0 9 L-2 2 L-9 0 L-2 -2Z"
FLAME = "M0 -9 C-7 -1 -6 6 0 9 C6 6 7 -1 0 -9Z"
PETAL = "M0 -8 C6 -8 8 0 0 8 C-8 0 -6 -8 0 -8Z"
HEARTF = "M0 6 C-10 -4 -6 -10 0 -5 C6 -10 10 -4 0 6Z"
def royal(name="Aarav", beat=None, fps=24):
    it = [P(G.corner(26, 26, 1, 1), .2, 2.2, sw=2, pen=3), P(G.corner(W-26, 26, -1, 1), .3, 2.2, sw=2, pen=3), P(G.corner(26, H-26, 1, -1), .4, 2.2, sw=2, pen=3), P(G.corner(W-26, H-26, -1, -1), .5, 2.2, sw=2, pen=3)]
    it += [P(G.rose(270, 450, 215, 6), .4, 3.2, sw=1.6, alpha=.55, spin=4, cx=270, cy=450, pen=3), P(G.rose(270, 450, 165, 4, .3), .8, 3.2, sw=1.4, alpha=.45, spin=-5, cx=270, cy=450, pen=3),
           P(G.dots(270, 450, 235, 48, 2.4), 2.5, 1.5, mode="fade", fill="#ffe9a8", fillA=.8, stroke="none", spin=2, cx=270, cy=450)]
    it += [P(G.heart(270, 215, 4.4), .5, 2.2, sw=4, glow=True, fill="#ff4f86", fillA=.6, stroke="#ff9fbd", pen=5, pulse=1, cx=270, cy=215, beatscale=.06)]
    it += [T("A song made just for", "PlayfairDisplay", 26, 335, 2.0, 1.4, sw=1.2), T(name, "Pacifico", 150, 520, 2.6, 2.6, sw=2.2), P(G.swash(120, 565, 300), 5.0, 1.5, sw=3, glow=True, pen=4),
           T("Happy Birthday!", "PlayfairDisplay", 46, 670, 5.4, 1.8, sw=1.4), T("ಹುಟ್ಟುಹಬ್ಬದ ಶುಭಾಶಯ", "NotoSansKannada", 38, 765, 7.0, 2.0, sw=1.2), T("GEETH UPAHAR", "Poppins-Bold", 20, 905, 8.6, 1.4, sw=1)]
    return dict(bg=["#4a1245", "#2a0a2c", "#10031a"], gold=["#ffe39a", "#f4b93c", "#c4801a"], ray="246,196,83", floaters=dict(d=SPARK, fill="#ffe9a8", n=12, size=8), items=it)
def rangoli(name="Sharma Family", beat=None, fps=24):
    cx, cy = 270, 520; it = []
    rings = [(60, "#ffd27a"), (105, "#ff9fbd"), (150, "#7ad7f0"), (196, "#ffd27a")]
    for k, (r, c) in enumerate(rings): it.append(P(G.circle(cx, cy, r), .4 + k*.35, 1.8, sw=2.2, stroke=c, pen=3))
    it += [P(G.petal_ring(cx, cy, 12, 78, 24, 38), 1.6, 1.6, mode="fade", fill="#ff5f8f", fillA=.55, stroke="#ffb3c8", sw=1.5, spin=3, cx=cx, cy=cy),
           P(G.petal_ring(cx, cy, 16, 48, 15, 112, .2), 2.2, 1.6, mode="fade", fill="#ffb02e", fillA=.6, stroke="#ffe39a", sw=1.2, spin=-3, cx=cx, cy=cy),
           P(G.dots(cx, cy, 128, 24, 4.5), 2.8, 1.2, mode="fade", fill="#fff", fillA=.95, stroke="none", spin=2, cx=cx, cy=cy),
           P(G.dots(cx, cy, 175, 36, 3.2, .1), 3.1, 1.2, mode="fade", fill="#ffe39a", fillA=.95, stroke="none", spin=-2, cx=cx, cy=cy),
           P(G.rose(cx, cy, 98, 8), 1.0, 3.0, sw=1.6, stroke="#fff", alpha=.7, spin=5, cx=cx, cy=cy, pen=3)]
    it += [P("M-130 50 Q0 150 130 50 Q100 100 0 112 Q-100 100 -130 50Z", 3.4, 1.8, sw=3, fill="#c9701a", fillA=.9, stroke="#ffd27a", transform="translate(270 845) scale(.55)"),
           P("M0 -50 C-22 -10 -22 20 0 38 C22 20 22 -10 0 -50Z", 4.6, 1.0, sw=2, fill="#ffb93c", fillA=.95, stroke="#fff2b0", transform="translate(270 818) scale(.55)", glow=True, pulse=1)]
    it += [T("Shubh Deepavali", "PlayfairDisplay", 44, 130, 1.0, 1.8, sw=1.3), T(name, "Pacifico", 78, 235, 2.2, 2.2, sw=1.8), T("a song for your family", "PlayfairDisplay", 24, 932, 6.0, 1.6, sw=1)]
    bs = bursts(beat or [], fps, 3.0, 99, [(120, 330), (420, 300), (270, 360), (90, 600), (450, 620)], ["#ffd27a", "#ff7aa8", "#7ad7f0", "#fff"]) if beat else [dict(t=3.5, x=120, y=330, c="#ffd27a"), dict(t=5, x=420, y=300, c="#ff7aa8"), dict(t=6.5, x=270, y=360, c="#7ad7f0")]
    it.append(dict(type="fireworks", bursts=bs, t0=0))
    return dict(bg=["#5a2208", "#2a0e05", "#120503"], gold=["#ffe0a0", "#ff9a2e", "#c9561a"], ray="255,170,60", floaters=dict(d=FLAME, colors=["#ffb347", "#ff7a2a", "#ffd27a"], n=14, size=8), dust="#ffd27a", items=it)
def romantic(name="Priya & Rohan", beat=None, fps=24):
    wire, pts = G.wire(-10, W+10, 62, 46, 80); bulbs = [pts[i] for i in range(4, 80, 6)]
    it = [dict(type="lights", wire=wire, pts=bulbs, colors=["#ffd9a0", "#ffb3c6", "#fff2c8"], t0=.2)]
    it += [P(G.rose(270, 400, 200, 5), .5, 3.2, sw=1.8, stroke="#ffb3c6", alpha=.6, spin=3, cx=270, cy=400, pen=3), P(G.rose(270, 400, 140, 3, .5), 1.0, 3.2, sw=1.6, stroke="#ffd9e6", alpha=.55, spin=-4, cx=270, cy=400, pen=3),
           P(G.heart(270, 405, 7.2), .8, 2.6, sw=5, glow=True, fill="#ff4f86", fillA=.6, stroke="#ffc2d6", pen=5, pulse=1, cx=270, cy=405, beatscale=.07)]
    it += [T("A song made just for", "PlayfairDisplay", 26, 650, 3.0, 1.4, sw=1.2), T(name, "Pacifico", 68, 745, 3.6, 2.6, sw=1.8), P(G.swash(130, 780, 280), 6.0, 1.4, sw=3, glow=True, pen=4),
           T("Happy Anniversary", "PlayfairDisplay", 38, 845, 6.6, 1.8, sw=1.2), T("GEETH UPAHAR", "Poppins-Bold", 18, 915, 8.4, 1.4, sw=1)]
    return dict(bg=["#5a0f3a", "#2a0720", "#12030f"], gold=["#fff0dc", "#ffb3c6", "#e0558a"], ray="255,120,160", dust="#ffd9e6", floaters=dict(d=PETAL, colors=["#ff7aa8", "#ffb3c6", "#ff4f86"], n=18, size=9, dir="down"), items=it)
def devotional(name="Ananya's Pooja", beat=None, fps=24):
    lot = G.lotus(270, 640, 1.0); cols = [("#ff7aa8", .5), ("#ff9fc0", .55), ("#ffd6e4", .7)]; it = []
    it += [P(G.arch(270, 60, 905, 470, 11), .3, 3.0, sw=3, pen=4), P(G.arch(270, 88, 905, 428, 11), .7, 3.0, sw=1.4, alpha=.5, pen=3)]
    it += [P(G.dots(270, 520, 210, 48, 2.6), 2.5, 1.4, mode="fade", fill="#ffe9a8", fillA=.9, stroke="none", spin=2, cx=270, cy=520)]
    for k, (nm, d) in enumerate(lot): it.append(P(d, 1.2 + k*.7, 2.0, sw=2, stroke="#ffe39a", fill=cols[k][0], fillA=cols[k][1], pen=4, pulse=.6))
    it += [P(G.circle(270, 640, 22), 3.8, 1.2, sw=2, stroke="#ffd24a", fill="#ffb02e", fillA=.9, glow=True, pulse=1)]
    it += [T("A song of devotion for", "PlayfairDisplay", 24, 215, 2.2, 1.5, sw=1.1), T(name, "Pacifico", 64, 300, 3.0, 2.4, sw=1.8), T("ದೀಪ ಬೆಳಗಿದೆ, ಮನೆ ತುಂಬ ಸಂಭ್ರಮ", "NotoSansKannada", 30, 800, 5.8, 2.2, sw=1.1), T("GEETH UPAHAR", "Poppins-Bold", 18, 870, 8.0, 1.4, sw=1)]
    return dict(bg=["#3a1a05", "#1a0a08", "#0b0408"], gold=["#fff0b0", "#ffc23c", "#d9801a"], ray="255,190,80", nrays=24, dust="#ffd27a", floaters=dict(d=FLAME, colors=["#ff9a2e", "#ffd24a"], n=12, size=7), items=it)
def party(name="Diya", beat=None, fps=24):
    it = [dict(type="balloons", n=9, colors=["#ff5f8f", "#ffd24a", "#7ad7f0", "#b983ff", "#ff9a3c", "#5fe0a0"], t0=.2)]
    it += [P(G.petal_ring(270, 470, 14, 150, 22, 100), .6, 2.2, sw=2, stroke="#ffe39a", alpha=.22, mode="fade", fill="#ffd24a", fillA=.05, spin=6, cx=270, cy=470),
           T("A song made just for", "Poppins-Bold", 22, 330, 1.4, 1.4, sw=1), T(name, "Baloo2", 190, 520, 2.0, 2.4, sw=2.6), P(G.swash(110, 560, 320), 4.5, 1.4, sw=4, glow=True, pen=4),
           T("Happy 5th Birthday!", "Baloo2", 58, 680, 5.0, 1.8, sw=1.6), P(G.heart(270, 790, 3.4), 6.2, 1.6, sw=3, glow=True, fill="#ff4f86", fillA=.7, stroke="#ffb3c8", pen=4, pulse=1, cx=270, cy=790, beatscale=.1), T("GEETH UPAHAR", "Poppins-Bold", 18, 900, 8.0, 1.4, sw=1)]
    bs = bursts(beat or [], fps, 3.0, 99, [(110, 250), (430, 230), (270, 210)], ["#ffd24a", "#ff7aa8", "#7ad7f0"]) if beat else []
    it.append(dict(type="fireworks", bursts=bs, t0=0))
    return dict(bg=["#1f5a7a", "#0f2f55", "#071530"], gold=["#fff3a0", "#ffb02e", "#ff6a3d"], ray="255,235,120", dust="#fff3a0", floaters=dict(d=STAR, colors=["#ffd24a", "#ff7aa8", "#7ad7f0"], n=16, size=8), items=it)
THEMES = dict(royal=royal, rangoli=rangoli, romantic=romantic, devotional=devotional, party=party)
def build(theme, out, name=None, audio=None, start=0, dur=12, fps=24):
    energy = beat = None
    if audio:
        from audio import envelopes; energy, beat = envelopes(audio, fps, start, dur)
    spec = THEMES[theme](**({"name": name} if name else {}), beat=beat, fps=fps)
    spec.update(w=W, h=H, fps=fps, energy=energy, beat=beat)
    html = open(os.path.join(D, "template.html")).read().replace("/*SPEC*/", "const SPEC=" + json.dumps(spec) + ";").replace("/*ENGINE*/", open(os.path.join(D, "engine.js")).read())
    open(out, "w").write(html)
if __name__ == "__main__":
    a = sys.argv; build(a[1], a[2], audio=a[3] if len(a) > 3 else None, start=float(a[4]) if len(a) > 4 else 0, dur=float(a[5]) if len(a) > 5 else 12)
