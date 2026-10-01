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

# ================================================================ batch 2: the four other 1024 m zones

def place(z, F, spec, L, N, S):
    """A place worth finding, from a spec: its landmark and props, its own monsters and their drop, its named and
    trophy, the reward, and two quests (a repeatable one for the drop, one for the trophy) from its own npc or the
    forward camp's scout (spec["giver"], an npc id). Returns the giver's dialogue entries for the place."""
    at = spec["at"]
    if spec.get("landmark"):
        kind, extra = spec["landmark"]
        L.append(lm(kind, at, **extra))
    for pid, dx, dy, yaw, collide in spec.get("props", []):
        p = bw.prop(pid, [at[0] + dx, at[1] + dy], collide=collide, yaw=yaw)
        if p:
            L.append(dict(p, **TAG))
    m, n = spec["mob"], spec["named"]
    did, dname, dvalue, dicon = m["drop"]
    bw.drop(did, dname, dvalue)
    bw.ITEMS[did]["icon"] = dicon
    tid, tname, ticon = n["trophy"]
    bw.item(tid, tname, value=dvalue * 5, lore=True, icon=ticon)
    mob_like(m["id"], m["base"], m["name"], m["level"], m["model"], [(did, 0.55)] + m.get("loot", []), **m.get("extra", {}))
    mob_like(n["id"], n["base"], n["name"], n["level"], n["model"], [(tid, 1.0), (did, 1.0)], named=True, **n.get("extra", {}))
    S += spawns({m["id"]: 1}, spread(at, spec.get("radius", 38), spec.get("count", 7), spec.get("turn", 0.3)), spec.get("respawn", 95), 12)
    S += spawns({n["id"]: 1}, [[at[0] + 3, at[1] + 2]], 1500, 4)
    rid, ritem = spec["reward"]
    bw.item(rid, **ritem)
    giver = spec["giver"]
    gname = bw.NPCS[giver]["name"] if giver in bw.NPCS else giver
    kw_m, kw_n = spec["keywords"]
    rep_xp, rep_coin, n_xp, n_coin = spec["xp"]
    t = spec["text"]
    bw.quest(m["id"] + "_q", t["rep_name"], giver, {did: 4}, rep_xp, rep_coin, None,
             "You have taken on a task: %s. Bring %s four %s." % (t["rep_name"], gname, t["drop_plural"]),
             t["rep_ready"], t["rep_done"], "", dict(spec["faction"]), keyword=kw_m, repeatable=True)
    bw.quest(n["id"] + "_q", n["name"][0].upper() + n["name"][1:], giver, {tid: 1}, n_xp, n_coin, rid,
             "You have taken on a task: %s. Bring %s %s." % (n["name"][0].upper() + n["name"][1:], gname, t["trophy_phrase"]),
             t["n_ready"], t["n_done"], t["n_reward"], {k: v * 3 for k, v in spec["faction"].items()}, keyword=kw_n)
    return {kw_m: t["kw_mob"], kw_n: t["kw_named"]}


def forward_camp(z, F, road, dist, side, scout, scout_name, scout_title, scout_model, scout_hail, sutler_id, sutler_name, sells,
                 guard_name, guard_title, takes, extra_dialogue, off=22, gender=None, at=None, face=None, scout_race="human"):
    """The camp near the far quests: waystation, scout (hand-ins for `takes`), sutler, guard."""
    L, N = [], []
    if at is None:
        camp, road_at = road_point(z, road, dist, side=side, off=off)
    else:
        camp, road_at = at, face
    L.append(lm("waystation", camp, face=road_at))
    dialogue = dict({"hail": scout_hail, "unknown": "Ask back at camp. I only watch the far end."}, **extra_dialogue)
    kw = {"gender": gender} if gender else {}
    bw.npc(scout, scout_name, F, scout_race, scout_model, dialogue, title=scout_title, weapon="bow", level=35, **kw)
    N += [npc_at(scout, [camp[0] + 4, camp[1] + 3], road_at),
          npc_at(sutler(sutler_id, sutler_name, F, scout_title, sells), [camp[0] - 5, camp[1] + 4], road_at),
          npc_at(guard(scout + "_guard", guard_name, F, guard_title), [camp[0] + 2, camp[1] - 8], road_at)]
    also_take(N, takes, scout)
    return L, N, camp


def huts_on(z, F, prefix, name, title, specs):
    L, N, spots = [], [], []
    for i, (road, dist, side) in enumerate(specs):
        hut, at = road_point(z, road, dist, side=side, off=16)
        L.append(lm("outpost", hut))
        N.append(npc_at(guard("%s_hut_guard_%d" % (prefix, i), name, F, title), [(hut[0] + at[0]) / 2, (hut[1] + at[1]) / 2], at))
        spots.append(hut)
    return L, N, spots


def camp_npc(nid, name, F, model, dialogue, title, pos, face, L, N, weapon="staff", gender=None, race="human", level=30):
    """Someone living by a place, with a tent and a fire of their own."""
    L += [dict(bw.prop("tent", pos, collide="box", yaw=45), **TAG), dict(bw.prop("campfire", [pos[0] + 6, pos[1] + 5], collide="none"), **TAG)]
    kw = {"gender": gender} if gender else {}
    bw.npc(nid, name, F, race, model, dialogue, title=title, weapon=weapon, level=level, **kw)
    N.append(npc_at(nid, [pos[0] + 8, pos[1] + 2], face))
    return nid


def the_burn(z):
    F = "forgehold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 0, 650, -1, "burn_ashrunner_beppe", "Ashrunner Beppe", "Forgehold Scouts", "ranger_class",
        "Cinderwatch, {name}: the Ashwatch's fire on the north road. The Warden's business, Mott's, Ilse's and the Ashseer's, you can all hand in here. And ask me about the [chapel].",
        "burn_sutler_jorunn", "Sutler Jorunn", ["iron_tipped_arrow", "windcutter_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "an Ashwatch sentry", "Forgehold Scouts", ["giants_coals", "thanes_crown", "imp_horns", "bottled_smoke", "cackleflames_crown", "firehound_manes",
        "ashmaws_mane", "firebird_feathers", "phoenix_ember"], {})
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "burn", "an Ashwatch sentry", "Forgehold Scouts", [(0, 300, 1), (1, 150, 1), (2, 140, -1)])
    L += hL
    N += hN
    dia = place(z, F, {"at": [330, 330], "landmark": ("ruins", {}), "giver": "burn_ashrunner_beppe",
        "props": [("smoldering_stump", 20, 18, 0, "box"), ("smoldering_stump", -18, 22, 0, "box"), ("burned_cabin", -30, -24, 40, "box")],
        "mob": {"id": "burn_kindled_husk", "name": "a kindled husk", "base": "fire_imp", "level": (30, 32), "model": "charred_dead",
                "drop": ("burn_cinder_bead", "Cinder Rosary Bead", 14, "bone_chips"), "extra": {"verb": ["claw", "claws"], "shape": "humanoid"}},
        "named": {"id": "burn_kindled_deacon", "name": "the Kindled Deacon", "base": "fire_imp", "level": (35, 35), "model": "fallen_fire_priest",
                  "trophy": ("burn_deacons_censer", "The Kindled Deacon's Censer", "phoenix_ember"), "extra": {"verb": ["strike", "strikes"], "shape": "humanoid", "scale": 1.15}},
        "reward": ("burn_cinderwatch_mantle", {"name": "Cinderwatch Mantle", "slot": "arms", "ac": 12, "sta": 5, "agi": 4, "hp": 45, "value": 20000, "rec_level": 33,
                   "no_drop": True, "lore": True, "wear": "leather_sleeves", "icon": "lg_herdwifes_mantle"}),
        "keywords": ("husks", "deacon"), "xp": (5200, 620, 13500, 1850), "faction": {F: 8},
        "text": {"rep_name": "Cinder Rosaries", "drop_plural": "cinder rosary beads", "trophy_phrase": "the Kindled Deacon's censer",
                 "rep_ready": "Beads. They're still smoking.", "rep_done": "Four husks that won't pray again.",
                 "n_ready": "The censer's gone cold. Good.", "n_done": "The chapel burns out at last.", "n_reward": "The Cinderwatch's mantle. Ash doesn't stick to it.",
                 "kw_mob": "Husks, burned in the chapel when the fire came through, still at their prayers. Four of their rosary beads and the Forge pays you, every time.",
                 "kw_named": "The Kindled Deacon. He led the prayers when the chapel burned, and he's leading them still. Bring me his censer."}}, L, N, S)
    bw.NPCS["burn_ashrunner_beppe"]["dialogue"].update(dia)
    bw.NPCS["burn_ashrunner_beppe"]["dialogue"]["chapel"] = "South-east, a chapel that burned with its congregation inside. They're still in there: [husks], and their [deacon]."
    rift = [-330, -280]
    renske = camp_npc("burn_prospector_renske", "Prospector Renske", F, "barbarian", {
        "hail": "Mind the rift, {name}. There's ore down there, Forge-grade, if you can get past the [newts]. And [Old Blisterback].",
        "unknown": "I dig, {name}. Ask the scouts."}, "Prospector", [rift[0] + 70, rift[1] + 55], rift, L, N, weapon="axe_1handed", race="dwarf", gender="female")
    dia = place(z, F, {"at": rift, "landmark": ("vent", {}), "giver": renske,
        "props": [("smoldering_stump", 24, -10, 0, "box"), ("giant_anvil", -26, 14, 30, "box")],
        "mob": {"id": "burn_cinder_newt", "name": "a cinder newt", "base": "firehound", "level": (30, 32), "model": "lava_salamander",
                "drop": ("burn_newt_blister", "Cinder Newt Blister", 14, "imp_horn"), "extra": {"verb": ["bite", "bites"]}},
        "named": {"id": "burn_old_blisterback", "name": "Old Blisterback", "base": "firehound", "level": (35, 35), "model": "lava_salamander",
                  "trophy": ("burn_blisterbacks_heartstone", "Old Blisterback's Heartstone", "phoenix_ember"), "extra": {"verb": ["bite", "bites"], "scale": 1.9}},
        "reward": ("burn_prospectors_pick", {"name": "Prospector's Pick", "slot": "primary", "dmg": 24, "delay": 2.8, "verb": ["smash", "smashes"], "model": "miners_pick",
                   "skill": "1h_blunt", "str": 5, "sta": 4, "hp": 30, "value": 20000, "rec_level": 33, "no_drop": True, "lore": True, "icon": "tw_woodcutters_hatchet"}),
        "keywords": ("newts", "old blisterback"), "xp": (5200, 620, 13500, 1850), "faction": {F: 8},
        "text": {"rep_name": "Newt Blisters", "drop_plural": "cinder newt blisters", "trophy_phrase": "Old Blisterback's heartstone",
                 "rep_ready": "Blisters! Careful, they pop.", "rep_done": "Four fewer in my rift.", "n_ready": "His heartstone. Still warm.",
                 "n_done": "The rift's mine now.", "n_reward": "My old pick. It's dug through worse than him.",
                 "kw_mob": "Cinder newts, fat with fire. Four of their blisters and I'll pay, as often as you like: the Forge uses them for flux.",
                 "kw_named": "The biggest newt in the rift, blistered all over. Bring me the heartstone out of him."}}, L, N, S)
    bw.NPCS[renske]["dialogue"].update(dia)
    L.append(lm("watchtower", [400, 150], face=[300, 150]))
    return L, N, S, [camp] + huts


def mirror_flats(z):
    F = "salt_traders"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "mf_skiffscout_imara", "Skiff-Scout Imara", "Salt Traders", "ranger_class",
        "Glasswater Camp, {name}: the traders' last fire before the glass. Rahel's work, Queenie's, Bram's, Kiri's, you can hand it all in to me. And ask me about the [skiff].",
        "mf_sutler_ilka", "Sutler Ilka", ["crude_arrow", "iron_tipped_arrow", "sling_stone", "loaf_of_bread", "roast_meat", "water_flask"],
        "a caravan guard", "Salt Traders", ["nomad_veil_q", "asras_salt_crown_q", "mirror_shard_q", "cracked_mirror_face_q", "salt_crab_claw_q",
        "saltclaws_pearl_q", "wader_plume_q", "sky_ray_spine_q"], {}, gender="female", at=[-60, -60], face=[0, 0])
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "mf", "a caravan guard", "Salt Traders", [(1, 70, 1)])
    L += hL
    N += hN
    L.append(lm("outpost", [236, 172]))
    N.append(npc_at(guard("mf_hut_guard_island", "a caravan guard", F, "Salt Traders"), [228, 162], [220, 150]))
    huts.append([236, 172])
    dia = place(z, F, {"at": [290, -270], "giver": "mf_skiffscout_imara",
        "props": [("sand_skiff", 0, 0, 120, "box"), ("sand_skiff", 14, 8, 250, "box"), ("caravan_wagon", -12, 10, 30, "box")],
        "mob": {"id": "mf_drowned_salter", "name": "a drowned salter", "base": "duneskiff_nomad", "level": (21, 23), "model": "drowned",
                "drop": ("mf_salters_locket", "Salter's Locket", 10, "waterlogged_locket"), "extra": {"verb": ["claw", "claws"], "faction": "undead", "flees": False}},
        "named": {"id": "mf_skiffmaster_dunmore", "name": "Skiffmaster Dunmore the Drowned", "base": "duneskiff_nomad", "level": (25, 25), "model": "drowned_captain",
                  "trophy": ("mf_dunmores_logbook", "Skiffmaster Dunmore's Logbook", "blackwaters_ledger"), "extra": {"verb": ["strike", "strikes"], "faction": "undead"}},
        "reward": ("mf_glasswater_boots", {"name": "Glasswater Boots", "slot": "feet", "ac": 10, "agi": 4, "sta": 3, "hp": 25, "value": 9000, "rec_level": 24,
                   "no_drop": True, "lore": True, "wear": "leather_boots", "icon": "stalkerhide_boots"}),
        "keywords": ("salters", "dunmore"), "xp": (3420, 380, 7600, 912), "faction": {F: 8},
        "text": {"rep_name": "Salters' Lockets", "drop_plural": "salters' lockets", "trophy_phrase": "Skiffmaster Dunmore's logbook",
                 "rep_ready": "Lockets. There's a face in this one.", "rep_done": "Four families can stop waiting.", "n_ready": "His logbook. Every crossing he made.",
                 "n_done": "The skiff can rest.", "n_reward": "Boots cut for the glass. You won't slip.",
                 "kw_mob": "A skiff went down in the far north-east, crew and all, and the salt kept them. They wander still. Their lockets, four at a time, and I'll pay.",
                 "kw_named": "Skiffmaster Dunmore. He still walks his deck. Bring me his logbook."}}, L, N, S)
    bw.NPCS["mf_skiffscout_imara"]["dialogue"].update(dia)
    bw.NPCS["mf_skiffscout_imara"]["dialogue"]["skiff"] = "A sand-skiff wrecked north-east of here, on a crossing nobody finished. The [salters] still crew it, and [Dunmore] still has the helm."
    pil = [-330, -60]
    wenzel = camp_npc("mf_glassseeker_wenzel", "Glass-Seeker Wenzel", F, "mage", {
        "hail": "The pillars, {name}! Salt, grown like glass, and something wakes in them. [Sentinels]. And the [Pillarmother].",
        "unknown": "I only study the glass."}, "Glass-Seeker", [pil[0] + 60, pil[1] + 50], pil, L, N)
    L += ring_of("salt_pillar", pil, 20, 7)
    dia = place(z, F, {"at": pil, "giver": wenzel, "radius": 40,
        "mob": {"id": "mf_saltglass_sentinel", "name": "a salt-glass sentinel", "base": "mirror_image", "level": (21, 23), "model": "glass_golem",
                "drop": ("mf_saltglass_chip", "Salt-Glass Chip", 10, "salt_crystal"), "extra": {"verb": ["crush", "crushes"], "scale": 0.8}},
        "named": {"id": "mf_pillarmother", "name": "the Pillarmother", "base": "mirror_image", "level": (25, 25), "model": "glass_golem",
                  "trophy": ("mf_pillarmothers_core", "The Pillarmother's Core", "salt_crystal"), "extra": {"verb": ["crush", "crushes"], "scale": 1.4}},
        "reward": ("mf_saltglass_lens", {"name": "Salt-Glass Lens", "slot": "neck", "ac": 5, "int": 5, "wis": 5, "mana": 45, "hp": 25, "value": 9000, "rec_level": 24,
                   "no_drop": True, "lore": True, "icon": "bone_talisman"}),
        "keywords": ("sentinels", "pillarmother"), "xp": (3420, 380, 7600, 912), "faction": {F: 8},
        "text": {"rep_name": "Salt-Glass Chips", "drop_plural": "salt-glass chips", "trophy_phrase": "the Pillarmother's core",
                 "rep_ready": "Chips! Look how the light goes through.", "rep_done": "Four more for my cases.", "n_ready": "Her core. It's humming.",
                 "n_done": "The pillars sleep.", "n_reward": "Ground from the purest glass. See the salt through it.",
                 "kw_mob": "The sentinels grow out of the pillars and walk. Four chips of them and I'll pay, again and again.",
                 "kw_named": "The Pillarmother. The oldest pillar, and the others grow from her. Bring me her core."}}, L, N, S)
    bw.NPCS[wenzel]["dialogue"].update(dia)
    L += [dict(bw.prop("market_stall", [-230, 330], collide="box", yaw=200), **TAG), dict(bw.prop("nomad_tent", [-244, 320], collide="box", yaw=140), **TAG)]
    return L, N, S, [camp] + huts


