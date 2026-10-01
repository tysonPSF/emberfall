"""Mirror Flats' shoreline, shore and islands, made to look like a place.

    python3 tools/zones/mirror_flats_shape.py            # write data/zones/mirror_flats.json
    python3 tools/zones/mirror_flats_shape.py --check    # report only

The flats were one octagon of hand-deep water over ground flattened level
by a single 440 m salt patch, so the lake had hard straight edges and the
camps, tents and the forward camp stood in the water. Here:

  the shoreline  wanders round the middle of the zone (a few low harmonics,
                 seeded, sampled every 5 degrees), with bays and points, and
                 bends back from anything placed near it that must stay dry
  islands        dry ground under anything placed far out in the water (the
                 Glasswater camp, the island hut, the Duneskiff camp)
  the shore      gentle dunes (height_amplitude), salt-crust pans and mud
                 flats in patches instead of one, sparse dry grass, pebbles
                 and the odd bush, outcrops of crag and salt pillar

Boats, the salt pillars, the mirror images and the obelisk may stand in the
shallows: it is a mirror. Rerun outline.py and spawn_fill.py --write after.
"""
import json, math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outline  # noqa: E402
import scale_zone  # noqa: E402

ROOT = outline.ROOT
PATH = f"{ROOT}/data/zones/mirror_flats.json"
CENTER = (10.0, -40.0)
RADIUS = 330.0
LIMIT = 395.0          # the water stays this far in from the middle on each axis (the mountains' foot is ~484)
SOUTH_SHORE = 300.0    # and north of the entry camp's shore
DRY_PROPS = {"nomad_tent", "tent", "scout_tent", "campfire", "caravan_wagon", "market_stall"}
DRY_TYPES = {"waystation", "outpost", "ruins", "camp", "obelisk", "cabin", "watchtower"}


def _ease(v, lo, hi, soft=80.0):
    """v kept inside lo..hi by easing it in over the last `soft` m rather than clipping it flat."""
    if v > hi - soft:
        v = hi - soft + soft * math.tanh((v - (hi - soft)) / soft)
    if v < lo + soft:
        v = lo + soft - soft * math.tanh(((lo + soft) - v) / soft)
    return v


def shoreline(rng):
    ph = [rng.uniform(0, math.tau) for _ in range(4)]
    out = []
    for k in range(72):
        t = k * math.tau / 72
        r = RADIUS * (1 + 0.16 * math.sin(2 * t + ph[0]) + 0.11 * math.sin(3 * t + ph[1]) + 0.07 * math.sin(5 * t + ph[2]) + 0.04 * math.sin(9 * t + ph[3]))
        x = CENTER[0] + r * math.cos(t) * 1.08
        y = CENTER[1] + r * math.sin(t) * 0.95
        x = _ease(x, -LIMIT, LIMIT)
        y = _ease(y, -LIMIT, SOUTH_SHORE)
        out.append([round(x, 1), round(y, 1)])
    return out


def _angle_index(p, n):
    a = math.atan2((p[1] - CENTER[1]) / 0.95, (p[0] - CENTER[0]) / 1.08) % math.tau
    return int(round(a / math.tau * n)) % n


def dry_things(z):
    """What must not stand in water, with how much dry ground it needs."""
    out = []
    for l in z["landmarks"]:
        if l["type"] in DRY_TYPES:
            out.append((l["pos"], 26 if l["type"] in ("waystation", "camp") else 16))
        elif l["type"] == "prop" and l.get("id") in DRY_PROPS:
            out.append((l["pos"], 10))
    for n in z.get("npcs", []):
        out.append((n["pos"], 8))
    return out


