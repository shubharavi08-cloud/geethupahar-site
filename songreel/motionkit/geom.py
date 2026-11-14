"""Vector geometry helpers (all return SVG path 'd' strings)."""
import math
def _f(v): return f"{v:.1f}"
def poly(pts, close=True): return "M" + " L".join(f"{_f(x)} {_f(y)}" for x, y in pts) + ("Z" if close else "")
def circle(cx, cy, r): return f"M{_f(cx-r)} {_f(cy)} a{_f(r)} {_f(r)} 0 1 0 {_f(2*r)} 0 a{_f(r)} {_f(r)} 0 1 0 {_f(-2*r)} 0"
def dots(cx, cy, R, n, r, phase=0): return " ".join(circle(cx + R*math.cos(phase + i*2*math.pi/n), cy + R*math.sin(phase + i*2*math.pi/n), r) for i in range(n))
def heart(cx, cy, s):
    pts = []
    for i in range(241):
        t = math.pi + i/240*2*math.pi
        x = 16*math.sin(t)**3; y = 13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t)
        pts.append((cx + x*s, cy - y*s))
    return poly(pts)
def rose(cx, cy, R, k, rot=0, n=720):
    pts = []
    for i in range(n+1):
        th = i/n*2*math.pi*(1 if k % 1 == 0 and int(k) % 2 == 0 else 1)
        r = R*math.cos(k*th); pts.append((cx + r*math.cos(th+rot), cy + r*math.sin(th+rot)))
    return poly(pts, False)
def spiro(cx, cy, R, r, d, n=900, turns=None):
    g = math.gcd(int(R), int(r)); turns = turns or int(r/g); pts = []
    for i in range(n+1):
        t = i/n*2*math.pi*turns
        x = (R-r)*math.cos(t) + d*math.cos((R-r)/r*t); y = (R-r)*math.sin(t) - d*math.sin((R-r)/r*t)
        pts.append((cx + x, cy + y))
    return poly(pts, False)
def petal(cx, cy, ang, length, width, r0=0):
    ca, sa = math.cos(ang), math.sin(ang)
    def P(u, v): return (cx + (r0+u)*ca - v*sa, cy + (r0+u)*sa + v*ca)
    a, b, c, d, e = P(0, 0), P(length*.35, -width), P(length*.85, -width*.55), P(length, 0), P(length*.85, width*.55)
    f, g = P(length*.35, width), P(0, 0)
    q = lambda p: f"{_f(p[0])} {_f(p[1])}"
    return f"M{q(a)} C{q(b)} {q(c)} {q(d)} C{q(e)} {q(f)} {q(g)}Z"
def petal_ring(cx, cy, n, length, width, r0=0, phase=0): return " ".join(petal(cx, cy, phase + i*2*math.pi/n, length, width, r0) for i in range(n))
def lotus(cx, cy, s):
    """layered lotus pointing up, centred at (cx,cy)"""
    out = []
    for n, L, w, ph in [(7, 150*s, 34*s, -math.pi/2 + 0.45), (7, 150*s, 34*s, -math.pi/2 - 0.45)]: pass
    layers = [("back", 9, 175*s, 46*s, -math.pi/2), ("mid", 7, 150*s, 40*s, -math.pi/2 + math.pi/7), ("front", 5, 120*s, 36*s, -math.pi/2)]
    res = []
    for name, n, L, w, ph in layers:
        ds = []
        for i in range(n):
            a = ph + (i - (n-1)/2) * (math.pi*0.78/ (n-1)) if n > 1 else ph
            ds.append(petal(cx, cy, a, L, w))
        res.append((name, " ".join(ds)))
    return res
def swash(x, y, w):
    return f"M{x} {y} C{x+w*.18} {y-26}, {x+w*.32} {y+22}, {x+w*.5} {y} S{x+w*.82} {y-22}, {x+w} {y-6} c14 -4 22 6 10 14 c-10 6 -22 -6 -8 -12"
def corner(x, y, sx, sy):
    return f"M{x} {y+90*sy} C{x} {y+30*sy}, {x+10*sx} {y+8*sx*sy}, {x+90*sx} {y} M{x+14*sx} {y+60*sy} C{x+14*sx} {y+30*sy}, {x+30*sx} {y+14*sy}, {x+60*sx} {y+14*sy}"
def arch(cx, top, bottom, w, scallops=9):
    """temple/mandap arch: scalloped top, straight sides"""
    x0, x1 = cx - w/2, cx + w/2; r = w/2; d = f"M{_f(x0)} {_f(bottom)} L{_f(x0)} {_f(top + r)} "
    for i in range(scallops):
        a0 = math.pi + i*math.pi/scallops; a1 = math.pi + (i+1)*math.pi/scallops
        px, py = cx + r*math.cos(a1), top + r + r*math.sin(a1); rr = r*math.sin(math.pi/(2*scallops))*1.0
        d += f"A{_f(rr)} {_f(rr)} 0 0 1 {_f(px)} {_f(py)} "
    return d + f"L{_f(x1)} {_f(bottom)}"
def wire(x0, x1, y, sag, n=60):
    pts = [(x0 + (x1-x0)*i/n, y + sag*math.sin(math.pi*i/n)) for i in range(n+1)]; return poly(pts, False), pts
def garland(x0, x1, y, sag, n):
    _, pts = wire(x0, x1, y, sag, 200); step = len(pts)//n
    return " ".join(circle(pts[i*step][0], pts[i*step][1], 9) + " " + circle(pts[i*step][0], pts[i*step][1], 5) for i in range(n+1) if i*step < len(pts))