def ivory_field(z):
    F = "barrowhold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 0, 530, 1, "if_pathfinder_anselm", "Pathfinder Anselm", "Tuskwatch", "ranger_class",
        "Hollowtusk Camp, {name}: Tuskwatch's fire at the crossroads. Anything the Bonewarden or the others asked of you, hand it in here. And ask me about the [gate].",
        "if_sutler_oona", "Sutler Oona", ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Tuskwatch warden", "Tuskwatch", ["ivory_shard_q", "ossuary_heartbone_q", "poached_ivory_q", "vargas_tusk_saw_q", "carrion_feather_q",
        "gorgemaws_beak_q", "ghost_ivory_q", "grandmothers_tusk_q"], {})
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "if", "a Tuskwatch warden", "Tuskwatch", [(1, 260, 1), (1, 780, -1), (0, 250, -1)])
    L += hL
    N += hN
    dia = place(z, F, {"at": [300, -300], "giver": "if_pathfinder_anselm",
        "props": [("tusk_field", 0, -16, 0, "box"), ("elephant_skull", 14, 6, 200, "box"), ("spirit_cairn", -16, 8, 0, "box")],
        "mob": {"id": "if_starving_shade", "name": "a starving shade", "base": "herd_spirit", "level": (43, 45), "model": "hungry_ghost",
                "drop": ("if_shade_bead", "Shade's Prayer Bead", 40, "ghost_ivory"), "extra": {"verb": ["claw", "claws"], "shape": "humanoid"}},
        "named": {"id": "if_hollow_mahout", "name": "the Hollow Mahout", "base": "herd_spirit", "level": (46, 46), "model": "wraith",
                  "trophy": ("if_mahouts_goad", "The Hollow Mahout's Goad", "ivory_shard"), "extra": {"verb": ["strike", "strikes"], "shape": "humanoid", "scale": 1.2}},
        "reward": ("if_tusk_gate_cowl", {"name": "Tusk Gate Cowl", "slot": "head", "ac": 16, "int": 9, "wis": 9, "mana": 100, "hp": 55, "value": 44000, "rec_level": 45,
                   "no_drop": True, "lore": True, "wear": "cloth_cap", "icon": "death_mask_cowl"}),
        "keywords": ("shades", "mahout"), "xp": (17100, 1900, 38000, 4560), "faction": {F: 8},
        "text": {"rep_name": "Shades' Prayer Beads", "drop_plural": "shades' prayer beads", "trophy_phrase": "the Hollow Mahout's goad",
                 "rep_ready": "Beads. Cold as snow.", "rep_done": "Four shades gone quiet.", "n_ready": "His goad. The herds are free of him.",
                 "n_done": "The gate's only bones now.", "n_reward": "A cowl the Tuskwatch wore at the gate. Take it.",
                 "kw_mob": "Shades gather at the Tusk Gate, starving for the herds they drove. Four of their beads and I'll pay, every time.",
                 "kw_named": "The Hollow Mahout drove the great herds here to die, and drives them still. Bring me his goad."}}, L, N, S)
    bw.NPCS["if_pathfinder_anselm"]["dialogue"].update(dia)
    bw.NPCS["if_pathfinder_anselm"]["dialogue"]["gate"] = "North-east, the Tusk Gate: an arch of tusks where the old herds came in to die. [Shades] wait there, and the [Mahout] who drove them."
    bh = [330, 320]
    ulrike = camp_npc("if_bonecarver_ulrike", "Bone-Carver Ulrike", F, "barbarian", {
        "hail": "Good ivory in that hollow, {name}, if the [beetles] would let a body work. And their [Marrow Queen].",
        "unknown": "I carve, {name}. The Bonewarden knows the rest."}, "Bone-Carver", [bh[0] - 70, bh[1] - 50], bh, L, N, weapon="dagger", gender="female")
    dia = place(z, F, {"at": bh, "giver": ulrike,
        "props": [("giant_ribcage", 0, 0, 30, "mesh"), ("ivory_pile", 18, -12, 0, "box"), ("ivory_pile", -16, 14, 0, "box")],
        "mob": {"id": "if_marrow_beetle", "name": "a marrow beetle", "base": "marrow_jackal", "level": (42, 44), "model": "fire_beetle",
                "drop": ("if_beetle_shell", "Marrow Beetle Shell", 40, "chitin_plate"), "extra": {"verb": ["bite", "bites"], "scale": 1.6}},
        "named": {"id": "if_marrow_queen", "name": "the Marrow Queen", "base": "marrow_jackal", "level": (46, 46), "model": "fire_beetle",
                  "trophy": ("if_queens_mandible", "The Marrow Queen's Mandible", "chitin_plate"), "extra": {"verb": ["bite", "bites"], "scale": 2.8}},
        "reward": ("if_bonecarvers_gloves", {"name": "Bone-Carver's Gloves", "slot": "hands", "ac": 14, "agi": 7, "str": 5, "hp": 50, "value": 44000, "rec_level": 45,
                   "no_drop": True, "lore": True, "wear": "leather_gloves", "icon": "hornbone_gauntlets"}),
        "keywords": ("beetles", "marrow queen"), "xp": (17100, 1900, 38000, 4560), "faction": {F: 8},
        "text": {"rep_name": "Marrow Beetle Shells", "drop_plural": "marrow beetle shells", "trophy_phrase": "the Marrow Queen's mandible",
                 "rep_ready": "Shells! Good for inlay.", "rep_done": "Four fewer in my hollow.", "n_ready": "Her mandible. What a size.",
                 "n_done": "The hollow's mine to work.", "n_reward": "My carving gloves. Keep your fingers.",
                 "kw_mob": "Beetles that eat the marrow out of the old bones. Four of their shells and I'll pay, as often as you bring them.",
                 "kw_named": "The Marrow Queen, as big as a cart, laying in the great ribcage. Bring me her mandible."}}, L, N, S)
    bw.NPCS[ulrike]["dialogue"].update(dia)
    L.append(lm("watchtower", [-400, 60], face=[-300, 60]))
    return L, N, S, [camp] + huts


REEDMERE_ISLANDS = [[-170, 10, 24], [200, 250, 16]]  # dry ground for the Heronwatch and the weir


def reedmere(z):
    F = "rainhold"
    L, N, S = [], [], []
    lake = z["lakes"][0]
    for isl in REEDMERE_ISLANDS:
        if isl not in lake["islands"]:
            lake["islands"].append(isl)
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "rm_reedwatcher_achebe", "Reedwatcher Achebe", "Reedwatch", "ranger_class",
        "The Heronwatch, {name}: the Reedwatch's island out in the middle. Pallavi's work, Kesh's, the Priestess's, you can hand it in here and save the wade back. And ask me about the [bell].",
        "rm_sutler_naledi", "Sutler Naledi", ["crude_arrow", "iron_tipped_arrow", "sling_stone", "loaf_of_bread", "roast_meat", "water_flask"],
        "a Rainhold Reedwatch", "Reedwatch", ["pondkin_fetishes", "bloatking_crown", "reedstalker_plumes", "stilt_legs_plume", "sunken_charms",
        "headwomans_lotus", "marrowroot_heart"], {}, at=[-170, 10], face=[-120, 10])
    L += cL
    N += cN
    dia = place(z, F, {"at": [0, -330], "giver": "rm_reedwatcher_achebe",
        "props": [("stilt_hut_sunken", 0, 0, 20, "box"), ("stilt_hut_sunken", 18, 10, 200, "box"), ("mooring_post", -12, 12, 0, "box")],
        "mob": {"id": "rm_drowned_ringer", "name": "a drowned bell-ringer", "base": "sunken_villager", "level": (23, 25), "model": "drowned",
                "drop": ("rm_bell_clapper", "Tarnished Bell Clapper", 10, "tarnished_ring"), "extra": {"verb": ["claw", "claws"]}},
        "named": {"id": "rm_bellwarden", "name": "the Bellwarden", "base": "sunken_villager", "level": (26, 26), "model": "tide_knight",
                  "trophy": ("rm_bellwardens_bell", "The Bellwarden's Bell", "bone_charm"), "extra": {"verb": ["strike", "strikes"]}},
        "reward": ("rm_heronwatch_blade", {"name": "Heronwatch Blade", "slot": "primary", "dmg": 16, "delay": 2.6, "verb": ["slash", "slashes"], "model": "sword_1handed",
                   "skill": "1h_slashing", "agi": 4, "str": 4, "hp": 25, "value": 9000, "rec_level": 25, "no_drop": True, "lore": True,
                   "classes": ["warrior", "rogue", "ranger"], "icon": "asras_skiff_blade"}),
        "keywords": ("ringers", "bellwarden"), "xp": (3200, 380, 7600, 912), "faction": {F: 8},
        "text": {"rep_name": "Bell Clappers", "drop_plural": "tarnished bell clappers", "trophy_phrase": "the Bellwarden's bell",
                 "rep_ready": "Clappers. They'll ring no more floods.", "rep_done": "Four bells quiet.", "n_ready": "His bell. Listen: nothing.",
                 "n_done": "The marsh can sleep.", "n_reward": "The Heronwatch's blade. It's cut a lot of reeds.",
                 "kw_mob": "The bell-ringers of the north hamlet, drowned at their ropes when the water came. Four of their clappers and I'll pay, every time.",
                 "kw_named": "The Bellwarden. He rang the flood bell too late, and now he rings it for the drowned. Bring me the bell."}}, L, N, S)
    bw.NPCS["rm_reedwatcher_achebe"]["dialogue"].update(dia)
    bw.NPCS["rm_reedwatcher_achebe"]["dialogue"]["bell"] = "North, a hamlet the marsh took, stilts and all. Its [ringers] still ring the flood bell, and the [Bellwarden] with them."
    weir = [250, 300]
    makena = camp_npc("rm_fisher_makena", "Fisher Makena", F, "barbarian", {
        "hail": "That was my weir, {name}, before the [eels] came up it. And the [Eel-Mother] behind them.",
        "unknown": "I fish, {name}. Ask Kesh about boats."}, "Fisher", [200, 250], weir, L, N, weapon="axe_1handed", gender="female")
    dia = place(z, F, {"at": weir, "giver": makena,
        "props": [("mooring_post", 0, -10, 0, "box"), ("mooring_post", 10, -4, 0, "box"), ("canoe", -10, 8, 60, "box"), ("drying_rack", 16, 12, 30, "box")],
        "mob": {"id": "rm_weir_eel", "name": "a weir eel", "base": "marsh_eel", "level": (22, 24), "model": "marsh_eel",
                "drop": ("rm_eel_fin", "Weir Eel Fin", 10, "eel_skin"), "extra": {"verb": ["bite", "bites"]}},
        "named": {"id": "rm_eel_mother", "name": "the Eel-Mother", "base": "marsh_eel", "level": (26, 26), "model": "marsh_eel",
                  "trophy": ("rm_eel_mothers_eye", "The Eel-Mother's Eye", "eel_skin"), "extra": {"verb": ["bite", "bites"], "scale": 2.2}},
        "reward": ("rm_weirkeepers_ring", {"name": "Weirkeeper's Ring", "slot": "ring", "ac": 5, "sta": 4, "agi": 3, "wis": 3, "hp": 35, "value": 9000, "rec_level": 25,
                   "no_drop": True, "lore": True, "icon": "breathshard_ring"}),
        "keywords": ("eels", "eel-mother"), "xp": (3200, 380, 7600, 912), "faction": {F: 8},
        "text": {"rep_name": "Weir Eel Fins", "drop_plural": "weir eel fins", "trophy_phrase": "the Eel-Mother's eye",
                 "rep_ready": "Fins! Makes a good soup.", "rep_done": "Four fewer in my weir.", "n_ready": "Her eye. Big as a plate.",
                 "n_done": "I'll mend the weir tomorrow.", "n_reward": "My mother's ring. She kept this weir before me.",
                 "kw_mob": "Eels, thick as your arm, up from the deep channels. Four of their fins and I'll pay, again and again.",
                 "kw_named": "The Eel-Mother, the one they all came up behind. Bring me her eye."}}, L, N, S)
    bw.NPCS[makena]["dialogue"].update(dia)
    L.append(lm("watchtower", [260, 80], face=[160, 80]))
    return L, N, S, [camp]


# ================================================================ batch 3: the Silted Reach, Blackglass, Smokewood, Stonesail

