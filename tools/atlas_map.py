"""
EMBERFALL — the world drawn as a map.

Everything here is DERIVED from docs/world-layout.json. The geography is
already in the data and it only has to be believed: a zone is a square ringed
by mountains with gaps at its passes, so on a map it is a lump of land joined
to its neighbours by narrow necks, with ridges along every shared wall. Draw
that and the map cannot drift from the layout, because the layout is what drew
it.

Two tricks keep a grid from looking like a grid:

  1. Each zone's blob is sized by its own `size` in metres and given a few
     radial harmonics, so a 224 m city is a small nub and a 512 m wild is a
     broad mass, and none of them are round.
  2. A smooth WARP field displaces every point on the map - coastline, ridges,
     glyphs, labels - by the same amount. The topology is untouched and the
     right angles are gone.
"""
import json, math, os
import numpy as np
from scipy import ndimage
from skimage import measure

def _outdir():
    """Write beside the repo's docs/ when run in the repo, else the render box."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, 'docs')
    return d if os.path.isdir(d) else os.environ.get('EMBERFALL_OUT', '/mnt/user-data/outputs')

OUT = _outdir()

W = json.load(open(os.path.join(OUT, 'world-layout.json')))
AREAS = W['areas']
ZONES = {z['id']: z for z in W['zones']}
LINKS = W['links']

P = 250.0                      # pixels per grid cell
MARGIN = 300.0
RIGHT_PAD = 300.0
BOTTOM_PAD = 90.0
BERTH = {'the_grove': (-3.3, 0.55)}     # off-grid zones get a display berth

def at(z):
    return tuple(z['cell']) if z['cell'] else BERTH[z['id']]

gxs = [at(z)[0] for z in ZONES.values()]
gys = [at(z)[1] for z in ZONES.values()]
X0, X1 = min(gxs), max(gxs)
Y0, Y1 = min(gys), max(gys)
Wpx = int((X1 - X0) * P + MARGIN + RIGHT_PAD)
Hpx = int((Y1 - Y0) * P + 2 * MARGIN + BOTTOM_PAD)

def to_px(gx, gy):
    """grid cell -> canvas pixels, y down"""
    return (MARGIN + (gx - X0) * P, MARGIN + (Y1 - gy) * P)

# ---------------------------------------------------------------- the warp
rng = np.random.default_rng(20260925)
def field(sigma, amp, shape):
    f = rng.normal(size=shape)
    f = ndimage.gaussian_filter(f, sigma)
    f /= (np.abs(f).max() + 1e-9)
    return f * amp

WS = 4                                    # warp field is coarse; sampled smoothly
wshape = (Hpx // WS + 2, Wpx // WS + 2)
WX = field(24, 0.150 * P, wshape) + field(8, 0.048 * P, wshape)
WY = field(24, 0.150 * P, wshape) + field(8, 0.048 * P, wshape)

def warp(x, y):
    """Displace a point by the shared field. Takes scalars or arrays."""
    xa = np.atleast_1d(np.asarray(x, float))
    ya = np.atleast_1d(np.asarray(y, float))
    u = np.clip(ya / WS, 0, wshape[0] - 1)
    v = np.clip(xa / WS, 0, wshape[1] - 1)
    dx = ndimage.map_coordinates(WX, [u, v], order=1, mode='nearest')
    dy = ndimage.map_coordinates(WY, [u, v], order=1, mode='nearest')
    ox, oy = xa + dx, ya + dy
    if np.isscalar(x) or np.ndim(x) == 0:
        return float(ox[0]), float(oy[0])
    return ox, oy

# ------------------------------------------------------------- the landmass
def blob(cx, cy, r, seed, n=220):
    """An irregular closed shape: a circle with a few low harmonics on it."""
    g = np.random.default_rng(seed)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rad = np.ones(n)
    for k, a in ((2, .16), (3, .13), (5, .085), (7, .05), (11, .03)):
        rad += a * np.sin(k * th + g.uniform(0, 6.283))
    rad = rad / rad.mean()
    return cx + r * rad * np.cos(th), cy + r * rad * np.sin(th)

def rasterise():
    """Union of zone blobs and the necks between them, as a float mask."""
    from PIL import Image, ImageDraw
    SS = 2                                    # mask at half resolution
    im = Image.new('L', (Wpx // SS, Hpx // SS), 0)
    d = ImageDraw.Draw(im)
    for i, z in enumerate(ZONES.values()):
        gx, gy = at(z)
        cx, cy = to_px(gx, gy)
        # Big enough that neighbours OVERLAP. The first cut used 0.47P and the
        # continent came out a net: the blobs met only along the necks, so
        # every group of four zones left a hole and the map read as lace.
        # The zone walls are mountains in this engine, not water, so the land
        # is solid and the structure is drawn on top of it.
        r = 0.70 * P * (z['size'] / 512.0) ** 0.30
        bx, by = blob(cx, cy, r, 900 + i * 7)
        d.polygon(list(zip(bx / SS, by / SS)), fill=255)
    # the necks: a zone line is an isthmus, so the land pinches between zones
    for l in LINKS:
        a, b = ZONES[l['a']], ZONES[l['b']]
        x1, y1 = to_px(*at(a)); x2, y2 = to_px(*at(b))
        d.line([(x1 / SS, y1 / SS), (x2 / SS, y2 / SS)],
               fill=255, width=int(0.30 * P / SS))
    m = np.asarray(im, float) / 255.0
    # close the small pockets the blob harmonics leave between four zones; a
    # lake is something we place on purpose, not a gap in the arithmetic
    m = ndimage.binary_fill_holes(m > 0.5).astype(float)
    m = ndimage.gaussian_filter(m, 4.0)
    return m, SS

MASK, MSS = rasterise()

def coastline():
    """Marching squares on the mask, then warped."""
    outs = []
    for c in measure.find_contours(MASK, 0.5):
        if len(c) < 60:
            continue
        xs, ys = c[:, 1] * MSS, c[:, 0] * MSS
        # thin it, then warp
        step = max(1, len(xs) // 900)
        xs, ys = xs[::step], ys[::step]
        wx, wy = warp(xs, ys)
        outs.append((wx, wy))
    return outs

if __name__ == '__main__':
    COAST = coastline()
    print(f'canvas {Wpx}x{Hpx}, {len(COAST)} landmasses, '
          f'{[len(c[0]) for c in COAST]} points')

# ============================================================ the rendering
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S = 2                                       # supersample; everything is drawn at S

FONT_DIR = '/usr/share/texmf/fonts/opentype/public'
FONTS = {
    'label':  f'{FONT_DIR}/tex-gyre/texgyrechorus-mediumitalic.otf',
    'serif':  f'{FONT_DIR}/tex-gyre/texgyrepagella-regular.otf',
    'bold':   f'{FONT_DIR}/tex-gyre/texgyrepagella-bold.otf',
    'caps':   f'{FONT_DIR}/lm/lmromancaps10-regular.otf',
    'basker': '/usr/share/fonts/truetype/baskerville/GFSBaskerville.otf',
}
_fc = {}
def font(kind, size):
    k = (kind, int(size * S))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTS[kind], int(size * S))
    return _fc[k]

INK      = (62, 44, 30)
INK_SOFT = (96, 74, 52)
SEA      = (196, 176, 140)

def parchment():
    """Aged paper: a warm base, fibre noise, blotches and a burnt edge."""
    h, w = Hpx, Wpx
    g = np.random.default_rng(7)
    base = np.zeros((h, w, 3), float)
    fine = ndimage.gaussian_filter(g.normal(size=(h, w)), 1.1)
    broad = ndimage.gaussian_filter(g.normal(size=(h, w)), 34)
    blotch = ndimage.gaussian_filter(g.normal(size=(h, w)), 11)
    t = (0.55 + 0.30 * (broad / (np.abs(broad).max() + 1e-9))
         + 0.10 * (blotch / (np.abs(blotch).max() + 1e-9))
         + 0.035 * fine)
    t = np.clip(t, 0, 1)
    for i, (lo, hi) in enumerate(((198, 236), (176, 214), (136, 176))):
        base[..., i] = lo + (hi - lo) * t
    # burnt edges
    yy, xx = np.mgrid[0:h, 0:w]
    ex = np.minimum(xx, w - 1 - xx) / (w * 0.5)
    ey = np.minimum(yy, h - 1 - yy) / (h * 0.5)
    edge = np.clip(np.minimum(ex, ey) * 3.4, 0, 1) ** 0.75
    base *= (0.62 + 0.38 * edge)[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype('uint8')).resize(
        (Wpx * S, Hpx * S), Image.BICUBIC)

def jitter(xs, ys, amp, seed, freq=0.06):
    """A hand-drawn wobble along a path."""
    g = np.random.default_rng(seed)
    n = len(xs)
    w1 = ndimage.gaussian_filter1d(g.normal(size=n), 3.0, mode='wrap')
    w2 = ndimage.gaussian_filter1d(g.normal(size=n), 9.0, mode='wrap')
    d = (w1 / (np.abs(w1).max() + 1e-9) * 0.6 + w2 / (np.abs(w2).max() + 1e-9))
    dx = np.gradient(xs); dy = np.gradient(ys)
    ln = np.hypot(dx, dy) + 1e-9
    return xs + (-dy / ln) * d * amp, ys + (dx / ln) * d * amp

def poly(d, xs, ys, fill=None, outline=None, width=1):
    pts = [(x * S, y * S) for x, y in zip(xs, ys)]
    if fill: d.polygon(pts, fill=fill)
    if outline: d.line(pts + [pts[0]], fill=outline, width=int(width * S), joint='curve')

def build():
    img = parchment()
    d = ImageDraw.Draw(img, 'RGBA')
    COAST = coastline()
    # the outer mass first, then everything else on top
    COAST.sort(key=lambda c: -len(c[0]))

    # land fill: a slightly warmer, lighter paper than the sea
    land = Image.new('RGBA', img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(land)
    for xs, ys in COAST:
        jx, jy = jitter(xs, ys, 2.6, 11 + int(xs[0]))
        poly(dl, jx, jy, fill=(226, 208, 168, 190))
    img.alpha_composite(land) if img.mode == 'RGBA' else img.paste(
        Image.alpha_composite(img.convert('RGBA'), land).convert('RGB'), (0, 0))
    d = ImageDraw.Draw(img, 'RGBA')

    # coastline: one firm line, then two soft echoes out to sea
    for xs, ys in COAST:
        jx, jy = jitter(xs, ys, 2.6, 11 + int(xs[0]))
        poly(d, jx, jy, outline=INK + (235,), width=1.7)
        cx, cy = jx.mean(), jy.mean()
        for k, (off, a, wd) in enumerate(((7, 90, 1.0), (15, 55, 0.9))):
            ux, uy = jx - cx, jy - cy
            ln = np.hypot(ux, uy) + 1e-9
            ex, ey = jx + ux / ln * off, jy + uy / ln * off
            ex, ey = jitter(ex, ey, 2.2, 400 + k * 13 + int(xs[0]))
            poly(d, ex, ey, outline=INK_SOFT + (a,), width=wd)
    return img


# ---------------------------------------------------------------- palette
# The map accents are chosen to sit on parchment, which the zone-diagram
# accents were not: #e8d49a is a fine gold on a dark chart and invisible here.
PEN = {
    'emberlands':  (58, 92, 48),
    'dawnstair':   (150, 106, 28),
    'monsoon':     (30, 104, 124),
    'ashfall':     (160, 54, 26),
    'standingsky': (78, 94, 106),
    'boneyard':    (86, 62, 124),
}

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def seeded(n):
    return np.random.default_rng(n)

def inland(x, y, margin=16):
    """Is this point comfortably on land? Keeps glyphs out of the sea."""
    j = np.clip(np.array([y / MSS, x / MSS]), 0,
                [MASK.shape[0] - 1, MASK.shape[1] - 1])
    return MASK[int(j[0]), int(j[1])] > 0.75

# ------------------------------------------------------------ ink strokes
def stroke(d, pts, color, width, alpha=255):
    d.line([(x * S, y * S) for x, y in pts], fill=color + (alpha,),
           width=max(1, int(width * S)), joint='curve')

def peak(d, x, y, h, w, seed, color=INK, shade=True):
    """One hand-drawn mountain: two flanks, a shaded face, a couple of ticks."""
    g = seeded(seed)
    lean = g.uniform(-0.22, 0.22)
    ax, ay = x + lean * h * 0.5, y - h
    lx, ly = x - w, y
    rx, ry = x + w, y
    if shade:                      # the dark side, hatched
        n = 4
        for i in range(n):
            t = (i + 1) / (n + 1)
            sx = ax + (rx - ax) * t
            sy = ay + (ry - ay) * t
            bx = x + (rx - x) * t * 0.55
            stroke(d, [(sx, sy), (bx, y - h * 0.06 * (1 - t))],
                   INK_SOFT, 0.65, 150)
    stroke(d, [(lx, ly), (ax, ay), (rx, ry)], color, 1.15)
    # a small shoulder so it is not a bare triangle
    stroke(d, [(lx + w * 0.55, ly - h * 0.30),
               (lx + w * 0.95, ly - h * 0.06)], color, 0.75, 190)

def ridge(d, a_cell, b_cell, heavy, gap_at=0.0, seed=0):
    """A mountain wall along the border between two zones, gapped at the pass.

    This is the engine's own geography: `Zone` rings every zone in mountains
    and opens a `pass` in the wall, so a border IS a range with a notch in it.
    A cross-area wall is drawn heavy; a wall inside one area is a lower line of
    hills, so the six realms read before the thirty zones do.
    """
    x1, y1 = to_px(*a_cell); x2, y2 = to_px(*b_cell)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy)
    px_, py_ = -dy / ln, dx / ln                    # along the wall
    L = P * (0.99 if heavy else 0.92)
    n = int(L / (13 if heavy else 15))
    g = seeded(seed)
    for i in range(n):
        t = (i + 0.5) / n - 0.5
        if abs(t - gap_at) < (0.085 if heavy else 0.07):
            continue                                 # the pass
        jx = g.uniform(-4, 4); jy = g.uniform(-5, 5)
        sx = mx + px_ * t * L + jx
        sy = my + py_ * t * L + jy
        wx, wy = warp(sx, sy)
        if not inland(float(wx), float(wy)):
            continue
        h = (g.uniform(17, 27) if heavy else g.uniform(9, 14))
        w = h * g.uniform(0.62, 0.85)
        peak(d, float(wx), float(wy), h, w, seed * 31 + i,
             INK if heavy else INK_SOFT)

# -------------------------------------------------------------- terrain
def tree(d, x, y, h, seed, kind='round'):
    g = seeded(seed)
    if kind == 'pine':
        stroke(d, [(x, y), (x, y - h * 0.25)], INK, 0.7)
        for i in range(3):
            t = i / 3.0
            w = h * (0.34 - 0.09 * i)
            yy = y - h * (0.22 + 0.26 * i)
            stroke(d, [(x - w, yy), (x, yy - h * 0.30), (x + w, yy)], INK, 0.85)
    elif kind == 'dead':
        stroke(d, [(x, y), (x, y - h * 0.8)], INK, 0.8)
        for s_ in (-1, 1):
            stroke(d, [(x, y - h * 0.5), (x + s_ * h * 0.3, y - h * 0.78)], INK, 0.6)
            stroke(d, [(x, y - h * 0.68), (x + s_ * h * 0.22, y - h * 0.92)], INK, 0.55)
    else:
        stroke(d, [(x, y), (x, y - h * 0.32)], INK, 0.7)
        r = h * 0.36
        cy = y - h * 0.58
        pts = []
        for k in range(13):
            a = k / 12 * 2 * math.pi
            rr = r * (1 + 0.20 * math.sin(3 * a + g.uniform(0, 6)))
            pts.append((x + rr * math.cos(a), cy + rr * math.sin(a) * 0.92))
        stroke(d, pts + [pts[0]], INK, 0.85)

def tuft(d, x, y, h, seed):
    g = seeded(seed)
    for k in (-1, 0, 1):
        stroke(d, [(x + k * h * 0.28, y),
                   (x + k * h * 0.28 + g.uniform(-.2, .2) * h, y - h * g.uniform(.7, 1.0))],
               INK_SOFT, 0.6, 210)

def wave(d, x, y, w, seed):
    g = seeded(seed)
    pts = [(x - w / 2 + w * i / 10, y + math.sin(i * 0.9 + g.uniform(0, 3)) * 1.6)
           for i in range(11)]
    stroke(d, pts, (52, 86, 104), 0.8, 190)

def dune(d, x, y, w, seed):
    pts = [(x - w / 2, y), (x - w * 0.15, y - w * 0.16), (x + w * 0.2, y - w * 0.05),
           (x + w / 2, y - w * 0.13)]
    stroke(d, pts, INK_SOFT, 0.8, 200)

def hillock(d, x, y, w, seed):
    stroke(d, [(x - w / 2, y), (x - w * 0.16, y - w * 0.32),
               (x + w * 0.16, y - w * 0.30), (x + w / 2, y)], INK_SOFT, 0.9, 220)

FILLERS = {
    'wood':      ('tree', 'round'), 'field': ('tuft', None),
    'water':     ('wave', None),    'burn':  ('tree', 'dead'),
    'plain':     ('tuft', None),    'waste': ('dune', None),
    'terrace':   ('hill', None),    'fog':   ('dune', None),
    'city':      (None, None),      'outpost': (None, None),
    'sanctuary': ('tree', 'round'),
}

def scatter(d, z):
    """Fill a zone with its own terrain, inside its blob and on land."""
    gx, gy = at(z)
    cx, cy = to_px(gx, gy)
    r = 0.70 * P * (z['size'] / 512.0) ** 0.30
    what, sub = FILLERS.get(z['kind'], ('tuft', None))
    if what is None:
        return
    g = seeded(hash(z['id']) % 99991)
    n = int((r / P) ** 2 * (70 if what == 'tree' else 46))
    placed = []
    for i in range(n * 3):
        if len([1 for _ in placed]) >= n:
            break
        a = g.uniform(0, 6.2832); rr = r * math.sqrt(g.uniform(0, 1)) * 0.82
        x = cx + rr * math.cos(a); y = cy + rr * math.sin(a)
        wx, wy = warp(x, y); wx, wy = float(wx), float(wy)
        if not inland(wx, wy):
            continue
        if any((wx - qx) ** 2 + (wy - qy) ** 2 < (15 if what == 'tree' else 13) ** 2
               for qx, qy in placed):
            continue
        placed.append((wx, wy))
        sd = 5000 + i * 13 + (hash(z['id']) % 1000)
        if what == 'tree':
            tree(d, wx, wy, g.uniform(13, 19), sd, sub)
        elif what == 'tuft':
            tuft(d, wx, wy, g.uniform(7, 11), sd)
        elif what == 'wave':
            wave(d, wx, wy, g.uniform(20, 30), sd)
        elif what == 'dune':
            dune(d, wx, wy, g.uniform(22, 34), sd)
        elif what == 'hill':
            hillock(d, wx, wy, g.uniform(24, 36), sd)

# ---------------------------------------------------- settlements & roads
def tower(d, x, y, h, seed, big):
    g = seeded(seed)
    w = h * 0.42
    stroke(d, [(x - w, y), (x - w, y - h), (x + w, y - h), (x + w, y), (x - w, y)], INK, 1.0)
    for k in range(3):                       # battlements
        bx = x - w + (2 * w) * (k + 0.5) / 3
        stroke(d, [(bx - w * 0.2, y - h), (bx - w * 0.2, y - h * 1.16),
                   (bx + w * 0.2, y - h * 1.16), (bx + w * 0.2, y - h)], INK, 0.9)
    if big:
        stroke(d, [(x - w * 0.35, y), (x - w * 0.35, y - h * 0.45),
                   (x + w * 0.35, y - h * 0.45), (x + w * 0.35, y)], INK, 0.8)

def settlement(d, z):
    gx, gy = at(z)
    cx, cy = to_px(gx, gy)
    wx, wy = warp(cx, cy); wx, wy = float(wx), float(wy)
    big = z['kind'] == 'city'
    if big:
        tower(d, wx - 11, wy + 4, 20, 1, False)
        tower(d, wx + 11, wy + 4, 17, 2, False)
        tower(d, wx, wy, 26, 3, True)
    else:
        tower(d, wx, wy, 18, 4, False)
    return wx, wy

def road(d, a, b, seed):
    """A dotted trail through the pass, the way the reference maps draw one."""
    x1, y1 = to_px(*at(a)); x2, y2 = to_px(*at(b))
    n = 46
    g = seeded(seed)
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x1 + (x2 - x1) * t; y = y1 + (y2 - y1) * t
        s_ = math.sin(t * math.pi) * 14
        x += -(y2 - y1) / (math.hypot(x2 - x1, y2 - y1) + 1e-9) * s_ * g.uniform(.6, 1.0)
        y += (x2 - x1) / (math.hypot(x2 - x1, y2 - y1) + 1e-9) * s_ * g.uniform(.6, 1.0)
        wx, wy = warp(x, y)
        pts.append((float(wx), float(wy)))
    for i in range(0, len(pts) - 1, 2):
        stroke(d, [pts[i], pts[i + 1]], (110, 86, 58), 1.1, 165)

# ------------------------------------------------------------- lettering
def text(d, xy, s_, kind, size, color, anchor='mm', alpha=255, spacing=0):
    f = font(kind, size)
    x, y = xy[0] * S, xy[1] * S
    if spacing:
        total = sum(d.textlength(ch, font=f) + spacing * S for ch in s_) - spacing * S
        x -= total / 2 if anchor[0] == 'm' else 0
        for ch in s_:
            d.text((x, y), ch, font=f, fill=color + (alpha,), anchor='l' + anchor[1])
            x += d.textlength(ch, font=f) + spacing * S
        return
    d.text((x, y), s_, font=f, fill=color + (alpha,), anchor=anchor)

def halo_text(d, xy, s_, kind, size, color, anchor='mm', spacing=0):
    """A light paper halo so a name stays legible over trees and hatching."""
    for ox, oy in ((-1.6, 0), (1.6, 0), (0, -1.6), (0, 1.6),
                   (-1.2, -1.2), (1.2, 1.2), (-1.2, 1.2), (1.2, -1.2)):
        text(d, (xy[0] + ox, xy[1] + oy), s_, kind, size, (232, 216, 178),
             anchor, 215, spacing)
    text(d, xy, s_, kind, size, color, anchor, 255, spacing)

# ------------------------------------------------------------ the legend
DEITY = {
    'dawnstair':   ('Prabhagaj', 'the Dawn-Tusk'),
    'monsoon':     ('Jalendra',  'the Tide-Trunked'),
    'ashfall':     ('Agnavar',   'the Ember-Tusked'),
    'standingsky': ('Vayuketh',  'He Who Breathes the Plains'),
    'boneyard':    ('Timiraj',   'the Unlit'),
}

def crest(d, x, y, r, area):
    """A small framed device per deity, in that area's ink."""
    c = PEN[area]
    d.rectangle([( (x-r)*S, (y-r)*S ), ((x+r)*S, (y+r)*S)],
                outline=INK + (255,), width=int(1.6*S), fill=(228, 210, 170, 255))
    d.rectangle([((x-r+4)*S, (y-r+4)*S), ((x+r-4)*S, (y+r-4)*S)],
                outline=INK_SOFT + (180,), width=int(0.8*S))
    g = seeded(hash(area) % 9999)
    if area == 'dawnstair':                      # a rising sun over a line
        d.arc([((x-r*0.62)*S, (y-r*0.35)*S), ((x+r*0.62)*S, (y+r*0.9)*S)],
              180, 360, fill=c + (255,), width=int(1.6*S))
        stroke(d, [(x-r*0.7, y+r*0.28), (x+r*0.7, y+r*0.28)], c, 1.4)
        for k in range(5):
            a = math.pi + (k+0.5)*math.pi/5
            stroke(d, [(x+math.cos(a)*r*0.7, y+r*0.28+math.sin(a)*r*0.7),
                       (x+math.cos(a)*r*0.95, y+r*0.28+math.sin(a)*r*0.95)], c, 1.1)
    elif area == 'monsoon':                      # three running waters
        for k in range(3):
            yy = y - r*0.4 + k*r*0.42
            wave(d, x, yy, r*1.25, 70+k)
    elif area == 'ashfall':                      # a flame
        stroke(d, [(x-r*0.32, y+r*0.5), (x-r*0.1, y-r*0.1), (x, y-r*0.62),
                   (x+r*0.14, y-r*0.05), (x+r*0.34, y+r*0.5)], c, 1.5)
        stroke(d, [(x-r*0.12, y+r*0.5), (x, y+r*0.05), (x+r*0.14, y+r*0.5)], c, 1.1)
    elif area == 'standingsky':                  # bent grass
        for k in (-1, 0, 1):
            stroke(d, [(x+k*r*0.36, y+r*0.5),
                       (x+k*r*0.36+r*0.22, y+r*0.05),
                       (x+k*r*0.36+r*0.62, y-r*0.35)], c, 1.2)
    else:                                        # a tusk, for the Unlit
        stroke(d, [(x-r*0.55, y-r*0.35), (x-r*0.1, y+r*0.3), (x+r*0.55, y+r*0.5)], c, 1.8)
        stroke(d, [(x-r*0.55, y-r*0.35), (x-r*0.25, y-r*0.05)], c, 1.0)

