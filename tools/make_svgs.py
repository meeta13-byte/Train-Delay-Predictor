"""Generate the isometric SVG illustrations used by the web client.

Run:  python tools/make_svgs.py   (writes client/src/assets/*.svg)

Everything is drawn from simple 3D boxes projected isometrically, in the
RailPulse palette: white, periwinkle and navy with small orange details.
"""

import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "client" / "src" / "assets"

WHITE = "#FFFFFF"
SIDE = "#EEF2FF"
BLOB = "#D9E6FF"
PERI = "#B6C4F8"
INDIGO = "#6E7FE6"
NAVY = "#33325C"
NAVY_SOFT = "#4A4A7A"
ORANGE = "#FB7B1B"
GREEN = "#2EAD7A"
SKIN = "#E9B992"

C30, S30 = math.cos(math.radians(30)), 0.5


class Iso:
    def __init__(self, ox, oy, scale=1.0):
        self.ox, self.oy, self.s = ox, oy, scale

    def p(self, x, y, z=0):
        return (self.ox + (x - y) * C30 * self.s, self.oy + (x + y) * S30 * self.s - z * self.s)

    def poly(self, pts, fill, extra=""):
        d = " ".join(f"{a:.1f},{b:.1f}" for a, b in (self.p(*q) for q in pts))
        return f'<polygon points="{d}" fill="{fill}"{extra}/>'

    def box(self, x, y, z, w, d, h, top=WHITE, right=PERI, left=SIDE, edge=None):
        """Box with visible top, +x face (right) and +y face (left)."""
        e = f' stroke="{edge}" stroke-width="1" stroke-linejoin="round"' if edge else ""
        return "".join([
            self.poly([(x + w, y, z), (x + w, y + d, z), (x + w, y + d, z + h), (x + w, y, z + h)], right, e),
            self.poly([(x, y + d, z), (x + w, y + d, z), (x + w, y + d, z + h), (x, y + d, z + h)], left, e),
            self.poly([(x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h)], top, e),
        ])

    def side_rect(self, x0, x1, y, z0, z1, fill, extra=""):
        """Rectangle painted on a +y face (the long, visible side of a train)."""
        return self.poly([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], fill, extra)

    def end_rect(self, x, y0, y1, z0, z1, fill, extra=""):
        """Rectangle painted on a +x face (the front end)."""
        return self.poly([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)], fill, extra)

    def line(self, a, b, stroke, width=2, extra=""):
        (x1, y1), (x2, y2) = self.p(*a), self.p(*b)
        return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"{extra}/>'

    def ellipse_top(self, cx, cy, z, r, fill, extra=""):
        """Circle lying flat on the ground plane (an ellipse on screen)."""
        X, Y = self.p(cx, cy, z)
        return f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{r * C30 * self.s * 1.414:.1f}" ry="{r * S30 * self.s * 1.414:.1f}" fill="{fill}"{extra}/>'


def coach(iso, x, y, length, kind="coach"):
    """A train car: navy undercarriage + white body with periwinkle/navy stripes and windows."""
    W, H, U = 18, 20, 5
    parts = [iso.box(x + 2, y + 2, 0, length - 4, W - 4, U, top=NAVY, right=NAVY, left=NAVY_SOFT)]
    parts.append(iso.box(x, y, U, length, W, H, top=WHITE, right=PERI, left="#F7F9FF"))
    yy = y + W
    parts.append(iso.side_rect(x, x + length, yy, U + 3, U + 6, PERI))
    parts.append(iso.side_rect(x, x + length, yy, U + 6, U + 7.2, NAVY))
    if kind == "loco":
        parts.append(iso.side_rect(x + length - 12, x + length - 3, yy, U + 10, U + 16, NAVY))
        parts.append(iso.side_rect(x + 4, x + length - 16, yy, U + 10, U + 14, INDIGO))
        # front end: windscreen + orange headlight
        parts.append(iso.end_rect(x + length, y + 3, y + W - 3, U + 11, U + 17, NAVY))
        parts.append(iso.end_rect(x + length, y + 7, y + W - 7, U + 3.5, U + 6, ORANGE))
        parts.append(iso.box(x + 8, y + 5, U + H, 14, 8, 2.5, top=PERI, right=INDIGO, left=PERI))
        parts.append(iso.line((x + 12, y + 9, U + H + 2.5), (x + 20, y + 9, U + H + 9), NAVY, 1.6))
        parts.append(iso.line((x + 20, y + 9, U + H + 9), (x + 26, y + 9, U + H + 2.5), NAVY, 1.6))
    else:
        for wx in range(int(x) + 5, int(x + length) - 6, 9):
            parts.append(iso.side_rect(wx, wx + 6, yy, U + 10, U + 15, NAVY))
        parts.append(iso.side_rect(x + length - 5, x + length - 1.5, yy, U + 1, U + 16, PERI))
        parts.append(iso.box(x + 10, y + 5, U + H, 10, 8, 2, top=PERI, right=INDIGO, left=PERI))
        parts.append(iso.box(x + length - 22, y + 5, U + H, 10, 8, 2, top=PERI, right=INDIGO, left=PERI))
    return "".join(parts)