def _t(rep_name, drop_plural, trophy_phrase, kw_mob, kw_named, rep_ready="Good. That's four.", rep_done="Four fewer out there.",
       n_ready="That's it. That's the one.", n_done="It's over, then. Thank you.", n_reward="Take this. You've earned it."):
    return {"rep_name": rep_name, "drop_plural": drop_plural, "trophy_phrase": trophy_phrase, "rep_ready": rep_ready, "rep_done": rep_done,
            "n_ready": n_ready, "n_done": n_done, "n_reward": n_reward, "kw_mob": kw_mob, "kw_named": kw_named}


def silted_reach(z):
    F = "rainhold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "sr_channelwatch_ioana", "Channelwatch Ioana", "Reedwatch", "ranger_class",
        "The Channelwatch, {name}: between the middle and east channels, as far up the delta as Rainhold keeps a fire. Sione's work, the Headman's, Anh's and Cato's, you can hand in here. And ask me about the [rookery].",
        "sr_sutler_femi", "Sutler Femi", ["crude_arrow", "iron_tipped_arrow", "sling_stone", "loaf_of_bread", "roast_meat", "water_flask"],
        "a Rainhold Reedwatch", "Reedwatch", ["whisker_barbel_q", "river_kings_pearl_crown_q", "mud_charm_q", "shell_mask_q", "serpent_scale_q",
        "coilmothers_fang_q", "smugglers_token_q", "blackwaters_ledger_q"], {}, gender="female", at=[40, -160], face=[40, -60])
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "sr", "a Rainhold Reedwatch", "Reedwatch", [(1, 120, 1), (2, 90, -1)])
    L += hL
    N += hN
    dia = place(z, F, {"at": [290, -290], "giver": "sr_channelwatch_ioana",
        "props": [("mud_dam", 0, 14, 20, "box"), ("crag_rock", -16, -10, 0, "box"), ("crag_rock", 18, -14, 90, "box")],
        "mob": {"id": "sr_delta_toad", "name": "a delta toad", "base": "delta_serpent", "level": (24, 26), "model": "mire_toad",
                "drop": ("sr_croaker_gland", "Croaker Gland", 12, "wallow_toad_skin"), "extra": {"verb": ["slam", "slams"], "scale": 1.4}},
        "named": {"id": "sr_gulmog", "name": "Gulmog the Bellower", "base": "delta_serpent", "level": (29, 29), "model": "mire_toad",
                  "trophy": ("sr_gulmogs_throat_sac", "Gulmog's Throat-Sac", "mire_toad_skin"), "extra": {"verb": ["slam", "slams"], "scale": 2.3}},
        "reward": ("sr_channelwatch_gloves", {"name": "Channelwatch Gloves", "slot": "hands", "ac": 11, "agi": 5, "sta": 4, "hp": 30, "value": 10000, "rec_level": 27,
                   "no_drop": True, "lore": True, "wear": "leather_gloves", "icon": "serpentscale_gloves"}),
        "keywords": ("toads", "gulmog"), "xp": (4500, 500, 10000, 1200), "faction": {F: 8},
        "text": _t("Croaker Glands", "croaker glands", "Gulmog's throat-sac",
                   "Delta toads, the size of a dog, crowding the rookery rocks. Four of their glands and I'll pay, every time: the apothecaries in Rainhold want them.",
                   "Gulmog the Bellower, the old bull of the rookery. You'll hear him before you see him. Bring me his throat-sac.",
                   rep_ready="Glands! Mind, they're slippery.", rep_done="Four quieter rocks.", n_ready="His throat-sac. The rookery can hear itself think.", n_done="No more bellowing on the channels.",
                   n_reward="Channelwatch gloves. They grip wet rope.")}, L, N, S)
    bw.NPCS["sr_channelwatch_ioana"]["dialogue"].update(dia)
    bw.NPCS["sr_channelwatch_ioana"]["dialogue"]["rookery"] = "Far north-east, where the channels start, a rock rookery full of [toads]. And the bull, [Gulmog]."
    mg = [-290, 40]
    ama = camp_npc("sr_herbalist_ama", "Herbalist Ama", F, "mage", {
        "hail": "Mind the mangroves, {name}. The roots walk here: [lurkers], and the old one they call [Tanglefoot].",
        "unknown": "I gather, {name}. Ask Sione."}, "Herbalist", [mg[0] + 60, mg[1] + 50], mg, L, N, gender="female")
    dia = place(z, F, {"at": mg, "giver": ama,
        "props": [("sunken_barge", 0, 16, 60, "box"), ("rowboat", -14, -12, 200, "box")],
        "mob": {"id": "sr_mangrove_lurker", "name": "a mangrove lurker", "base": "whiskerfolk", "level": (25, 27), "model": "bog_lurker",
                "drop": ("sr_mangrove_root", "Walking Mangrove Root", 12, "ember_heartwood"), "extra": {"verb": ["lash", "lashes"], "faction": "wildlife", "social": False}},
        "named": {"id": "sr_old_tanglefoot", "name": "Old Tanglefoot", "base": "whiskerfolk", "level": (29, 29), "model": "bog_lurker",
                  "trophy": ("sr_tanglefoots_heartroot", "Old Tanglefoot's Heartroot", "ember_heartwood"), "extra": {"verb": ["lash", "lashes"], "faction": "wildlife", "scale": 1.8}},
        "reward": ("sr_mangrove_circlet", {"name": "Mangrove Circlet", "slot": "head", "ac": 12, "wis": 6, "int": 6, "hp": 30, "mana": 50, "value": 10000, "rec_level": 28,
                   "no_drop": True, "lore": True, "wear": "cloth_cap", "icon": "pearl_crown_of_the_river"}),
        "keywords": ("lurkers", "tanglefoot"), "xp": (4500, 500, 10000, 1200), "faction": {F: 8},
        "text": _t("Mangrove Roots", "walking mangrove roots", "Old Tanglefoot's heartroot",
                   "The lurkers are the mangroves themselves, walking. Four of their roots and I'll pay you, as often as you bring them: they make the best poultice in the Monsoon.",
                   "Tanglefoot is the oldest of them. His heartroot is black as tar. Bring it to me.",
                   rep_ready="Roots. Still twitching.", rep_done="Four more poultices.", n_ready="His heartroot. It's gone still.", n_done="The mangroves are only trees again.",
                   n_reward="Woven from the first roots I ever cut. It keeps your head clear.")}, L, N, S)
    bw.NPCS[ama]["dialogue"].update(dia)
    L.append(lm("watchtower", [-230, 240], face=[-150, 200]))
    return L, N, S, [camp] + huts


def blackglass(z):
    F = "forgehold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "bg_glasswalker_hrafn", "Glasswalker Hrafn", "Forgehold Scouts", "ranger_class",
        "Glassfire Camp, {name}: the Forge's only fire on the glass. Solveig's work, Uzma's, Farid's and Captain Ragna's, you can hand it all in here, and save the walk to Forgehold. Ask me about the [borers].",
        "bg_sutler_greta", "Sutler Greta", ["iron_tipped_arrow", "windcutter_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Forgehold sentry", "Forgehold Scouts", ["drake_scales", "glass_cores", "colossus_heart", "vitrax_eye", "glass_silk", "shardmothers_crown",
        "glassbound_insignia", "aldrics_banner"], {}, at=[-40, 40], face=[40, 80])
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "bg", "a Forgehold sentry", "Forgehold Scouts", [(0, 200, 1), (0, 520, -1)])
    L += hL
    N += hN
    tomb = [-330, -20]
    dia = place(z, F, {"at": tomb, "giver": "bg_glasswalker_hrafn",
        "props": [("glass_entombed", 0, 0, 30, "box"), ("glass_entombed", 16, 10, 200, "box"), ("broken_pillar", -14, 12, 80, "mesh"), ("glass_shards", 10, -16, 0, "none")],
        "mob": {"id": "bg_obsidian_borer", "name": "an obsidian borer", "base": "glass_spider", "level": (32, 34), "model": "fire_beetle",
                "drop": ("bg_borer_carapace", "Obsidian Borer Carapace", 20, "obsidian_scale"), "extra": {"verb": ["bite", "bites"], "scale": 1.5, "color": "#2a2a33"}},
        "named": {"id": "bg_sable_borer", "name": "the Sable Borer", "base": "glass_spider", "level": (36, 36), "model": "fire_beetle",
                  "trophy": ("bg_sable_mandible", "The Sable Borer's Mandible", "chitin_plate"), "extra": {"verb": ["bite", "bites"], "scale": 2.6, "color": "#1a1a22"}},
        "reward": ("bg_glassfire_leggings", {"name": "Glassfire Leggings", "slot": "legs", "ac": 20, "sta": 6, "agi": 5, "hp": 50, "value": 21000, "rec_level": 34,
                   "no_drop": True, "lore": True, "wear": "leather_leggings", "icon": "obsidian_scale_leggings"}),
        "keywords": ("borers", "sable borer"), "xp": (6200, 760, 15000, 2100), "faction": {F: 8},
        "text": _t("Borer Carapaces", "obsidian borer carapaces", "the Sable Borer's mandible",
                   "Beetles that eat into the glass, around the entombed watch in the west. Four of their carapaces and the Forge pays, every time.",
                   "The Sable Borer, black as the glass it eats. It dug the watchmen out of the glass to get at them. Bring me its mandible.",
                   rep_ready="Carapaces. Sharp as the glass.", rep_done="Four borers the watch won't hear.", n_ready="Its mandible. The watch can lie still.", n_done="The glass keeps its dead now.",
                   n_reward="Leggings cut from its shell. Nothing on the glass will cut through them.")}, L, N, S)
    bw.NPCS["bg_glasswalker_hrafn"]["dialogue"].update(dia)
    bw.NPCS["bg_glasswalker_hrafn"]["dialogue"]["borers"] = "West, a Forge watch the glass swallowed whole, men and all. The [borers] are digging them out again, and the [Sable Borer] is the worst."
    gd = [300, 120]
    tovi = camp_npc("bg_glassdiviner_tovi", "Glass-Diviner Tovi", F, "mage", {
        "hail": "You see the lights, {name}? The garden grows them. [Wisps], and something brighter at the heart: [Prism-Heart].",
        "unknown": "I read the glass. Hrafn reads the rest."}, "Glass-Diviner", [gd[0] - 60, gd[1] + 50], gd, L, N)
    dia = place(z, F, {"at": gd, "giver": tovi,
        "props": [("glass_pool", 0, 0, 0, "none"), ("obsidian_spire", 18, -10, 40, "box"), ("obsidian_spire", -16, 14, 140, "box"), ("glass_shards", -10, -18, 0, "none")],
        "mob": {"id": "bg_glass_wisp", "name": "a glass wisp", "base": "glass_golem", "level": (32, 34), "model": "mirage_wisp",
                "drop": ("bg_wisp_prism", "Wisp Prism", 20, "glass_core"), "extra": {"verb": ["sear", "sears"]}},
        "named": {"id": "bg_prism_heart", "name": "Prism-Heart", "base": "glass_golem", "level": (36, 36), "model": "mirage_wisp",
                  "trophy": ("bg_prism_hearts_core", "Prism-Heart's Core", "salt_crystal"), "extra": {"verb": ["sear", "sears"], "scale": 1.8}},
        "reward": ("bg_diviners_lens", {"name": "Diviner's Lens", "slot": "neck", "ac": 7, "int": 7, "wis": 7, "mana": 70, "hp": 40, "value": 21000, "rec_level": 35,
                   "no_drop": True, "lore": True, "icon": "glasswrights_lenses"}),
        "keywords": ("wisps", "prism-heart"), "xp": (6200, 760, 15000, 2100), "faction": {F: 8},
        "text": _t("Wisp Prisms", "wisp prisms", "Prism-Heart's core",
                   "The wisps are light the glass caught and won't let go. Four of their prisms and I'll pay, every time.",
                   "Prism-Heart, the brightest of them, at the garden's pool. Bring me its core, and the garden will go dark.",
                   rep_ready="Prisms! Hold one to the sun.", rep_done="Four lights put out.", n_ready="Its core. Still warm.", n_done="The garden's dark. Good.",
                   n_reward="Ground from a prism. You'll see the glass differently now.")}, L, N, S)
    bw.NPCS[tovi]["dialogue"].update(dia)
    L.append(lm("watchtower", [200, 240], face=[120, 200]))
    return L, N, S, [camp] + huts


