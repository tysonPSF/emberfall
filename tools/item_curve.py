"""Checks that gear gets better as the zones get harder.

    python3 tools/item_curve.py [--all]

Two reports:

1. Quest rewards and named drops against a curve: each item gets a score
   (AC, stats, health and mana / 5, regen x 4, haste / 2, a proc; for a weapon
   10 x damage / delay on top), each slot a line through the origin fitted to
   every reward's score against the level of the zone it comes from. Anything
   under 70% of its slot's line at its zone's level is listed: a ring from a
   14-18 zone should not be worse than one from a 5-10 zone. --all lists
   every reward, not only the weak ones.

2. The random gear monsters spawn wearing (mobs.json "gear" -> loot.json
   tables): any monster whose table can still hand out gear more than 12
   levels below it. Tables that climb with level ({"tiers": [[from level,
   {item: weight}], ...]}) are read at the monster's level, as the game does
   (World.loot_table), and generic gear climbs its ladder ("ladders": the
   best rung the level has reached, World.climb_ladder).

Exits non-zero when either report finds something, so it can guard a change.
"""
import collections, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
STAT = ["str", "sta", "agi", "wis", "int"]
WEAK = 0.7
STALE = 12


def load(path):
    return json.load(open(path))


items = {}
for f in sorted(glob.glob("data/items/*.json")):
    items.update(load(f))
npcs, quests, mobs = load("data/npcs.json"), load("data/quests.json"), load("data/mobs.json")
loot = load("data/loot.json")["tables"]
zones = {os.path.basename(f)[:-5]: load(f) for f in glob.glob("data/zones/*.json")}
npc_zone, mob_zones = {}, collections.defaultdict(set)
for zid, z in zones.items():
    for n in z.get("npcs", []):
        npc_zone.setdefault(n["id"], zid)
    for s in z.get("spawns", []):
        for m in s["pool"]:
            mob_zones[m].add(zid)


def zone_level(zid):
    lv = zones.get(zid, {}).get("levels")
    return (lv[0] + lv[1]) / 2 if lv else None


def score(v):
    s = float(v.get("ac", 0)) + sum(float(v.get(k, 0)) for k in STAT) + float(v.get("hp", 0)) / 5 + float(v.get("mana", 0)) / 5
    s += float(v.get("hp_regen", 0)) * 4 + float(v.get("mana_regen", 0)) * 4 + float(v.get("haste", 0)) / 2 + (4 if v.get("proc") else 0)
    if v.get("slot") == "primary" and v.get("dmg"):
        s += 10 * float(v["dmg"]) / float(v.get("delay", 3))
    return s


# ---- 1. rewards against the curve
origin = {}
for qid, q in quests.items():
    given = q.get("first_reward_item")
    for it in (set(given.values()) if isinstance(given, dict) else [given]):  # {class: item} when each class gets its own
        if it and zone_level(npc_zone.get(q["giver"], "")):
            origin.setdefault(it, (zone_level(npc_zone[q["giver"]]), "quest " + qid))
for mid, m in mobs.items():
    if not m.get("named"):
        continue
    for l in m.get("loot", []):
        for zid in mob_zones.get(mid, []):
            if zone_level(zid) and items.get(l["item"], {}).get("slot"):
                origin.setdefault(l["item"], (zone_level(zid), "named " + mid))
rewards = [(k, items[k], lv, how) for k, (lv, how) in origin.items() if k in items and items[k].get("slot") not in (None, "range")]
by_slot = collections.defaultdict(list)
for k, v, lv, how in rewards:
    by_slot[v["slot"]].append((lv, score(v)))
fit = {s: sum(l * sc for l, sc in pts) / sum(l * l for l, sc in pts) for s, pts in by_slot.items()}
weak = []
for k, v, lv, how in sorted(rewards, key=lambda r: (r[1]["slot"], r[2])):
    exp = fit[v["slot"]] * lv
    low = lv >= 4 and score(v) < WEAK * exp
    if low:
        weak.append(k)
    if low or "--all" in sys.argv:
        print("%s %-9s %-28s zone level %4.1f  score %5.1f  curve %5.1f  (%s)" % ("WEAK" if low else "    ", v["slot"], k, lv, score(v), exp, how))
print("rewards: %d checked, %d under %d%% of their slot's curve" % (len(rewards), len(weak), WEAK * 100))


# ---- 2. random gear against the monster's level
def table_at(tid, level):
    t = loot.get(tid, {})
    if "tiers" not in t:
        return t
    pick = t["tiers"][0][1]
    for lv, d in t["tiers"]:
        if level >= lv:
            pick = d
    return pick


LADDERS = load("data/loot.json").get("ladders", {})
ladder_of = {r[1]: (name, r[0]) for name, rungs in LADDERS.items() for r in rungs}


def climb(it, level):
    """World.climb_ladder: generic gear becomes the best rung of its ladder the level has reached."""
    if it not in ladder_of:
        return it
    name, best_lv = ladder_of[it]
    best = it
    for lv, rung in LADDERS[name]:
        if best_lv < lv <= level:
            best, best_lv = rung, lv
    return best


stale = []
for mid, m in mobs.items():
    for lvl in set(m.get("level", [1])):
        for e in m.get("gear", []):
            for it in (table_at(e["table"], lvl) if "table" in e else {e.get("item", ""): 1}):
                it = climb(it, lvl)
                rec = int(items.get(it, {}).get("rec_level", 0))
                if lvl - rec > STALE and lvl > STALE:
                    stale.append((lvl, mid, e.get("table", "item"), it, rec))
for s in sorted(set(stale))[:40]:
    print("STALE level %2d %-24s %-18s %s (rec %d)" % s)
print("random gear: %d monster/table pairs hand out gear more than %d levels below them" % (len(set(stale)), STALE))
sys.exit(1 if weak or stale else 0)
