"""Writes The Blackwater: the evil races' homelands (2026-09-29).

    python3 tools/zones/blackwater.py [--placeholder]

Murkhold (trolls and ogres' city in a black bog), The Wallow (their beginner
swamp, 1-10), Duskwood (the dark elves' beginner forest, 1-10), Duskhold (the
dark elves' city in a cavern under Duskwood, reached by a cave door), and The
Rotfen (the shared 10-18 fen). Also Rainhold's west gate (onto Stormcut Gorge
since the Blackwater moved west; tools/zones/west_march.py writes the gorge
and the Broken March between).

Writes the five zone files, patches rainhold.json, and merges the area's
npcs, mobs and quests into data/npcs.json, data/mobs.json and
data/quests.json (all three survive a load-and-dump), its items into
data/items/blackwater.json, and its two blessing spells into data/spells.json
(spliced as text: that file doesn't survive a dump). Rerun it after changing
anything here: it replaces what it wrote before.

Borders come from docs/world-layout.json's links with the arithmetic in
docs/zone-implementation.md; never type them by hand. --placeholder swaps art
that isn't built yet for existing props.
"""
import json, math, os, sys, random

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLACEHOLDER = "--placeholder" in sys.argv
MODELS = json.load(open(f"{ROOT}/data/models.json"))
LAYOUT = json.load(open(f"{ROOT}/docs/world-layout.json"))
ZONES = {z["id"]: z for z in LAYOUT["zones"]}
AREA = ["murkhold", "the_wallow", "duskwood", "the_rotfen", "duskhold"]

# art that may not be built yet -> an existing stand-in
STAND_IN = {
    "murk_longhouse": "stilt_hall", "murk_hut": "troll_hut", "bone_palisade": "palisade",
    "bone_gate": "temple_arch_ruin", "bog_lantern": "torch_post", "murk_cauldron": "hag_cauldron",
    "idol_makarosh": "bog_totem", "idol_mahishra": "troll_totem",
    "cavern_dome": None, "dusk_spire": "obsidian_spire", "dusk_house": "eclipse_house",
    "dusk_bridge": "bridge_wood", "stalagmite_cluster": "boulder_c", "glow_crystal": "salt_crystals",
    "candle_stand": "candle_lit", "dusk_gate": "temple_arch_ruin",
    "dusk_tree": "black_tree", "dusk_tree_b": "black_tree_b",
    "idol_tantuvi": None, "idol_dipanti": None,
}


def art(pid):
    """A prop id to place, or None to leave it out (not built, no stand-in)."""
    if pid in MODELS["props"] and not PLACEHOLDER:
        return pid
    if pid in MODELS["props"] and pid not in STAND_IN:
        return pid
    return STAND_IN.get(pid, pid if pid in MODELS["props"] else None)


def prop(pid, pos, face=None, collide="box", scale=None, yaw=None):
    pid = art(pid)
    if pid is None:
        return None
    lm = {"type": "prop", "pos": [round(pos[0], 1), round(pos[1], 1)], "id": pid, "collide": collide}
    if face is not None:
        lm["face"] = [round(face[0], 1), round(face[1], 1)]
    if yaw is not None:
        lm["yaw"] = yaw
    if scale is not None:
        lm["scale"] = scale
    return lm


def at(bearing, r, c=(0, 0)):
    """bearing 0 = east, 90 = north (engine -z)."""
    a = math.radians(bearing)
    return [c[0] + r * math.cos(a), c[1] - r * math.sin(a)]


# ---------------------------------------------------------------- borders

CITY_DEPTH = {"rainhold": {"south": 54}}  # Rainhold's south arrival, if it ever gets one again: 66 m in is the lagoon
CITY_INSET = 15


def half(zid):
    return ZONES[zid]["size"] / 2


def edge_pass(zid, edge, k=0):
    h = half(zid)
    return {"north": [k, -h, 9], "south": [k, h, 9], "east": [h, k, 9], "west": [-h, k, 9]}[edge]


def arrive_in(zid, edge, k=0):
    """Where you appear coming into zid through its `edge`, and where you face."""
    h = half(zid)
    city = ZONES[zid]["kind"] == "city"
    depth = CITY_DEPTH.get(zid, {}).get(edge, 66) if city else 25
    inward = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}[edge]
    base = {"north": (k, -h), "south": (k, h), "east": (h, k), "west": (-h, k)}[edge]
    p = [base[0] + inward[0] * depth, base[1] + inward[1] * depth]
    f = [p[0] + inward[0] * 40, p[1] + inward[1] * 40]
    return p, f


def zone_line(zid, edge, to, to_edge, k=0):
    h = half(zid)
    inset = CITY_INSET if ZONES[zid]["kind"] == "city" else 11
    pos = {"north": [k, -(h - inset)], "south": [k, h - inset], "east": [h - inset, k], "west": [-(h - inset), k]}[edge]
    size = [18, 8] if edge in ("north", "south") else [8, 18]
    arr, face = arrive_in(to, to_edge, k)
    return {"pos": pos, "size": size, "to": to, "arrive": arr, "arrive_face": face}


def borders(zid):
    passes, lines = [], []
    for l in LAYOUT["links"]:
        if l["a"] == zid:
            passes.append(edge_pass(zid, l["a_edge"])); lines.append(zone_line(zid, l["a_edge"], l["b"], l["b_edge"]))
        elif l["b"] == zid:
            passes.append(edge_pass(zid, l["b_edge"])); lines.append(zone_line(zid, l["b_edge"], l["a"], l["a_edge"]))
    return passes, lines


# ---------------------------------------------------------------- monsters

# typical non-named monster stats by level, read off the shipped mobs (1-19)
CURVE = [(1, 6, 5, 1, 2, 1), (2, 9, 7, 1, 4, 3), (4, 20, 10, 2, 6, 8), (6, 26, 11, 2, 7, 10),
         (7.5, 36, 12, 3, 9, 12), (10, 45, 14, 5, 11, 15), (12, 48, 14, 5, 12, 17), (15, 88, 17, 8, 17, 23),
         (17, 105, 19, 10, 20, 28), (19, 115, 20, 11, 22, 30)]


def curve(lv):
    for i in range(len(CURVE) - 1):
        a, b = CURVE[i], CURVE[i + 1]
        if a[0] <= lv <= b[0]:
            t = (lv - a[0]) / (b[0] - a[0])
            return [round(a[j] + (b[j] - a[j]) * t) for j in range(1, 6)]
    return list(CURVE[-1][1:])


MOBS = {}


def mob(mid, name, lv, model, faction="wildlife", verb=("bite", "bites"), aggressive=True, social=False, loot=(),
        coin=(0, 0), named=False, scale=1.0, speed=6.4, delay=2.6, extra=None, flees=False, color="#707060"):
    mid_lv = (lv[0] + lv[1]) / 2
    hp_base, hp_per, dmin, dmax, ac = curve(mid_lv)
    d = {"name": name, "level": list(lv), "hp_base": hp_base, "hp_per_level": hp_per, "dmg_min": dmin, "dmg_max": dmax,
         "attack_delay": delay, "ac": ac, "speed": speed, "aggressive": aggressive, "aggro_radius": 12 if aggressive else 0,
         "social": social, "flees": flees, "faction": faction, "verb": list(verb), "shape": "humanoid", "color": color,
         "scale": scale, "coin": list(coin), "loot": [{"item": i, "chance": c} for i, c in loot], "model": model}
    if named:
        d["named"] = True
        d["hp_base"] = int((60 if mid_lv <= 10 else 75) * mid_lv)
        d["hp_per_level"] = 0
        d["dmg_min"] = round(dmin * 1.4)
        d["dmg_max"] = round(dmax * 1.45)
        d["ac"] = round(ac * 1.3)
    d.update(extra or {})
    MOBS[mid] = d
    return mid


# ---------------------------------------------------------------- items

ITEMS = {}


def item(iid, name, **kw):
    ITEMS[iid] = dict({"name": name}, **kw)
    return iid


def drop(iid, name, value=6):
    return item(iid, name, value=value, stack=20)


# the Wallow
drop("bog_rat_tail", "Bog Rat Tail", 3)
drop("wallow_toad_skin", "Wallow Toad Skin", 6)
drop("swamp_leech_teeth", "Swamp Leech Teeth", 6)
drop("pondkin_bead", "Pondkin Bead", 8)
drop("mud_turtle_shell", "Mud Turtle Shell", 12)
drop("bog_wisp_light", "Bog Wisp Light", 10)
item("gulpmaws_tongue", "Gulpmaw's Tongue", value=40, lore=True)
item("wetbellys_crown", "Wetbelly's Reed Crown", value=40, lore=True)
# Duskwood
drop("gloom_rat_tail", "Gloom Rat Tail", 3)
drop("duskwood_silk", "Duskwood Spider Silk", 6)
drop("gloomfang_pelt", "Gloomfang Pelt", 10)
drop("hearth_scout_badge", "Hearth Scout's Badge", 12)
drop("shade_dust", "Shade Dust", 10)
item("vyss_fang", "The Silkmother's Fang", value=40, lore=True)
item("aldrens_orders", "Scout-Captain Aldren's Orders", value=40, lore=True)
# the Rotfen
drop("plague_rat_tail", "Plague Rat Tail", 6)
drop("rotfen_lurker_hide", "Rotfen Lurker Hide", 14)
drop("fen_eel_skin", "Fen Eel Skin", 12)
drop("hag_charm", "Hag's Bone Charm", 16)
item("chief_sisskas_totem", "Chief Sisska's Totem", value=60, lore=True)
item("gristleworts_heart", "Gristlewort's Withered Heart", value=60, lore=True)
item("mudjaws_tooth", "Old Mudjaw's Tooth", value=60, lore=True)
# bag quest pieces
item("toadskin_panel", "Tanned Toadskin Panel", value=0, lore=True, no_drop=True)
item("bogtanner_pack_body", "Stitched Bogtanner Pack", value=0, lore=True, no_drop=True)
item("gorras_bogtanner_pack", "Gorra's Bogtanner Pack", bag=10, value=60, lore=True, no_drop=True, weight_reduction=0.5)
item("spun_duskwood_silk", "Spun Duskwood Silk", value=0, lore=True, no_drop=True)
item("gloomfang_satchel_body", "Gloomfang Satchel", value=0, lore=True, no_drop=True)
item("dresnas_silkweave_satchel", "Dresna's Silkweave Satchel", bag=10, value=60, lore=True, no_drop=True, weight_reduction=0.5)
# rewards
ALL_MELEE = ["warrior", "rogue", "shaman", "ranger"]
item("toadhide_sandals", "Toadhide Sandals", slot="feet", ac=2, sta=1, agi=1, value=90, rec_level=3, no_drop=True, lore=True, wear="sandals")
item("pondkin_reed_spear", "Pondkin Reed Spear", slot="primary", dmg=7, delay=2.8, verb=["pierce", "pierces"], model="dagger",
     skill="piercing", str=1, value=500, rec_level=7, no_drop=True, lore=True)