def smokewood(z):
    F = "forgehold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 0, 480, -1, "sw_woodrunner_kasia", "Woodrunner Kasia", "Woodwardens", "ranger_class",
        "Emberfall Camp, {name}: the woodwardens' fire in the heart of the wood. Sefa's work, Bartek's, Liesl's, Ondine's, hand it in here. And ask me about the [hollow].",
        "sw_sutler_piet", "Sutler Piet", ["iron_tipped_arrow", "windcutter_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Smokewood warden", "Woodwardens", ["ember_heartwood_q", "emberhearts_heart_q", "smoke_pelt_q", "ashen_antler_q", "soot_mask_fragment_q",
        "kolts_antlered_mask_q", "fire_moth_dust_q", "moth_queens_wing_q"], {}, gender="female")
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "sw", "a Smokewood warden", "Woodwardens", [(0, 200, 1), (1, 150, 1), (2, 150, -1)])
    L += hL
    N += hN
    fh = [-200, -280]
    dia = place(z, F, {"at": fh, "giver": "sw_woodrunner_kasia",
        "props": [("giant_fungus", 0, 0, 0, "box"), ("giant_fungus", 16, 12, 90, "box"), ("giant_fungus", -18, 8, 200, "box"), ("glowing_roots", 6, -16, 0, "none")],
        "mob": {"id": "sw_spore_shambler", "name": "a spore-shambler", "base": "walking_fungus", "level": (33, 35), "model": "walking_fungus",
                "drop": ("sw_spore_sac", "Spore Sac", 24, "glowcap"), "extra": {"verb": ["slam", "slams"]}},
        "named": {"id": "sw_rotcap", "name": "the Rotcap", "base": "walking_fungus", "level": (38, 38), "model": "walking_fungus",
                  "trophy": ("sw_rotcaps_gills", "The Rotcap's Gills", "glowcap"), "extra": {"verb": ["slam", "slams"], "scale": 2.2}},
        "reward": ("sw_emberfall_hood", {"name": "Emberfall Hood", "slot": "head", "ac": 13, "int": 8, "wis": 8, "mana": 80, "hp": 40, "value": 23000, "rec_level": 37,
                   "no_drop": True, "lore": True, "wear": "cloth_cap", "icon": "sootveil_hood"}),
        "keywords": ("shamblers", "rotcap"), "xp": (8775, 975, 19500, 2340), "faction": {F: 8},
        "text": _t("Spore Sacs", "spore sacs", "the Rotcap's gills",
                   "In the north-west hollow the fungus walks. Four of their spore sacs and I'll pay, every time: burned, they keep the moths off.",
                   "The Rotcap is the mother of the hollow, tall as a treant. Bring me its gills.",
                   rep_ready="Sacs. Don't squeeze them.", rep_done="Four fewer shambling about.", n_ready="Its gills. The hollow will wither.", n_done="The moths will have to go elsewhere.",
                   n_reward="The hood I wear in the hollow. The spores can't touch you in it.")}, L, N, S)
    bw.NPCS["sw_woodrunner_kasia"]["dialogue"].update(dia)
    bw.NPCS["sw_woodrunner_kasia"]["dialogue"]["hollow"] = "North-west, a hollow where the fungus grows taller than the trees: [shamblers], and the one they grow from, the [Rotcap]."
    kc = [260, -250]
    ottokar = camp_npc("sw_charcoal_burner_ottokar", "Charcoal-Burner Ottokar", F, "barbarian", {
        "hail": "My kilns, {name}. We burned charcoal here for the Forge until the [imps] moved into them. And [Old Bellows].",
        "unknown": "I burn wood, {name}. Vard sells what I burn."}, "Charcoal-Burner", [kc[0] - 60, kc[1] + 50], kc, L, N, weapon="axe_1handed")
    dia = place(z, F, {"at": kc, "giver": ottokar,
        "props": [("charcoal_kiln", 0, 0, 0, "box"), ("charcoal_kiln", 18, 10, 60, "box"), ("charcoal_kiln", -16, 12, 200, "box"), ("ember_treant_stump", 10, -18, 0, "box")],
        "mob": {"id": "sw_kiln_imp", "name": "a kiln imp", "base": "fire_moth", "level": (34, 36), "model": "fire_imp",
                "drop": ("sw_kiln_cinder", "Kiln Cinder", 24, "giants_coal"), "extra": {"verb": ["claw", "claws"], "shape": "humanoid"}},
        "named": {"id": "sw_old_bellows", "name": "Old Bellows", "base": "fire_moth", "level": (38, 38), "model": "imp_lord",
                  "trophy": ("sw_bellows_horn", "Old Bellows's Horn", "imp_horn"), "extra": {"verb": ["claw", "claws"], "shape": "humanoid"}},
        "reward": ("sw_kilnkeepers_gloves", {"name": "Kilnkeeper's Gloves", "slot": "hands", "ac": 14, "str": 6, "sta": 5, "hp": 45, "value": 23000, "rec_level": 37,
                   "no_drop": True, "lore": True, "wear": "leather_gloves", "icon": "smokehide_gloves"}),
        "keywords": ("imps", "old bellows"), "xp": (8775, 975, 19500, 2340), "faction": {F: 8},
        "text": _t("Kiln Cinders", "kiln cinders", "Old Bellows's horn",
                   "Imps, nesting in my kilns and keeping them hot. Four of their cinders and I'll pay, again and again.",
                   "Old Bellows, the big one. He sleeps in the middle kiln and blows it white-hot. Bring me his horn.",
                   rep_ready="Cinders. Still glowing.", rep_done="Four fewer in my kilns.", n_ready="His horn. The kiln's cooling already.", n_done="We'll burn charcoal again by the first frost.",
                   n_reward="My kiln gloves. They've held hotter things than him.")}, L, N, S)
    bw.NPCS[ottokar]["dialogue"].update(dia)
    L.append(lm("watchtower", [200, 220], face=[120, 180]))
    return L, N, S, [camp] + huts


def stonesail(z):
    F = "galehold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "ss_moorrunner_edric", "Moorrunner Edric", "Moorwatch", "ranger_class",
        "The Westwatch, {name}: the Moorwatch's fire past the great circle. Aldous's work, Wenna's, Idris's and Agathe's, you can hand it in here. And ask me about the [kite hill].",
        "ss_sutler_brisa", "Sutler Brisa", ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Moorwatch ranger", "Moorwatch", ["singing_stone_chip_q", "orlas_tuning_stone_q", "moor_hide_q", "skathes_barbed_tail_q", "rune_shard_q",
        "thrums_heartstone_q", "hags_hair_knot_q", "mirewhistles_ladle_q"], {}, at=[-100, 40], face=[0, 0])
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "ss", "a Moorwatch ranger", "Moorwatch", [(0, 180, 1), (1, 120, -1)])
    L += hL
    N += hN
    kh = [240, -280]
    dia = place(z, F, {"at": kh, "giver": "ss_moorrunner_edric",
        "props": [("kite_pole", 0, 0, 0, "box"), ("kite_pole", 14, 10, 0, "box"), ("banner_pole", -12, 12, 0, "box"), ("crag_rock", 16, -14, 30, "box")],
        "mob": {"id": "ss_moor_harrier", "name": "a moor harrier", "base": "moor_wolf", "level": (37, 39), "model": "giant_eagle",
                "drop": ("ss_harrier_feather", "Harrier Flight-Feather", 28, "firebird_feather"), "extra": {"verb": ["rake", "rakes"], "scale": 0.8}},
        "named": {"id": "ss_old_talonmere", "name": "Old Talonmere", "base": "moor_wolf", "level": (42, 42), "model": "giant_eagle",
                  "trophy": ("ss_talonmeres_talon", "Old Talonmere's Talon", "firebird_feather"), "extra": {"verb": ["rake", "rakes"], "scale": 1.4}},
        "reward": ("ss_westwatch_cloak", {"name": "Westwatch Cloak", "slot": "arms", "ac": 15, "sta": 7, "agi": 6, "hp": 60, "value": 26000, "rec_level": 41,
                   "no_drop": True, "lore": True, "wear": "leather_sleeves", "icon": "moorhide_cloak"}),
        "keywords": ("harriers", "talonmere"), "xp": (10350, 1150, 23000, 2760), "faction": {F: 8},
        "text": _t("Harrier Feathers", "harrier flight-feathers", "Old Talonmere's talon",
                   "Harriers took the kite hill when the kite-flyers left it. Four of their flight-feathers and I'll pay, every time: Galehold fletches with them.",
                   "Old Talonmere, the hen of the hill. She took a kite-flyer once, kite and all. Bring me her talon.",
                   rep_ready="Feathers. Long ones.", rep_done="Four fewer over the hill.", n_ready="Her talon. The kites can fly again.", n_done="Galehold's flyers will be back by spring.",
                   n_reward="A Westwatch cloak. It's kept the moor wind off better riders than me.")}, L, N, S)
    bw.NPCS["ss_moorrunner_edric"]["dialogue"].update(dia)
    bw.NPCS["ss_moorrunner_edric"]["dialogue"]["kite hill"] = "North-east, where Galehold's kite-flyers used to fly. The [harriers] took it, and [Old Talonmere] rules it."
    cn = [-330, -40]
    mabyn = camp_npc("ss_stonereader_mabyn", "Stone-Reader Mabyn", F, "mage", {
        "hail": "The cairns are waking, {name}. Old kings under the moor, and their [wights] with them. The oldest is the [Cairn-King].",
        "unknown": "I read the stones. Idris cuts them."}, "Stone-Reader", [cn[0] + 60, cn[1] + 50], cn, L, N, gender="female")
    L += ring_of("rune_menhir", cn, 18, 5)
    dia = place(z, F, {"at": cn, "giver": mabyn,
        "mob": {"id": "ss_cairn_wight", "name": "a cairn wight", "base": "stone_singer", "level": (38, 40), "model": "barrow_wight",
                "drop": ("ss_cairn_bone", "Cairn Bone", 28, "bleached_bone"), "extra": {"verb": ["strike", "strikes"], "faction": "undead"}},
        "named": {"id": "ss_cairn_king", "name": "the Cairn-King", "base": "stone_singer", "level": (42, 42), "model": "barrow_lord",
                  "trophy": ("ss_cairn_kings_torc", "The Cairn-King's Torc", "bone_charm"), "extra": {"verb": ["strike", "strikes"], "faction": "undead"}},
        "reward": ("ss_stonereaders_torque", {"name": "Stone-Reader's Torque", "slot": "neck", "ac": 9, "int": 8, "wis": 8, "mana": 80, "hp": 50, "value": 26000, "rec_level": 41,
                   "no_drop": True, "lore": True, "icon": "singers_torque"}),
        "keywords": ("wights", "cairn-king"), "xp": (10350, 1150, 23000, 2760), "faction": {F: 8},
        "text": _t("Cairn Bones", "cairn bones", "the Cairn-King's torc",
                   "The wights of the cairns walk at the ring. Four of their bones, and I'll lay them back, and pay you for every four.",
                   "The Cairn-King. His torc is the last gold on the moor. Bring it to me, and the cairns will sleep.",
                   rep_ready="Bones. I'll lay them back tonight.", rep_done="Four wights at rest.", n_ready="His torc. Heavy with years.", n_done="The cairns are quiet.",
                   n_reward="A reader's torque. The stones speak louder to whoever wears it.")}, L, N, S)
    bw.NPCS[mabyn]["dialogue"].update(dia)
    L.append(lm("watchtower", [200, 220], face=[120, 180]))
    return L, N, S, [camp] + huts


# ================================================================ batch 4: Hollow Air, Fogfall, the Unlit, Lastwalk, High Terrace

def _named_lines(t, rr, rd, nr, nd, nw):
    t.update({"rep_ready": rr, "rep_done": rd, "n_ready": nr, "n_done": nd, "n_reward": nw})
    return t


def hollow_air(z):
    F = "galehold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 2, 230, 1, "ha_skyrunner_odile", "Skyrunner Odile", "Driftwatch", "ranger_class",
        "The Highwatch, {name}: Driftwatch's fire under the cloud hall. Imani's work, Kael's, Benedikt's, the Bosun's, hand it in here. And ask me about the [fallen isle].",
        "ha_sutler_mato", "Sutler Mato", ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Driftwatch sentinel", "Driftwatch", ["tempest_mote_q", "hollow_winds_eye_q", "serpent_plume_q", "coilclouds_fang_q", "cloudstone_q",
        "hauvars_mist_crown_q", "skyship_sailcloth_q", "mirelas_spyglass_q"], {}, gender="female")
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "ha", "a Driftwatch sentinel", "Driftwatch", [(0, 400, 1), (1, 250, -1)])
    L += hL
    N += hN
    dia = place(z, F, {"at": [220, -250], "giver": "ha_skyrunner_odile",
        "props": [("fallen_isle", 0, 0, 30, "box"), ("rope_anchor", 18, 12, 0, "box"), ("kite_pole", -16, 14, 0, "box")],
        "mob": {"id": "ha_cloud_ray", "name": "a cloud ray", "base": "sky_serpent", "level": (40, 42), "model": "sky_ray",
                "drop": ("ha_ray_barb", "Cloud Ray Tail-Barb", 30, "serpent_scale"), "extra": {"verb": ["lash", "lashes"]}},
        "named": {"id": "ha_old_stormbarb", "name": "Old Stormbarb", "base": "sky_serpent", "level": (44, 44), "model": "great_sky_ray",
                  "trophy": ("ha_stormbarbs_spine", "Old Stormbarb's Spine", "wader_plume"), "extra": {"verb": ["lash", "lashes"]}},
        "reward": ("ha_highwatch_bracer", {"name": "Highwatch Bracer", "slot": "arms", "ac": 16, "sta": 7, "agi": 6, "hp": 65, "value": 30000, "rec_level": 43,
                   "no_drop": True, "lore": True, "wear": "leather_sleeves", "icon": "tempest_bracer"}),
        "keywords": ("rays", "stormbarb"), "xp": (11700, 1300, 26000, 3120), "faction": {F: 8},
        "text": _named_lines(_t("Cloud Ray Barbs", "cloud ray tail-barbs", "Old Stormbarb's spine",
                   "Cloud rays feed round the isle that fell, north-east. Four of their tail-barbs and I'll pay, every time: Galehold tips its harpoons with them.",
                   "Old Stormbarb, the oldest ray over the isle, grey as a thundercloud. Bring me its spine."),
                   "Barbs. Careful where you put them.", "Four rays fewer in the sky.", "The spine! It's longer than I am.", "The sky over the isle is ours.",
                   "A Highwatch bracer. Keeps the wind off your sword arm.")}, L, N, S)
    bw.NPCS["ha_skyrunner_odile"]["dialogue"].update(dia)
    bw.NPCS["ha_skyrunner_odile"]["dialogue"]["fallen isle"] = "North-east, an isle that lost its tether and came down. The [rays] feed round it, and [Stormbarb] is the oldest of them."
    kw = [-250, 230]
    sunniva = camp_npc("ha_kitewright_sunniva", "Kitewright Sunniva", F, "mage", {
        "hail": "My glider, {name}, or what's left of it. The [sprites] tore it down, and their [Gustmother] with them.",
        "unknown": "I build kites, {name}. Tarrow flies them."}, "Kitewright", [kw[0] + 60, kw[1] - 50], kw, L, N, gender="female")
    dia = place(z, F, {"at": kw, "giver": sunniva,
        "props": [("kite_glider", 0, 0, 40, "box"), ("kite_glider", 14, 12, 200, "box"), ("kite_pole", -14, -10, 0, "box")],
        "mob": {"id": "ha_gale_sprite", "name": "a gale sprite", "base": "tempest_elemental", "level": (39, 41), "model": "gale_spirit",
                "drop": ("ha_sprite_ribbon", "Sprite-Silk Ribbon", 30, "moonsilk_sash"), "extra": {"verb": ["buffet", "buffets"], "scale": 0.8}},
        "named": {"id": "ha_gustmother", "name": "the Gustmother", "base": "tempest_elemental", "level": (44, 44), "model": "gale_spirit",
                  "trophy": ("ha_gustmothers_breath", "The Gustmother's Breath", "tempest_mote"), "extra": {"verb": ["buffet", "buffets"], "scale": 1.7}},
        "reward": ("ha_kitewrights_sash", {"name": "Kitewright's Sash", "slot": "waist", "ac": 12, "agi": 7, "int": 4, "wis": 4, "hp": 30, "mana": 30, "value": 30000,
                   "rec_level": 43, "no_drop": True, "lore": True, "icon": "plumed_belt"}),
        "keywords": ("sprites", "gustmother"), "xp": (11700, 1300, 26000, 3120), "faction": {F: 8},
        "text": _named_lines(_t("Sprite-Silk Ribbons", "sprite-silk ribbons", "the Gustmother's breath",
                   "The sprites weave ribbons of wind and wear them. Four of the ribbons and I'll pay, again and again: they make the best kite-tails.",
                   "The Gustmother is the wind the sprites come from. Catch her breath in a jar and bring it to me."),
                   "Ribbons! Look how they flutter with no wind.", "Four more kite-tails.", "Her breath. The jar's straining.", "I can rebuild in peace.",
                   "My sash. The wind likes whoever wears it.")}, L, N, S)
    bw.NPCS[sunniva]["dialogue"].update(dia)
    L.append(lm("watchtower", [200, 230], face=[120, 190]))
    return L, N, S, [camp] + huts


