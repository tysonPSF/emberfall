"""Forward camps, guard huts and places worth finding in the grown zones.

    python3 tools/zones/hubs.py            # write them
    python3 tools/zones/hubs.py --check    # report where everything would go

The zones grew (tools/zones/scale_zone.py) and their towns and camps moved out
whole, so the far end of a big zone was a two-minute walk from anyone who
takes a hand-in, and the new ground between held only monsters. Each zone
here gets:

  a forward camp   near its far quests: a scout who also takes the hand-ins of
                   the zone's quests ("also_taken_by", World.takes_hand_in)
                   and gives two of its own, a sutler, a guard
  guard huts       a watch house by the long roads with a guard who helps
                   anyone in trouble close by
  places           a woodcutters' camp, a ruined shrine, a standing-stone ring,
                   a wreck: each with its own monsters and a named, and two
                   quests from whoever is there (or the forward camp's scout);
                   and one or two quiet ones that are only something to see

Pilot (2026-09-30): Thornwood Vale, the Long Grass, the Bleach. Everything it
adds to a zone file carries "hubs": true, and every npc, mob, item and quest
id is its own, so a rerun replaces what it wrote and nothing else. Ordinary
spawns inside a new camp or hut are taken out (spawn_fill.py fills round
them). Afterwards: tools/zones/outline.py, spawn_fill.py --write, item_curve.py.
"""
import copy, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blackwater as bw  # noqa: E402  its npc / item / quest helpers and its merge
import outline  # noqa: E402
import scale_zone  # noqa: E402

ROOT = bw.ROOT
CHECK = "--check" in sys.argv
bw.MOBS, bw.ITEMS, bw.NPCS, bw.QUESTS = {}, {}, {}, {}
MOBS_NOW = json.load(open(f"{ROOT}/data/mobs.json"))
NPCS_NOW = json.load(open(f"{ROOT}/data/npcs.json"))
QUESTS_NOW = json.load(open(f"{ROOT}/data/quests.json"))
TAG = {"hubs": True}


# ---------------------------------------------------------------- helpers

def road_point(z, road, dist, side=1, off=16.0):
    """A point `dist` m along road `road` from its first point, `off` m to one side (1 right, -1 left, walking it)."""
    pts = z["roads"][road]["points"]
    left = dist
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        if left <= seg:
            t = left / seg
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            dx, dy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
            return [round(x - dy * off * side, 1), round(y + dx * off * side, 1)], [round(x, 1), round(y, 1)]
        left -= seg
    return list(pts[-1]), list(pts[-1])


def mob_like(mid, base, name, level, model, loot, named=False, **kw):
    """A new monster built on one the zone already has (its stats, speed and manners), renamed and re-dressed."""
    d = copy.deepcopy(MOBS_NOW[base])
    d.update({"name": name, "level": list(level), "model": model, "loot": [{"item": i, "chance": c} for i, c in loot]})
    d.pop("gear", None)
    if named:
        d["named"] = True
        d["xp_bonus"] = 3.0
        d["flees"] = False
        d["coin"] = [d.get("coin", [0, 0])[1] * 3, d.get("coin", [0, 0])[1] * 8]
    d.update(kw)
    bw.MOBS[mid] = d
    return mid


def guard(nid, name, faction, title, level=40, shout="Hold on, {name}! I'm coming!"):
    d = copy.deepcopy(NPCS_NOW["caravan_guard"])
    d.update({"name": name, "title": title, "faction": faction, "level": level,
              "dialogue": {"hail": "The road's watched from here, {name}. Anything chasing you, bring it past me.", "unknown": "I just keep the road."}})
    d["guard"]["shouts"] = [shout, "Behind me, {name}!"]
    d["guard"]["hunt_shouts"] = ["Not on my road!", "Back into the wilds!"]
    bw.NPCS[nid] = d
    return nid


def sutler(nid, name, faction, title, sells, model="barbarian", **kw):
    return bw.npc(nid, name, faction, "human", model, {
        "hail": "Food, water and arrows, {name}, and not a coin more than it cost to haul them out here. Press G.",
        "unknown": "Ask the scout. I only count the stores."}, title=title, weapon="axe_1handed", level=30,
        merchant={"sells": sells, "buy_rate": 0.5}, **kw)


def spread(center, r, n, turn=0.0):
    return [[round(center[0] + r * math.cos(turn + k * math.tau / n), 1), round(center[1] + r * math.sin(turn + k * math.tau / n), 1)] for k in range(n)]


def spawns(pool, spots, respawn, wander=12, when=None):
    out = []
    for s in spots:
        e = dict({"pos": s, "pool": dict(pool), "respawn": respawn, "wander": wander}, **TAG)
        if when:
            e["when"] = when
        out.append(e)
    return out