def legend(d):
    """A cartouche in the open sea, bottom right.

    It lived in a right-hand gutter first and ran off the plate: the continent
    reaches gx 3, and Forgehold and Lanternhold sit under where the crests
    were. The empty water below them is the only clear space big enough.
    """
    w, h = 470, 604
    x = Wpx - w - 118
    y = Hpx - h - 150
    d.rectangle([(x * S, y * S), ((x + w) * S, (y + h) * S)],
                fill=(231, 214, 176, 224), outline=INK + (255,), width=int(2.2 * S))
    d.rectangle([((x + 9) * S, (y + 9) * S), ((x + w - 9) * S, (y + h - 9) * S)],
                outline=INK_SOFT + (165,), width=int(0.9 * S))
    halo_text(d, (x + w / 2, y + 40), 'THE SIX', 'caps', 21, INK, 'mm', 4)
    halo_text(d, (x + w / 2, y + 66), 'and the realms they keep', 'label', 16,
              INK_SOFT, 'mm')
    stroke(d, [(x + 60, y + 84), (x + w - 60, y + 84)], INK_SOFT, 0.9, 190)
    ry = y + 108
    for area in ('dawnstair', 'monsoon', 'ashfall', 'standingsky', 'boneyard'):
        name, title_ = DEITY[area]
        crest(d, x + 52, ry + 26, 27, area)
        text(d, (x + 94, ry + 12), name, 'bold', 18, PEN[area], 'lm')
        text(d, (x + 94, ry + 33), title_, 'label', 15, INK_SOFT, 'lm')
        text(d, (x + 94, ry + 53), AREAS[area]['name'], 'label', 15,
             lerp(PEN[area], INK_SOFT, .45), 'lm')
        ry += 72
    stroke(d, [(x + 60, ry + 2), (x + w - 60, ry + 2)], INK_SOFT, 0.9, 190)
    text(d, (x + 94, ry + 24), 'The Emberlands', 'bold', 18, PEN['emberlands'], 'lm')
    text(d, (x + 94, ry + 45), 'no god claims it', 'label', 15, INK_SOFT, 'lm')
    n = sum(1 for z in ZONES.values() if z.get('built') and z['cell'])
    d.ellipse([((x + 44) * S, (ry + 74) * S), ((x + 62) * S, (ry + 92) * S)],
              fill=PEN['emberlands'] + (70,), outline=INK_SOFT + (140,), width=int(0.8 * S))
    text(d, (x + 94, ry + 83), f'coloured ground: built, {n} of '
         f'{sum(1 for z in ZONES.values() if z["cell"])}', 'label', 15, INK_SOFT, 'lm')