item("gulpmaw_hide_bracer", "Gulpmaw-Hide Bracer", slot="arms", ac=5, sta=2, hp=10, value=700, rec_level=8, no_drop=True, lore=True, wear="leather_sleeves")
item("wetbellys_ring", "Wetbelly's Signet", slot="ring", ac=1, sta=2, wis=1, value=500, rec_level=9, no_drop=True, lore=True)
item("gloomsilk_gloves", "Gloomsilk Gloves", slot="hands", ac=2, agi=1, int=1, value=90, rec_level=3, no_drop=True, lore=True, wear="leather_gloves")
item("gloomfang_mantle", "Gloomfang Mantle", slot="arms", ac=5, agi=2, sta=1, value=700, rec_level=8, no_drop=True, lore=True, wear="leather_sleeves")
item("silkmother_stiletto", "Silkmother's Stiletto", slot="primary", dmg=6, delay=2.1, verb=["pierce", "pierces"], model="dagger",
     skill="piercing", agi=2, value=900, rec_level=9, no_drop=True, lore=True,
     classes=["warrior", "wizard", "rogue", "magician", "necromancer", "shaman", "ranger", "cleric"])
item("scout_captains_ring", "Scout-Captain's Ring", slot="ring", ac=1, int=2, wis=2, mana=10, value=500, rec_level=9, no_drop=True, lore=True)
item("fenwalker_boots", "Fenwalker Boots", slot="feet", ac=6, sta=2, agi=2, value=1500, rec_level=13, no_drop=True, lore=True, wear="leather_boots")
item("sisskas_scaled_belt", "Sisska's Scaled Belt", slot="waist", ac=6, str=3, sta=2, hp=20, value=2200, rec_level=16, no_drop=True, lore=True)
item("gristlewort_amulet", "Gristlewort's Amulet", slot="neck", ac=2, int=3, wis=3, mana=30, value=2200, rec_level=17, no_drop=True, lore=True)
item("mudjaw_tooth_club", "Mudjaw-Tooth Club", slot="primary", dmg=14, delay=3.0, verb=["crush", "crushes"], model="axe_1handed",
     skill="1h_blunt", str=3, sta=2, value=3000, rec_level=17, no_drop=True, lore=True)

# ---------------------------------------------------------------- npcs

NPCS = {}
GUARD = {"radius": 22, "leash": 34, "speed": 6.4, "assist_standing": 0, "hunt_radius": 18, "hunt_aggressive_only": True}
GUARD_COMBAT = {"hp": 3200, "hp_regen": 50, "ac": 95, "dmg": [18, 34], "delay": 2.4, "verb": ["slash", "slashes"]}
SUPPLIES = ["draught_of_homecoming", "bone_chips", "bag_of_flour", "jar_of_spices", "vial_of_water", "tanning_salts", "spool_of_thread",
            "bundle_of_herbs", "small_brick_of_ore", "large_brick_of_ore", "water_flask", "bundle_of_shafts", "smithy_hammer",
            "sewing_kit", "mortar_and_pestle", "hearthside_cookbook", "tailors_pattern_book", "alchemists_notes", "smiths_handbook",
            "fishing_pole", "fishing_bait", "loaf_of_bread"]
OUTFIT = ["leather_cap", "leather_tunic", "leather_leggings", "cloth_cap", "patchwork_pants", "leather_gloves", "leather_boots",
          "leather_sleeves", "leather_belt", "leather_sling", "sling_stone", "small_sack", "leather_backpack",
          "hardened_leather_jerkin", "hardened_leather_leggings", "hardened_leather_gloves", "hardened_leather_boots"]
ARMS = ["iron_dagger", "iron_short_sword", "iron_hand_axe", "oak_staff", "hunting_shortbow", "crude_arrow", "iron_coif",
        "iron_greaves", "studded_tunic", "round_shield", "iron_kite_shield", "iron_gauntlets", "iron_boots", "tempered_dirk",
        "tempered_longsword", "tempered_war_axe", "tempered_helm", "tempered_breastplate", "tempered_vambraces",
        "tempered_gauntlets", "tempered_greaves", "tempered_boots", "tempered_kite_shield"]


def npc(nid, name, faction, race, model, dialogue, title=None, weapon="", gender=None, level=30, **kw):
    d = {"name": name, "level": level, "model": model, "weapon": weapon, "faction": faction, "race": race, "dialogue": dialogue}
    if title:
        d["title"] = title
    if gender:
        d["gender"] = gender
    d.update(kw)
    NPCS[nid] = d
    return nid


def guard(nid, name, faction, race, city, gender=None):
    return npc(nid, name, faction, race, "knight" if race == "dark_elf" else "barbarian", {
        "hail": f"Keep walking, {{name}}. {city} doesn't care for strangers and cares less for trouble.",
        "unknown": "Ask someone who cares."}, weapon="sword_1handed" if race == "dark_elf" else "axe_2handed", gender=gender, level=35,
        guard=dict(GUARD, shouts=["Hold, {name}!", f"For {city}!"], hunt_shouts=[f"Not in {city}!"],
                   shouts_player=["Halt, {name}!", f"{city} will answer that, {{name}}!"]), combat=dict(GUARD_COMBAT))


# ---------------------------------------------------------------- quests

QUESTS = {}


def quest(qid, name, giver, wants, xp, coin, reward_item, accept, ready, complete, first_complete, faction, keyword=None,
          repeatable=False, nxt=None):
    q = {"name": name, "giver": giver, "wants": wants, "reward": {"xp": xp, "coin": coin}, "accept_text": accept,
         "ready_text": ready, "complete_text": complete, "faction": faction}
    if reward_item:
        q["first_reward_item"] = reward_item
        q["first_complete_text"] = first_complete
    if keyword:
        q["start_keyword"] = keyword
    if repeatable:
        q["repeatable"] = True
    if nxt:
        q["next"] = nxt
    QUESTS[qid] = q
    return qid


# ================================================================ MURKHOLD

