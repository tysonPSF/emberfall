"""Gives every outdoor zone an uneven mountain edge instead of a square wall.

    python3 tools/zones/outline.py            # write data/zone_outlines.json and report each zone
    python3 tools/zones/outline.py --check    # report only

A zone is a square `size` m across, and its mountains used to rise at the
same 28 m in from every side (`Zone.height_at`), so every zone felt like the
same box. Here each side gets an inset profile: how far in from that square
line the mountains start, sampled every STEP m along the side. Ridges (spurs)
reach into the zone, the corners are rounded, and the whole line wobbles.
`Zone.edge_depth` reads the profiles; this file is the only thing that makes
them, so rerun it after moving anything near a zone's edge.

Nothing a zone places is buried: landmarks, npcs and their patrols, the bind
point, roads, rivers, lakes, fields, ground patches, named or night spawns,
and the arrival points of every zone line into the zone hold the mountains
back (`_limits`), and a pass stays exactly as it was. Ordinary spawns don't:
`Zone._build_spawns` walks one that a ridge covers back onto open ground
(rerun spawn_fill.py afterwards for any ground left emptier). Caves and
interiors have no mountains and get no outline.

The shapes are seeded by the zone id, so a rerun gives the same edges unless
the zone's content changed.
"""
import glob, json, math, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = f"{ROOT}/data/zone_outlines.json"
STEP = 8          # m between samples along a side
FOOT = 28.0       # the mountains' foot from the square edge with no inset (Zone.height_at)
CLEAR = 6.0       # extra open ground kept round anything placed
PASS_CLEAR = 40.0  # open edge either side of a pass's gap
SLOPE = 0.9       # the steepest an inset may change per meter along a side (a ridge's flank)
SIDES = ("n", "s", "e", "w")


def _poly_inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _polyline(points, spacing=6.0):
    out = []
    for a, b in zip(points, points[1:]):
        n = max(1, int(math.dist(a, b) / spacing))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    if points:
        out.append(tuple(points[-1]))
    return out


def keep_clear(z, arrivals):
    """Points the mountains must stay back from, as (x, z, radius)."""
    pts = []
    add = lambda p, r: pts.append((float(p[0]), float(p[1]), float(r)))
    if z.get("bind_point"):
        add(z["bind_point"], float(z.get("flat_radius", 26)) + 10)
    for lm in z.get("landmarks", []):
        add(lm["pos"], 30.0 * float(lm.get("size", 1.0)))
        for key in ("y_at",):
            for p in lm.get(key, []):
                add(p, 8)
    for n in z.get("npcs", []):
        add(n["pos"], 10)
        for p in n.get("patrol", []):
            add(p, 8)
    for s in z.get("spawns", []):
        if s.get("when") or any(MOBS.get(m, {}).get("named") for m in s["pool"]):
            add(s["pos"], float(s.get("wander", 8)) + 10)
    for road in z.get("roads", []):
        for p in _polyline(road["points"]):
            add(p, float(road.get("width", 4)) * 0.5 + 6)
    for river in z.get("rivers", []):
        for p in _polyline(river["points"]):
            add(p, float(river.get("width", 10)) * 0.5 + float(river.get("bank", 6)) + 4)
    for lake in z.get("lakes", []):
        poly = lake["points"]
        for p in _polyline(poly + poly[:1]):
            add(p, float(lake.get("bank", 8)) + 6)
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x = min(xs)
        while x <= max(xs):
            y = min(ys)
            while y <= max(ys):
                if _poly_inside((x, y), poly):
                    add((x, y), 6)
                y += 8
            x += 8
    for f in z.get("fields", []):
        add(f["pos"], math.hypot(*f["size"]) * 0.5 + 6)
    for g in z.get("ground_patches", []):
        add(g["pos"], float(g["radius"]) + 4)
    for p in arrivals:
        add(p, 16)
    return pts


