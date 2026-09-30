"""Makes a zone bigger without making what's in it bigger.

    python3 tools/zones/scale_zone.py thornwood 2          # a report: what would move where
    python3 tools/zones/scale_zone.py thornwood 2 --write  # rewrite the zone, its neighbors' arrivals and the layout

The open ground stretches by the factor: the size, the spaces between places,
roads, rivers, lakes, lone spawns and the number of trees and rocks. What's
built stays its own size and shape: landmarks standing close together (a
village, a camp and its tents, a ruin and its tower) are one settlement and
move as one piece, and the npcs, spawns, patrol points, fields, road points
and lights inside a settlement move with it, so a camp's people stay round
their fire. Anything within EDGE m of a side (passes, zone lines, the
rockslides and signposts in the passes) keeps its distance from that side, and
so do the arrival points in every other zone's zone lines into this one.

Afterwards run tools/world_layout.py (the size is changed in its ZONES table),
tools/zones/outline.py and tools/zones/spawn_fill.py --write (the new ground
needs monsters), and look at the zone.
"""
import glob, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EDGE = 40.0      # points this close to a side keep their distance from it
LINK = 12.0      # landmarks whose grounds come this close are one settlement
GENERATED = {"the_wallow": "tools/zones/blackwater.py", "duskwood": "tools/zones/blackwater.py", "the_rotfen": "tools/zones/blackwater.py",
             "murkhold": "tools/zones/blackwater.py", "duskhold": "tools/zones/blackwater.py",
             "broken_march": "tools/zones/west_march.py", "stormcut_gorge": "tools/zones/west_march.py", "the_grove": "tools/zones/the_grove.py"}
NEVER_GROUP = {"bridge", "signpost", "rockslide"}  # they sit on a road or in a pass, which stretches: they go with it


def reach(lm):
    """How far a landmark's own ground spreads (Zone.height_at levels 30 m x its size)."""
    return 22.0 * float(lm.get("size", 1.0)) if lm["type"] not in NEVER_GROUP else 0.0


class Scaler:
    def __init__(self, z, f):
        self.f = f
        self.half = float(z.get("size", 384)) * 0.5
        self.new_half = self.half * f
        lms = [l for l in z.get("landmarks", []) if l["type"] not in NEVER_GROUP]
        # settlements: landmarks linked when their grounds come within LINK m
        group = list(range(len(lms)))
        find = lambda i: i if group[i] == i else find(group[i])
        for i in range(len(lms)):
            for j in range(i + 1, len(lms)):
                if math.dist(lms[i]["pos"], lms[j]["pos"]) < reach(lms[i]) + reach(lms[j]) + LINK:
                    group[find(i)] = find(j)
        self.settlements = {}
        for i, l in enumerate(lms):
            self.settlements.setdefault(find(i), []).append(l)
        self.centers = {}
        for g, members in self.settlements.items():
            cx = sum(m["pos"][0] for m in members) / len(members)
            cy = sum(m["pos"][1] for m in members) / len(members)
            self.centers[g] = (cx, cy)

    def settlement_of(self, p, pad=8.0):
        best = None
        for g, members in self.settlements.items():
            for m in members:
                d = math.dist(p, m["pos"]) - reach(m) - pad
                if d < 0 and (best is None or d < best[0]):
                    best = (d, g)
        return None if best is None else best[1]

    def edge_keep(self, v):
        """One coordinate stretched, or kept at its distance from a side it's near."""
        if abs(v) > self.half - EDGE:
            return math.copysign(self.new_half - (self.half - abs(v)), v)
        return v * self.f

    def near_edge(self, p):
        return max(abs(float(p[0])), abs(float(p[1]))) > self.half - EDGE

    def border(self, p):
        """A border's own point (a zone line in a pass, an arrival): it keeps its place on
        its pass, never moving with a settlement that happens to stand by the pass."""
        if self.near_edge(p):
            return [_r(self.edge_keep(float(p[0]))), _r(self.edge_keep(float(p[1])))]
        return self.point(p)  # a door inside the zone (a cave) goes with what it's in

    def point(self, p, g=None):
        """Where p goes: with its settlement (g, or the one it stands in), else stretched."""
        x, y = float(p[0]), float(p[1])
        if g is None:
            g = self.settlement_of((x, y))
        if g is not None:
            cx, cy = self.centers[g]
            return [_r(x + cx * (self.f - 1)), _r(y + cy * (self.f - 1))]
        return [_r(self.edge_keep(x)), _r(self.edge_keep(y))]

    def facing(self, p, face, new_p):
        """A point something faces: the same offset from where it now stands."""
        return [_r(new_p[0] + face[0] - p[0]), _r(new_p[1] + face[1] - p[1])]