def murkhold():
    passes, lines = borders("murkhold")
    L = []
    # the bog: hand-deep black water over the whole city, mud islands where it stands
    lake = [at(b, 102 + 6 * math.sin(b * 0.13)) for b in range(0, 360, 20)]
    islands = [[0, 0, 26], [-52, -6, 16], [34, -36, 14], [34, 34, 14], [-34, 42, 13], [-34, -46, 12], [70, 0, 14]]
    L.append(prop("bone_gate", [96, 0], face=[0, 0], collide="mesh"))
    for side in (-1, 1):
        for k in range(4):
            L.append(prop("bone_palisade", [99 - k * 2, side * (12 + k * 8)], face=[0, side * (12 + k * 8)], collide="box"))
    # the plaza of the two gods
    L.append(prop("idol_makarosh", [-10, -8], face=[0, 4], collide="box", scale=1.6))
    L.append(prop("idol_mahishra", [10, -8], face=[0, 4], collide="box", scale=1.6))
    L.append(prop("murk_cauldron", [0, 14], collide="box"))
    for b in range(0, 360, 45):
        L.append(prop("bog_lantern", at(b + 22, 22), collide="none"))
    L.append(prop("murk_longhouse", [-52, -6], face=[0, -6], collide="mesh"))
    for spot in [[34, -36], [34, 34], [-34, 42], [-34, -46], [70, -14], [70, 14], [-70, 30], [-70, -34], [0, -60], [0, 62]]:
        L.append(prop("murk_hut", spot, face=[0, 0], collide="mesh"))
    for spot in [[46, -20], [-20, 60], [-60, 60], [60, 56], [-12, -70]]:
        L.append(prop("troll_totem", spot, face=[0, 0], collide="box"))
    for spot in [[-82, 70], [82, -70], [-88, -60], [80, 70], [-40, -84], [40, 84], [-90, 10], [20, -88]]:
        L.append(prop("mangrove_tree", spot, collide="trunk", scale=1.3))
    # crafting, beside the provisioner
    for pid, spot in [("forge", [42, 24]), ("oven", [48, 32]), ("loom", [40, 42]), ("brew_barrel", [28, 44])]:
        L.append(prop(pid, spot, face=[34, 34], collide="box"))
    L.append({"type": "signpost", "pos": [84, 6], "face": [100, 6], "labels": ["The Wallow"]})
    L = [l for l in L if l]
    npcs = []

    def put(nid, pos, face=(0, 0)):
        npcs.append({"id": nid, "pos": [round(pos[0], 1), round(pos[1], 1)], "face": list(face)})

    F, C = "murkhold", "Murkhold"
    put(npc("murk_priest_makarosh", "Deep-Priestess Gharra", F, "troll", "shaman", {
        "hail": "Be still, {name}. The black water is listening. I keep the Deep-Jawed's idol, and I can [bind] your soul to Murkhold, so the bog takes you back when the world spits you out. Followers of Makarosh may ask for his [blessing].",
        "bind": "Down on your knees in the mud, {name}. ...There. Makarosh has your scent now: you'll wake in Murkhold.",
        "unknown": "The water doesn't answer that. Neither do I."},
        title="Keeper of the Deep-Jawed", weapon="staff", gender="female", level=40, binds=True,
        blesses={"deity": "mire", "spell": "makarosh_blessing", "keyword": "blessing", "every": 3600,
                 "refuse": "His blessing is for his own, {name}. The water doesn't feed strangers.",
                 "wait": "You had his blessing within the hour. Patience, {name}. He has more of it than you.",
                 "give": "Hold still... The deep takes a breath, and gives it to you."}), [-6, -2], [0, 6])
    put(npc("murk_priest_mahishra", "Horn-Speaker Brugg", F, "ogre", "shaman", {
        "hail": "HRAH. Welcome to the churned ground, {name}. I speak for the Mud-Horned. Followers of Mahishra can ask me for his [blessing]; anyone can ask me to [bind] them to Murkhold.",
        "bind": "Stand firm. Firmer. ...Good. Mahishra's mud remembers your feet now.",
        "unknown": "Brugg does not know. Brugg does not mind."},
        title="Voice of the Mud-Horned", weapon="staff", level=40, binds=True,
        blesses={"deity": "horn", "spell": "mahishra_blessing", "keyword": "blessing", "every": 3600,
                 "refuse": "The Mud-Horned lends his strength to his own herd, {name}. Not to you.",
                 "wait": "Once an hour. The herd doesn't stampede twice before breakfast.",
                 "give": "Lower your head. ...Feel that? That's the herd behind you."}), [6, -2], [0, 6])
    put(npc("murk_gm_warrior", "Warlord Kragga", F, "ogre", "barbarian", {
        "hail": "You want to hit things harder, {name}? Good. Hit them first, hit them twice, and don't stop until they're mud. I train Murkhold's warriors.",
        "unknown": "Ask the priests. I hit things."}, title="Warrior Guildmaster", weapon="axe_2handed", level=40,
        guildmaster={"class": "warrior", "refuse": "Not a fighter, {name}? Then go find someone who teaches what you are."}), [-40, -24], [-52, -6])
    put(npc("murk_gm_shaman", "Bog-Mother Yeshka", F, "troll", "shaman", {
        "hail": "The spirits of the bog are hungry and patient, {name}, like everything that lives here. If you hear them, I can teach you to answer.",
        "unknown": "The spirits don't say."}, title="Shaman Guildmaster", weapon="staff", gender="female", level=40,
        guildmaster={"class": "shaman", "refuse": "The spirits don't talk to you, {name}. I can't change that."}), [-40, 14], [-52, -6])
    put(npc("murk_banker", "Hoardkeeper Mulg", F, "ogre", "barbarian", {
        "hail": "Mulg keeps your things. Mulg does not eat your things. Mostly. Press G.",
        "unknown": "Mulg only keeps things."}, title="Murkhold Hoard", banker=True, level=20), [-30, -6], [0, 0])
    put(npc("murk_registrar", "Registrar Oolg", F, "ogre", "mage", {
        "hail": "Oolg writes the names of the warbands, {name}. Want a [charter]?",
        "charter": "Ten platinum, and level 10 at least. Stand here and say /guildcreate <name>. Oolg will write it big.",
        "guild": "A warband with a name, and the others hear each other with /gu. Ask Oolg for a [charter].",
        "unknown": "Oolg only writes names."}, title="Guild Registrar", guild_registrar=True, level=30), [-30, 6], [0, 0])
    put(npc("murk_provisioner", "Provisioner Sleesh", F, "troll", "rogue", {
        "hail": "Flour, salt, thread, bait... all the things that aren't food yet, {name}. Press G.",
        "unknown": "Buying or not?"}, title="Provisioner", level=25, merchant={"sells": SUPPLIES, "buy_rate": 0.5}), [36, 26], [42, 34])
    put(npc("murk_outfitter", "Hidemonger Gorra", F, "ogre", "barbarian", {
        "hail": "Hides, straps, sacks. Everything a new bog-runner needs, {name}. And if you've got legs and patience, I could use help with a proper [pack].",
        "pack": "A Bogtanner's pack, like the old hunters carried: toad skin, sewn tight, a shell clasp. Bring me four wallow toad skins from the pools east of the gate and I'll start on it.",
        "unknown": "Ask Sleesh. Sleesh knows everything and sells half of it."},
        title="Outfitter", level=25, merchant={"sells": OUTFIT, "buy_rate": 0.5}), [44, -30], [34, -36])
    put(npc("murk_smith", "Smith Thuk", F, "troll", "barbarian", {
        "hail": "Iron and more iron, {name}. Some of it even has an edge. Press G.",
        "unknown": "Thuk makes weapons. Thuk doesn't make conversation."},
        title="Blacksmith", weapon="axe_1handed", level=25, merchant={"sells": ARMS, "buy_rate": 0.5}), [26, -44], [34, -36])
    for i, spot in enumerate([[88, -8], [88, 8], [20, -18], [-20, 20]]):
        nid = guard("murkhold_guard_ogre" if i % 2 else "murkhold_guard", "a Murkhold bruiser", F, "ogre" if i % 2 else "troll", C)
        put(nid, spot, (0, spot[1]) if spot[0] > 80 else (0, 0))
    zone = {"name": "Murkhold", "music": "murkhold", "seed": 7311, "size": 224, "bindstone": True, "bind_point": [0, 4],
            "height_amplitude": 1.2, "flat_radius": 80, "clear_radius": 96, "trees": 0, "rocks": 6,
            "grass_colors": ["#3e4a2c", "#4a5632"], "fog_density": 0.02, "fog_color": "#4c5840", "sun_energy": 0.55,
            "rain": {"amount": 900}, "passes": passes, "zone_lines": lines,
            "water": {"shallow": "#1e2416", "deep": "#0a0d07", "sky": "#2a3024", "murk": 0.2, "foam": 0.04, "shine": 0.12},
            "lakes": [{"points": lake, "depth": 0.25, "shelf": 20, "bank": 8, "islands": islands}],
            "roads": [{"points": [[112, 0], [80, 0], [30, 0]], "width": 3.4}],
            "clutter": {"reeds_tall": {"density": 0.02, "patch": 0.7, "sway": 0.2, "range": 50, "scale": [0.8, 1.3]},
                        "grass_b": {"density": 0.12, "patch": 0.5, "sway": 0.14, "range": 45, "tint": "ground", "scale": [0.8, 1.2]}},
            "landmarks": L, "npcs": npcs, "spawns": []}
    return zone


# ================================================================ THE WALLOW