def halves(z):
    """Half a zone east to west and north to south: its "extent" [x, z], else its square size."""
    size = float(z.get("size", 384))
    ext = z.get("extent", [size, size])
    return float(ext[0]) * 0.5, float(ext[1]) * 0.5


def side_geometry(hx, hz):
    """Each side's half length (along it) and the distance of its foot from the middle."""
    return {"n": (hx, hz - FOOT), "s": (hx, hz - FOOT), "e": (hz, hx - FOOT), "w": (hz, hx - FOOT)}


def side_of(x, y, hx, hz):
    """Which side a point on the edge (a pass, a zone line) is on, and where along it: the nearer side (Zone.is_north_south)."""
    if hz - abs(y) <= hx - abs(x):
        return ("s" if y > 0 else "n"), x
    return ("e" if x > 0 else "w"), y


def _count(side_half):
    return int(round(2 * side_half / STEP)) + 1


def _limits(z, hx, hz, arrivals):
    """The deepest each side's inset may go at each sample, from what's placed."""
    geo = side_geometry(hx, hz)
    lim = {s: [geo[s][1] * 0.45] * _count(geo[s][0]) for s in SIDES}
    for (x, y, r) in keep_clear(z, arrivals):
        r += CLEAR
        # how far in from each side's foot line the point stands
        room = {"n": geo["n"][1] + y, "s": geo["s"][1] - y, "e": geo["e"][1] - x, "w": geo["w"][1] + x}
        along = {"n": x, "s": x, "e": y, "w": y}
        for s in SIDES:
            if room[s] - r > geo[s][1] * 0.45:
                continue
            cap = max(0.0, room[s] - r)
            lo = int(math.floor((along[s] - r + geo[s][0]) / STEP))
            hi = int(math.ceil((along[s] + r + geo[s][0]) / STEP))
            for i in range(max(0, lo), min(len(lim[s]), hi + 1)):
                lim[s][i] = min(lim[s][i], cap)
    for ps in z.get("passes", []):
        width = float(ps[2]) if len(ps) > 2 else 9.0
        s, at = side_of(float(ps[0]), float(ps[1]), hx, hz)
        for i in range(len(lim[s])):
            if abs(-geo[s][0] + i * STEP - at) < width + 14 + PASS_CLEAR:
                lim[s][i] = 0.0
    return lim


def _raw(zid, hx, hz, city, lim):
    """The shape a side takes: ridges where there's room for them (lim), a wobble, rounded corners."""
    rng = random.Random(zid)
    scale = min(1.0, max(0.45, min(hx, hz) / 256.0)) * (0.55 if city else 1.0)  # a narrow canyon keeps its ridges small
    geo = side_geometry(hx, hz)
    corner = {c: rng.uniform(34, 80) * scale for c in ("ne", "nw", "se", "sw")}
    ends = {"n": ("nw", "ne"), "s": ("sw", "se"), "e": ("ne", "se"), "w": ("nw", "sw")}
    raw = {}
    for s in SIDES:
        half = geo[s][0]
        count = _count(half)
        prof = [0.0] * count
        ph = [rng.uniform(0, math.tau) for _ in range(3)]
        wob = rng.uniform(6, 16) * scale
        ridges = []
        taken = [False] * count
        for _ in range(int(2 * half / 120) + rng.randint(0, 1)):
            # a ridge goes where the ground behind the edge is empty enough to hold it, not on a pass or a camp
            room = [0.0 if taken[i] else max(0.0, lim[s][i] - 12) ** 2 for i in range(count)]
            if sum(room) <= 0:
                break
            pick = rng.uniform(0, sum(room))
            i = 0
            while pick > room[i]:
                pick -= room[i]
                i += 1
            c = -half + i * STEP
            wl, wr = rng.uniform(28, 75) * scale, rng.uniform(28, 75) * scale  # its two flanks, each its own length
            ridges.append((c, wl, wr, rng.uniform(40, 115) * scale))
            for j in range(count):
                if -wl * 0.8 < -half + j * STEP - c < wr * 0.8:
                    taken[j] = True
        for i in range(count):
            a = -half + i * STEP
            u = a / half
            v = wob * (0.5 + 0.5 * math.sin(u * 2.3 + ph[0])) + wob * 0.6 * (0.5 + 0.5 * math.sin(u * 5.1 + ph[1]))
            for (c, wl, wr, d) in ridges:  # a ridge: a rounded spur of mountain reaching in
                t = (c - a) / wl if a < c else (a - c) / wr
                if t < 1.0:
                    v = max(v, d * (0.5 + 0.5 * math.cos(t * math.pi)) * (0.85 + 0.15 * math.sin(a * 0.11 + ph[2])))
            for (end, sign) in ((ends[s][0], -1), (ends[s][1], 1)):  # the corners, rounded to an arc of radius R
                R = corner[end]
                from_end = half - sign * a  # distance along the side from that corner's square edge
                k = FOOT + R - from_end
                if k > 0:
                    v = max(v, R - math.sqrt(max(0.0, R * R - min(k, R) ** 2)))
            prof[i] = v
        raw[s] = prof
    return raw