def person(iso, x, y):
    parts = [
        iso.ellipse_top(x + 3, y + 3, 0, 4.5, NAVY, ' opacity="0.18"'),
        iso.box(x, y + 1, 0, 2.5, 2.5, 12, top=NAVY, right=NAVY, left=NAVY_SOFT),
        iso.box(x + 3.5, y + 1, 0, 2.5, 2.5, 12, top=NAVY, right=NAVY, left=NAVY_SOFT),
        iso.box(x - 0.5, y, 12, 7, 5, 13, top=ORANGE, right="#E86A0C", left=ORANGE),
    ]
    hx, hy = iso.p(x + 3, y + 2.5, 30)
    parts.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{4.6 * iso.s:.1f}" fill="{SKIN}"/>')
    parts.append(f'<path d="M{hx - 4.8 * iso.s:.1f},{hy - 0.5 * iso.s:.1f} a{4.8 * iso.s:.1f},{4.8 * iso.s:.1f} 0 0 1 {9.6 * iso.s:.1f},0 l-1,-1.5 q-4,-3 -7.6,0 z" fill="{NAVY}"/>')
    # arm raised holding a phone
    ax, ay = iso.p(x + 6.5, y + 5, 22)
    px, py = iso.p(x + 7, y + 7, 27)
    parts.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{px:.1f}" y2="{py + 3:.1f}" stroke="{ORANGE}" stroke-width="{2.6 * iso.s:.1f}" stroke-linecap="round"/>')
    parts.append(f'<rect x="{px - 2.2 * iso.s:.1f}" y="{py - 3.2 * iso.s:.1f}" width="{4.4 * iso.s:.1f}" height="{7 * iso.s:.1f}" rx="{1 * iso.s:.1f}" fill="{NAVY}" transform="rotate(-18 {px:.1f} {py:.1f})"/>')
    parts.append(f'<rect x="{px - 1.4 * iso.s:.1f}" y="{py - 2.2 * iso.s:.1f}" width="{2.8 * iso.s:.1f}" height="{4.6 * iso.s:.1f}" rx="0.6" fill="{PERI}" transform="rotate(-18 {px:.1f} {py:.1f})"/>')
    return "".join(parts)


def signal(iso, x, y):
    parts = [
        iso.box(x - 1, y - 1, 0, 6, 6, 2, top=PERI, right=INDIGO, left=PERI),
        iso.box(x + 1, y + 1, 2, 2, 2, 40, top=NAVY, right=NAVY, left=NAVY_SOFT),
        iso.box(x - 1, y, 34, 6, 4, 16, top=NAVY_SOFT, right=NAVY, left=NAVY),
    ]
    for z, col in ((46, ORANGE), (40, GREEN)):
        X, Y = iso.p(x + 2, y + 4, z)
        parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{1.9 * iso.s:.1f}" fill="{col}"/>')
    return "".join(parts)