def main():
    check = "--check" in sys.argv
    z = json.load(open(PATH))
    rng = random.Random("mirror_flats_shore")
    pts = shoreline(rng)
    lake = z["lakes"][0]
    islands = [i for i in lake.get("islands", []) if i[2] <= 12 or i[:2] == [-294.2, 198.3]]  # the salt-crust isles; earlier runs' are rebuilt below
    n = len(pts)
    bent = added = 0
    for (p, need) in dry_things(z):
        if not outline._poly_inside(p, pts) and min(math.dist(p, q) for q in outline._polyline(pts + pts[:1], 6)) > need:
            continue  # already on dry shore
        d_center = math.hypot((p[0] - CENTER[0]) / 1.08, (p[1] - CENTER[1]) / 0.95)
        i = _angle_index(p, n)
        r_here = math.hypot((pts[i][0] - CENTER[0]) / 1.08, (pts[i][1] - CENTER[1]) / 0.95)
        if d_center > r_here * 0.62:  # near the shore: the shore bends back round it
            for k in range(-3, 4):
                j = (i + k) % n
                rj = math.hypot((pts[j][0] - CENTER[0]) / 1.08, (pts[j][1] - CENTER[1]) / 0.95)
                want = max(40.0, d_center - (need + 22) / 1.0 - abs(k) * 4.0)
                if rj > want:
                    f = want / rj
                    pts[j] = [round(CENTER[0] + (pts[j][0] - CENTER[0]) * f, 1), round(CENTER[1] + (pts[j][1] - CENTER[1]) * f, 1)]
            bent += 1
        else:  # far out: an island under it
            if not any(math.dist(p, isl[:2]) < isl[2] - need * 0.5 for isl in islands):
                islands.append([round(p[0], 1), round(p[1], 1), need + 10])
                added += 1
    lake["points"] = pts
    lake["islands"] = islands
    lake["depth"] = 0.08
    # the shore: dunes, salt pans and mud in patches, dry grass, outcrops
    z["height_amplitude"] = 4.5
    z["sun_energy"] = 1.05  # the salt glares; the sand needs less sun to read as sand
    patches = []
    prng = random.Random("mirror_flats_patches")
    for k in range(14):
        while True:
            p = (prng.uniform(-420, 420), prng.uniform(-420, 440))
            if not outline._poly_inside(p, pts):
                break
        salt = k % 3 != 2
        patches.append({"pos": [round(p[0]), round(p[1])], "radius": round(prng.uniform(26, 60)), "color": "#f2eee8" if salt else "#a89a84",
                        "flatten": 0.5 if salt else 0.3, "bare": True})
    z["ground_patches"] = patches
    z["grass_colors"] = ["#8c7a5c", "#a28f6c"]  # sand, so the salt pans show white against it
    z["clutter"] = {"grass_b": {"density": 0.035, "patch": 0.7, "sway": 0.12, "range": 50, "tint": "ground", "scale": [0.6, 1.0]},
                    "pebbles": {"density": 0.025, "patch": 0.6, "range": 45, "tint": "ground", "scale": [0.8, 1.4]},
                    "bush_a": {"density": 0.0008, "patch": 0.7, "range": 110, "shadow": True, "scale": [0.6, 1.0]}}
    z["landmarks"] = [l for l in z["landmarks"] if not l.get("shore")]
    orng = random.Random("mirror_flats_outcrops")
    for k in range(12):
        while True:
            c = (orng.uniform(-400, 400), orng.uniform(-400, 400))
            if not outline._poly_inside(c, pts) and all(math.dist(c, p) > 50 for p, _ in dry_things(z)):
                break
        for m in range(orng.randint(2, 4)):
            pid = orng.choice(["crag_rock", "crag_rock", "salt_pillar", "boulder_b"])
            z["landmarks"].append({"type": "prop", "pos": [round(c[0] + orng.uniform(-9, 9), 1), round(c[1] + orng.uniform(-9, 9), 1)], "id": pid,
                                   "collide": "box", "yaw": orng.randint(0, 359), "scale": round(orng.uniform(0.8, 1.5), 2), "shore": True})
    print("shoreline %d points; bent round %d things near it, %d new islands under things far out; %d islands in all" % (n, bent, added, len(islands)))
    wet = [(l.get("id") or l["type"]) for l in z["landmarks"] if (l["type"] in DRY_TYPES or l.get("id") in DRY_PROPS)
           and outline._poly_inside(l["pos"], pts) and not any(math.dist(l["pos"], i[:2]) < i[2] for i in islands)]
    wet += [nn["id"] for nn in z["npcs"] if outline._poly_inside(nn["pos"], pts) and not any(math.dist(nn["pos"], i[:2]) < i[2] for i in islands)]
    print("still in the water:", wet or "nothing")
    if not check:
        open(PATH, "w").write(scale_zone.dumps(z) + "\n")
        print("wrote", os.path.relpath(PATH, ROOT))


if __name__ == "__main__":
    main()
