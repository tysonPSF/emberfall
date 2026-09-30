"""Fills a zone's empty ground with monsters.

    python3 tools/zones/spawn_fill.py            # report: new spawns each zone would get
    python3 tools/zones/spawn_fill.py --write    # add them to the hand-made zone files

Walks the open ground on an 8 m grid (20 m in from the mountains' foot, which
tools/zones/outline.py shapes per zone; off
water, rivers, fields, and 45 m clear of towns, camps and the arrival points
at borders) and, while any of it lies more than TARGET m from a spawn, puts a
new spawn at the farthest spot, with the monsters of the nearest ordinary
spawn (not a named one, not a night one): so a region keeps its own
creatures, levels and respawn. 65 m is about Thornwood's density, which plays
well; High Terrace and the 30-50 zones had a third to half of their ground
emptier than that (2026-09-29).

Zones written by a generator (tools/zones/blackwater.py, west_march.py) call
fill() themselves as they write, so a rerun keeps the extra spawns; --write
skips them. Rerun after changing a zone's spawns, lakes or camps.
"""
import glob, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outline  # noqa: E402  the zones' uneven mountain edges

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET, KEEP_OUT, STEP, EDGE = 65, 45, 8, 48
GENERATED = {"murkhold", "the_wallow", "duskwood", "duskhold", "the_rotfen", "broken_march", "stormcut_gorge", "the_grove"}


def _inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1:
            c = not c
    return c


def _seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy or 1
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _blocked(z, p, npcs):
    for lake in z.get("lakes", []):
        if _inside(p, lake["points"]) and not any(math.dist(p, (i[0], i[1])) < i[2] - 4 for i in lake.get("islands", [])):
            return True
    for r in z.get("rivers", []):
        pts = r["points"]
        if any(_seg(p, pts[i], pts[i + 1]) < r.get("width", 10) / 2 + r.get("bank", 10) * 0.5 + 2 for i in range(len(pts) - 1)):
            return True
    for f in z.get("fields", []):
        if math.dist(p, f["pos"]) < max(f["size"]) / 1.4 + 6:
            return True
    for n in npcs:
        if math.dist(p, n) < KEEP_OUT:
            return True
    for zl in z.get("zone_lines", []):
        if math.dist(p, zl["arrive"]) < KEEP_OUT - 10 or math.dist(p, zl["pos"]) < KEEP_OUT - 10:
            return True
    return False


def fill(z, mobs, zid=""):
    """The spawns to add to zone data z (a dict), as a list; z is not changed.
    zid names its outline in data/zone_outlines.json (none: the square edge)."""
    def ordinary(s):
        return s.get("when") != "night" and not any(mobs.get(m, {}).get("named") for m in s["pool"])
    base = [s for s in z.get("spawns", []) if ordinary(s)]
    if not base:
        return []
    npcs = [n["pos"] for n in z.get("npcs", [])] + ([z["bind_point"]] if z.get("bind_point") else [])
    npcs += [l["pos"] for l in z.get("landmarks", []) if l["type"] in ("camp", "outpost", "waystation", "hearth_plaza", "market",
                                                                     "stilt_village", "stilt_city")]
    half = z.get("size", 512) / 2 - EDGE
    edges = outline.load().get(zid)
    grid = []
    x = -half
    while x <= half:
        y = -half
        while y <= half:
            if outline.edge_depth(edges, z.get("size", 512) / 2, x, y) <= -(EDGE - outline.FOOT) and not _blocked(z, (x, y), npcs):
                grid.append((x, y))
            y += STEP
        x += STEP
    pts = [s["pos"] for s in z.get("spawns", []) if s.get("when") != "night"]
    added = []
    while grid:
        far = max(grid, key=lambda g: min(math.dist(g, p) for p in pts))
        if min(math.dist(far, p) for p in pts) <= TARGET:
            break
        near = min(base, key=lambda s: math.dist(s["pos"], far))
        e = {"pos": [round(far[0]), round(far[1])], "pool": dict(near["pool"]), "respawn": near.get("respawn", 90), "wander": near.get("wander", 14)}
        added.append(e)
        pts.append(e["pos"])
    return added


def main():
    write = "--write" in sys.argv
    layout = {z["id"]: z for z in json.load(open(f"{ROOT}/docs/world-layout.json"))["zones"]}
    mobs = json.load(open(f"{ROOT}/data/mobs.json"))
    total = 0
    for f in sorted(glob.glob(f"{ROOT}/data/zones/*.json")):
        zid = os.path.basename(f)[:-5]
        if zid not in layout or layout[zid]["kind"] == "city" or not layout[zid].get("cell"):
            continue
        text = open(f).read()
        z = json.loads(text)
        added = fill(z, mobs, zid)
        total += len(added)
        if added:
            print("%-16s +%d%s" % (zid, len(added), "  (its generator adds these)" if zid in GENERATED else ""))
        if not write or not added or zid in GENERATED:
            continue
        if json.dumps(z, indent=2) + "\n" == text:  # the file survives a load and dump: write it as data
            z["spawns"] += added
            open(f, "w").write(json.dumps(z, indent=2) + "\n")
        else:  # hand-formatted: add the lines at the head of its spawn list, touching nothing else
            i = text.index('"spawns": [') + len('"spawns": [')
            nl = text.index("\n", i)
            nxt = text[nl + 1:]
            ind = nxt[:len(nxt) - len(nxt.lstrip())] or "    "
            text2 = text[:i] + "".join("\n" + ind + json.dumps(e) + "," for e in added) + text[i:]
            json.loads(text2)
            open(f, "w").write(text2)
    print("%d new spawns%s" % (total, "" if write else " (a report: --write adds them)"))


if __name__ == "__main__":
    main()