def hero():
    iso = Iso(330, 140, 2.15)
    W, H = 720, 520
    blob = ('<path class="hero-blob-shape" fill="#D9E6FF" d="M140,250 C120,140 230,60 360,62 C470,64 560,40 650,90 '
            'C760,150 760,330 720,420 C680,500 560,500 450,486 C340,472 250,500 180,440 C120,390 150,320 140,250 Z"/>')
    blob2 = '<path class="hero-blob-shape slow" fill="#ECF2FF" d="M520,40 C600,20 700,40 720,110 L720,230 C660,190 600,170 560,120 C530,90 490,60 520,40 Z"/>'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">',
           '<title id="t">Isometric illustration of an Indian Railways train arriving at a station platform</title>',
           blob2, blob]

    # dashed track lines running off the blob in both directions
    for yy in (8, 20):
        out.append(iso.line((-120, yy, 0), (-40, yy, 0), PERI, 2, ' stroke-dasharray="6 7"'))
        out.append(iso.line((200, yy, 0), (300, yy, 0), PERI, 2, ' stroke-dasharray="6 7"'))
    # parking-style ground lines near the platform
    for gx in (150, 165, 180):
        out.append(iso.line((gx, 62, 0), (gx, 80, 0), WHITE, 2.2, ' opacity="0.9"'))

    # track bed, sleepers, rails
    out.append(iso.box(-40, 4, 0, 240, 20, 1.5, top="#C9D3F7", right=PERI, left=PERI))
    for sx in range(-36, 196, 8):
        out.append(iso.box(sx, 5, 1.5, 3, 18, 1.2, top=NAVY_SOFT, right=NAVY, left=NAVY))
    for ry in (8, 20):
        out.append(iso.box(-40, ry - 0.6, 2.7, 240, 1.2, 1.4, top=WHITE, right=PERI, left=INDIGO))

    # train (animated group)
    shadow = iso.poly([(-6, 6, 0), (176, 6, 0), (180, 26, 0), (-2, 26, 0)], NAVY, ' opacity="0.16"')
    out.append(shadow)
    out.append('<g class="hero-train">')
    out.append(coach(iso, -6, 5, 52))
    out.append(coach(iso, 49, 5, 52))
    out.append(coach(iso, 104, 5, 64, kind="loco"))
    out.append('</g>')

    # platform in front of the track
    out.append(iso.box(-10, 34, 0, 200, 26, 7, top=WHITE, right=PERI, left="#E3E9FB"))
    out.append(iso.box(-10, 34, 7, 200, 2.5, 0.6, top=ORANGE, right=ORANGE, left=ORANGE))
    out.append(iso.box(18, 50, 7, 24, 7, 1.4, top=PERI, right=INDIGO, left=PERI))  # bench seat
    out.append(iso.box(20, 52, 0, 2, 2, 7, top=NAVY, right=NAVY, left=NAVY))
    out.append(iso.box(38, 52, 0, 2, 2, 7, top=NAVY, right=NAVY, left=NAVY))
    out.append(signal(iso, 175, 40))
    out.append(person(iso, 95, 42))
    # station name board
    out.append(iso.box(60, 54, 7, 1.6, 1.6, 22, top=NAVY, right=NAVY, left=NAVY))
    out.append(iso.box(80, 54, 7, 1.6, 1.6, 22, top=NAVY, right=NAVY, left=NAVY))
    out.append(iso.box(57, 53.4, 25, 27, 2.8, 9, top=NAVY_SOFT, right=NAVY, left=WHITE))
    out.append(iso.side_rect(60, 81, 56.2, 27.5, 31.5, PERI))

    # small floating ETA card above the train
    cx, cy = iso.p(150, 0, 70)
    out.append(f'<g class="hero-chip"><rect x="{cx - 46:.0f}" y="{cy - 20:.0f}" width="92" height="40" rx="12" fill="#FFFFFF" '
               f'stroke="#D9E6FF"/><circle cx="{cx - 28:.0f}" cy="{cy:.0f}" r="8" fill="{ORANGE}"/>'
               f'<path d="M{cx - 28:.0f},{cy - 4:.0f} v4 h3" stroke="#fff" stroke-width="1.8" fill="none" stroke-linecap="round"/>'
               f'<rect x="{cx - 14:.0f}" y="{cy - 7:.0f}" width="44" height="5" rx="2.5" fill="{NAVY}"/>'
               f'<rect x="{cx - 14:.0f}" y="{cy + 3:.0f}" width="28" height="5" rx="2.5" fill="{PERI}"/></g>')
    out.append("</svg>")
    return "\n".join(out)