def _r(v):
    v = round(v, 1)
    return int(v) if v == int(v) else v


def scale(z, f):
    s = Scaler(z, f)
    out = dict(z)
    out["size"] = _r(float(z.get("size", 384)) * f)
    area = f * f
    for key in ("trees", "rocks"):
        if key in z:
            out[key] = int(round(z[key] * area))
    if "grid" in z:
        out["grid"] = int(round(z["grid"] * f))
    if "bind_point" in z:
        out["bind_point"] = s.point(z["bind_point"])
    lm_group = {}
    for g, members in s.settlements.items():
        for m in members:
            lm_group[id(m)] = g
    lms = []
    for l in z.get("landmarks", []):
        n = dict(l)
        if l["type"] == "bridge":  # it stands where a road crosses a river, both stretched: it stretches with them
            n["pos"] = [_r(s.edge_keep(float(l["pos"][0]))), _r(s.edge_keep(float(l["pos"][1])))]
        else:
            n["pos"] = s.point(l["pos"], lm_group.get(id(l)))
        if "face" in l:
            n["face"] = s.facing(l["pos"], l["face"], n["pos"])
        if "y_at" in l:
            n["y_at"] = [s.facing(l["pos"], p, n["pos"]) for p in l["y_at"]]
        if "pieces" in l:  # a stilt city's pieces are laid where they stand: they move with it
            n["pieces"] = [[pc[0]] + s.facing(l["pos"], pc[1:3], n["pos"]) + list(pc[3:]) for pc in l["pieces"]]
        lms.append(n)
    out["landmarks"] = lms
    npcs = []
    for n in z.get("npcs", []):
        m = dict(n)
        m["pos"] = s.point(n["pos"])
        if "face" in n:
            m["face"] = s.facing(n["pos"], n["face"], m["pos"])
        if "patrol" in n:
            m["patrol"] = [s.point(p) for p in n["patrol"]]
        npcs.append(m)
    out["npcs"] = npcs
    spawns = []
    for e in z.get("spawns", []):
        m = dict(e)
        m["pos"] = s.point(e["pos"])
        if "face" in e:
            m["face"] = s.facing(e["pos"], e["face"], m["pos"])
        spawns.append(m)
    out["spawns"] = spawns
    for key in ("fields", "ground_patches", "lights", "chests"):
        if key in z:
            items = []
            for e in z[key]:
                m = dict(e)
                m["pos"] = s.point(e["pos"])
                if key == "ground_patches" and s.settlement_of(e["pos"]) is None:
                    m["radius"] = _r(float(e["radius"]) * f)  # a salt pan or a mud flat is land: it grows with it
                if "face" in e:
                    m["face"] = s.facing(e["pos"], e["face"], m["pos"])
                items.append(m)
            out[key] = items
    if "roads" in z:
        out["roads"] = [dict(r, points=[s.point(p) for p in r["points"]]) for r in z["roads"]]
    stretch = lambda p: [_r(s.edge_keep(float(p[0]))), _r(s.edge_keep(float(p[1])))]
    if "rivers" in z:
        out["rivers"] = [dict(r, points=[stretch(p) for p in r["points"]]) for r in z["rivers"]]
    if "lakes" in z:
        def island(i):  # grows with the lake, unless a settlement stands on it
            if s.settlement_of((i[0], i[1])) is not None:
                return s.point((i[0], i[1])) + [i[2]]
            return [_r(i[0] * f), _r(i[1] * f), _r(i[2] * f)]
        out["lakes"] = [dict(l, points=[stretch(p) for p in l["points"]], **({"islands": [island(i) for i in l["islands"]]} if "islands" in l else {}))
                        for l in z["lakes"]]
    if "passes" in z:
        out["passes"] = [[_r(s.edge_keep(float(p[0]))), _r(s.edge_keep(float(p[1])))] + list(p[2:]) for p in z["passes"]]
    if "zone_lines" in z:
        out["zone_lines"] = [dict(zl, pos=s.border(zl["pos"]), **({"refused_to": s.point(zl["refused_to"])} if "refused_to" in zl else {}))
                             for zl in z["zone_lines"]]  # a cave's door, and where a guard turns you back from it, go with its cave
    if "terraces" in z:
        t = dict(z["terraces"])
        for key in ("start", "end"):
            if key in t:
                t[key] = _r(float(t[key]) * f)
        out["terraces"] = t
    return out, s