def ring_of(prop_id, center, r, n, scale=None):
    return [dict(bw.prop(prop_id, p, collide="box", yaw=int(k * 360 / n) % 360, scale=scale), **TAG)
            for k, p in enumerate(spread(center, r, n))]


def lm(kind, pos, **kw):
    return dict({"type": kind, "pos": [round(pos[0], 1), round(pos[1], 1)]}, **kw, **TAG)


def npc_at(nid, pos, face):
    return dict({"id": nid, "pos": [round(pos[0], 1), round(pos[1], 1)], "face": [round(face[0], 1), round(face[1], 1)]}, **TAG)


def also_take(zone_npcs, quest_ids, scout):
    """The forward camp's scout takes these quests' hand-ins too (Galehold's, the hub's)."""
    for qid in quest_ids:
        q = QUESTS_NOW[qid]
        takers = [t for t in q.get("also_taken_by", []) if t != scout] + [scout]
        TAKEN[qid] = takers


TAKEN = {}  # quest id -> also_taken_by


# ================================================================ THORNWOOD VALE (6-14)

def thornwood(z):
    F = "watch"
    L, N, S = [], [], []
    # the Northwatch: the Vale Patrol's camp on the north road, between the orcs, the spiders and the old watch
    camp, road_at = road_point(z, 0, 690, side=-1, off=20)
    L.append(lm("waystation", camp, face=road_at))
    scout = bw.npc("tw_corporal_brannic", "Corporal Brannic", F, "human", "knight", {
        "hail": "The Northwatch, {name}: as far up the vale as the Patrol keeps a fire. Harlan's work and the hermit's, you can hand in here; I'll see it gets to them. And there's the [shrine].",
        "shrine": "North-east, a shrine to the Dawn-Tusk nobody's prayed at since the Watch fell. There are acolytes there again, dead ones, telling [beads]. The one who leads them is [Brother Vesk].",
        "beads": "Their prayer beads. Four, and the Patrol pays, as often as you bring them. Every bead you take is one less prayer to whatever they pray to now.",
        "brother vesk": "He kept that shrine when the Watch still stood. Now he keeps it for something else. His censer still smokes: bring it to me.",
        "unknown": "Ask Harlan, back down the road. He's walked it longer."},
        title="Vale Patrol", weapon="sword_1handed", level=30)
    N += [npc_at(scout, [camp[0] + 4, camp[1] + 3], road_at),
          npc_at(sutler("tw_sutler_wenna", "Sutler Wenna", F, "Vale Patrol",
                        ["crude_arrow", "iron_tipped_arrow", "sling_stone", "loaf_of_bread", "roast_meat", "water_flask"], gender="female"),
                 [camp[0] - 5, camp[1] + 4], road_at),
          npc_at(guard("tw_northwatch_guard", "a Northwatch sentry", F, "Vale Patrol"), [camp[0] + 2, camp[1] - 8], road_at)]
    also_take(N, ["thinning_the_pack", "silk_and_venom", "bloodtusk_tusks", "grolthars_necklace", "the_hollow_watch"], scout)
    # guard huts: the main road halfway up, and out along the east and west roads
    for i, (road, dist, side) in enumerate([(0, 420, 1), (1, 250, -1), (2, 300, 1)]):
        hut, at = road_point(z, road, dist, side=side, off=16)
        L.append(lm("outpost", hut))
        N.append(npc_at(guard("tw_hut_guard_%d" % i, "a Vale Patrol watchman", F, "Vale Patrol"), [(hut[0] + at[0]) / 2, (hut[1] + at[1]) / 2], at))

    # the woodcutters' camp, south-west: boars rooting through what's left, and the bear that drove them out
    wc = [-300, 300]
    L.append(lm("cabin", wc, face=[wc[0] + 40, wc[1]]))
    L += [dict(bw.prop(p, pos, collide="box", yaw=y), **TAG) for p, pos, y in
          [("log_pile", [wc[0] - 14, wc[1] + 10], 20), ("stump", [wc[0] + 12, wc[1] - 14], 0), ("stump", [wc[0] + 18, wc[1] - 8], 0)] if bw.prop(p, pos)]
    hob = bw.npc("tw_hob_woodcutter", "Hob the Woodcutter", "emberhold", "human", "barbarian", {
        "hail": "Don't mind the mess, {name}. We had a camp here, six of us, until [Old Greyback] came. And the [boars] that follow him about for his leavings.",
        "boars": "Tuskers, the size of a cart. Four of their tusks and I'll pay, again and again: I'm selling them to the Patrol for spear points.",
        "old greyback": "A bear, grey as ash, with a scar down his back where my brother's axe went in. He sleeps west of the camp. Bring me his hide and we can come home.",
        "unknown": "I cut wood, {name}. Ask the hermit."}, title="Woodcutter", weapon="axe_1handed", level=20)
    N.append(npc_at(hob, [wc[0] + 10, wc[1] + 2], [wc[0] + 40, wc[1]]))
    boar = mob_like("tw_tusker_boar", "black_bear", "a thornwood tusker", (8, 10), "boar", [("tw_tusker_tusk", 0.55), ("raw_meat", 0.3)],
                    verb=["gore", "gores"], scale=1.25)
    grey = mob_like("tw_old_greyback", "black_bear", "Old Greyback", (13, 13), "bear", [("tw_greybacks_hide", 1.0), ("bear_hide", 1.0)],
                    named=True, scale=1.45, color="#8a8a86")
    S += spawns({boar: 1}, spread(wc, 55, 6, 0.3), 90, 14)
    S += spawns({grey: 1}, [[wc[0] - 70, wc[1] - 20]], 1500, 6)
    bw.drop("tw_tusker_tusk", "Thornwood Tusker Tusk", 8)
    bw.ITEMS["tw_tusker_tusk"]["icon"] = "orc_tusk"
    bw.item("tw_greybacks_hide", "Old Greyback's Scarred Hide", value=40, lore=True, icon="bear_hide")
    bw.item("tw_woodcutters_hatchet", "Woodcutter's Hatchet", slot="primary", dmg=10, delay=2.6, verb=["chop", "chops"], model="axe_1handed",
            skill="1h_slashing", str=3, sta=2, value=1800, rec_level=12, no_drop=True, lore=True)
    bw.quest("tw_tusker_tusks", "Tusker Tusks", hob, {"tw_tusker_tusk": 4}, 480, 110, None,
             "You have taken on a task: Tusker Tusks. Bring Hob the Woodcutter four thornwood tusker tusks.",
             "Tusks! The Patrol will pay double for these.", "Four fewer tuskers rooting through our things.", "",
             {"emberhold": 5, "watch": 5}, keyword="boars", repeatable=True)
    bw.quest("tw_old_greyback", "Old Greyback", hob, {"tw_greybacks_hide": 1}, 1400, 320, "tw_woodcutters_hatchet",
             "You have taken on a task: Old Greyback. Bring Hob the Woodcutter the scarred hide of Old Greyback.",
             "That scar. That's him.", "We can come home now. Thank you, {name}.", "My brother's hatchet. He'd want it swinging.",
             {"emberhold": 20, "watch": 10}, keyword="old greyback")

    # the forsworn shrine, north-east: dead acolytes round a broken shrine, and their brother
    sh = [330, -360]
    L.append(lm("ruins", sh))
    L += ring_of("standing_stone", sh, 20, 6) if "standing_stone" in bw.MODELS["props"] else []
    aco = mob_like("tw_forsworn_acolyte", "skeleton_knight", "a forsworn acolyte", (10, 12), "skeleton_mage", [("tw_prayer_bead", 0.55), ("bone_chips", 0.4)],
                   verb=["strike", "strikes"])
    vesk = mob_like("tw_brother_vesk", "skeleton_knight", "Brother Vesk the Forsworn", (14, 14), "necromancer", [("tw_vesks_censer", 1.0), ("bone_chips", 1.0)],
                    named=True, verb=["strike", "strikes"])
    S += spawns({aco: 1}, spread(sh, 34, 6, 0.5), 100, 10)
    S += spawns({vesk: 1}, [sh], 1500, 4)
    bw.drop("tw_prayer_bead", "Forsworn Prayer Bead", 9)
    bw.ITEMS["tw_prayer_bead"]["icon"] = "bone_chips"
    bw.item("tw_vesks_censer", "Brother Vesk's Censer", value=40, lore=True, icon="bone_charm")
    bw.item("tw_northwatch_cloak", "Northwatch Cloak", slot="arms", ac=6, sta=3, wis=2, int=2, hp=18, value=1900, rec_level=13, no_drop=True, lore=True,
            wear="leather_sleeves")
    bw.quest("tw_prayer_beads", "Forsworn Prayer Beads", scout, {"tw_prayer_bead": 4}, 520, 120, None,
             "You have taken on a task: Forsworn Prayer Beads. Bring Corporal Brannic four forsworn prayer beads.",
             "Beads. They're still warm.", "Four fewer prayers. Good.", "", {F: 10}, keyword="beads", repeatable=True)
    bw.quest("tw_brother_vesk", "Brother Vesk the Forsworn", scout, {"tw_vesks_censer": 1}, 1500, 340, "tw_northwatch_cloak",
             "You have taken on a task: Brother Vesk the Forsworn. Bring Corporal Brannic Brother Vesk's censer.",
             "The censer. It's gone cold at last.", "The shrine's quiet. The Dawn-Tusk can have it back.", "The Northwatch's cloak. You've earned the colors.",
             {F: 25}, keyword="brother vesk")

    # quiet places: a merchant's wagon lost on the west road, a lookout over the south-east
    wreck, _ = road_point(z, 2, 430, side=-1, off=12)
    L += [dict(bw.prop("caravan_wagon", [wreck[0] + dx, wreck[1] + dy], collide="box", yaw=y), **TAG) for dx, dy, y in [(0, 0, 70), (7, 5, 160)]]
    L.append(lm("watchtower", [330, 330], face=[250, 250]))
    return L, N, S, [camp] + [road_point(z, r, d, s, 16)[0] for r, d, s in [(0, 420, 1), (1, 250, -1), (2, 300, 1)]]


