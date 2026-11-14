import json, math, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from shape import text_paths
F = lambda n: os.path.join(os.path.dirname(__file__), "fonts", n + ".ttf")
def heart(cx, cy, s):
    pts = []
    for i in range(0, 241):
        t = math.pi + i / 240 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
def text(s, font, size, x, y, t0, dur, t1=None, align="center", **k):
    r = text_paths(s, F(font), size)
    d = dict(type="text", glyphs=r["glyphs"], w=r["width"], x=x, y=y, t0=t0, dur=dur, align=align)
    if t1: d["t1"] = t1
    d.update(k); return d
def swash(x, y, w, t0, dur, t1=None):
    d = f"M{x} {y} C{x+w*.18} {y-26}, {x+w*.32} {y+22}, {x+w*.5} {y} S{x+w*.82} {y-22}, {x+w} {y-6} c14 -4 22 6 10 14 c-10 6 -22 -6 -8 -12"
    return dict(type="path", d=d, t0=t0, dur=dur, sw=3, glow=True, pen=4, **({"t1": t1} if t1 else {}))
def corner(x, y, sx, sy, t0):
    d = f"M{x} {y+90*sy} C{x} {y+30*sy}, {x+10*sx} {y+8*sx*sy}, {x+90*sx} {y} M{x+14*sx} {y+60*sy} C{x+14*sx} {y+30*sy}, {x+30*sx} {y+14*sy}, {x+60*sx} {y+14*sy}"
    return dict(type="path", d=d, t0=t0, dur=2.2, sw=2, pen=3)
def demo():
    W, H = 540, 960
    items = [corner(26, 26, 1, 1, .2), corner(W-26, 26, -1, 1, .3), corner(26, H-26, 1, -1, .4), corner(W-26, H-26, -1, -1, .5)]
    items.append(dict(type="path", d=heart(W/2, 250, 7.5), t0=.5, dur=2.4, sw=5, glow=True, fill="#ff4f86", fillA=.55, pen=5, stroke="#ff9fbd"))
    items.append(text("A song made just for", "PlayfairDisplay", 26, W/2, 410, 2.2, 1.4, t1=7.3, sw=1.2))
    items.append(text("Aarav", "Pacifico", 150, W/2, 560, 2.8, 2.6, sw=2.2))
    items.append(swash(120, 600, 300, 5.0, 1.6))
    items.append(text("Happy Birthday!", "PlayfairDisplay", 46, W/2, 690, 5.6, 1.8, sw=1.4))
    items.append(text("ಹುಟ್ಟುಹಬ್ಬದ ಶುಭಾಶಯ", "NotoSansKannada", 40, W/2, 790, 7.2, 2.2, sw=1.2))
    items.append(text("GEETH UPAHAR", "Poppins-Bold", 20, W/2, 905, 8.6, 1.4, sw=1))
    return dict(w=W, h=H, bg=["#4a1245", "#2a0a2c", "#10031a"], ray="246,196,83", items=items)
if __name__ == "__main__":
    spec = demo()
    html = open(os.path.join(os.path.dirname(__file__), "template.html")).read()
    eng = open(os.path.join(os.path.dirname(__file__), "engine.js")).read()
    open(sys.argv[1] if len(sys.argv) > 1 else "scene.html", "w").write(html.replace("/*SPEC*/", "const SPEC=" + json.dumps(spec) + ";").replace("/*ENGINE*/", eng))