def the_wallow():
    passes, lines = borders("the_wallow")
    L = []
    rng = random.Random(9021)
    pools = []
    for c, r in [((-40, -60), 34), ((60, 40), 40), ((-80, 90), 30), ((110, -90), 30), ((0, 120), 26)]:
        pools.append({"points": [[c[0] + r * math.cos(a) * (1 + 0.15 * math.sin(a * 3)), c[1] + r * math.sin(a) * (1 + 0.12 * math.cos(a * 2))]
                                 for a in [i * math.tau / 14 for i in range(14)]], "depth": 0.7, "shelf": 12, "bank": 6})
    # the Murkhold hunters' camp, just inside the west gate
    L.append({"type": "camp", "pos": [-148, -30]})
    L.append({"type": "signpost", "pos": [-170, 8], "face": [-190, 8], "labels": ["Murkhold"]})
    L.append({"type": "signpost", "pos": [172, 8], "face": [190, 8], "labels": ["The Broken March"]})
    L.append({"type": "signpost", "pos": [8, 172], "face": [8, 190], "labels": ["The Rotfen"]})
    # the pondkin raiders' camp, north-east
    for spot in [[120, -120], [138, -104], [104, -142], [150, -132]]:
        L.append(prop("pondkin_hut", spot, face=[126, -122], collide="mesh"))
    L.append(prop("pondkin_totem", [126, -122], collide="box"))
    for k in range(10):
        L.append(prop("bog_totem" if k % 3 == 0 else "reed_hut" if k % 3 == 1 else "silt_mound",
                      [rng.uniform(-160, 160), rng.uniform(-160, 160)], collide="box"))
    L = [l for l in L if l]
    npcs = [
        {"id": npc("wallow_hunter_snikk", "Hunter Snikk", "murkhold", "troll", "ranger_class", {
            "hail": "Quiet, {name}. You'll scare off dinner. The Wallow feeds Murkhold: rats, toads, leeches, and the frog-things to the north-east who think it's theirs. Help me keep the [pondkin] off our pools.",
            "pondkin": "Frog-folk. They raid our traps and call it hunting. Bring me four of their beads and I'll pay, every time. And their chief, [Wetbelly], wears a crown of reeds I'd like on my wall.",
            "wetbelly": "Fat old thing, sits in the middle of their huts to the north-east and croaks orders. Bring me his crown.",
            "gulpmaw": "The biggest toad in the Wallow. Swallowed my brother's dog. Bring me its tongue and I'll have something made for you.",
            "unknown": "Ask Gorra in the city. Or the priests. Not me."},
            title="Wallow Hunter", weapon="bow", level=20), "pos": [-150, -40], "face": [-148, -30]},
        {"id": "murkhold_guard", "name": "Camp Bruiser Hask", "pos": [-160, -22], "face": [-150, -30]},
    ]
    Q = quest("wallow_pondkin_beads", "Frogs in the Pools", "wallow_hunter_snikk", {"pondkin_bead": 4}, 120, 40, "toadhide_sandals",
              "You have taken on a task: Frogs in the Pools. Bring Hunter Snikk four pondkin beads.",
              "Beads! How many frogs, {name}?", "Four frogs fewer. Good.", "Take these. Toad hide, so the bog doesn't eat your feet.",
              {"murkhold": 10}, keyword="pondkin", repeatable=True)
    quest("wallow_wetbelly", "Wetbelly's Crown", "wallow_hunter_snikk", {"wetbellys_crown": 1}, 500, 150, "wetbellys_ring",
          "You have taken on a task: Wetbelly's Crown. Bring Hunter Snikk the pondkin chief's reed crown.",
          "Is that... the crown? Give it here.", "Ha! It stinks of frog. It's perfect.", "His signet was sewn into it. Yours now.",
          {"murkhold": 25}, keyword="wetbelly")
    quest("wallow_gulpmaw", "The Toad That Ate a Dog", "wallow_hunter_snikk", {"gulpmaws_tongue": 1}, 450, 120, "gulpmaw_hide_bracer",
          "You have taken on a task: The Toad That Ate a Dog. Bring Hunter Snikk Gulpmaw's tongue.",
          "The tongue? You killed Gulpmaw?", "For you, Grunt. Good dog.", "Gorra made this from its hide while you were gone. Don't ask how.",
          {"murkhold": 20}, keyword="gulpmaw")
    # the bag quest: Gorra -> Snikk -> Gorra
    quest("bogtanner_skins", "The Bogtanner's Pack (1 of 3)", "murk_outfitter", {"wallow_toad_skin": 4}, 40, 10, "toadskin_panel",
          "You have taken on a task: The Bogtanner's Pack. Bring Hidemonger Gorra four wallow toad skins.",
          "Skins? Let's see them.", "Scrape, stretch, soak in the black water... there. A panel.",
          "Hunter Snikk out in the Wallow sews the old way. Take him this and ask him about [Gorra]; he'll want leech teeth for the stitching.",
          {"murkhold": 5}, keyword="pack", nxt="bogtanner_stitch")
    quest("bogtanner_stitch", "The Bogtanner's Pack (2 of 3)", "wallow_hunter_snikk", {"toadskin_panel": 1, "swamp_leech_teeth": 3}, 90, 20,
          "bogtanner_pack_body", "You have taken on a task: The Bogtanner's Pack. Bring Hunter Snikk the toadskin panel and three swamp leech teeth.",
          "Gorra's panel, and teeth. Hand them over.", "Leech teeth make the best needles. Stitch, stitch... done.",
          "Back to Gorra for the clasp. She'll want a mud turtle's shell for it.", {"murkhold": 5}, nxt="bogtanner_clasp")
    quest("bogtanner_clasp", "The Bogtanner's Pack (3 of 3)", "murk_outfitter", {"bogtanner_pack_body": 1, "mud_turtle_shell": 1}, 150, 30,
          "gorras_bogtanner_pack", "You have taken on a task: The Bogtanner's Pack. Bring Hidemonger Gorra the stitched pack and a mud turtle shell.",
          "Shell and pack. Good.", "Shell clasp, nothing gets in, nothing gets out unless you want it. A real bog-runner's pack.",
          "It's yours, {name}. Don't fill it with frogs.", {"murkhold": 10})
    mob("bog_rat", "a bog rat", (1, 2), "rat", loot=[("bog_rat_tail", 0.5), ("raw_meat", 0.2)], speed=6.0, aggressive=False, delay=2.6)
    mob("wallow_toad", "a wallow toad", (2, 4), "mire_toad", verb=("slam", "slams"), loot=[("wallow_toad_skin", 0.55), ("frog_legs", 0.25)],
        aggressive=False, scale=0.7, delay=2.8)
    mob("swamp_leech", "a swamp leech", (3, 5), "bog_leech", loot=[("swamp_leech_teeth", 0.5)], scale=0.75)
    mob("pondkin_forager", "a pondkin forager", (4, 6), "pondkin", faction="wallow_pondkin", verb=("stab", "stabs"), social=True,
        loot=[("pondkin_bead", 0.5)], coin=(3, 20), flees=True)
    mob("pondkin_mudslinger", "a pondkin mudslinger", (5, 7), "pondkin_mudcaller", faction="wallow_pondkin", verb=("slap", "slaps"),
        social=True, loot=[("pondkin_bead", 0.5)], coin=(5, 25))
    mob("mud_turtle", "a mud turtle", (6, 8), "snapping_turtle", loot=[("mud_turtle_shell", 0.45)], aggressive=False, delay=3.2, scale=0.8)
    mob("bog_wisp", "a bog wisp", (5, 8), "lantern_wisp", loot=[("bog_wisp_light", 0.5)], extra={"xp_mult": 1.1})
    mob("chief_wetbelly", "Chief Wetbelly", (9, 9), "pondkin_bloatking", faction="wallow_pondkin", verb=("slam", "slams"), social=True,
        named=True, loot=[("wetbellys_crown", 1.0)], coin=(40, 140))
    mob("gulpmaw", "Gulpmaw", (8, 8), "mire_toad", verb=("swallow", "swallows"), named=True, loot=[("gulpmaws_tongue", 1.0)], scale=1.7,
        aggressive=False)
    spawns = []

    def spawn(pool, spots, respawn=60, wander=12, when=None):
        for s in spots:
            e = {"pos": s, "pool": pool, "respawn": respawn, "wander": wander}
            if when:
                e["when"] = when
            spawns.append(e)
    # the beginners' own: enough rats and toads that a few new trolls and ogres don't queue for them (2026-09-29: was 6 of each)
    spawn({"bog_rat": 1}, [[-130, -80], [-110, -10], [-120, 40], [-90, -40], [-140, 70], [-70, 10], [-100, -120], [-150, 20], [-60, -60],
                           [-100, 110], [-30, 40]], 30)
    spawn({"wallow_toad": 1}, [[-40, -20], [-10, -60], [-60, -100], [40, 10], [80, 70], [30, 80], [0, -110], [60, -40], [100, 20],
                               [-20, 120], [60, 130]], 40)
    spawn({"swamp_leech": 1}, [[-80, 60], [-100, 110], [-50, 120], [20, 130], [90, 40]], 50)
    spawn({"pondkin_forager": 3, "pondkin_mudslinger": 1}, [[100, -110], [140, -90], [110, -150], [160, -140], [80, -130], [130, -70]], 70, 8)
    spawn({"mud_turtle": 1}, [[0, 150], [60, 140], [-40, 160], [120, 100], [150, 40]], 70)
    spawn({"bog_wisp": 1}, [[0, 0], [50, -40], [-20, 90], [100, 0]], 90, 20, "night")
    spawn({"chief_wetbelly": 1}, [[126, -128]], 900, 2)
    spawn({"gulpmaw": 1}, [[60, 40]], 900, 6)
    zone = {"name": "The Wallow", "levels": [1, 10], "music": "the_wallow", "seed": 7321, "size": 384,
            "bind_point": [-150, -10], "height_amplitude": 3.0, "flat_radius": 24, "trees": 140,
            "tree_mix": [art("mangrove_tree") or "jungle_tree", "jungle_tree", art("mangrove_tree") or "jungle_tree"], "groves": 0.45, "rocks": 30,
            "grass_colors": ["#4a5a30", "#5c6a38"], "fog_density": 0.012, "fog_color": "#6c7858", "sun_energy": 0.8,
            "rain": {"amount": 1200}, "passes": passes, "zone_lines": lines, "lakes": pools,
            "water": {"shallow": "#34402a", "deep": "#12180e", "sky": "#4a5640"},
            "roads": [{"points": [[-192, 0], [-150, -8], [-80, 10], [0, 20], [90, 0], [192, 0]], "width": 3.0},
                      {"points": [[0, 20], [10, 100], [0, 192]], "width": 2.6}],
            "clutter": {"grass_a": {"density": 0.3, "patch": 0.55, "sway": 0.18, "range": 55, "tint": "ground", "scale": [0.8, 1.3]},
                        "reeds_tall": {"density": 0.02, "patch": 0.8, "sway": 0.2, "range": 55, "scale": [0.8, 1.4]},
                        "fern": {"density": 0.02, "patch": 0.8, "sway": 0.08, "range": 50, "scale": [0.9, 1.4]}},
            "landmarks": L, "npcs": npcs, "spawns": spawns}
    return zone


# ================================================================ DUSKWOOD

CAVE = [150, 120]  # the cave down to Duskhold, mouth facing east (like Greenmoor's)