def _soft_min(a, b, k):
    """min(a, b), rounded over k m where they meet (never above either)."""
    h = max(0.0, min(1.0, 0.5 + 0.5 * (b - a) / k))
    return min(min(a, b), b + (a - b) * h - k * h * (1 - h))


def outline(zid, z, arrivals, city):
    hx, hz = halves(z)
    lim = _limits(z, hx, hz, arrivals)
    raw = _raw(zid, hx, hz, city, lim)
    out = {"step": STEP}
    for s in SIDES:
        # a ridge held back by something rounds off before it rather than being cut flat
        v = [_soft_min(a, b, 14.0) for a, b in zip(raw[s], lim[s])]
        for _ in range(3):  # smoothed, then never past what holds it back, and no flank steeper than SLOPE
            v = [min(lim[s][i], (v[max(0, i - 1)] + 2 * v[i] + v[min(len(v) - 1, i + 1)]) / 4) for i in range(len(v))]
        for i in range(1, len(v)):
            v[i] = min(v[i], v[i - 1] + SLOPE * STEP)
        for i in range(len(v) - 2, -1, -1):
            v[i] = min(v[i], v[i + 1] + SLOPE * STEP)
        out[s] = [round(max(0.0, x), 1) for x in v]
    return out


def open_share(z, o):
    """The share of the old rectangle's open ground still open under outline o."""
    hx, hz = halves(z)
    inside = total = 0
    x = -(hx - FOOT)
    while x <= hx - FOOT:
        y = -(hz - FOOT)
        while y <= hz - FOOT:
            total += 1
            if edge_depth(o, (hx, hz), x, y) <= 0:
                inside += 1
            y += 4
        x += 4
    return inside / max(1, total)


def _inset(prof, step, half, along):
    f = (along + half) / step
    i = max(0, min(len(prof) - 2, int(math.floor(f))))
    t = max(0.0, min(1.0, f - i))
    return prof[i] + (prof[i + 1] - prof[i]) * t


def edge_depth(o, half, x, y):
    """How far (x, y) stands past the mountains' foot (negative: open ground). Zone.edge_depth in Python.
    half is the zone's half size, or (half east-west, half north-south) for a rectangle."""
    hx, hz = half if isinstance(half, (tuple, list)) else (half, half)
    bx, bz = hx - FOOT, hz - FOOT
    if not o:
        return max(abs(x) - bx, abs(y) - bz)
    st = o["step"]
    return max(-y - bz + _inset(o["n"], st, hx, x), y - bz + _inset(o["s"], st, hx, x),
               x - bx + _inset(o["e"], st, hz, y), -x - bx + _inset(o["w"], st, hz, y))