def compass(d, x, y, r):
    """A plain rose. North is up, which is worth stating on a map whose engine
    calls +z south."""
    for k in range(8):
        a = k * math.pi / 4 - math.pi / 2
        ln = r if k % 2 == 0 else r * 0.52
        w = 2.0 if k % 2 == 0 else 1.0
        tip = (x + math.cos(a) * ln, y + math.sin(a) * ln)
        b1 = (x + math.cos(a + 0.42) * ln * 0.24, y + math.sin(a + 0.42) * ln * 0.24)
        b2 = (x + math.cos(a - 0.42) * ln * 0.24, y + math.sin(a - 0.42) * ln * 0.24)
        stroke(d, [b1, tip, b2], INK, w)
    d.ellipse([((x - r * 0.24) * S, (y - r * 0.24) * S),
               ((x + r * 0.24) * S, (y + r * 0.24) * S)],
              outline=INK + (255,), width=int(1.2 * S))
    d.ellipse([((x - r * 1.18) * S, (y - r * 1.18) * S),
               ((x + r * 1.18) * S, (y + r * 1.18) * S)],
              outline=INK_SOFT + (150,), width=int(0.8 * S))
    halo_text(d, (x, y - r * 1.44), 'N', 'caps', 17, INK, 'mm')


def frame(d):
    """A plain double rule with corner lozenges - a border, not a distraction."""
    for inset, w, a in ((26, 3.2, 255), (38, 1.1, 210), (44, 0.8, 150)):
        d.rectangle([(inset * S, inset * S), ((Wpx - inset) * S, (Hpx - inset) * S)],
                    outline=INK + (a,), width=int(w * S))
    for cx, cy in ((38, 38), (Wpx - 38, 38), (38, Hpx - 38), (Wpx - 38, Hpx - 38)):
        for rr, w in ((13, 1.6), (7, 1.0)):
            d.polygon([((cx) * S, (cy - rr) * S), ((cx + rr) * S, cy * S),
                       (cx * S, (cy + rr) * S), ((cx - rr) * S, cy * S)],
                      outline=INK + (255,), width=int(w * S))