def duskwood():
    passes, lines = borders("duskwood")
    lines.append({"pos": [CAVE[0] - 7.5, CAVE[1]], "size": [3, 4], "to": "duskhold", "arrive": list(DUSKHOLD_ARRIVE),
                  "arrive_face": list(DUSKHOLD_ARRIVE_FACE)})
    L = [{"type": "cave", "pos": CAVE, "face": [CAVE[0] + 150, CAVE[1]]},
         {"type": "signpost", "pos": [8, -170], "face": [8, -190], "labels": ["The Broken March"]},
         {"type": "signpost", "pos": [-170, 8], "face": [-190, 8], "labels": ["The Rotfen"]},
         {"type": "signpost", "pos": [166, 108], "face": [150, 120], "labels": ["Duskhold"]},
         {"type": "camp", "pos": [166, 138]}]
    # the Hearth scouts' camp in the east, watching the dark elves from the Emberhold side
    L.append({"type": "outpost", "pos": [120, -110]})
    for spot in [[-120, -60], [-60, 110], [40, 60]]:
        L.append({"type": "ruins", "pos": spot})
    L.append({"type": "spider_nest", "pos": [-130, 120]})
    L = [l for l in L if l]
    npcs = [
        {"id": npc("dusk_sentinel_vaelith", "Sentinel Vaelith", "duskhold", "dark_elf", "rogue", {
            "hail": "Keep to the shadows, {name}. The Emberhold [scouts] camp in the east of the wood, spying on the cave. Every badge you take from them is one less pair of eyes.",
            "scouts": "Humans from the Hearth. Four of their badges, and Duskhold pays, every time. Their captain, [Aldren], carries orders I want to read.",
            "aldren": "Scout-Captain Aldren. He never leaves their outpost. Bring me his orders.",
            "silkmother": "The great spider in the west of the wood. Her fang is worth a great deal to the right alchemist.",
            "unknown": "Ask below, in Duskhold."}, title="Duskwood Watch", weapon="dagger", gender="female", level=25),
         "pos": [172, 130], "face": [150, 120]},
        {"id": npc("dusk_huntress_ilvra", "Huntress Ilvra", "duskhold", "dark_elf", "ranger_class", {
            "hail": "The wood is kind to those who know it, {name}, and cruel to the rest. Dresna in the city sent you about the [satchel]?",
            "satchel": "Bring Dresna's silk to me, with two gloomfang pelts, and I'll make the body of it.",
            "dresna": "Dresna weaves in Duskhold. If she sent silk, give it here.",
            "unknown": "The trees don't say, and neither do I."}, title="Huntress", weapon="bow", gender="female", level=25),
         "pos": [160, 144], "face": [166, 138]},
        {"id": "duskhold_guard", "name": "Cave Sentinel Rhyzz", "pos": [158, 112], "face": [150, 120]},
    ]
    quest("dusk_scout_badges", "Eyes in the Wood", "dusk_sentinel_vaelith", {"hearth_scout_badge": 4}, 140, 50, "gloomsilk_gloves",
          "You have taken on a task: Eyes in the Wood. Bring Sentinel Vaelith four Hearth scouts' badges.",
          "Badges. How many eyes closed?", "Four fewer spies. Duskhold thanks you.", "Take these. Silk, so your hands stay quiet.",
          {"duskhold": 10}, keyword="scouts", repeatable=True)
    quest("dusk_aldren", "The Captain's Orders", "dusk_sentinel_vaelith", {"aldrens_orders": 1}, 500, 150, "scout_captains_ring",
          "You have taken on a task: The Captain's Orders. Bring Sentinel Vaelith Scout-Captain Aldren's orders.",
          "His orders? Let me read them.", "...They know about the cave. Of course they do. Good work.", "His ring. It suits you better.",
          {"duskhold": 25}, keyword="aldren")
    quest("dusk_silkmother", "The Silkmother's Fang", "dusk_sentinel_vaelith", {"vyss_fang": 1}, 450, 120, "silkmother_stiletto",
          "You have taken on a task: The Silkmother's Fang. Bring Sentinel Vaelith the Silkmother's fang.",
          "Her fang! Carefully, {name}.", "Still wet with venom. Perfect.", "Our smiths set its twin into a blade. Take it.",
          {"duskhold": 20}, keyword="silkmother")
    quest("silkweave_silk", "The Silkweave Satchel (1 of 3)", "dusk_outfitter", {"duskwood_silk": 4}, 40, 10, "spun_duskwood_silk",
          "You have taken on a task: The Silkweave Satchel. Bring Silkweaver Dresna four strands of Duskwood spider silk.",
          "Silk? Show me.", "Wound, drawn, spun... there. Duskwood silk, strong as wire.",
          "Take it up to Huntress Ilvra by the cave mouth and ask her about [Dresna]. She'll want gloomfang pelts for the body.",
          {"duskhold": 5}, keyword="satchel", nxt="silkweave_body")
    quest("silkweave_body", "The Silkweave Satchel (2 of 3)", "dusk_huntress_ilvra", {"spun_duskwood_silk": 1, "gloomfang_pelt": 2}, 90, 20,
          "gloomfang_satchel_body", "You have taken on a task: The Silkweave Satchel. Bring Huntress Ilvra the spun silk and two gloomfang pelts.",
          "Dresna's silk, and pelts. Give them here.", "Pelt outside, silk seams... done.",
          "Back to Dresna for the clasp. She'll want shade dust to set it.", {"duskhold": 5}, nxt="silkweave_clasp")
    quest("silkweave_clasp", "The Silkweave Satchel (3 of 3)", "dusk_outfitter", {"gloomfang_satchel_body": 1, "shade_dust": 1}, 150, 30,
          "dresnas_silkweave_satchel", "You have taken on a task: The Silkweave Satchel. Bring Silkweaver Dresna the gloomfang satchel and some shade dust.",
          "The satchel, and shade dust. Good.", "A clasp of set shadow: it opens for you and no one else.", "It's yours, {name}.",
          {"duskhold": 10})
    mob("gloom_rat", "a gloom rat", (1, 2), "rat", loot=[("gloom_rat_tail", 0.5), ("raw_meat", 0.2)], aggressive=False, speed=6.0)
    mob("dusk_spiderling", "a duskwood spiderling", (2, 4), "spider", loot=[("duskwood_silk", 0.55)], scale=0.55, aggressive=False)
    mob("gloomwing_moth", "a gloomwing moth", (3, 5), "lantern_moth", verb=("buffet", "buffets"), loot=[("moth_wing", 0.5)], scale=1.25,
        aggressive=False, extra={"color": "#6a5a8a"})
    mob("restless_bones", "restless bones", (3, 5), "skeleton_minion", faction="undead", verb=("claw", "claws"), loot=[("bone_chips", 0.4)],
        coin=(0, 8))
    mob("gloomfang_wolf", "a gloomfang wolf", (4, 6), "wolf", loot=[("gloomfang_pelt", 0.5), ("raw_meat", 0.3)], social=True, speed=7.0)
    mob("lesser_shade", "a lesser shade", (5, 7), "shade", faction="undead", verb=("touch", "touches"), loot=[("shade_dust", 0.5)], scale=0.8)
    mob("hearth_scout", "a Hearth scout", (6, 8), "ranger_class", faction="hearth_scouts", verb=("slash", "slashes"), social=True,
        loot=[("hearth_scout_badge", 0.5)], coin=(8, 30), extra={"weapon": "sword_1handed"})
    mob("hearth_archer", "a Hearth archer", (7, 9), "ranger_class", faction="hearth_scouts", verb=("shoot", "shoots"), social=True,
        loot=[("hearth_scout_badge", 0.5)], coin=(8, 30), extra={"weapon": "bow"})
    mob("silkmother_vyss", "the Silkmother Vyss", (9, 9), "spider", named=True, loot=[("vyss_fang", 1.0)], scale=1.5)
    mob("scout_captain_aldren", "Scout-Captain Aldren", (10, 10), "knight", faction="hearth_scouts", verb=("slash", "slashes"), social=True,
        named=True, loot=[("aldrens_orders", 1.0)], coin=(60, 200), extra={"weapon": "sword_1handed"})
    spawns = []

    def spawn(pool, spots, respawn=60, wander=12, when=None):
        for s in spots:
            e = {"pos": s, "pool": pool, "respawn": respawn, "wander": wander}
            if when:
                e["when"] = when
            spawns.append(e)
    # the beginners' own (2026-09-29: was 6 rats and 6 spiderlings, then only things that attack on sight)
    spawn({"gloom_rat": 1}, [[130, 80], [110, 150], [90, 110], [140, 60], [70, 150], [100, 40], [150, 40], [120, 100], [60, 120],
                             [90, 70], [40, 170]], 30)
    spawn({"dusk_spiderling": 1}, [[40, 110], [0, 140], [-40, 100], [-80, 140], [20, 60], [-100, 80], [0, 100], [-40, 150], [30, 130],
                                   [-60, 60]], 40)
    spawn({"gloomwing_moth": 1}, [[80, -20], [40, -60], [-20, 20], [20, 30], [-60, -30], [100, -50]], 50, 16)  # a calm step between the spiderlings and the wolves
    spawn({"restless_bones": 1}, [[-120, -50], [-110, -70], [-60, 100], [-70, 120], [40, 50], [30, 70]], 60)
    spawn({"gloomfang_wolf": 1}, [[-40, 0], [0, -30], [-80, -20], [40, -40], [-20, 40], [60, 10]], 55)
    spawn({"lesser_shade": 1}, [[-120, -60], [-60, 110], [40, 60], [-20, -80]], 80, 16, "night")
    spawn({"hearth_scout": 2, "hearth_archer": 1}, [[100, -100], [140, -120], [120, -140], [150, -90], [90, -130]], 70, 8)
    spawn({"silkmother_vyss": 1}, [[-136, 124]], 900, 4)
    spawn({"scout_captain_aldren": 1}, [[122, -114]], 900, 3)
    zone = {"name": "Duskwood", "levels": [1, 10], "music": "duskwood", "seed": 7331, "size": 384, "bind_point": [166, 150],
            "height_amplitude": 5.0, "flat_radius": 20, "trees": 320,
            "tree_mix": [art("dusk_tree") or "black_tree", art("dusk_tree_b") or "black_tree_b", art("dusk_tree") or "black_tree", "pine_a"],
            "groves": 0.55, "rocks": 50, "grass_colors": ["#2e3a2a", "#3c4632"], "fog_density": 0.02, "fog_color": "#3a3448",
            "sun_energy": 0.5, "passes": passes, "zone_lines": lines,
            "roads": [{"points": [[0, -192], [-6, -120], [10, -40], [0, 40], [-60, 20], [-120, 0], [-192, 0]], "width": 3.0},
                      {"points": [[0, 40], [60, 90], [120, 120], [150, 120]], "width": 2.8}],
            "clutter": {"grass_b": {"density": 0.22, "patch": 0.5, "sway": 0.14, "range": 45, "tint": "ground", "scale": [0.8, 1.2]},
                        "fern": {"density": 0.04, "patch": 0.8, "sway": 0.08, "range": 50, "scale": [0.9, 1.6]},
                        "mushrooms": {"density": 0.01, "patch": 0.8, "sway": 0.0, "range": 40, "scale": [0.8, 1.4]}},
            "landmarks": L, "npcs": npcs, "spawns": spawns}
    return zone