def load():
    """{zone id: outline} as written, for other tools (spawn_fill.py)."""
    if not os.path.exists(OUT):
        return {}
    return json.load(open(OUT))


MOBS = json.load(open(f"{ROOT}/data/mobs.json"))


def mountain_line(key, u):
    """The skyline of one range of mountains at u m along it from its pass: (crest, peak).
    crest scales the steep band at the mountains' foot (0.75-1.3); peak is how much a
    tall summit adds behind it (0 along most of the range). A border's range is keyed
    by both zones and measured from its pass, so the two sides see the same mountains."""
    rng = random.Random(key)
    ph = [rng.uniform(0, math.tau) for _ in range(3)]
    crest = 1.0 + 0.18 * math.sin(u * 0.013 + ph[0]) + 0.1 * math.sin(u * 0.037 + ph[1])
    peak = 0.0
    for _ in range(rng.randint(2, 4)):
        c = rng.choice((-1, 1)) * rng.uniform(80, 480)  # never over the pass itself
        w = rng.uniform(40, 95)
        t = abs(u - c) / w
        if t < 1.0:
            peak = max(peak, rng.uniform(50, 170) * (0.5 + 0.5 * math.cos(t * math.pi)))
        else:
            rng.uniform(50, 170)  # the same draws either way, so each peak's height doesn't hang on u
    return crest, peak


def skylines(zid, z, links):
    """Each side's crest and peak, sampled like the insets: shared with the zone across a border."""
    hx, hz = halves(z)
    geo = side_geometry(hx, hz)
    out = {}
    for s in SIDES:
        key, k = f"{zid}:{s}", 0.0
        if s in links:
            other = links[s]
            key = "|".join(sorted((zid, other)))
            for ps in z.get("passes", []):
                side, at = side_of(float(ps[0]), float(ps[1]), hx, hz)
                if side == s:
                    k = at
        half = geo[s][0]
        vals = [mountain_line(key, -half + i * STEP - k) for i in range(_count(half))]
        out["c" + s] = [round(v[0], 2) for v in vals]
        out["p" + s] = [round(v[1], 1) for v in vals]
    return out


def main():
    write = "--check" not in sys.argv
    layout = {z["id"]: z for z in json.load(open(f"{ROOT}/docs/world-layout.json"))["zones"]}
    zones = {}
    for f in sorted(glob.glob(f"{ROOT}/data/zones/*.json")):
        zones[os.path.basename(f)[:-5]] = json.load(open(f))
    edge_names = {"north": "n", "south": "s", "east": "e", "west": "w"}
    links = {}
    for l in json.load(open(f"{ROOT}/docs/world-layout.json"))["links"]:
        links.setdefault(l["a"], {})[edge_names[l["a_edge"]]] = l["b"]
        links.setdefault(l["b"], {})[edge_names[l["b_edge"]]] = l["a"]
    arrivals = {}
    for zid, z in zones.items():
        for zl in z.get("zone_lines", []):
            if "arrive" in zl and isinstance(zl["arrive"], list):
                arrivals.setdefault(zl["to"], []).append(zl["arrive"])
    result = {}
    for zid, z in zones.items():
        if z.get("tunnel") or z.get("interior"):
            continue
        city = layout.get(zid, {}).get("kind") == "city"
        o = outline(zid, z, arrivals.get(zid, []), city)
        o.update(skylines(zid, z, links.get(zid, {})))
        result[zid] = o
        deep = max(max(o[s]) for s in SIDES)
        print(f"{zid:20s} {int(z.get('size', 384)):4d} m  deepest ridge {deep:5.1f} m  open ground kept {open_share(z, o) * 100:5.1f}%")
    if write:
        with open(OUT, "w") as fh:
            fh.write("{\n")
            fh.write(",\n".join(f'  "{zid}": {json.dumps(o, separators=(", ", ": "))}' for zid, o in sorted(result.items())))
            fh.write("\n}\n")
        print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(result)} zones)")


if __name__ == "__main__":
    main()