# ================================================================ THE LONG GRASS (34-38)

def long_grass(z):
    F = "galehold"
    L, N, S = [], [], []
    camp, road_at = road_point(z, 1, 230, side=-1, off=22)
    L.append(lm("waystation", camp, face=road_at))
    scout = bw.npc("lg_outrider_temperance", "Outrider Temperance", F, "human", "ranger_class", {
        "hail": "Windrider's Rest, {name}: Galehold's last fire before the herds. Whatever the city's asked of you out here, you can hand in to me; the riders carry it back. Mind the [stones] up north.",
        "stones": "A ring of standing stones in the north grass, humming. They get up and walk now, the [sentinels], and something wakes in the middle of them: the [Ringwarden].",
        "sentinels": "Stone that walks. Bring me four chips of it and I'll pay, as often as you like: Galehold's stonecutters want to know what they're made of.",
        "ringwarden": "The biggest of the stones, the one in the middle. It carries a rune-stone in its chest. Bring me that.",
        "unknown": "Galehold's the place for questions. I'm the place for answers you can use."},
        title="Galehold Outrider", weapon="bow", gender="female", level=45)
    N += [npc_at(scout, [camp[0] + 4, camp[1] + 3], road_at),
          npc_at(sutler("lg_sutler_ansgar", "Sutler Ansgar", F, "Galehold Outriders",
                        ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"]),
                 [camp[0] - 5, camp[1] + 4], road_at),
          npc_at(guard("lg_rest_guard", "a Galehold outrider", F, "Galehold Outriders"), [camp[0] + 2, camp[1] - 8], road_at)]
    also_take(N, ["horsetail_braid_q", "khans_horsetail_banner_q", "stalker_pelt_q", "tawnyjaws_fang_q", "thunderhoof_horn_q",
                  "herd_kings_horn_q", "barrow_bronze_q", "barrow_lords_death_mask_q"], scout)
    huts = [(0, 230, 1), (0, 560, -1), (1, 470, 1)]
    for i, (road, dist, side) in enumerate(huts):
        hut, at = road_point(z, road, dist, side=side, off=16)
        L.append(lm("outpost", hut))
        N.append(npc_at(guard("lg_hut_guard_%d" % i, "a Galehold outrider", F, "Galehold Outriders"), [(hut[0] + at[0]) / 2, (hut[1] + at[1]) / 2], at))

    # the Whispering Ring, north: standing stones that walk, and the one at the heart of them
    ring = [20, -370]
    L += ring_of("standing_stone", ring, 22, 9, scale=1.3)
    sent = mob_like("lg_ringstone_sentinel", "barrow_wight", "a ringstone sentinel", (35, 37), "menhir", [("lg_humming_stone_chip", 0.55)],
                    verb=["crush", "crushes"], social=True)
    ward = mob_like("lg_ringwarden", "barrow_wight", "the Ringwarden", (39, 39), "old_thrum", [("lg_ringwardens_rune", 1.0), ("lg_humming_stone_chip", 1.0)],
                    named=True, verb=["crush", "crushes"], scale=1.2)
    S += spawns({sent: 1}, spread(ring, 44, 7, 0.2), 110, 12)
    S += spawns({ward: 1}, [ring], 1500, 3)
    bw.drop("lg_humming_stone_chip", "Humming Stone Chip", 30)
    bw.ITEMS["lg_humming_stone_chip"]["icon"] = "salt_crystal"
    bw.item("lg_ringwardens_rune", "The Ringwarden's Rune-Stone", value=200, lore=True, icon="salt_crystal")
    bw.item("lg_ringstone_band", "Ringstone Band", slot="ring", ac=6, sta=6, wis=5, int=5, hp=50, mana=50, value=24000, rec_level=37, no_drop=True, lore=True,
            icon="breathshard_ring")
    bw.quest("lg_stone_chips", "Humming Stone", scout, {"lg_humming_stone_chip": 4}, 8550, 950, None,
             "You have taken on a task: Humming Stone. Bring Outrider Temperance four humming stone chips.",
             "Chips! Put your ear to one.", "The stonecutters will be up all night.", "", {F: 15}, keyword="sentinels", repeatable=True)
    bw.quest("lg_ringwarden", "The Ringwarden", scout, {"lg_ringwardens_rune": 1}, 19000, 2280, "lg_ringstone_band",
             "You have taken on a task: The Ringwarden. Bring Outrider Temperance the Ringwarden's rune-stone.",
             "It's stopped humming.", "The ring is only stones again.", "Cut from its heart. It still hums, a little.", {F: 30}, keyword="ringwarden")

    # the Broken Wheel, south-east: a Hoofborn camp left to the carrion jackals, and a herdwife who won't leave it
    bw_at = [300, 300]
    L += [dict(bw.prop(p, pos, collide="box", yaw=y), **TAG) for p, pos, y in
          [("hoofborn_yurt", [bw_at[0], bw_at[1]], 10), ("hoofborn_yurt", [bw_at[0] + 16, bw_at[1] - 8], 130), ("hoofborn_yurt", [bw_at[0] - 12, bw_at[1] + 14], 250),
           ("horse_totem", [bw_at[0] + 4, bw_at[1] + 18], 0), ("herd_bones", [bw_at[0] - 20, bw_at[1] - 12], 40), ("herd_bones", [bw_at[0] + 24, bw_at[1] + 10], 200)]]
    saule_at = [bw_at[0] - 70, bw_at[1] - 60]
    L += [dict(bw.prop("tent", saule_at, collide="box", yaw=45), **TAG), dict(bw.prop("campfire", [saule_at[0] + 6, saule_at[1] + 5], collide="none"), **TAG)]
    saule = bw.npc("lg_herdwife_saule", "Herdwife Saule", F, "human", "ranger", {
        "hail": "That was my husband's camp, {name}, before the fever took the herd and the Khan took the riders. Now the [jackals] have it. And [Old Rakemaw].",
        "jackals": "Carrion jackals, come for the bones. Bring me four of their ears and I'll pay you every time: I'll have them gone from that camp if I have to buy every ear on the plain.",
        "old rakemaw": "The pack's old mother. Grey muzzle, one eye. She dens in my husband's yurt. Bring me her jawbone.",
        "unknown": "I only know the herd, {name}. What's left of it."}, title="of the Broken Wheel", weapon="staff", gender="female", level=40)
    N.append(npc_at(saule, [saule_at[0] + 8, saule_at[1] + 2], bw_at))
    jack = mob_like("lg_carrion_jackal", "grass_howler", "a carrion jackal", (34, 36), "marrow_jackal", [("lg_jackal_ear", 0.55)], social=True)
    rake = mob_like("lg_old_rakemaw", "grass_howler", "Old Rakemaw", (39, 39), "gorgemaw", [("lg_rakemaws_jawbone", 1.0), ("lg_jackal_ear", 1.0)], named=True)
    S += spawns({jack: 1}, spread(bw_at, 40, 7, 0.4), 90, 14)
    S += spawns({rake: 1}, [[bw_at[0] + 2, bw_at[1] + 2]], 1500, 4)
    bw.drop("lg_jackal_ear", "Carrion Jackal Ear", 28)
    bw.ITEMS["lg_jackal_ear"]["icon"] = "stalker_pelt"
    bw.item("lg_rakemaws_jawbone", "Old Rakemaw's Jawbone", value=200, lore=True, icon="bleached_bone")
    bw.item("lg_herdwifes_mantle", "Herdwife's Mantle", slot="arms", ac=14, sta=6, agi=5, hp=55, value=24000, rec_level=37, no_drop=True, lore=True,
            wear="leather_sleeves")
    bw.quest("lg_jackal_ears", "Carrion Jackal Ears", saule, {"lg_jackal_ear": 4}, 8550, 950, None,
             "You have taken on a task: Carrion Jackal Ears. Bring Herdwife Saule four carrion jackal ears.",
             "Ears. Good.", "Four fewer at the bones.", "", {F: 15}, keyword="jackals", repeatable=True)
    bw.quest("lg_old_rakemaw", "Old Rakemaw", saule, {"lg_rakemaws_jawbone": 1}, 19000, 2280, "lg_herdwifes_mantle",
             "You have taken on a task: Old Rakemaw. Bring Herdwife Saule the jawbone of Old Rakemaw.",
             "Her jaw. She won't bite again.", "I can bury my husband's things now.", "My mantle. Wear it on the plain, it's kept me warm on worse nights.",
             {F: 30}, keyword="old rakemaw")

    # a quiet place: a broken lookout on the west grass
    L.append(lm("watchtower", [-300, 170], face=[-200, 170]))
    return L, N, S, [camp] + [road_point(z, r, d, s, 16)[0] for r, d, s in huts]


# ================================================================ THE BLEACH (16-21)

def bleach(z):
    F = "salt_traders"
    L, N, S = [], [], []
    camp, road_at = road_point(z, 0, 660, side=1, off=22)
    L.append(lm("waystation", camp, face=road_at))
    scout = bw.npc("bl_outrider_kofi", "Outrider Kofi", F, "human", "ranger_class", {
        "hail": "Saltwater Well, {name}: the only sweet water north of the waystation, and the caravans' last stop before the pan. Suri's and Ibrem's business you can hand in here. And ask me about the [mine].",
        "mine": "The old salt mine east of here. The miners never left: the brine got into them. They wander the shacks still, with their [tags] round their necks, and their [foreman] with them.",
        "tags": "Their mine tags. Bring me four and I'll pay each time; their families in Lanternhold will want to know.",
        "foreman": "Foreman Dask. He kept the ledger. Bring it to me and the families will know who went down and didn't come up.",
        "unknown": "Suri knows the road. I know the water."},
        title="Salt Traders", weapon="bow", level=30)
    N += [npc_at(scout, [camp[0] + 4, camp[1] + 3], road_at),
          npc_at(sutler("bl_sutler_amara", "Sutler Amara", F, "Salt Traders",
                        ["crude_arrow", "iron_tipped_arrow", "sling_stone", "loaf_of_bread", "roast_meat", "water_flask"], gender="female"),
                 [camp[0] - 5, camp[1] + 4], road_at),
          npc_at(guard("bl_well_guard", "a caravan guard", F, "Salt Traders"), [camp[0] + 2, camp[1] - 8], road_at)]
    L += [dict(bw.prop("salt_crystals", [camp[0] + 14, camp[1] - 6], collide="none"), **TAG)]
    also_take(N, ["stingers_for_the_road", "the_salt_wolf", "heart_of_the_titan"], scout)
    huts = [(0, 330, 1), (1, 260, 1)]
    for i, (road, dist, side) in enumerate(huts):
        hut, at = road_point(z, road, dist, side=side, off=16)
        L.append(lm("outpost", hut))
        N.append(npc_at(guard("bl_hut_guard_%d" % i, "a caravan guard", F, "Salt Traders"), [(hut[0] + at[0]) / 2, (hut[1] + at[1]) / 2], at))

    # the old salt mine, east: the brine-dead miners and their foreman
    mine = [380, 160]
    L.append(lm("ruins", mine))
    L += [dict(bw.prop(p, pos, collide="box", yaw=y), **TAG) for p, pos, y in
          [("caravan_wagon", [mine[0] - 22, mine[1] + 14], 30), ("salt_crystals", [mine[0] + 18, mine[1] - 16], 0), ("salt_crystals", [mine[0] - 16, mine[1] - 20], 0)]]
    miner = mob_like("bl_brine_miner", "salt_raider", "a brine-drowned miner", (17, 19), "sunken_villager", [("bl_miners_tag", 0.55)],
                     verb=["claw", "claws"], faction="undead", flees=False, social=True)
    dask = mob_like("bl_foreman_dask", "salt_raider", "Foreman Dask", (21, 21), "drowned_captain", [("bl_foremans_ledger", 1.0), ("bl_miners_tag", 1.0)],
                    named=True, verb=["claw", "claws"], faction="undead", social=True)
    S += spawns({miner: 1}, spread(mine, 36, 7, 0.1), 95, 10)
    S += spawns({dask: 1}, [[mine[0] + 4, mine[1]]], 1500, 4)
    bw.drop("bl_miners_tag", "Brine-Crusted Mine Tag", 14)
    bw.ITEMS["bl_miners_tag"]["icon"] = "tarnished_ring"
    bw.item("bl_foremans_ledger", "Foreman Dask's Ledger", value=60, lore=True, icon="blackwaters_ledger")
    bw.item("bl_saltminers_girdle", "Saltminer's Girdle", slot="waist", ac=10, str=4, sta=4, hp=30, value=5800, rec_level=19, no_drop=True, lore=True,
            icon="stonefist_girdle")
    bw.quest("bl_mine_tags", "Mine Tags", scout, {"bl_miners_tag": 4}, 5200, 500, None,
             "You have taken on a task: Mine Tags. Bring Outrider Kofi four brine-crusted mine tags.",
             "Tags. Let me read the names.", "Four families will know.", "", {F: 15, "lanternhold": 5}, keyword="tags", repeatable=True)
    bw.quest("bl_foreman_dask", "Foreman Dask", scout, {"bl_foremans_ledger": 1}, 12000, 1500, "bl_saltminers_girdle",
             "You have taken on a task: Foreman Dask. Bring Outrider Kofi Foreman Dask's ledger.",
             "The ledger. Every name in it.", "They'll be mourned properly now.", "His belt. It held up a lot of salt.", {F: 30, "lanternhold": 10},
             keyword="foreman")

    # the wreck, west: a caravan the salt swallowed, crabs in it, and a trader who came back for the cargo
    wk = [-340, -300]
    L += [dict(bw.prop("caravan_wagon", [wk[0] + dx, wk[1] + dy], collide="box", yaw=y), **TAG) for dx, dy, y in [(0, 0, 80), (10, -6, 200), (-8, 10, 320)]]
    L += [dict(bw.prop("dead_palm", [wk[0] + dx, wk[1] + dy], collide="box"), **TAG) for dx, dy in [(20, 14), (-22, -10)]]
    trader_at = [wk[0] + 60, wk[1] + 50]
    L += [dict(bw.prop("tent", trader_at, collide="box", yaw=200), **TAG), dict(bw.prop("campfire", [trader_at[0] - 6, trader_at[1] - 5], collide="none"), **TAG)]
    trader = bw.npc("bl_trader_oyelowo", "Trader Oyelowo", F, "human", "rogue_hooded", {
        "hail": "My caravan, {name}. Lost to the salt in a storm, three years ago. I came back for the cargo and found the [crabs] living in it. And the [Wreck-Shell].",
        "crabs": "Salt crabs, big ones, nesting in the wagons. Four of their claws and I'll pay: the cooks in Lanternhold pay me more.",
        "wreck-shell": "The old one. A shell like a wagon wheel. It lives under the lead wagon, on my strongbox. Bring me a piece of its shell and I'll know it's done.",
        "unknown": "I trade, {name}. I don't know much else."}, title="Trader", weapon="dagger", level=25)
    N.append(npc_at(trader, [trader_at[0] + 6, trader_at[1] - 2], wk))
    crab = mob_like("bl_wreck_crab", "giant_scorpion", "a wreck crab", (16, 18), "salt_crab", [("bl_crab_claw", 0.55)], verb=["pinch", "pinches"])
    shell = mob_like("bl_wreck_shell", "giant_scorpion", "the Wreck-Shell", (21, 21), "old_saltclaw", [("bl_wreckshell_shard", 1.0), ("bl_crab_claw", 1.0)],
                     named=True, verb=["pinch", "pinches"])
    S += spawns({crab: 1}, spread(wk, 34, 7, 0.6), 85, 12)
    S += spawns({shell: 1}, [[wk[0] + 2, wk[1] + 2]], 1500, 4)
    bw.drop("bl_crab_claw", "Wreck Crab Claw", 12)
    bw.ITEMS["bl_crab_claw"]["icon"] = "chitin_plate"
    bw.item("bl_wreckshell_shard", "Shard of the Wreck-Shell", value=60, lore=True, icon="chitin_plate")
    bw.item("bl_wreckers_buckler", "Wrecker's Buckler", slot="secondary", ac=12, sta=4, hp=35, value=6000, rec_level=19, no_drop=True, lore=True,
            shield=True, model="shield_round", classes=["warrior", "cleric", "shaman", "ranger"])
    bw.quest("bl_crab_claws", "Wreck Crab Claws", trader, {"bl_crab_claw": 4}, 5200, 500, None,
             "You have taken on a task: Wreck Crab Claws. Bring Trader Oyelowo four wreck crab claws.",
             "Claws! The cooks will sing.", "Four fewer in my wagons.", "", {F: 15}, keyword="crabs", repeatable=True)
    bw.quest("bl_wreck_shell", "The Wreck-Shell", trader, {"bl_wreckshell_shard": 1}, 12000, 1500, "bl_wreckers_buckler",
             "You have taken on a task: The Wreck-Shell. Bring Trader Oyelowo a shard of the Wreck-Shell.",
             "A piece of it. It's really gone.", "My strongbox, at last.", "Made from the lead wagon's wheel-guard. Take it.", {F: 30}, keyword="wreck-shell")

    # a quiet place: a dead oasis in the south-west, a pool gone to salt
    oa = [-300, 300]
    L += [dict(bw.prop(p, [oa[0] + dx, oa[1] + dy], collide=c), **TAG) for p, dx, dy, c in
          [("dead_palm", 10, 0, "box"), ("dead_palm", -8, 9, "box"), ("dead_palm", -4, -11, "box"), ("salt_crystals", 0, 0, "none"), ("salt_crystals", 6, 6, "none")]]
    return L, N, S, [camp] + [road_point(z, r, d, s, 16)[0] for r, d, s in huts]


# ================================================================ write

ZONES = {"thornwood": thornwood, "the_long_grass": long_grass, "the_bleach": bleach}


def check_spot(zid, z, edges, p, what):
    """Problems with putting something at p: in the mountains, in water, on a road."""
    hx, hz = outline.halves(z)
    probs = []
    if outline.edge_depth(edges, (hx, hz), p[0], p[1]) > -30:
        probs.append("near the mountains")
    for r in z.get("rivers", []):
        if not r.get("dry") and min(math.dist(p, q) for q in bw_poly(r["points"])) < r.get("width", 10) / 2 + 12:
            probs.append("in a river")
    for lk in z.get("lakes", []):
        if outline._poly_inside(p, lk["points"]):
            probs.append("in a lake")
    return probs


def bw_poly(points):
    return outline._polyline(points, 4.0)


# Places that stayed packed together when their zone grew (a settlement moves whole),
# pulled apart: every landmark (not a signpost) and spawn within `radius` of `from`
# moves by the same offset to `to`, and ordinary spawns already there make room.
# A rerun finds nothing left at `from` and does nothing.
MOVES = {
    "high_terrace": [  # the Terrace Colossus's sun shrine sat 80 m from the monastery; the Ghost at its gate
        {"from": (76.8, -239.7), "radius": 30, "to": (280, -40), "what": "the Terrace Colossus's sun shrine and golems"},
        {"from": (-81.2, -194.7), "radius": 3, "to": (-300, -60), "what": "the Ghost of the Terraces"},
    ],
}


def move_places():
    for zid, moves in MOVES.items():
        path = f"{ROOT}/data/zones/{zid}.json"
        z = json.load(open(path))
        changed = False
        for mv in moves:
            fx, fy = mv["from"]
            dx, dy = mv["to"][0] - fx, mv["to"][1] - fy
            near = lambda e: math.dist(e["pos"], (fx, fy)) <= mv["radius"]
            lms = [l for l in z["landmarks"] if near(l) and l["type"] not in ("signpost", "rockslide", "bridge")]
            sps = [s for s in z["spawns"] if near(s)]
            if not lms and not sps:
                continue
            print("%-16s moving %s: %d landmarks, %d spawns, %.0f m" % (zid, mv["what"], len(lms), len(sps), math.hypot(dx, dy)))
            for e in lms + sps:
                e["pos"] = [round(e["pos"][0] + dx, 1), round(e["pos"][1] + dy, 1)]
                if "face" in e:
                    e["face"] = [round(e["face"][0] + dx, 1), round(e["face"][1] + dy, 1)]
            z["spawns"] = [s for s in z["spawns"] if s in sps or math.dist(s["pos"], mv["to"]) > 40]
            changed = True
        if changed and not CHECK:
            open(path, "w").write(scale_zone.dumps(z) + "\n")


def main():
    move_places()
    edges_all = outline.load()
    for zid, build in ZONES.items():
        path = f"{ROOT}/data/zones/{zid}.json"
        z = json.load(open(path))
        for key in ("landmarks", "npcs", "spawns"):  # what an earlier run wrote comes out first
            z[key] = [e for e in z.get(key, []) if not e.get("hubs")]
        L, N, S, keep_clear = build(z)
        L = [l for l in L if l]
        edges = edges_all.get(zid)
        for e in L + N:
            probs = check_spot(zid, z, edges, e["pos"], e.get("type", e.get("id")))
            if probs and e.get("type") not in ("prop",):
                print("  %s: %s at %s: %s" % (zid, e.get("type", e.get("id")), e["pos"], ", ".join(probs)))
        before = len(z["spawns"])
        z["spawns"] = [s for s in z["spawns"] if s.get("hubs") or not any(math.dist(s["pos"], c) < 40 for c in keep_clear)
                       and not any(math.dist(s["pos"], sp["pos"]) < 22 for sp in S)]
        print("%-16s +%d landmarks, +%d npcs, +%d spawns (%d ordinary ones cleared from the camps and new places)" % (
            zid, len(L), len(N), len(S), before - len(z["spawns"])))
        if CHECK:
            continue
        z["landmarks"] += L
        z["npcs"] += N
        z["spawns"] += S
        open(path, "w").write(scale_zone.dumps(z) + "\n")
    if CHECK:
        return
    bw.merge(f"{ROOT}/data/npcs.json", bw.NPCS)
    bw.merge(f"{ROOT}/data/mobs.json", bw.MOBS)
    for qid, takers in TAKEN.items():  # the forward camps take these hand-ins too
        bw.QUESTS[qid] = dict(QUESTS_NOW[qid], also_taken_by=takers)
    bw.merge(f"{ROOT}/data/quests.json", bw.QUESTS)
    with open(f"{ROOT}/data/items/hubs.json", "w") as f:
        f.write(json.dumps(bw.ITEMS, indent=2) + "\n")
    print("wrote %d npcs, %d monsters, %d quests (%d of them taking hand-ins at the camps), %d items" % (
        len(bw.NPCS), len(bw.MOBS), len(bw.QUESTS), len(TAKEN), len(bw.ITEMS)))


if __name__ == "__main__":
    main()