def fogfall(z):
    F = "barrowhold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 1, 384, -1, "ff_lanternrunner_quill", "Lanternrunner Quill", "Lanternwatch", "ranger_class",
        "The Crossroads Lantern, {name}: as far into the fog as the Lanternwatch keeps a flame. Evander's work, Hilde's, Osric's, Cassia's, hand it in here. And ask me about the [crypt].",
        "ff_sutler_greer", "Sutler Greer", ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Barrowhold lantern-warden", "Lanternwatch", ["tarnished_court_silver_q", "ismays_mourning_veil_q", "gargoyle_stone_q", "grimwatchs_stone_heart_q",
        "fog_hound_pelt_q", "whitemaws_collar_q", "stolen_grave_goods_q", "crowes_black_lantern_q"], {})
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "ff", "a Barrowhold lantern-warden", "Lanternwatch", [(1, 150, 1), (1, 620, -1), (0, 200, 1)])
    L += hL
    N += hN
    cr = [-250, -250]
    dia = place(z, F, {"at": cr, "giver": "ff_lanternrunner_quill",
        "props": [("tombstone_cluster", 0, 0, 0, "box"), ("tombstone_cluster", 16, 12, 90, "box"), ("fog_lantern", -12, 10, 0, "box"), ("fog_ruin_wall", 14, -16, 30, "mesh")],
        "mob": {"id": "ff_fog_wraith", "name": "a fog wraith", "base": "fog_courtier", "level": (41, 43), "model": "wraith",
                "drop": ("ff_shroud_scrap", "Wraith-Shroud Scrap", 34, "sedge_charm"), "extra": {"verb": ["claw", "claws"]}},
        "named": {"id": "ff_veiled_chaplain", "name": "the Veiled Chaplain", "base": "fog_courtier", "level": (44, 44), "model": "mummy_priest",
                  "trophy": ("ff_chaplains_psalter", "The Veiled Chaplain's Psalter", "blackwaters_ledger"), "extra": {"verb": ["strike", "strikes"]}},
        "reward": ("ff_lanternrunner_cloak", {"name": "Lanternrunner's Cloak", "slot": "arms", "ac": 16, "sta": 7, "wis": 5, "int": 5, "hp": 60, "value": 32000, "rec_level": 43,
                   "no_drop": True, "lore": True, "wear": "leather_sleeves", "icon": "foghound_cloak"}),
        "keywords": ("wraiths", "chaplain"), "xp": (15300, 1700, 34000, 4080), "faction": {F: 8},
        "text": _named_lines(_t("Wraith-Shroud Scraps", "wraith-shroud scraps", "the Veiled Chaplain's psalter",
                   "The crypt north-west has no lanterns left, and the wraiths walk out of it. Four scraps of their shrouds and I'll pay, every time.",
                   "The Veiled Chaplain buried Ysmoor's dead, and reads over them still. Bring me his psalter."),
                   "Scraps. They weigh nothing.", "Four wraiths gone back into the fog.", "His psalter. The last page is blank.", "The crypt's dark and quiet.",
                   "A lanternrunner's cloak. The fog slides off it.")}, L, N, S)
    bw.NPCS["ff_lanternrunner_quill"]["dialogue"].update(dia)
    bw.NPCS["ff_lanternrunner_quill"]["dialogue"]["crypt"] = "North-west, Ysmoor's old crypt, the lanterns all out. [Wraiths] come out of it, and the [Chaplain] who kept it."
    qy = [280, 40]
    bertil = camp_npc("ff_quarryman_bertil", "Quarryman Bertil", F, "barbarian", {
        "hail": "Ysmoor was built from this quarry, {name}, and the stone doesn't want to be quarried any more. [Rubble] gets up and walks. And [Old Cairnback].",
        "unknown": "I cut stone. Hilde sets it."}, "Quarryman", [qy[0] - 60, qy[1] + 50], qy, L, N, weapon="axe_1handed")
    dia = place(z, F, {"at": qy, "giver": bertil,
        "props": [("dig_pit", 0, 0, 0, "none"), ("dig_pit", 16, 12, 90, "none"), ("rubble_large", -14, -12, 30, "box"), ("fog_ruin_wall", 18, -16, 120, "mesh")],
        "mob": {"id": "ff_rubble_golem", "name": "a rubble golem", "base": "fog_gargoyle", "level": (41, 43), "model": "earth_elemental",
                "drop": ("ff_fogstone_chip", "Fogstone Chip", 34, "rune_shard"), "extra": {"verb": ["crush", "crushes"]}},
        "named": {"id": "ff_old_cairnback", "name": "Old Cairnback", "base": "fog_gargoyle", "level": (44, 44), "model": "earth_elemental",
                  "trophy": ("ff_cairnbacks_keystone", "Old Cairnback's Keystone", "rune_shard"), "extra": {"verb": ["crush", "crushes"], "scale": 1.8}},
        "reward": ("ff_quarrymans_girdle", {"name": "Quarryman's Girdle", "slot": "waist", "ac": 12, "str": 7, "sta": 6, "hp": 40, "value": 32000, "rec_level": 43,
                   "no_drop": True, "lore": True, "icon": "robbers_sash"}),
        "keywords": ("rubble", "cairnback"), "xp": (15300, 1700, 34000, 4080), "faction": {F: 8},
        "text": _named_lines(_t("Fogstone Chips", "fogstone chips", "Old Cairnback's keystone",
                   "Rubble that walks, in my quarry. Four chips of it and I'll pay, again and again: Hilde needs the stone.",
                   "Old Cairnback is the old quarry face itself, come loose. Bring me the keystone out of him."),
                   "Chips! Good stone, this.", "Four less rubble walking.", "The keystone. It's cracked right through.", "I can cut again tomorrow.",
                   "My girdle. It's held up under a lot of stone.")}, L, N, S)
    bw.NPCS[bertil]["dialogue"].update(dia)
    L += [dict(bw.prop("fog_lantern", [-200, 250], collide="box"), **TAG)]
    L.append(lm("watchtower", [-180, 240], face=[-100, 200]))
    return L, N, S, [camp] + huts


def the_unlit(z):
    F = "barrowhold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 0, 330, 1, "un_lampbearer_ines", "Lampbearer Ines", "Lampward", "ranger_class",
        "The Midnight Lamp, {name}: the Lampward's fire in the middle of the dark. Solenne's work, Kwame's, Yuna's, Aurelio's, hand it in here. And ask me about the [folly].",
        "un_sutler_corwen", "Sutler Corwen", ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Lampward sentinel", "Lampward", ["shade_essence_q", "nameless_echo_q", "shadowhide_q", "starveils_eye_q", "luminous_dust_q",
        "moon_moths_antenna_q", "morvaine_crest_q", "countess_locket_q"], {}, gender="female")
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "un", "a Lampward sentinel", "Lampward", [(0, 200, -1), (0, 620, 1), (1, 200, 1)])
    L += hL
    N += hN
    fo = [300, 20]
    dia = place(z, F, {"at": fo, "giver": "un_lampbearer_ines",
        "props": [("iron_fence", 0, -14, 0, "box"), ("iron_fence", 14, 0, 90, "box"), ("iron_fence", -14, 0, 90, "box"), ("lampward_lamp", 12, 14, 0, "box")],
        "mob": {"id": "un_morvaine_hound", "name": "a Morvaine hound", "base": "night_stalker", "level": (44, 46), "model": "unlit_hound",
                "drop": ("un_collar_stud", "Silver Collar-Stud", 40, "tarnished_ring"), "extra": {"verb": ["bite", "bites"], "faction": "house_morvaine"}},
        "named": {"id": "un_blackfang", "name": "Blackfang, the Countess's Pet", "base": "night_stalker", "level": (48, 48), "model": "unlit_hound",
                  "trophy": ("un_blackfangs_collar", "Blackfang's Jeweled Collar", "morvaine_signet_ring"), "extra": {"verb": ["bite", "bites"], "faction": "house_morvaine", "scale": 1.6}},
        "reward": ("un_lampbearers_gloves", {"name": "Lampbearer's Gloves", "slot": "hands", "ac": 16, "agi": 8, "str": 6, "hp": 60, "value": 38000, "rec_level": 47,
                   "no_drop": True, "lore": True, "wear": "leather_gloves", "icon": "shade_silk_gloves"}),
        "keywords": ("hounds", "blackfang"), "xp": (18900, 2100, 42000, 5040), "faction": {F: 8},
        "text": _named_lines(_t("Silver Collar-Studs", "silver collar-studs", "Blackfang's collar",
                   "The Countess keeps her hounds at her summerhouse, east, behind the iron fence: Morvaine's Folly. Four of their collar-studs and I'll pay, every time.",
                   "Blackfang, her favorite. Bring me its collar, and she'll know who took it."),
                   "Studs. Real silver, too.", "Four hounds that won't bay.", "The collar! She'll be furious.", "The Folly's empty now.",
                   "A lampbearer's gloves. The dark can't get a grip on you.")}, L, N, S)
    bw.NPCS["un_lampbearer_ines"]["dialogue"].update(dia)
    bw.NPCS["un_lampbearer_ines"]["dialogue"]["folly"] = "East, the Countess's summerhouse behind an iron fence: Morvaine's Folly. Her [hounds] run there, and her pet, [Blackfang]."
    mw = [-300, 0]
    oriel = camp_npc("un_wellwarden_oriel", "Well-Warden Oriel", F, "mage", {
        "hail": "This well held the moon, {name}, before the moon went out. Now [wisps] rise out of it, and the [Pale Keeper].",
        "unknown": "I keep the well. Solenne keeps the lamps."}, "Well-Warden", [mw[0] + 60, mw[1] + 50], mw, L, N)
    dia = place(z, F, {"at": mw, "giver": oriel,
        "props": [("moon_well", 0, 0, 0, "box"), ("shade_obelisk", 18, -12, 0, "box"), ("lampward_lamp", -14, 12, 0, "box")],
        "mob": {"id": "un_well_wisp", "name": "a well-wisp", "base": "shade", "level": (44, 46), "model": "lantern_wisp",
                "drop": ("un_moonwater", "Drop of Moonwater", 40, "vial_of_water"), "extra": {"verb": ["sear", "sears"]}},
        "named": {"id": "un_pale_keeper", "name": "the Pale Keeper", "base": "shade", "level": (48, 48), "model": "wraith",
                  "trophy": ("un_pale_keepers_lantern", "The Pale Keeper's Lantern", "echo_of_the_nameless"), "extra": {"verb": ["strike", "strikes"], "scale": 1.4}},
        "reward": ("un_wellwardens_sash", {"name": "Well-Warden's Sash", "slot": "waist", "ac": 13, "int": 8, "wis": 8, "mana": 75, "hp": 30, "value": 38000, "rec_level": 47,
                   "no_drop": True, "lore": True, "icon": "moonsilk_sash"}),
        "keywords": ("wisps", "pale keeper"), "xp": (18900, 2100, 42000, 5040), "faction": {F: 8},
        "text": _named_lines(_t("Drops of Moonwater", "drops of moonwater", "the Pale Keeper's lantern",
                   "The wisps carry the last of the moon's water. Four drops and I'll pay you, as often as you bring them.",
                   "The Pale Keeper was the well's first warden. Bring me his lantern, and the well will sleep."),
                   "Moonwater. It glows in the jar.", "Four fewer wisps.", "His lantern. It's gone cold.", "The well is only a well again.",
                   "My sash. It holds a little of the moon.")}, L, N, S)
    bw.NPCS[oriel]["dialogue"].update(dia)
    L.append(lm("watchtower", [-150, 250], face=[-80, 200]))
    return L, N, S, [camp] + huts


def lastwalk(z):
    F = "barrowhold"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "lw_vigilrunner_tamsin", "Vigilrunner Tamsin", "Pilgrim's Vigil", "ranger_class",
        "The Last Fire, {name}: the Vigil's camp under the Marshal's hill. Mateo's work, Freydis's, Kanoa's, Wilhelmina's, hand it in here. And ask me about the [blade].",
        "lw_sutler_ambrose", "Sutler Ambrose", ["windcutter_arrow", "iron_tipped_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "a Vigil warden", "Pilgrim's Vigil", ["godwar_insignia_q", "marshals_broken_standard_q", "petrified_shard_q", "champions_stone_crest_q",
        "divine_bronze_q", "godforged_core_q", "stolen_relic_q", "oszkars_relic_crown_q"], {}, gender="female", at=[-60, -40], face=[0, 0])
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "lw", "a Vigil warden", "Pilgrim's Vigil", [(0, 180, 1), (1, 200, -1)])
    L += hL
    N += hN
    bl = [250, -260]
    dia = place(z, F, {"at": bl, "giver": "lw_vigilrunner_tamsin",
        "props": [("shattered_divine_blade", 0, 0, 30, "mesh"), ("war_crater", 16, 14, 0, "none"), ("divine_shield_fragment", -14, 12, 60, "box")],
        "mob": {"id": "lw_blade_sentinel", "name": "a blade-shard sentinel", "base": "divine_construct", "level": (47, 49), "model": "sky_guardian",
                "drop": ("lw_divine_steel", "Fleck of Divine Steel", 44, "divine_bronze"), "extra": {"verb": ["cut", "cuts"]}},
        "named": {"id": "lw_blades_warden", "name": "the Blade's Warden", "base": "divine_construct", "level": (50, 50), "model": "sky_guardian",
                  "trophy": ("lw_wardens_hilt_gem", "The Blade's Warden's Hilt-Gem", "godforged_heart_amulet"), "extra": {"verb": ["cut", "cuts"], "scale": 1.5}},
        "reward": ("lw_last_fire_pauldrons", {"name": "Last Fire Pauldrons", "slot": "arms", "ac": 22, "str": 8, "sta": 8, "hp": 80, "value": 44000, "rec_level": 49,
                   "no_drop": True, "lore": True, "wear": "plate_vambraces", "icon": "godwar_pauldrons", "classes": ["warrior", "cleric"]}),
        "keywords": ("sentinels", "warden"), "xp": (21600, 2400, 48000, 5760), "faction": {F: 8},
        "text": _named_lines(_t("Flecks of Divine Steel", "flecks of divine steel", "the Blade's Warden's hilt-gem",
                   "North-east, a god's sword lies broken in the ground, and its shards stand up and guard it. Four flecks of the steel and I'll pay, every time.",
                   "The Blade's Warden guards the hilt. Bring me the gem out of it."),
                   "Flecks. They hum.", "Four sentinels down.", "The hilt-gem. Still warm from the war.", "Let the blade rest.",
                   "Pauldrons from the Vigil's armory. The last fire's colors.")}, L, N, S)
    bw.NPCS["lw_vigilrunner_tamsin"]["dialogue"].update(dia)
    bw.NPCS["lw_vigilrunner_tamsin"]["dialogue"]["blade"] = "North-east, where a god's sword broke. Its shards stand guard: [sentinels], and the [Warden] at the hilt."
    dg = [250, 230]
    ingrith = camp_npc("lw_excavator_ingrith", "Excavator Ingrith", F, "barbarian", {
        "hail": "The dig's mine, {name}, if I could get at it. The war-[hounds] of the last charge are still buried here, and they don't like being dug up. [Ashfang] least of all.",
        "unknown": "I dig. Wilhelmina keeps what I find."}, "Excavator", [dg[0] - 60, dg[1] - 50], dg, L, N, weapon="axe_1handed", gender="female")
    dia = place(z, F, {"at": dg, "giver": ingrith,
        "props": [("relic_cart", 0, 0, 30, "box"), ("dig_pit", 16, 12, 0, "none") if False else ("war_crater", 16, 12, 0, "none"), ("godwar_banner", -14, 12, 0, "box")],
        "mob": {"id": "lw_godwar_hound", "name": "a godwar hound", "base": "relic_scavenger", "level": (46, 48), "model": "fog_hound",
                "drop": ("lw_hound_bone", "Godwar Hound Bone", 44, "bone_charm"), "extra": {"verb": ["bite", "bites"], "faction": "godwar_dead", "color": "#8a8478"}},
        "named": {"id": "lw_ashfang", "name": "Ashfang, Hound of the Last Charge", "base": "relic_scavenger", "level": (50, 50), "model": "fog_hound",
                  "trophy": ("lw_ashfangs_collar", "Ashfang's War-Collar", "tarnished_ring"), "extra": {"verb": ["bite", "bites"], "faction": "godwar_dead", "scale": 1.6}},
        "reward": ("lw_excavators_ring", {"name": "Excavator's Ring", "slot": "ring", "ac": 9, "sta": 8, "agi": 6, "wis": 5, "hp": 70, "value": 44000, "rec_level": 49,
                   "no_drop": True, "lore": True, "icon": "divine_bronze_ring"}),
        "keywords": ("hounds", "ashfang"), "xp": (21600, 2400, 48000, 5760), "faction": {F: 8},
        "text": _named_lines(_t("Godwar Hound Bones", "godwar hound bones", "Ashfang's war-collar",
                   "The hounds of the last charge, dug up and walking. Four of their bones and I'll pay, as often as you bring them.",
                   "Ashfang led the charge. Bring me the war-collar off him."),
                   "Bones. Old as the war.", "Four fewer at my dig.", "His collar. Look at the work in it.", "I can dig in peace.",
                   "The first thing I ever dug up here. It was lucky for me.")}, L, N, S)
    bw.NPCS[ingrith]["dialogue"].update(dia)
    L += [dict(bw.prop("petrified_giant", [-250, 40], collide="mesh", yaw=80), **TAG)]
    return L, N, S, [camp] + huts