def icon(body, size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" aria-hidden="true">{body}</svg>')


def icons():
    i = Iso(32, 44, 0.95)
    res = {}
    # chart bars
    res["chart"] = icon(i.box(-12, 6, 0, 8, 8, 10, top=PERI, right=INDIGO, left=SIDE)
                        + i.box(-2, 0, 0, 8, 8, 18, top=WHITE, right=PERI, left=SIDE)
                        + i.box(8, -6, 0, 8, 8, 26, top=ORANGE, right="#E86A0C", left="#FDBA86"))
    # database cylinder
    def cyl(z, h, top):
        X, Y = i.p(0, 0, z)
        rx, ry = 15, 8
        return (f'<path d="M{X - rx},{Y} v{-h} a{rx},{ry} 0 0 0 {2 * rx},0 v{h} a{rx},{ry} 0 0 1 {-2 * rx},0 z" fill="{PERI}"/>'
                f'<ellipse cx="{X}" cy="{Y - h}" rx="{rx}" ry="{ry}" fill="{top}"/>')
    res["database"] = icon(cyl(2, 9, INDIGO) + cyl(-9, 9, PERI) + cyl(-20, 9, WHITE)
                           + f'<circle cx="42" cy="{i.p(0, 0, 0)[1] - 10:.0f}" r="2" fill="{ORANGE}"/>')
    # clock on an iso tile
    X, Y = i.p(0, 0, 0)
    res["clock"] = icon(i.box(-14, -14, 0, 28, 28, 4, top=WHITE, right=PERI, left=SIDE)
                        + f'<circle cx="{X}" cy="{Y - 20}" r="14" fill="{WHITE}" stroke="{NAVY}" stroke-width="3"/>'
                        + f'<path d="M{X},{Y - 20} V{Y - 29} M{X},{Y - 20} l7,4" stroke="{NAVY}" stroke-width="3" stroke-linecap="round" fill="none"/>'
                        + f'<circle cx="{X}" cy="{Y - 20}" r="2.5" fill="{ORANGE}"/>')
    # signal post
    s = Iso(30, 60, 1.05)
    res["signal"] = icon(signal(s, 0, 0))
    # map pin
    res["pin"] = icon(i.box(-14, -14, 0, 28, 28, 3, top=SIDE, right=PERI, left=PERI)
                      + i.ellipse_top(0, 0, 3, 6, PERI)
                      + f'<path d="M{X},{Y - 2} C{X - 3},{Y - 10} {X - 11},{Y - 15} {X - 11},{Y - 24} a11,11 0 0 1 22,0 C{X + 11},{Y - 15} {X + 3},{Y - 10} {X},{Y - 2} z" fill="{ORANGE}"/>'
                      + f'<circle cx="{X}" cy="{Y - 24}" r="4.5" fill="{WHITE}"/>')
    # forecast graph on a tile
    pts = [i.p(-12, 12, 4 + v) for v in (0,)]
    res["forecast"] = icon(i.box(-15, -15, 0, 30, 30, 3, top=WHITE, right=PERI, left=SIDE)
                           + f'<polyline points="12,38 22,30 30,34 40,22" fill="none" stroke="{INDIGO}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>'
                           + f'<polyline points="40,22 50,12" fill="none" stroke="{ORANGE}" stroke-width="3.2" stroke-dasharray="3 4" stroke-linecap="round"/>'
                           + f'<circle cx="50" cy="12" r="3.5" fill="{ORANGE}"/>')
    # file stack
    files = ""
    for k, col in enumerate((PERI, SIDE, WHITE)):
        files += i.box(-12 + k * 3, -10 - k * 3, k * 6, 22, 18, 3, top=col, right=PERI, left=INDIGO if k == 0 else PERI)
    tx, ty = i.p(2, -8, 15)
    res["files"] = icon(files + f'<rect x="{tx - 7}" y="{ty - 3}" width="14" height="5" rx="2.5" fill="{ORANGE}"/>')
    # broom
    res["broom"] = icon(f'<line x1="44" y1="6" x2="30" y2="36" stroke="{NAVY}" stroke-width="4" stroke-linecap="round"/>'
                        + f'<path d="M24,34 L38,40 L34,56 Q22,58 12,50 Z" fill="{ORANGE}"/>'
                        + f'<path d="M18,48 L28,40 M22,52 L31,43 M27,54 L34,45" stroke="#E86A0C" stroke-width="2" stroke-linecap="round"/>'
                        + f'<rect x="23" y="32" width="16" height="6" rx="2" fill="{PERI}" transform="rotate(24 31 35)"/>')
    # small train (planner)
    t = Iso(30, 38, 0.72)
    res["train"] = icon(coach(t, -26, -6, 58, kind="loco"))
    # route with two pins
    res["route"] = icon(i.box(-15, -15, 0, 30, 30, 3, top=WHITE, right=PERI, left=SIDE)
                        + f'<path d="M14,30 C24,40 34,20 48,28" stroke="{INDIGO}" stroke-width="3" fill="none" stroke-dasharray="4 4" stroke-linecap="round"/>'
                        + f'<circle cx="14" cy="30" r="5" fill="{NAVY}"/><circle cx="48" cy="28" r="5" fill="{ORANGE}"/>')
    # empty state: magnifier over tile
    res["empty"] = icon(i.box(-16, -16, 0, 32, 32, 3, top=WHITE, right=PERI, left=SIDE)
                        + f'<circle cx="30" cy="24" r="11" fill="{BLOB}" stroke="{NAVY}" stroke-width="3.5"/>'
                        + f'<line x1="38" y1="32" x2="48" y2="42" stroke="{NAVY}" stroke-width="4.5" stroke-linecap="round"/>')
    return res


def logo():
    i = Iso(16, 12, 0.62)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" aria-hidden="true">'
            + i.box(-12, -12, -16, 24, 24, 24, top=ORANGE, right=INDIGO, left=PERI) + "</svg>")


if __name__ == "__main__":
    (OUT / "icons").mkdir(parents=True, exist_ok=True)
    (OUT / "hero.svg").write_text(hero())
    (OUT / "logo.svg").write_text(logo())
    for name, svg in icons().items():
        (OUT / "icons" / f"{name}.svg").write_text(svg)
    print("wrote", OUT)