# ================================================================ DUSKHOLD

DUSKHOLD_ARRIVE = [0, -80]
DUSKHOLD_ARRIVE_FACE = [0, -40]


def duskhold():
    L = []
    L.append(prop("cavern_dome", [0, 0], collide="none"))
    L.append(prop("dusk_gate", [0, -96], face=[0, 0], collide="mesh"))
    # the lake, an island in it, and bridges to the island
    lake = [at(b, 36) for b in range(0, 360, 15)]
    L.append(prop("timiraj_shrine", [0, 0], face=[0, -20], collide="box"))
    # the dark elves' own gods beside the Unlit on the island: the spider west, the moth east
    L.append(prop("idol_tantuvi", [-10, 2], face=[-10, -30], collide="box", scale=1.8))
    L.append(prop("idol_dipanti", [10, 2], face=[10, -30], collide="box", scale=1.8))
    for b in (90, 270):  # the bridge spans along its own X: turned so it runs from the shore out to the island
        spot = at(b, 25.5)  # 24 m at 1.2 scale: from the island's edge (15) onto the shore (36)
        bridge = prop("dusk_bridge", spot, face=[spot[0] + 60, spot[1]], collide="mesh", scale=1.2)
        if bridge:
            bridge["y_at"] = [[round(c, 1) for c in at(b, 13.5)], [round(c, 1) for c in at(b, 37.5)]]  # level with its ends, not the lake bed
            bridge["slope"] = True  # stay exactly on the line between them
            L.append(bridge)
    for b in range(15, 360, 30):
        L.append(prop("glow_crystal", at(b, 40), collide="box"))
    for b in [20, 70, 110, 160, 200, 250, 290, 340]:
        L.append(prop("dusk_spire", at(b, 78), face=[0, 0], collide="mesh"))
    for b in [0, 45, 135, 180, 225, 315]:
        L.append(prop("dusk_house", at(b, 60), face=[0, 0], collide="mesh"))
    for b in range(0, 360, 20):
        L.append(prop("stalagmite_cluster", at(b + 7, 98), collide="box"))
    for b in range(10, 360, 40):
        L.append(prop("candle_stand", at(b, 48), collide="trunk"))
    for pid, b in [("forge", 232), ("oven", 238), ("loom", 244), ("brew_barrel", 250)]:
        L.append(prop(pid, at(b, 50), face=[0, 0], collide="box"))
    L = [l for l in L if l]
    npcs = []

    def put(nid, pos, face=(0, 0)):
        npcs.append({"id": nid, "pos": [round(pos[0], 1), round(pos[1], 1)], "face": [round(face[0], 1), round(face[1], 1)]})

    F, C = "duskhold", "Duskhold"
    put(npc("dusk_priest_seyra", "Umbral Mother Seyra", F, "dark_elf", "necromancer", {
        "hail": "The Unlit remembers you, {name}, as he remembers everyone. Here, under the world, we remember him back. I can [bind] your soul to his shrine, and his followers may ask for his [blessing].",
        "bind": "Close your eyes. It's no darker than it is with them open. ...There. You'll wake here, in his dark.",
        "unknown": "Ask the dark. It knows."}, title="Keeper of the Unlit Shrine", weapon="staff", gender="female", level=40, binds=True,
        blesses={"deity": "dark", "spell": "veil_of_the_unlit", "keyword": "blessing", "every": 3600,
                 "refuse": "His veil is for his own, {name}.", "wait": "Within the hour, {name}. Even the dark keeps time.",
                 "give": "Hold still. ...The veil settles."}), [0, 8], [0, 30])
    put(npc("dusk_priest_tantuvi", "Weaver-Priestess Ysvaine", F, "dark_elf", "necromancer", {
        "hail": "Every thread ends somewhere, {name}. Tantuvi knows where yours does, and she isn't telling. I keep her idol; I can [bind] you to Duskhold, and her followers may ask for her [blessing].",
        "bind": "Hold still, as the fly does. ...There. Your thread is tied here now.",
        "unknown": "The web knows. Ask it."}, title="Priestess of the Many-Eyed", weapon="staff", gender="female", level=40, binds=True,
        blesses={"deity": "web", "spell": "tantuvi_blessing", "keyword": "blessing", "every": 3600,
                 "refuse": "Her silk is for her own, {name}.", "wait": "Within the hour, {name}. A web takes time to spin.",
                 "give": "Be still. ...Feel the threads? They're yours for a while."}), [-7, -4], [-7, -30])
    put(npc("dusk_priest_dipanti", "Lamp-Keeper Aelyss", F, "dark_elf", "mage", {
        "hail": "Mind the candles, {name}. Every one is a prayer, and every one is bait. I tend the Lamp-Eater's idol; I can [bind] you here, and her followers may ask for her [blessing].",
        "bind": "Close your eyes. The light goes out, and... there. You'll wake by these candles.",
        "unknown": "Ask the flame. It won't last long enough to answer."}, title="Keeper of the Lamp-Eater", weapon="staff", gender="female", level=40,
        binds=True, blesses={"deity": "moth", "spell": "dipanti_blessing", "keyword": "blessing", "every": 3600,
                             "refuse": "The light she gives is for her own, {name}.", "wait": "Within the hour, {name}. Even she must wait for the next flame.",
                             "give": "Breathe in. ...The candle's light is in you now."}), [7, -4], [7, -30])
    gms = [("warrior", "Blademaster Zhaelith", "knight", "sword_1handed", "male", "Steel is honest, {name}. Everything else down here lies."),
           ("cleric", "High Priestess Ysmae", "knight", "wand", "female", "The Unlit gives mercy only to his own, {name}, and so do I. If you're mine, kneel."),
           ("rogue", "Shade-Master Vessk", "rogue", "dagger", "male", "You didn't hear me coming. Good. Neither will they, once I've finished with you."),
           ("wizard", "Magister Olvaine", "mage", "staff", "female", "Fire burns brighter in the dark, {name}. Let me show you how bright."),
           ("magician", "Summoner Ilzareth", "magician", "staff", "male", "What you call, you command, {name}. What you command, you keep."),
           ("necromancer", "Grave-Lord Mhaerik", "necromancer", "staff", "male", "The dead are patient servants, {name}. Learn to be a patient master.")]
    for i, (cls, name, model, weapon, gender, hail) in enumerate(gms):
        b = 200 - i * 28
        put(npc(f"dusk_gm_{cls}", name, F, "dark_elf", model, {"hail": hail, "unknown": "Ask the Umbral Mother."},
                title=f"{cls.capitalize()} Guildmaster", weapon=weapon, gender=gender, level=40,
                guildmaster={"class": cls, "refuse": "Not my art, {name}. Look elsewhere."}), at(b, 66), (0, 0))
    put(npc("dusk_banker", "Vaultkeeper Nyx", F, "dark_elf", "rogue_hooded", {
        "hail": "Your treasures are safe beneath the world, {name}. Safer than you are. Press G.", "unknown": "I keep the vault."},
        title="Duskhold Vault", banker=True, gender="female", level=20), at(20, 50), (0, 0))
    put(npc("dusk_registrar", "Registrar Tsyl", F, "dark_elf", "mage", {
        "hail": "The houses of Duskhold are written in my book, {name}. Would you found one? Ask for a [charter].",
        "charter": "Ten platinum, and you must have reached level 10. Stand before me and say /guildcreate <name>.",
        "guild": "A house: a name, a roster, and a voice its members hear anywhere with /gu. Ask for a [charter].",
        "unknown": "I keep the book of houses."}, title="Guild Registrar", guild_registrar=True, level=30), at(34, 50), (0, 0))
    put(npc("dusk_provisioner", "Provisioner Aelis", F, "dark_elf", "rogue", {
        "hail": "Salt, thread, flour and the rest, {name}, carried down the long stair at great expense. Press G.",
        "unknown": "Buying?"}, title="Provisioner", gender="female", level=25, merchant={"sells": SUPPLIES, "buy_rate": 0.5}), at(240, 58), (0, 0))
    put(npc("dusk_outfitter", "Silkweaver Dresna", F, "dark_elf", "mage", {
        "hail": "Silk and leather for those who go up into the wood, {name}. And if you'll gather for me, I'll weave you a proper [satchel].",
        "satchel": "A silkweave satchel, the kind the wood-runners carry. Start me with four strands of Duskwood spider silk; the little spiders in the wood above make it.",
        "unknown": "I weave. I don't gossip."}, title="Outfitter", gender="female", level=25, merchant={"sells": OUTFIT, "buy_rate": 0.5}),
        at(300, 58), (0, 0))
    put(npc("dusk_smith", "Smith Kaelvor", F, "dark_elf", "knight", {
        "hail": "Dark steel, forged at the heat of the deep vents. Press G, {name}.", "unknown": "I forge. That's all."},
        title="Blacksmith", weapon="sword_1handed", level=25, merchant={"sells": ARMS, "buy_rate": 0.5}), at(320, 58), (0, 0))
    for i, spot in enumerate([[-7, -84], [7, -84], at(250, 30), at(290, 30)]):
        nid = guard("duskhold_guard_f" if i % 2 else "duskhold_guard", "a Duskhold sentinel", F, "dark_elf", C, gender="female" if i % 2 else None)
        put(nid, spot, (0, -110) if spot[1] < -80 else (0, 0))
    back = [CAVE[0] + 6, CAVE[1]]
    zone = {"name": "Duskhold", "interior": True, "music": "duskhold", "seed": 7341, "size": 224, "bindstone": True, "bind_point": [0, 6],
            "height_amplitude": 1.0, "flat_radius": 70, "clear_radius": 100, "trees": 0, "rocks": 20,
            "ambient_color": "#9a8ac0", "ambient_energy": 0.55, "fog_color": "#1c1628", "fog_density": 0.006, "grass_colors": ["#2a2630", "#34303c"],
            "passes": [[0, -112, 9]],  # a gap in the cavern wall behind the gate, where the tunnel leads up
            "zone_lines": [{"pos": [0, -101], "size": [8, 4], "to": "duskwood", "arrive": back, "arrive_face": [back[0] + 30, back[1]]}],
            "water": {"shallow": "#1a1628", "deep": "#06040c", "sky": "#2a2440"},
            "lakes": [{"points": lake, "depth": 3.0, "shelf": 6, "bank": 4, "islands": [[0, 0, 15]]}],
            "roads": [{"points": [[0, -96], [0, -60], [0, -36]], "width": 3.4}],
            "landmarks": L, "npcs": npcs, "spawns": []}
    return zone