def high_terrace(z):
    F = "dawn_pilgrims"
    L, N, S = [], [], []
    cL, cN, camp = forward_camp(z, F, 0, 470, -1, "ht_pilgrim_lobsang", "Pilgrim-Guide Lobsang", "Dawn Pilgrims", "ranger_class",
        "The High Shelter, {name}: the pilgrims' last rest before the monastery. Brother Tenzin's work and the Tea-Mother's, you can hand it in here. And ask me about the [stupa].",
        "ht_sutler_dechen", "Sutler Dechen", ["crude_arrow", "iron_tipped_arrow", "sling_stone", "loaf_of_bread", "terrace_tea", "water_flask"],
        "a Terrace Warden", "Dawn Pilgrims", ["tenzins_beads", "the_abbots_seal", "the_colossus_heart", "pemas_talons", "skyrends_plume"], {})
    L += cL
    N += cN
    hL, hN, huts = huts_on(z, F, "ht", "a Terrace Warden", "Dawn Pilgrims", [(1, 290, 1), (2, 200, -1)])
    L += hL
    N += hN
    st = [-280, 110]
    dia = place(z, F, {"at": st, "giver": "ht_pilgrim_lobsang",
        "props": [("stupa", 0, 0, 0, "box"), ("prayer_wheel", 14, 10, 0, "box"), ("prayer_flags", -12, 12, 0, "none"), ("broken_pillar", 16, -14, 60, "mesh")],
        "mob": {"id": "ht_forsaken_pilgrim", "name": "a forsaken pilgrim", "base": "fallen_monk", "level": (19, 21), "model": "hungry_ghost",
                "drop": ("ht_prayer_scrap", "Pilgrim's Prayer Scrap", 8, "sunken_charm"), "extra": {"verb": ["claw", "claws"], "faction": "undead"}},
        "named": {"id": "ht_unshriven", "name": "the Unshriven", "base": "fallen_monk", "level": (23, 23), "model": "hungry_ghost",
                  "trophy": ("ht_unshrivens_bell", "The Unshriven's Prayer-Bell", "bone_charm"), "extra": {"verb": ["claw", "claws"], "faction": "undead", "scale": 1.4}},
        "reward": ("ht_high_shelter_wraps", {"name": "High Shelter Wraps", "slot": "hands", "ac": 9, "agi": 4, "wis": 4, "hp": 25, "value": 5800, "rec_level": 22,
                   "no_drop": True, "lore": True, "wear": "leather_gloves", "icon": "monks_wraps"}),
        "keywords": ("pilgrims", "unshriven"), "xp": (2200, 300, 5200, 700), "faction": {F: 8},
        "text": _named_lines(_t("Pilgrims' Prayer Scraps", "pilgrims' prayer scraps", "the Unshriven's prayer-bell",
                   "West, a stupa pilgrims died at in the snow, before they reached the monastery. They haunt it still. Four of their prayers and I'll pay, every time.",
                   "The Unshriven led them. He rings his bell for a monastery that never answers. Bring it to me."),
                   "Prayers. I'll say them for them.", "Four pilgrims at rest.", "His bell. It's quiet at last.", "The stupa can be a shrine again.",
                   "Wraps the pilgrims wear for the climb. Warm hands, steady blade.")}, L, N, S)
    bw.NPCS["ht_pilgrim_lobsang"]["dialogue"].update(dia)
    bw.NPCS["ht_pilgrim_lobsang"]["dialogue"]["stupa"] = "West, a stupa where pilgrims froze on the way up. They're still there: forsaken [pilgrims], and the [Unshriven] who led them."
    sh = [300, 140]
    dolkar = camp_npc("ht_herder_dolkar", "Herder Dolkar", F, "barbarian", {
        "hail": "The shielings are ours in summer, {name}, but the [wolves] came down early this year. And [Old Frostjaw] with them.",
        "unknown": "I keep yaks, {name}. The Tea-Mother keeps everything else."}, "Yak-Herder", [sh[0] - 60, sh[1] + 50], sh, L, N, weapon="axe_1handed")
    dia = place(z, F, {"at": sh, "giver": dolkar,
        "props": [("pilgrim_shelter", 0, 0, 30, "box"), ("pilgrim_shelter", 16, 12, 200, "box"), ("prayer_flags", -12, 10, 0, "none")],
        "mob": {"id": "ht_high_wolf", "name": "a high wolf", "base": "snow_leopard", "level": (19, 21), "model": "wolf",
                "drop": ("ht_high_wolf_pelt", "High Wolf Pelt", 8, "wolf_pelt"), "extra": {"verb": ["bite", "bites"], "color": "#d8d8d8"}},
        "named": {"id": "ht_old_frostjaw", "name": "Old Frostjaw", "base": "snow_leopard", "level": (23, 23), "model": "wolf",
                  "trophy": ("ht_frostjaws_fang", "Old Frostjaw's Fang", "wolf_pelt"), "extra": {"verb": ["bite", "bites"], "scale": 1.6, "color": "#f0f0f0"}},
        "reward": ("ht_herders_ring", {"name": "Herder's Ring", "slot": "ring", "ac": 4, "sta": 4, "agi": 3, "hp": 25, "value": 5800, "rec_level": 22,
                   "no_drop": True, "lore": True, "icon": "heartstone_ring"}),
        "keywords": ("wolves", "frostjaw"), "xp": (2200, 300, 5200, 700), "faction": {F: 8},
        "text": _named_lines(_t("High Wolf Pelts", "high wolf pelts", "Old Frostjaw's fang",
                   "The high wolves came down to the shielings. Four pelts and I'll pay, every time: the yaks sleep easier.",
                   "Old Frostjaw leads them, white as the snow. Bring me his fang."),
                   "Pelts. Good and thick.", "Four fewer at my yaks.", "His fang. Longer than my thumb.", "The herd can graze again.",
                   "My father's ring. He'd want it on a wolf-killer.")}, L, N, S)
    bw.NPCS[dolkar]["dialogue"].update(dia)
    L.append(lm("watchtower", [280, -250], face=[200, -200]))
    return L, N, S, [camp] + huts


# ================================================================ batch 5: the smaller open zones (576-672 m): a hut and a place each

def pick_base(z, level):
    """An ordinary monster already in the zone nearest `level`: a new one takes its stats and manners."""
    ids = {m for s in z["spawns"] for m in s["pool"] if not MOBS_NOW.get(m, {}).get("named") and m in MOBS_NOW and not s.get("hubs")}
    return min(sorted(ids), key=lambda m: abs(sum(MOBS_NOW[m]["level"]) / 2 - level))


PINNED_XP = {  # place mob id -> (repeatable xp, coin, named xp, coin): what zone_xp gave when each was written, kept so a rerun can't drift
    "gm_grain_weevil": (80, 50, 90, 20),
    "hf_field_crow": (220, 40, 560, 120),
    "hm_marsh_gnats": (700, 120, 1500, 300),
    "ds_bamboo_viper": (260, 36, 1400, 180),
    "su_dust_scarab": (3200, 300, 7500, 1000),
    "wt_rain_panther": (7000, 600, 16000, 2000),
    "cp_ash_beetle": (4200, 500, 9000, 1200),
    "wb_crag_lizard": (7200, 800, 16000, 1920),
    "wl_bog_crawdad": (120, 40, 150, 30),
    "dk_duskwing": (140, 50, 90, 20),
    "rf_bloated_dead": (700, 120, 1900, 450),
    "bm_cairn_raven": (1000, 180, 2800, 650),
    "cp_slag_hound": (4200, 500, 9000, 1200),
}