def grow(zones, authored, sizes):
    """For a generator: zones ({id: data} built at `authored` sizes) scaled to `sizes`
    in place, and the arrivals between them moved to match."""
    for zid in list(zones):
        f = float(sizes[zid]) / float(authored[zid])
        if abs(f - 1.0) < 1e-6:
            continue
        zones[zid], sc = scale(zones[zid], f)
        for oid, oz in zones.items():
            if oid != zid:
                oz["zone_lines"] = [arrival(sc, zl) if zl.get("to") == zid else zl for zl in oz.get("zone_lines", [])]
    return zones


def arrival(s, zl):
    """A neighbor's zone line into the scaled zone, with its arrival moved to match."""
    m = dict(zl)
    if isinstance(zl.get("arrive"), list):
        m["arrive"] = s.border(zl["arrive"])
        if isinstance(zl.get("arrive_face"), list):
            m["arrive_face"] = s.facing(zl["arrive"], zl["arrive_face"], m["arrive"])
    return m


def dumps(v, ind=0):
    """JSON the way the zone files read: short lists and objects on one line."""
    flat = json.dumps(v, ensure_ascii=False)
    if len(flat) + ind <= 150 or not isinstance(v, (dict, list)) or not v:
        return flat
    pad = "  " * (ind + 1)
    if isinstance(v, dict):
        body = ",\n".join(f"{pad}{json.dumps(k)}: {dumps(x, ind + 1)}" for k, x in v.items())
        return "{\n" + body + "\n" + "  " * ind + "}"
    body = ",\n".join(pad + dumps(x, ind + 1) for x in v)
    return "[\n" + body + "\n" + "  " * ind + "]"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--write" in sys.argv
    zid, f = args[0], float(args[1])
    if zid in GENERATED:
        sys.exit(f"{zid} is written by {GENERATED[zid]}: set its size in tools/world_layout.py and rerun that generator (it scales what it writes)")
    path = f"{ROOT}/data/zones/{zid}.json"
    z = json.load(open(path))
    out, s = scale(z, f)
    print(f"{zid}: {int(z['size'])} m -> {out['size']} m, trees {z.get('trees')} -> {out.get('trees')}")
    for g, members in s.settlements.items():
        c = s.centers[g]
        print(f"  settlement at ({c[0]:.0f}, {c[1]:.0f}) -> ({c[0] * f:.0f}, {c[1] * f:.0f}): " + ", ".join(m["type"] for m in members))
    touched = []
    for other in sorted(glob.glob(f"{ROOT}/data/zones/*.json")):
        if other == path:
            continue
        text = open(other).read()
        oz = json.loads(text)
        new_text = text
        for zl in oz.get("zone_lines", []):
            if zl.get("to") != zid or not isinstance(zl.get("arrive"), list):
                continue
            m = arrival(s, zl)
            print(f"  {os.path.basename(other)[:-5]}: arrive {zl['arrive']} -> {m['arrive']}")
            # splice the numbers in place, so a hand-formatted neighbor keeps its layout
            for key in ("arrive", "arrive_face"):
                if key in zl:
                    pat = re.compile(r'("to":\s*"%s"[^{}]*?"%s":\s*)\[[^\]]*\]' % (re.escape(zid), key))
                    new_text, n = pat.subn(lambda mt: mt.group(1) + json.dumps(m[key]).replace(",", ", ").replace(",  ", ", "), new_text, count=1)
                    if n != 1:
                        sys.exit(f"{other}: couldn't find the {key} of its zone line to {zid}")
        if new_text != text:
            json.loads(new_text)
            touched.append((other, new_text))
    if not write:
        print("(a report: --write changes the files)")
        return
    open(path, "w").write(dumps(out) + "\n")
    for other, text in touched:
        open(other, "w").write(text)
    lay = f"{ROOT}/tools/world_layout.py"
    t = open(lay).read()
    pat = re.compile(r"""(\('%s',\s*(?:'[^']*'|"[^"]*"),\s*'[^']*',\s*\([^)]*\),\s*)(\d+)""" % re.escape(zid))  # a name with an apostrophe is in double quotes
    t2, n = pat.subn(lambda mt: mt.group(1) + str(int(out["size"])), t, count=1)
    if n == 1:
        open(lay, "w").write(t2)
    print(f"wrote {zid} and {len(touched)} neighbor(s); layout size {'updated' if n == 1 else 'NOT found'}")


if __name__ == "__main__":
    main()