def title(d):
    x, y = MARGIN - 130, MARGIN - 150
    halo_text(d, (x + 150, y + 40), 'EMBERFALL', 'caps', 52, INK, 'mm', 8)
    stroke(d, [(x + 10, y + 76), (x + 290, y + 76)], INK, 1.4)
    stroke(d, [(x + 40, y + 82), (x + 260, y + 82)], INK_SOFT, 0.8, 180)
    halo_text(d, (x + 150, y + 104), 'the six realms and their zones',
              'label', 19, INK_SOFT, 'mm')

# ================================================================ assemble
def build():
    img = parchment().convert('RGBA')
    COAST = coastline()
    COAST.sort(key=lambda c: -len(c[0]))

    land = Image.new('RGBA', img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(land)
    for xs, ys in COAST:
        jx, jy = jitter(xs, ys, 2.6, 11 + int(xs[0]))
        poly(dl, jx, jy, fill=(228, 210, 170, 205))
    img = Image.alpha_composite(img, land)
    d = ImageDraw.Draw(img, 'RGBA')

    for xs, ys in COAST:                       # coast + its echoes out to sea
        jx, jy = jitter(xs, ys, 2.6, 11 + int(xs[0]))
        cx, cy = jx.mean(), jy.mean()
        for k, (off, a, wd) in enumerate(((8, 95, 1.0), (17, 60, 0.9), (27, 35, 0.8))):
            ux, uy = jx - cx, jy - cy
            ln = np.hypot(ux, uy) + 1e-9
            ex, ey = jx + ux / ln * off, jy + uy / ln * off
            ex, ey = jitter(ex, ey, 2.4, 400 + k * 13 + int(xs[0]))
            poly(d, ex, ey, outline=INK_SOFT + (a,), width=wd)
        poly(d, jx, jy, outline=INK + (240,), width=1.8)

    # THE WASH: a built zone is tinted with its element, and nothing else is.
    #
    # Faint on purpose - it should answer "how far along are we" at a glance
    # without competing with the ink or turning the map into a chart. Blurred
    # so the edges are weather rather than borders, and multiplied by the land
    # mask so no colour reaches the sea.
    wash = Image.new('RGBA', img.size, (0, 0, 0, 0))
    dw = ImageDraw.Draw(wash)
    any_built = False
    for i, z in enumerate(ZONES.values()):
        if not z.get('built') or not z['cell']:
            continue
        any_built = True
        cx, cy = to_px(*at(z))
        r = 0.70 * P * (z['size'] / 512.0) ** 0.30
        bx, by = blob(cx, cy, r * 0.97, 900 + list(ZONES).index(z['id']) * 7)
        wx, wy = warp(bx, by)
        poly(dw, wx, wy, fill=PEN[z["area"]] + (40,))
    if any_built:
        wash = wash.filter(ImageFilter.GaussianBlur(15 * S))
        wa = np.asarray(wash).astype(np.float32)
        land = ndimage.zoom(MASK, (img.size[1] / MASK.shape[0], img.size[0] / MASK.shape[1]),
                            order=1)
        land = np.clip(land, 0, 1)[:wa.shape[0], :wa.shape[1]]
        if land.shape != wa.shape[:2]:
            land = np.pad(land, ((0, wa.shape[0] - land.shape[0]),
                                 (0, wa.shape[1] - land.shape[1])), mode='edge')
        wa[..., 3] *= land
        wash = Image.fromarray(np.clip(wa, 0, 255).astype('uint8'))
        img = Image.alpha_composite(img, wash)
        d = ImageDraw.Draw(img, 'RGBA')

    for z in ZONES.values():                   # terrain, over the wash
        scatter(d, z)

    for i, l in enumerate(LINKS):              # the walls, and the notch in each
        a, b = ZONES[l['a']], ZONES[l['b']]
        if not (a['cell'] and b['cell']):
            continue
        ridge(d, at(a), at(b), l['cross_area'], 0.0, 100 + i)

    for i, l in enumerate(LINKS):              # trails through the passes
        a, b = ZONES[l['a']], ZONES[l['b']]
        if not (a['cell'] and b['cell']):
            continue
        if a['kind'] in ('city', 'outpost') or b['kind'] in ('city', 'outpost') \
           or l['cross_area']:
            road(d, a, b, 700 + i)

    spots = {}
    for z in ZONES.values():                   # towns
        if z['kind'] in ('city', 'outpost'):
            spots[z['id']] = settlement(d, z)

    for z in ZONES.values():                   # names
        gx, gy = at(z)
        cx, cy = to_px(gx, gy)
        wx, wy = warp(cx, cy); wx, wy = float(wx), float(wy)
        col = PEN[z['area']]
        big = z['kind'] == 'city'
        dy = 34 if z['id'] in spots else 0
        halo_text(d, (wx, wy + dy), z['name'], 'bold' if big else 'label',
                  20 if big else 19, col, 'mm')
        if z['kind'] not in ('city', 'sanctuary'):
            lo, hi = z['levels']
            halo_text(d, (wx, wy + dy + 20), f'{lo}–{hi}', 'serif', 14,
                      lerp(col, (120, 100, 78), .45), 'mm')

    # the realm names, big and faint, under the zone labels
    for key, meta in AREAS.items():
        cs = [at(z) for z in ZONES.values() if z['area'] == key and z['cell']]
        mx = sum(c[0] for c in cs) / len(cs)
        my = sum(c[1] for c in cs) / len(cs)
        px_, py_ = to_px(mx, my)
        wx, wy = warp(px_, py_ - 0.36 * P)
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1.5, -1.5),
                       (1.5, 1.5), (-1.5, 1.5), (1.5, -1.5)):
            text(d, (float(wx) + ox, float(wy) + oy), meta['name'].upper(),
                 'caps', 26, (232, 216, 178), 'mm', 200, 6)
        text(d, (float(wx), float(wy)), meta['name'].upper(), 'caps', 26,
             PEN[key], 'mm', 190, 6)

    # the Grove says what it is, since nothing connects to it
    gz = ZONES['the_grove']
    gx, gy = to_px(*at(gz))
    wx, wy = warp(gx, gy)
    halo_text(d, (float(wx), float(wy) + 64), 'no road reaches it', 'label', 15,
              INK_SOFT, 'mm')

    legend(d)
    compass(d, MARGIN - 120, Hpx - MARGIN - 470, 46)
    title(d)
    frame(d)
    return img

if __name__ == '__main__':
    out = build().convert('RGB').resize((Wpx, Hpx), Image.LANCZOS)
    out.save(os.path.join(OUT, 'world-atlas.png'))
    print('atlas', out.size)