def zone_xp(z, key=None):
    """What the zone's own quests pay: (a repeatable one's xp, coin; a named one's xp, coin), medians.
    A place already written keeps the value it got then (PINNED_XP, by its mob id `key`): the medians
    move whenever anyone adds a quest that touches the zone (Nick's line wanting Dewstep's moth wings
    took Jade-Eye from 1400 xp to 120 on a rerun), and a reward shouldn't change under the players."""
    if key in PINNED_XP:
        return tuple(PINNED_XP[key])
    if key:
        print("  NEW place %s: zone_xp worked out its reward; pin it in PINNED_XP" % key)
    here = {n["id"] for n in z.get("npcs", [])}
    drops = {l["item"] for s in z["spawns"] for m in s["pool"] for l in MOBS_NOW.get(m, {}).get("loot", [])}
    qs = [q for q in QUESTS_NOW.values() if (q.get("giver") in here or set(q.get("wants", {})) & drops) and q.get("reward", {}).get("xp")]
    med = lambda v: sorted(v)[len(v) // 2] if v else 0
    rep = [q for q in qs if q.get("repeatable")]
    one = [q for q in qs if not q.get("repeatable")]
    return (med([q["reward"]["xp"] for q in rep]), med([q["reward"].get("coin", 0) for q in rep]),
            med([q["reward"]["xp"] for q in one]), med([q["reward"].get("coin", 0) for q in one]))


def reward_for(level, slot, name, icon, stats, **kw):
    """A quest reward for its level: armor from a straight line in the level (tools/item_curve.py checks it),
    `stats` naming which two attributes it favors."""
    L = level
    ac = round(0.3 * L) + 1 if slot not in ("ring", "neck") else round(0.16 * L) + 1
    d = {"name": name, "slot": slot, "ac": ac, stats[0]: round(L / 6.5) + 1, stats[1]: round(L / 8) + 1, "hp": round(L * 1.1) + 4,
         "value": L * L * 12, "rec_level": L, "no_drop": True, "lore": True, "icon": icon}
    d.update(kw)
    return d


def light_zone(z, F, spec, hut=None):
    """A smaller zone's share: one place with its own npc and two quests, and a guard hut on its main road."""
    L, N, S = [], [], []
    spots = []
    if hut:
        hL, hN, hs = huts_on(z, F, spec["prefix"], hut[0], hut[1], [hut[2]])
        L += hL
        N += hN
        spots += hs
    at = spec["at"]
    home = spec.get("npc_at") or [at[0] - math.copysign(55, at[0]) * 0.8, at[1] - math.copysign(55, at[1]) * 0.6]
    n = spec["npc"]
    giver = camp_npc(n["id"], n["name"], F, n["model"], n["dialogue"], n["title"], home, at, L, N, weapon=n.get("weapon", "staff"),
                     gender=n.get("gender"), race=n.get("race", "human"), level=n.get("level", 30))
    lv = spec["level"]
    spec["mob"]["base"] = pick_base(z, lv)
    spec["named"]["base"] = spec["mob"]["base"]
    spec["mob"]["level"] = (lv - 1, lv + 1)
    spec["named"]["level"] = (lv + 3, lv + 3)
    spec["giver"] = giver
    spec["xp"] = spec.get("xp") or zone_xp(z, spec["mob"]["id"])
    spec["faction"] = spec.get("faction") or {F: 8}
    dia = place(z, F, spec, L, N, S)
    bw.NPCS[giver]["dialogue"].update(dia)
    return L, N, S, spots + [home]


def _p(pid, dx, dy, yaw=0, collide="box"):
    return (pid, dx, dy, yaw, collide)


def greenmoor(z):
    F = "emberhold"
    return light_zone(z, F, {"prefix": "gm", "at": [204, 60], "level": 4, "landmark": ("ruins", {}), "count": 7, "respawn": 45,
        "props": [_p("well", 12, 14), _p("hay_bale", -14, 10), _p("hay_bale", -18, 4)],
        "npc": {"id": "gm_farmwife_gudrun", "name": "Farmwife Gudrun", "model": "barbarian", "title": "of the Old Granary", "gender": "female", "level": 15,
                "dialogue": {"hail": "That's our old granary, {name}, what the fire left. The [weevils] have it now, grain and all. And the [Granary Queen].",
                             "unknown": "I only know grain, love. Ask in town."}},
        "mob": {"id": "gm_grain_weevil", "name": "a grain weevil", "model": "rice_beetle", "drop": ("gm_weevil_husk", "Grain Weevil Husk", 2, "beetle_eye"),
                "extra": {"verb": ["bite", "bites"], "aggressive": False, "aggro_radius": 0}},
        "named": {"id": "gm_granary_queen", "name": "the Granary Queen", "model": "rice_beetle", "trophy": ("gm_granary_queens_crown", "The Granary Queen's Crest", "beetle_eye"),
                  "extra": {"verb": ["bite", "bites"], "scale": 2.0}},
        "reward": ("gm_gudruns_mittens", reward_for(6, "hands", "Gudrun's Harvest Mittens", "wolfhide_boots", ("sta", "agi"), wear="leather_gloves")),
        "keywords": ("weevils", "granary queen"),
        "text": _named_lines(_t("Weevil Husks", "grain weevil husks", "the Granary Queen's crest",
                   "Weevils big as your boot, in what's left of the grain. Four of their husks and I'll pay, every time.",
                   "The Queen, fat as a pig, in the granary cellar. Bring me her crest and the rest will scatter."),
                   "Husks! Crunchy.", "Four fewer at the grain.", "Her crest. Nasty thing.", "We might plant again this spring.",
                   "My harvest mittens. Warm hands for cold mornings.")},
        hut=("a Watch patrolman", "The Watch", (0, 150, 1)))


def harrowfield(z):
    F = "emberhold"
    return light_zone(z, F, {"prefix": "hf", "at": [44, -212], "level": 7, "landmark": ("ruins", {}), "respawn": 55,
        "props": [_p("scarecrow_post", 0, 14), _p("hay_bale", 14, -10), _p("scarecrow_post", -16, -12, 90)],
        "npc": {"id": "hf_crofter_ewan", "name": "Crofter Ewan", "model": "barbarian", "title": "Crofter", "level": 15,
                "dialogue": {"hail": "The north field's lost, {name}. The [crows] came for the seed and never left, and [Old Blackwing] leads them.",
                             "unknown": "Ask Farmer Oswin. He knows more than me."}},
        "mob": {"id": "hf_field_crow", "name": "a field crow", "model": "bone_vulture", "drop": ("hf_crow_feather", "Field Crow Feather", 3, "carrion_feather"),
                "extra": {"verb": ["peck", "pecks"], "scale": 0.5, "color": "#222222"}},
        "named": {"id": "hf_old_blackwing", "name": "Old Blackwing", "model": "bone_vulture", "trophy": ("hf_blackwings_eye", "Old Blackwing's Eye", "carrion_feather"),
                  "extra": {"verb": ["peck", "pecks"], "scale": 0.9, "color": "#111111"}},
        "reward": ("hf_crofters_boots", reward_for(9, "feet", "Crofter's Boots", "wolfhide_boots", ("sta", "agi"), wear="leather_boots")),
        "keywords": ("crows", "blackwing"),
        "text": _named_lines(_t("Crow Feathers", "field crow feathers", "Old Blackwing's eye",
                   "Four of their feathers and I'll pay, every time. My wife stuffs pillows with them. Small mercies.",
                   "Old Blackwing, big as a goose. He sits on the old scarecrow and laughs at me. Bring me his eye."),
                   "Feathers. Soft, at least.", "Four fewer at my seed.", "His eye! Ha.", "The north field's mine again.",
                   "My good boots. For walking the furrows.")},
        hut=("a Watch patrolman", "The Watch", (0, 150, -1)))


def hollowmere(z):
    F = "hollowfolk"
    return light_zone(z, F, {"prefix": "hm", "at": [-84, -260], "level": 13, "respawn": 70,
        "props": [_p("reed_hut", 0, 0, 30), _p("reed_hut", 16, 10, 200), _p("rowboat", -14, 12, 60)],
        "npc": {"id": "hm_reedcutter_olwen", "name": "Reedcutter Olwen", "model": "ranger", "title": "Reedcutter", "gender": "female", "level": 20,
                "dialogue": {"hail": "The north landing was ours, {name}, until the [gnats] bred in the shallows. And the [Droning Mother] they come from.",
                             "unknown": "Ask Elder Tamsin. I cut reeds."}},
        "mob": {"id": "hm_marsh_gnats", "name": "a marsh gnat swarm", "model": "biting_swarm", "drop": ("hm_gnat_wing", "Marsh Gnat Wing", 5, "bogwing_wing"),
                "extra": {"verb": ["sting", "stings"]}},
        "named": {"id": "hm_droning_mother", "name": "the Droning Mother", "model": "biting_swarm", "trophy": ("hm_drone_queens_sac", "The Droning Mother's Egg-Sac", "blightmothers_venom_sac"),
                  "extra": {"verb": ["sting", "stings"], "scale": 2.0}},
        "reward": ("hm_reedcutters_sleeves", reward_for(15, "arms", "Reedcutter's Sleeves", "brigand_armband", ("sta", "agi"), wear="leather_sleeves")),
        "keywords": ("gnats", "droning mother"),
        "text": _named_lines(_t("Gnat Wings", "marsh gnat wings", "the Droning Mother's egg-sac",
                   "Swarms thick as smoke over the landing. Four of their wings and I'll pay, every time.",
                   "The Droning Mother, big as a hen, in the reeds by my old hut. Bring me her egg-sac."),
                   "Wings. Ugh.", "Four swarms fewer.", "Her egg-sac! Burn it, quick.", "The landing's quiet at last.",
                   "Reed-cutting sleeves. Nothing bites through them.")},
        hut=("a Mere Sentry", "Hollowfolk", (0, 200, 1)))


def dewstep(z):
    F = "lanternhold"
    return light_zone(z, F, {"prefix": "ds", "at": [188, -20], "level": 6, "respawn": 45, "npc_at": [196, -78],
        "props": [_p("stone_lantern", 0, 14), _p("stone_lantern", 14, -10), _p("shrine_broken", -12, -8, 90)],
        "npc": {"id": "ds_tea_roller_sunita", "name": "Tea-Roller Sunita", "model": "mage", "title": "Tea-Roller", "gender": "female", "race": "high_elf", "level": 15,
                "dialogue": {"hail": "Mind your ankles by the old shrine, {name}. The [vipers] nest in the lantern stones. And [Jade-Eye], the old mother.",
                             "unknown": "Ask Anjali. She runs the gardens."}},
        "mob": {"id": "ds_bamboo_viper", "name": "a bamboo viper", "model": "water_snake", "drop": ("ds_viper_skin", "Bamboo Viper Skin", 3, "serpent_scale"),
                "extra": {"verb": ["bite", "bites"], "aggressive": False, "aggro_radius": 0, "color": "#6aa050"}},
        "named": {"id": "ds_jade_eye", "name": "Jade-Eye", "model": "water_snake", "trophy": ("ds_jade_eyes_fang", "Jade-Eye's Fang", "serpent_scale"),
                  "extra": {"verb": ["bite", "bites"], "scale": 1.8, "color": "#4a8a40"}},
        "reward": ("ds_tea_rollers_gloves", reward_for(8, "hands", "Tea-Roller's Gloves", "wolfhide_boots", ("agi", "wis"), wear="leather_gloves")),
        "keywords": ("vipers", "jade-eye"),
        "text": _named_lines(_t("Viper Skins", "bamboo viper skins", "Jade-Eye's fang",
                   "Four of their skins and I'll pay, every time: the lantern-makers want them for shades.",
                   "Jade-Eye, green as new tea, sleeps under the broken shrine. Bring me her fang."),
                   "Skins. Mind, they're still slippery.", "Four fewer by the stones.", "Her fang. Longer than my finger.", "The pickers can walk to the shrine again.",
                   "My rolling gloves. Soft on the leaf, soft on your hands.")},
        hut=("a Lanternhold warden", "Lanternhold", (0, 150, 1)))


def sunward_steps(z):
    F = "dawn_pilgrims"
    return light_zone(z, F, {"prefix": "su", "at": [-116, 204], "level": 16, "respawn": 75,
        "props": [_p("well", 0, 0), _p("broken_pillar", 14, 10, 30, "mesh"), _p("broken_pillar", -12, -12, 120, "mesh")],
        "npc": {"id": "su_water_seeker_anil", "name": "Water-Seeker Anil", "model": "ranger", "title": "Water-Seeker", "level": 25,
                "dialogue": {"hail": "The old cistern ran dry, {name}, and the [scarabs] came up out of it. And [Old Dunebore], who dug it dry.",
                             "unknown": "Ask Pilgrim-Mother Ysolde."}},
        "mob": {"id": "su_dust_scarab", "name": "a dust scarab", "model": "fire_beetle", "drop": ("su_scarab_shell", "Dust Scarab Shell", 7, "chitin_plate"),
                "extra": {"verb": ["bite", "bites"], "color": "#c8a870", "scale": 1.2}},
        "named": {"id": "su_old_dunebore", "name": "Old Dunebore", "model": "fire_beetle", "trophy": ("su_dunebores_horn", "Old Dunebore's Horn", "chitin_plate"),
                  "extra": {"verb": ["bite", "bites"], "color": "#a88850", "scale": 2.4}},
        "reward": ("su_water_seekers_sash", reward_for(18, "waist", "Water-Seeker's Sash", "barbel_whip_belt", ("sta", "wis"))),
        "keywords": ("scarabs", "dunebore"),
        "text": _named_lines(_t("Scarab Shells", "dust scarab shells", "Old Dunebore's horn",
                   "Four of their shells and I'll pay, every time. They make good cups, and the pilgrims need cups.",
                   "Old Dunebore dug under the cistern and drank it dry. Bring me his horn."),
                   "Shells. Dusty.", "Four fewer in my cistern.", "His horn. The well might fill again.", "Water, by the next rains.",
                   "A seeker's sash. It's found water in worse places.")},
        hut=("a Dawnwatch Sentry", "Dawn Pilgrims", (0, 200, 1)))


def weeping_throat(z):
    F = "rainhold"
    return light_zone(z, F, {"prefix": "wt", "at": [92, -228], "level": 22, "respawn": 80,
        "props": [_p("tent", 0, 0, 30), _p("campfire", 8, 6, 0, "none"), _p("drying_rack", -12, 10, 60)],
        "npc": {"id": "wt_tracker_mbali", "name": "Tracker Mbali", "model": "ranger_class", "title": "Rainhold Tracker", "gender": "female", "level": 30, "weapon": "bow",
                "dialogue": {"hail": "Quiet, {name}. There are [panthers] in these trees you'll never see. And [Silkpaw], who I've tracked three rains.",
                             "unknown": "I track, {name}. Ask in Rainhold."}},
        "mob": {"id": "wt_rain_panther", "name": "a rain panther", "model": "tigress", "drop": ("wt_panther_whisker", "Rain Panther Whisker", 9, "whisker_barbel"),
                "extra": {"verb": ["claw", "claws"], "color": "#222222"}},
        "named": {"id": "wt_silkpaw", "name": "Silkpaw", "model": "tiger", "trophy": ("wt_silkpaws_pelt", "Silkpaw's Pelt", "smoke_pelt"),
                  "extra": {"verb": ["claw", "claws"], "scale": 1.3, "color": "#111111"}},
        "reward": ("wt_trackers_boots", reward_for(24, "feet", "Tracker's Boots", "stalkerhide_boots", ("agi", "sta"), wear="leather_boots")),
        "keywords": ("panthers", "silkpaw"),
        "text": _named_lines(_t("Panther Whiskers", "rain panther whiskers", "Silkpaw's pelt",
                   "Four whiskers and I'll pay, every time: proof you got close enough to take them.",
                   "Silkpaw, black as the rain at night. I've had her in my sights three times and missed. Bring me her pelt."),
                   "Whiskers. You got close.", "Four fewer in the trees.", "Her pelt. Three rains I chased her.", "I can track something else now.",
                   "My boots. Quiet on the leaves.")}, hut=None)


def cinderpass(z):
    F = "forgehold"
    L, N, S, spots = light_zone(z, F, {"prefix": "cp", "at": [28, 44], "level": 28, "respawn": 85,
        "props": [_p("caravan_wagon", 0, 0, 70), _p("rubble_large", 14, 10, 30), _p("smoldering_stump", -12, -10)],
        "npc": {"id": "cp_carter_hodd", "name": "Carter Hodd", "model": "barbarian", "title": "Forgehold Carter", "level": 30, "weapon": "axe_1handed",
                "dialogue": {"hail": "My cart, {name}, under the ash. Ore for the Forge, and the [beetles] have nested in it. [Cinderback] too, the big one.",
                             "unknown": "Ask Scout-Captain Brenna. I haul ore."}},
        "mob": {"id": "cp_ash_beetle", "name": "an ash beetle", "model": "fire_beetle", "drop": ("cp_ash_carapace", "Ash Beetle Carapace", 14, "chitin_plate"),
                "extra": {"verb": ["bite", "bites"], "color": "#555050", "scale": 1.3}},
        "named": {"id": "cp_cinderback", "name": "Cinderback", "model": "fire_beetle", "trophy": ("cp_cinderbacks_ember_gland", "Cinderback's Ember Gland", "phoenix_ember"),
                  "extra": {"verb": ["bite", "bites"], "color": "#403838", "scale": 2.4}},
        "reward": ("cp_carters_gloves", reward_for(30, "hands", "Carter's Gloves", "smokehide_gloves", ("str", "sta"), wear="leather_gloves")),
        "keywords": ("beetles", "cinderback"),
        "text": _named_lines(_t("Ash Beetle Carapaces", "ash beetle carapaces", "Cinderback's ember gland",
                   "Four of their carapaces and I'll pay, every time. Smith Tovar fires them for flux.",
                   "Cinderback, the biggest, sits right on my cart. Bring me its ember gland."),
                   "Carapaces. Hot still.", "Four fewer in my cart.", "The gland. Careful, it's still burning.", "I can dig my ore out.",
                   "Carter's gloves. For hot ore.")},
        hut=("an Ashwatch sentry", "Forgehold Scouts", (0, 200, 1)))
    # the north road, 2026-10-01: a forward camp between Cindermaw and Pyrrhus, so the far end's hand-ins
    # aren't a 500 m walk back to the outpost, and an abandoned smelter to find west of it
    cL, cN, camp = forward_camp(z, F, None, 0, 0, "cp_ventrunner_odalys", "Ventrunner Odalys", "Forgehold Scouts", "ranger_class",
        "Ventwatch, {name}: the scouts' fire at the top of the pass. Brenna's work, Tovar's, Carter Hodd's, you can hand it all in here and save the walk south. Ask me about the [smelter].",
        "cp_sutler_hadley", "Sutler Hadley", ["iron_tipped_arrow", "windcutter_arrow", "sling_stone", "hunters_pie", "roast_meat", "water_flask"],
        "an Ashwatch sentry", "Forgehold Scouts", ["ember_sigils", "ashkars_brand", "cindermaws_heart", "cp_ash_beetle_q", "cp_cinderback_q"], {},
        at=[-30, -215], face=[6, -215], gender="female")
    L += cL
    N += cN
    smelter = [-130, -150]
    dia = place(z, F, {"at": smelter, "landmark": ("ruins", {}), "giver": "cp_ventrunner_odalys", "count": 7, "respawn": 85,
        "props": [_p("giant_anvil", 12, -8, 30), _p("rubble_large", -16, 12, 80), _p("broken_pillar", 18, 14, 10, "mesh"), _p("smoldering_stump", -10, -18)],
        "mob": {"id": "cp_slag_hound", "name": "a slag hound", "base": pick_base(z, 29), "level": (28, 30), "model": "firehound",
                "drop": ("cp_slag_fang", "Slag Hound Fang", 14, "gnoll_fang"), "extra": {"verb": ["bite", "bites"], "color": "#5a4a40"}},
        "named": {"id": "cp_old_clinkerjaw", "name": "Old Clinkerjaw", "base": pick_base(z, 29), "level": (32, 32), "model": "firehound",
                  "trophy": ("cp_clinkerjaws_tooth", "Old Clinkerjaw's Molten Tooth", "phoenix_ember"), "extra": {"verb": ["bite", "bites"], "scale": 1.8, "color": "#3a2e28"}},
        "reward": ("cp_smeltermans_belt", reward_for(31, "waist", "Smelterman's Belt", "thunderstone_girdle", ("sta", "str"))),
        "keywords": ("hounds", "clinkerjaw"), "xp": zone_xp(z, "cp_slag_hound"), "faction": {F: 8},
        "text": _named_lines(_t("Slag Hound Fangs", "slag hound fangs", "Old Clinkerjaw's molten tooth",
                   "Slag hounds, lean and smoking, denned in the old smelter west of here. Four of their fangs and the Forge pays, every time.",
                   "Old Clinkerjaw leads them, half slag himself. The smelter's crew never got out. Bring me the molten tooth out of his jaw."),
                   "Fangs. Still hot from the slag.", "Four fewer at the smelter.", "His tooth. It's glowing.", "The smelter's quiet. The Forge might fire it again.",
                   "The smelterman's belt. It was his, and it's yours now.")}, L, N, S)
    bw.NPCS["cp_ventrunner_odalys"]["dialogue"].update(dia)
    bw.NPCS["cp_ventrunner_odalys"]["dialogue"]["smelter"] = "West, toward the lava. The Forge ran a smelter there before the ash came. [Slag hounds] den in it now, and [Old Clinkerjaw] with them."
    return L, N, S, spots + [camp, smelter]


def windbreak(z):
    F = "galehold"
    return light_zone(z, F, {"prefix": "wb", "at": [28, -52], "level": 34, "respawn": 90,
        "props": [_p("mesa", 0, -18, 30), _p("crag_rock", 16, 10, 90), _p("crag_rock", -16, 10, 200)],
        "npc": {"id": "wb_arch_warden_petra", "name": "Arch-Warden Petra", "model": "ranger_class", "title": "Wind Scouts", "gender": "female", "level": 40, "weapon": "bow",
                "dialogue": {"hail": "Under the arch, {name}, the rock's warm all day and the [lizards] know it. And [Old Sunbask], who's lain there since before the scouts.",
                             "unknown": "Ask Scout-Leader Emeka."}},
        "mob": {"id": "wb_crag_lizard", "name": "a crag lizard", "model": "lava_salamander", "drop": ("wb_crag_scale", "Crag Lizard Scale", 26, "obsidian_scale"),
                "extra": {"verb": ["bite", "bites"], "color": "#a07850"}},
        "named": {"id": "wb_old_sunbask", "name": "Old Sunbask", "model": "lava_salamander", "trophy": ("wb_sunbasks_frill", "Old Sunbask's Frill", "obsidian_scale"),
                  "extra": {"verb": ["bite", "bites"], "color": "#806040", "scale": 1.9}},
        "reward": ("wb_arch_wardens_bracer", reward_for(36, "arms", "Arch-Warden's Bracer", "tempest_bracer", ("agi", "sta"), wear="leather_sleeves")),
        "keywords": ("lizards", "sunbask"),
        "text": _named_lines(_t("Crag Lizard Scales", "crag lizard scales", "Old Sunbask's frill",
                   "Four of their scales and I'll pay, every time: Galehold's shieldmakers want them.",
                   "Old Sunbask, big as a skiff, on the warm stone under the arch. Bring me her frill."),
                   "Scales. Warm from the sun.", "Four fewer under the arch.", "Her frill. What colors.", "The arch is ours for the watch.",
                   "A warden's bracer. Cut from the arch's own hide, we say.")},
        hut=("a wind scout", "Wind Scouts", (0, 200, 1)))


def the_wallow(z):
    F = "murkhold"
    return light_zone(z, F, {"prefix": "wl", "at": [-116, 60], "level": 5, "respawn": 45,
        "props": [_p("murk_hut", 0, 0, 30), _p("bog_lantern", 12, 10)],
        "npc": {"id": "wl_bog_wife_grunna", "name": "Bog-Wife Grunna", "model": "shaman", "title": "of the Sinking Hut", "gender": "female", "race": "troll", "level": 15,
                "dialogue": {"hail": "My hut's sinkin', {name}, and the [crawdads] come up through the floor. And [Old Pinchmud], the biggest.",
                             "unknown": "Ask Hunter Snikk. Grunna only cooks."}},
        "mob": {"id": "wl_bog_crawdad", "name": "a bog crawdad", "model": "salt_crab", "drop": ("wl_crawdad_tail", "Bog Crawdad Tail", 2, "salt_crab_claw"),
                "extra": {"verb": ["pinch", "pinches"], "aggressive": False, "aggro_radius": 0, "scale": 0.6, "color": "#6a4a3a"}},
        "named": {"id": "wl_old_pinchmud", "name": "Old Pinchmud", "model": "salt_crab", "trophy": ("wl_pinchmuds_claw", "Old Pinchmud's Great Claw", "salt_crab_claw"),
                  "extra": {"verb": ["pinch", "pinches"], "scale": 1.3, "color": "#5a3a2a"}},
        "reward": ("wl_grunnas_wrap", reward_for(7, "waist", "Grunna's Stewing Wrap", "barbel_whip_belt", ("sta", "str"))),
        "keywords": ("crawdads", "pinchmud"),
        "text": _named_lines(_t("Crawdad Tails", "bog crawdad tails", "Old Pinchmud's great claw",
                   "Four tails and Grunna pays, every time. They're good in the pot.",
                   "Old Pinchmud lives under the floor. Big as a stool. Bring Grunna his claw."),
                   "Tails! Into the pot.", "Four for the stew.", "His claw! Grunna'll hang it on the door.", "Maybe the hut stops sinkin'.",
                   "Grunna's stewing wrap. It's kept her warm by the pot for years.")}, hut=None)


def duskwood(z):
    F = "duskhold"
    return light_zone(z, F, {"prefix": "dk", "at": [204, 12], "level": 5, "respawn": 45,
        "props": [_p("stone_lantern", 0, 12), _p("shrine_broken", -12, -8, 90)],
        "npc": {"id": "dk_moth_seer_lirael", "name": "Moth-Seer Lirael", "model": "mage", "title": "Moth-Seer", "gender": "female", "race": "dark_elf", "level": 15,
                "dialogue": {"hail": "The shrine glows at dusk, {name}, and the [duskwings] come to it. And the [Pale Mothmother], who leads them.",
                             "unknown": "The moths tell me little of the rest."}},
        "mob": {"id": "dk_duskwing", "name": "a duskwing moth", "model": "lantern_moth", "drop": ("dk_duskwing_scale", "Duskwing Wing-Scale", 2, "bogwing_wing"),
                "extra": {"verb": ["flutter at", "flutters at"], "aggressive": False, "aggro_radius": 0, "color": "#7050a0"}},
        "named": {"id": "dk_pale_mothmother", "name": "the Pale Mothmother", "model": "lantern_moth", "trophy": ("dk_mothmothers_antenna", "The Pale Mothmother's Antenna", "bogwing_wing"),
                  "extra": {"verb": ["flutter at", "flutters at"], "scale": 2.0, "color": "#d0c0f0"}},
        "reward": ("dk_moth_seers_circlet", reward_for(7, "head", "Moth-Seer's Circlet", "pearl_crown_of_the_river", ("int", "wis"), wear="cloth_cap")),
        "keywords": ("duskwings", "mothmother"),
        "text": _named_lines(_t("Duskwing Scales", "duskwing wing-scales", "the Pale Mothmother's antenna",
                   "Four of their wing-scales and I'll pay, every time: I read the dusk in them.",
                   "The Pale Mothmother, white as the moon, at the shrine's heart. Bring me her antenna."),
                   "Scales. Look how they shimmer.", "Four more for my readings.", "Her antenna. The dusk will be quieter.", "The shrine is only stone again.",
                   "My circlet. It shows you a little of the dusk.")}, hut=None)


def the_rotfen(z):
    F = "rainhold"
    return light_zone(z, F, {"prefix": "rf", "at": [252, -212], "level": 15, "respawn": 70,
        "props": [_p("sunken_barge", 0, 0, 60), _p("rowboat", 14, 12, 200), _p("bone_totem", -12, 10)],
        "npc": {"id": "rf_fen_priest_orun", "name": "Fen-Priest Orun", "model": "mage", "title": "of Jalendra", "level": 25,
                "dialogue": {"hail": "A plague barge, {name}, run aground and never burned. Its [dead] still ride it. And the [Barge-Warden].",
                             "unknown": "Grisk and Nyssa know the fen. I only know the dead."}},
        "mob": {"id": "rf_bloated_dead", "name": "a bloated fen-dead", "model": "drowned", "drop": ("rf_plague_bone", "Plague-Barge Finger-Bone", 5, "bone_chips"),
                "extra": {"verb": ["claw", "claws"], "faction": "undead", "flees": False}},
        "named": {"id": "rf_barge_warden", "name": "the Barge-Warden", "model": "drowned_captain", "trophy": ("rf_wardens_bell", "The Barge-Warden's Plague-Bell", "bone_charm"),
                  "extra": {"verb": ["strike", "strikes"], "faction": "undead"}},
        "reward": ("rf_fen_priests_charm", reward_for(17, "neck", "Fen-Priest's Charm", "shellmask_amulet", ("wis", "sta"))),
        "keywords": ("dead", "barge-warden"),
        "text": _named_lines(_t("Plague Finger-Bones", "plague-barge finger-bones", "the Barge-Warden's plague-bell",
                   "Four of their finger-bones and I'll bless them to rest, and pay you, every time.",
                   "The Barge-Warden rang the plague-bell as they ran aground. Bring me the bell."),
                   "Bones. I'll say the words.", "Four at rest.", "The bell. Silent now.", "I'll burn the barge at last.",
                   "Jalendra's charm. The dead don't like it.")},
        hut=("a Rainhold Reedwatch", "Reedwatch", (0, 150, 1)))


def broken_march(z):
    F = "rainhold"
    return light_zone(z, F, {"prefix": "bm", "at": [12, -244], "level": 17, "landmark": ("ruins", {}), "respawn": 75,
        "props": [_p("crag_rock", 14, 12, 90), _p("banner_pole", -12, 12)],
        "npc": {"id": "bm_beacon_keeper_hesk", "name": "Beacon-Keeper Hesk", "model": "knight", "title": "of the Last Beacon", "level": 30, "weapon": "sword_1handed",
                "dialogue": {"hail": "The Last Beacon, {name}: it warned the keep, once. Now the [ravens] nest in it, and [Grimquill] above them all.",
                             "unknown": "Ask the Marchwarden."}},
        "mob": {"id": "bm_cairn_raven", "name": "a cairn raven", "model": "bone_vulture", "drop": ("bm_raven_quill", "Cairn Raven Quill", 7, "carrion_feather"),
                "extra": {"verb": ["peck", "pecks"], "scale": 0.6, "color": "#151515"}},
        "named": {"id": "bm_grimquill", "name": "Grimquill", "model": "bone_vulture", "trophy": ("bm_grimquills_beak", "Grimquill's Beak", "carrion_feather"),
                  "extra": {"verb": ["peck", "pecks"], "scale": 1.0, "color": "#0a0a0a"}},
        "reward": ("bm_beacon_keepers_boots", reward_for(19, "feet", "Beacon-Keeper's Boots", "wolfhide_boots", ("sta", "agi"), wear="leather_boots")),
        "keywords": ("ravens", "grimquill"),
        "text": _named_lines(_t("Raven Quills", "cairn raven quills", "Grimquill's beak",
                   "Four of their quills and I'll pay, every time. I'll write the beacon's last watch with them.",
                   "Grimquill, the old king of them, sits on the beacon's top. Bring me his beak, and I'll light it again."),
                   "Quills. Good for writing.", "Four fewer on the beacon.", "His beak. The beacon's mine.", "I'll light it tonight.",
                   "A keeper's boots. For the climb to the top.")},
        hut=("a Marchwatch guard", "Marchwatch", (0, 150, 1)))


ZONES = {"thornwood": thornwood, "the_long_grass": long_grass, "the_bleach": bleach,
         "the_burn": the_burn, "mirror_flats": mirror_flats, "ivory_field": ivory_field, "reedmere": reedmere,
         "silted_reach": silted_reach, "blackglass": blackglass, "smokewood": smokewood, "stonesail": stonesail,
         "hollow_air": hollow_air, "fogfall": fogfall, "the_unlit": the_unlit, "lastwalk": lastwalk, "high_terrace": high_terrace,
         "greenmoor": greenmoor, "harrowfield": harrowfield, "hollowmere": hollowmere, "dewstep": dewstep, "sunward_steps": sunward_steps,
         "weeping_throat": weeping_throat, "cinderpass": cinderpass, "windbreak": windbreak, "the_wallow": the_wallow, "duskwood": duskwood,
         "the_rotfen": the_rotfen, "broken_march": broken_march}


def check_spot(zid, z, edges, p, what):
    """Problems with putting something at p: in the mountains, in water, on a road."""
    hx, hz = outline.halves(z)
    probs = []
    if outline.edge_depth(edges, (hx, hz), p[0], p[1]) > -30:
        probs.append("near the mountains")
    for r in z.get("rivers", []):
        if not r.get("dry") and min(math.dist(p, q) for q in bw_poly(r["points"])) < r.get("width", 10) / 2 + 12:
            probs.append("in a river")
    for f in z.get("fields", []):
        if math.dist(p, f["pos"]) < max(f["size"]) * 0.5 + 12:
            probs.append("on a field")
    for lk in z.get("lakes", []):
        on_island = any(math.dist(p, i[:2]) < i[2] - 4 for i in lk.get("islands", []))
        if outline._poly_inside(p, lk["points"]) and float(lk.get("depth", 1)) > 0.5 and not on_island:
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
        # the Abbot and a monk stood inside the hall, whose only door is shut: out into the courtyard before its steps
        {"from": (-1.2, -240.7), "radius": 2, "to": (-1.2, -224.0), "what": "Abbot Varun, out of his shut hall", "spawns_only": True, "clear": False},
        {"from": (-1.2, -249.7), "radius": 2, "to": (-14.0, -219.0), "what": "the monk shut in behind him", "spawns_only": True, "clear": False},
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
            lms = [] if mv.get("spawns_only") else [l for l in z["landmarks"] if near(l) and l["type"] not in ("signpost", "rockslide", "bridge")]
            sps = [s for s in z["spawns"] if near(s)]
            if not lms and not sps:
                continue
            print("%-16s moving %s: %d landmarks, %d spawns, %.0f m" % (zid, mv["what"], len(lms), len(sps), math.hypot(dx, dy)))
            for e in lms + sps:
                e["pos"] = [round(e["pos"][0] + dx, 1), round(e["pos"][1] + dy, 1)]
                if "face" in e:
                    e["face"] = [round(e["face"][0] + dx, 1), round(e["face"][1] + dy, 1)]
            if mv.get("clear", True):
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