# ================================================================ THE ROTFEN

def the_rotfen():
    passes, lines = borders("the_rotfen")
    L = [{"type": "camp", "pos": [40, -40]},
         {"type": "signpost", "pos": [8, -206], "face": [8, -224], "labels": ["The Wallow"]},
         {"type": "signpost", "pos": [206, 8], "face": [224, 8], "labels": ["Duskwood"]},
         {"type": "lizard_camp", "pos": [-140, -60]}]
    for spot in [[140, 150], [160, 120], [120, 170]]:
        L.append(prop("hag_hut", spot, face=[140, 140], collide="mesh"))
    L.append(prop("hag_cauldron", [140, 140], collide="box"))
    L.append({"type": "ruins", "pos": [-40, 150]})
    L = [l for l in L if l]
    pools = []
    for c, r, dp in [((-40, 60), 40, 1.2), ((80, -120), 34, 0.8), ((-120, 150), 36, 0.9), ((150, 30), 30, 0.7), ((-60, 150), 30, 2.4)]:
        pools.append({"points": [[c[0] + r * math.cos(a) * (1 + 0.15 * math.sin(a * 3)), c[1] + r * math.sin(a) * (1 + 0.12 * math.cos(a * 2))]
                                 for a in [i * math.tau / 14 for i in range(14)]], "depth": dp, "shelf": 12, "bank": 6})
    npcs = [
        {"id": npc("fen_warden_grisk", "Fenwarden Grisk", "murkhold", "troll", "barbarian", {
            "hail": "Murkhold and Duskhold both hunt the Rotfen, {name}, and neither trusts the other. I don't care, as long as the [lizardfolk] stop taking my traps.",
            "lizardfolk": "The Mirescale, west of here. Four of their scales and I pay, every time. Their chief, [Sisska], carries a totem I want burned.",
            "sisska": "Chief Sisska. Biggest lizard in the camp to the west. Bring me the totem.",
            "mudjaw": "Old Mudjaw. A crocodile older than Murkhold, in the deep pool south-west. Bring me one of its teeth, if you can pull one.",
            "unknown": "Ask Nyssa. She pretends to know everything."}, title="Fenwarden", weapon="axe_2handed", level=30),
         "pos": [34, -54], "face": [34, -70]},
        {"id": npc("blade_sister_nyssa", "Blade-Sister Nyssa", "duskhold", "dark_elf", "rogue", {
            "hail": "Grisk hunts lizards. I hunt [hags]. The coven in the south-east steals our dead for their pots.",
            "hags": "The Gristle Coven. Bring me three of their bone charms and I'll pay each time. Their mother, [Gristlewort], I want dead.",
            "gristlewort": "Mother Gristlewort. She stirs the big cauldron in the coven's camp. Bring me her heart.",
            "unknown": "Grisk might know. He won't tell you, but he might know."}, title="Blade of Duskhold", weapon="dagger", gender="female",
            level=30), "pos": [46, -54], "face": [46, -70]},
    ]
    quest("rotfen_scales", "Scales for the Fenwarden", "fen_warden_grisk", {"mirescale_scale": 4}, 600, 120, "fenwalker_boots",
          "You have taken on a task: Scales for the Fenwarden. Bring Fenwarden Grisk four mirescale scales.",
          "Scales. Good.", "That's four lizards who won't touch my traps.", "Boots for fen-walking. You'll need them.",
          {"murkhold": 10, "duskhold": 5}, keyword="lizardfolk", repeatable=True)
    quest("rotfen_sisska", "The Chief's Totem", "fen_warden_grisk", {"chief_sisskas_totem": 1}, 1800, 400, "sisskas_scaled_belt",
          "You have taken on a task: The Chief's Totem. Bring Fenwarden Grisk Chief Sisska's totem.",
          "Sisska's totem!", "Into the fire with it. The camp will be leaderless for a while.", "Her belt. Wear it well.",
          {"murkhold": 25, "duskhold": 10}, keyword="sisska")
    quest("rotfen_mudjaw", "Old Mudjaw's Tooth", "fen_warden_grisk", {"mudjaws_tooth": 1}, 2000, 500, "mudjaw_tooth_club",
          "You have taken on a task: Old Mudjaw's Tooth. Bring Fenwarden Grisk one of Old Mudjaw's teeth.",
          "A tooth that size... you really did it.", "Makarosh must be pleased. Or jealous.", "I set the other half in a club. Take it.",
          {"murkhold": 25, "duskhold": 10}, keyword="mudjaw")
    quest("rotfen_hag_charms", "The Gristle Coven", "blade_sister_nyssa", {"hag_charm": 3}, 600, 120, None, "", "", "", "", {}, keyword="hags")
    QUESTS["rotfen_hag_charms"].update({
        "accept_text": "You have taken on a task: The Gristle Coven. Bring Blade-Sister Nyssa three hag's bone charms.",
        "ready_text": "Charms. Hand them over.", "complete_text": "Three fewer pots stirring our dead.", "faction": {"duskhold": 10, "murkhold": 5},
        "repeatable": True})
    quest("rotfen_gristlewort", "Mother Gristlewort", "blade_sister_nyssa", {"gristleworts_heart": 1}, 1900, 450, "gristlewort_amulet",
          "You have taken on a task: Mother Gristlewort. Bring Blade-Sister Nyssa Mother Gristlewort's heart.",
          "Her heart. Show me.", "Withered and black. As it should be.", "Her amulet. The coven's power, turned to our use.",
          {"duskhold": 25, "murkhold": 10}, keyword="gristlewort")
    mob("plague_rat", "a plague rat", (10, 11), "rat", loot=[("plague_rat_tail", 0.5)], scale=1.3, social=True)
    mob("fen_eel", "a fen eel", (10, 12), "marsh_eel", loot=[("fen_eel_skin", 0.5)])
    mob("rotfen_lurker", "a rotfen lurker", (11, 13), "bog_lurker", verb=("lash", "lashes"), loot=[("rotfen_lurker_hide", 0.5)])
    mob("rotfen_mirescale", "a mirescale fenhunter", (12, 14), "lizardfolk", faction="mirescale", verb=("stab", "stabs"), social=True,
        loot=[("mirescale_scale", 0.55)], coin=(12, 45))
    mob("rotfen_mirescale_shaman", "a mirescale fen-shaman", (12, 14), "lizardfolk_shaman", faction="mirescale", verb=("strike", "strikes"),
        social=True, loot=[("mirescale_scale", 0.55)], coin=(15, 55))
    mob("gristle_hag", "a gristle hag", (14, 16), "bog_hag", faction="gristle_coven", verb=("claw", "claws"), social=True,
        loot=[("hag_charm", 0.5)], coin=(20, 70))
    mob("feral_fen_troll", "a feral fen troll", (15, 17), "river_troll", faction="wildlife", verb=("smash", "smashes"),
        loot=[("troll_tusk", 0.5)], coin=(20, 80), extra={"hp_regen": 12})
    mob("chief_sisska", "Chief Sisska", (16, 16), "lizardfolk_chief", faction="mirescale", verb=("stab", "stabs"), social=True, named=True,
        loot=[("chief_sisskas_totem", 1.0)], coin=(150, 400))
    mob("mother_gristlewort", "Mother Gristlewort", (17, 17), "bog_hag", faction="gristle_coven", verb=("claw", "claws"), social=True,
        named=True, loot=[("gristleworts_heart", 1.0)], coin=(150, 420), scale=1.25)
    mob("old_mudjaw", "Old Mudjaw", (17, 17), "ancient_croc", verb=("bite", "bites"), named=True, loot=[("mudjaws_tooth", 1.0)],
        aggressive=False)
    spawns = []

    def spawn(pool, spots, respawn=90, wander=14, when=None):
        for s in spots:
            e = {"pos": s, "pool": pool, "respawn": respawn, "wander": wander}
            if when:
                e["when"] = when
            spawns.append(e)
    spawn({"plague_rat": 1}, [[0, -150], [40, -170], [-40, -160], [80, -60], [100, -20], [-10, -100]], 60)
    spawn({"fen_eel": 1}, [[-40, 60], [-20, 40], [80, -120], [150, 30], [-120, 150]], 70, 10)
    spawn({"rotfen_lurker": 1}, [[-80, 40], [0, 90], [60, 120], [-100, 100], [120, 60], [20, 20]], 80)
    spawn({"rotfen_mirescale": 2, "rotfen_mirescale_shaman": 1}, [[-130, -40], [-150, -80], [-110, -90], [-160, -30], [-120, -20]], 90, 8)
    spawn({"gristle_hag": 1}, [[130, 140], [160, 150], [150, 110], [110, 160]], 100, 8)
    spawn({"feral_fen_troll": 1}, [[-20, 180], [30, 190], [-70, 190], [60, 160]], 110)
    spawn({"chief_sisska": 1}, [[-140, -62]], 1200, 3)
    spawn({"mother_gristlewort": 1}, [[140, 136]], 1200, 3)
    spawn({"old_mudjaw": 1}, [[-60, 150]], 1200, 6)
    zone = {"name": "The Rotfen", "levels": [10, 18], "music": "the_rotfen", "seed": 7351, "size": 448, "bind_point": [40, -30],
            "height_amplitude": 3.5, "flat_radius": 20, "trees": 170,
            "tree_mix": [art("mangrove_tree") or "jungle_tree", "black_tree", art("mangrove_tree") or "jungle_tree", "jungle_tree"],
            "groves": 0.5, "rocks": 40, "grass_colors": ["#3e4a2a", "#4e5634"], "fog_density": 0.016, "fog_color": "#5a6048",
            "sun_energy": 0.7, "rain": {"amount": 1500}, "passes": passes, "zone_lines": lines, "lakes": pools,
            "water": {"shallow": "#303a26", "deep": "#10150c", "sky": "#465038"},
            "roads": [{"points": [[0, -224], [10, -150], [40, -40], [120, 0], [224, 0]], "width": 3.0}],
            "clutter": {"grass_a": {"density": 0.26, "patch": 0.55, "sway": 0.18, "range": 55, "tint": "ground", "scale": [0.8, 1.3]},
                        "reeds_tall": {"density": 0.025, "patch": 0.8, "sway": 0.2, "range": 55, "scale": [0.8, 1.4]},
                        "mushrooms": {"density": 0.008, "patch": 0.8, "sway": 0.0, "range": 40, "scale": [0.8, 1.4]}},
            "landmarks": L, "npcs": npcs, "spawns": spawns}
    return zone


# ================================================================ RAINHOLD's new gates

def rainhold():
    path = f"{ROOT}/data/zones/rainhold.json"
    z = json.load(open(path))
    passes, lines = borders("rainhold")
    z["passes"], z["zone_lines"] = passes, lines
    sc = [l for l in z["landmarks"] if l["type"] == "stilt_city"][0]
    new = [["stilt_walkway", -25.5, 0, 90], ["boardwalk_ramp", -30.0, 0, 270]]
    gone = [["stilt_walkway", -7.5, 48, 0], ["boardwalk_ramp", -7.5, 52.5, 0]]  # the south gate's pier: nothing lies south since the Blackwater moved
    sc["pieces"] = [p for p in sc["pieces"] if p not in new and p not in gone] + new
    roads = [r for r in z["roads"] if r["points"][0] not in ([-112, 0], [0, 112])]
    roads += [{"points": [[-112, 0], [-70, 0], [-38, 0]], "width": 4}]
    z["roads"] = roads
    signs = [l for l in z["landmarks"] if not (l["type"] == "signpost" and l.get("labels") in (["The Wallow"], ["Duskwood"], ["Stormcut Gorge"]))]
    signs += [{"type": "signpost", "pos": [-54, 7], "face": [-112, 7], "labels": ["Stormcut Gorge"]}]
    z["landmarks"] = signs
    json.dump(z, open(path, "w"), indent=2)
    open(path, "a").write("\n")


# ================================================================ write

def merge(path, new, owned_prefix=None):
    """Adds or replaces this generator's entries in a shared data file by
    text, touching nothing else: the files mix formats (other people's
    entries are hand-written), and re-dumping them would reformat everything."""
    t = open(path).read()
    d = json.loads(t)
    for k, v in new.items():
        block = json.dumps(v, indent=2).replace("\n", "\n  ")
        if k not in d:
            end = t.rstrip()
            i = end.rfind("\n}")
            t = end[:i] + ",\n  %s: %s" % (json.dumps(k), block) + end[i:] + "\n"
        elif d[k] != v:
            start = t.index("\n  %s: " % json.dumps(k))
            nxt = t.find("\n  \"", start + 1)  # the next top-level key, or the file's end
            stop = nxt if nxt >= 0 else t.rstrip().rfind("\n}")
            body = t[start:stop]
            comma = "," if body.rstrip().endswith(",") else ""
            t = t[:start] + "\n  %s: %s%s" % (json.dumps(k), block, comma) + t[stop:]
        d = json.loads(t)
    assert all(d[k] == v for k, v in new.items()), path
    with open(path, "w") as f:
        f.write(t)


def factions():
    path = f"{ROOT}/data/factions.json"
    t = open(path).read()
    add = {
        "wallow_pondkin": {"name": "Pondkin of the Wallow", "default": -800, "kos_at": -750, "on_kill": {"wallow_pondkin": -10, "murkhold": 3}},
        "hearth_scouts": {"name": "Scouts of the Hearth", "default": -800, "kos_at": -750, "on_kill": {"hearth_scouts": -10, "duskhold": 3}},
        "gristle_coven": {"name": "The Gristle Coven", "default": -800, "kos_at": -750,
                          "on_kill": {"gristle_coven": -10, "duskhold": 3, "murkhold": 2}},
    }
    add = {k: v for k, v in add.items() if '"%s"' % k not in t}
    if not add:
        return
    end = t.rstrip()
    i = end.rfind("\n}")
    body = "".join(",\n  %s: %s" % (json.dumps(k), json.dumps(v, indent=2).replace("\n", "\n  ")) for k, v in add.items())
    t2 = end[:i] + body + end[i:] + "\n"
    json.loads(t2)
    open(path, "w").write(t2)


def spells():
    path = f"{ROOT}/data/spells.json"
    t = open(path).read()
    add = {
        "makarosh_blessing": {"name": "Deep-Jaw's Patience", "type": "buff", "target": "self", "mana": 0, "cast_time": 0, "recast": 0, "range": 0,
                              "duration": 1800, "stats": {"ac": 10, "hp": 50, "hp_regen": 2}, "classes": {},
                              "land_text": "The black water closes over your thoughts, still and patient: the Deep-Jawed sees you.",
                              "fade_text": "The Deep-Jawed's patience leaves you.",
                              "desc": "For half an hour: +10 AC, +50 hit points and +2 health regeneration. Makarosh's gift to his followers, once an hour at his idol in Murkhold.",
                              "fx": {"kind": "buff", "color": "#5a7a3a"}},
        "mahishra_blessing": {"name": "Mud-Horn's Strength", "type": "buff", "target": "self", "mana": 0, "cast_time": 0, "recast": 0, "range": 0,
                              "duration": 1800, "stats": {"str": 12, "sta": 12, "hp": 40}, "classes": {},
                              "land_text": "The ground seems to push up through your feet: the Mud-Horned sees you.",
                              "fade_text": "The Mud-Horned's strength drains back into the earth.",
                              "desc": "For half an hour: +12 strength, +12 stamina and +40 hit points. Mahishra's gift to his followers, once an hour at his idol in Murkhold.",
                              "fx": {"kind": "buff", "color": "#8a6a3a"}},
        "tantuvi_blessing": {"name": "Tantuvi's Silk", "type": "buff", "target": "self", "mana": 0, "cast_time": 0, "recast": 0, "range": 0,
                             "duration": 1800, "stats": {"agi": 12, "ac": 10, "hp": 30}, "classes": {},
                             "land_text": "Fine threads settle over your skin, cool and strong: the Many-Eyed sees you.",
                             "fade_text": "Tantuvi's silk comes loose and drifts away.",
                             "desc": "For half an hour: +12 agility, +10 AC and +30 hit points. Tantuvi's gift to her followers, once an hour at her idol in Duskhold.",
                             "fx": {"kind": "buff", "color": "#b8b0d8"}},
        "dipanti_blessing": {"name": "Dipanti's Stolen Light", "type": "buff", "target": "self", "mana": 0, "cast_time": 0, "recast": 0, "range": 0,
                             "duration": 1800, "stats": {"int": 10, "wis": 10, "mana": 60, "mana_regen": 2}, "classes": {},
                             "land_text": "A candle gutters out nearby, and its light is in you: the Lamp-Eater sees you.",
                             "fade_text": "The stolen light in you burns down.",
                             "desc": "For half an hour: +10 intelligence, +10 wisdom, +60 mana and +2 mana every tick. Dipanti's gift to her followers, once an hour at her idol in Duskhold.",
                             "fx": {"kind": "buff", "color": "#d8a860"}},
    }
    add = {k: v for k, v in add.items() if '"%s"' % k not in t}
    if not add:
        return
    end = t.rstrip()
    i = end.rfind("\n}")
    body = "".join(",\n  %s: %s" % (json.dumps(k), json.dumps(v, indent=2).replace("\n", "\n  ")) for k, v in add.items())
    t2 = end[:i] + body + end[i:] + "\n"
    json.loads(t2)
    open(path, "w").write(t2)


def main():
    zones = {"murkhold": murkhold(), "the_wallow": the_wallow(), "duskwood": duskwood(), "duskhold": duskhold(), "the_rotfen": the_rotfen()}
    for zid, z in zones.items():
        with open(f"{ROOT}/data/zones/{zid}.json", "w") as f:
            f.write(json.dumps(z, indent=2) + "\n")
    rainhold()
    merge(f"{ROOT}/data/npcs.json", NPCS)
    merge(f"{ROOT}/data/mobs.json", MOBS)
    merge(f"{ROOT}/data/quests.json", QUESTS)
    with open(f"{ROOT}/data/items/blackwater.json", "w") as f:
        f.write(json.dumps(ITEMS, indent=2) + "\n")
    spells()
    factions()
    missing = [l["id"] for z in zones.values() for l in z["landmarks"] if l.get("type") == "prop" and l["id"] not in MODELS["props"]]
    print("wrote %s; %d npcs, %d mobs, %d quests, %d items%s" % (", ".join(zones), len(NPCS), len(MOBS), len(QUESTS), len(ITEMS),
                                                                  "; MISSING props: %s" % sorted(set(missing)) if missing else ""))


if __name__ == "__main__":
    main()
