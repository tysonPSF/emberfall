"""Writes the ground between the Blackwater and Rainhold (2026-09-29).

    python3 tools/zones/west_march.py

The Blackwater moved two cells west so the evil homelands weren't packed
against Emberhold and Rainhold; this fills the gap with two neutral zones:

The Broken March (broken_march, 14-20): wind-scoured heath and crags, the
ruins of an old border war. Marchwarden's Post (Rainhold's wardens, neutral to
both sides) in the middle; march wolves and brambleback boars, the Marchreaver
highwaymen (Redhand Corvel), the restless dead of the broken keep (the Hollow
Marshal at night), crag wyverns (Scythewing). West to the Wallow, south to
Duskwood, east to Stormcut Gorge: the Blackwater's way out after the Rotfen.

Stormcut Gorge (stormcut_gorge, 18-22): a rain-cut canyon with a river down
its length and waterfalls off the south cliffs. The Cutwatch (Rainhold) by the
east gate; gorge crocodiles and canyon adders on the river, the Stonefist
trolls' camp on the west bank (Chief Grukk Stonefist), griffons on the
north-east crags (Stormcrest), the spirits of the falls (the Voice of the
Falls). East to Rainhold, north to Reedmere, west to the Broken March.

Also opens Reedmere's south pass onto the gorge. Reuses blackwater.py's
helpers (borders from the layout, the monster curve, npc/mob/quest/item) and
its merge, which edits only these entries in the shared data files. Rerun it
after changing anything here: it replaces what it wrote before.
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blackwater as bw  # noqa: E402

ROOT = bw.ROOT
bw.MOBS, bw.ITEMS, bw.NPCS, bw.QUESTS = {}, {}, {}, {}
# the monster curve reaches level 19; these two points come off shipped 20-24 monsters (griffons, river trolls, crocs)
bw.CURVE = bw.CURVE + [(21, 130, 21, 13, 25, 34), (23, 150, 21, 15, 28, 38)]
mob, item, drop, npc, quest, prop, borders = bw.mob, bw.item, bw.drop, bw.npc, bw.quest, bw.prop, bw.borders
NEUTRAL = "rainhold"  # the wardens of both camps answer to Rainhold, which takes neither side

# ---------------------------------------------------------------- items

# the Broken March
drop("march_wolf_pelt", "March Wolf Pelt", 14)
drop("boar_bristles", "Brambleback Bristles", 10)
drop("highwayman_token", "Marchreaver's Token", 18)
drop("grave_iron", "Grave-Iron Shard", 16)
drop("wyvern_scale", "Crag Wyvern Scale", 20)
item("corvels_signet", "Redhand Corvel's Signet", value=80, lore=True)
item("hollow_marshals_seal", "The Hollow Marshal's Seal", value=80, lore=True)
item("scythewings_talon", "Scythewing's Talon", value=80, lore=True)
# Stormcut Gorge
drop("gorge_croc_hide", "Gorge Crocodile Hide", 18)
drop("adder_venom_sac", "Canyon Adder Venom Sac", 16)
drop("stonefist_tusk", "Stonefist Troll Tusk", 20)
# griffon feathers are High Terrace's griffon_feather: the same bird, the same feather
drop("falls_essence", "Essence of the Falls", 22)
item("grukks_knuckle", "Chief Grukk's Knuckle-Bone", value=100, lore=True)
item("stormcrest_plume", "Stormcrest's Crest Plume", value=100, lore=True)
item("heart_of_the_cataract", "Heart of the Cataract", value=100, lore=True)
# rewards: the March 14-20, the Gorge 18-22
item("wardens_march_cloak", "Warden's March Cloak", slot="arms", ac=6, sta=2, agi=2, hp=15, value=1600, rec_level=15, no_drop=True,
     lore=True, wear="leather_sleeves")
item("reaverhide_boots", "Reaver-Hide Boots", slot="feet", ac=6, agi=3, sta=1, value=1700, rec_level=16, no_drop=True, lore=True,
     wear="leather_boots")
item("corvels_red_glove", "Corvel's Red Glove", slot="hands", ac=5, str=3, agi=2, value=2400, rec_level=17, no_drop=True, lore=True,
     wear="leather_gloves")
item("gravewardens_band", "Gravewarden's Band", slot="ring", ac=2, wis=2, int=2, mana=15, value=1800, rec_level=16, no_drop=True, lore=True)
item("marshals_broken_blade", "The Marshal's Broken Blade", slot="primary", dmg=13, delay=2.8, verb=["slash", "slashes"], model="sword_1handed",
     skill="1h_slashing", str=2, sta=2, value=3600, rec_level=18, no_drop=True, lore=True, classes=["warrior", "rogue", "ranger", "shaman"])
item("scythewing_charm", "Scythewing Talon Charm", slot="neck", ac=3, agi=3, str=2, hp=20, value=3200, rec_level=19, no_drop=True, lore=True)
item("ropewalkers_gloves", "Ropewalker's Gloves", slot="hands", ac=7, agi=3, str=2, value=2400, rec_level=19, no_drop=True, lore=True,
     wear="leather_gloves")
item("stonefist_girdle", "Stonefist Girdle", slot="waist", ac=8, str=4, sta=3, hp=25, value=4200, rec_level=21, no_drop=True, lore=True,
     wear="leather_belt")
item("griffon_feather_mantle", "Griffon-Feather Mantle", slot="arms", ac=8, agi=3, sta=2, hp=20, value=3000, rec_level=20, no_drop=True,
     lore=True, wear="leather_sleeves")
item("stormcrest_plumed_cap", "Stormcrest Plumed Cap", slot="head", ac=8, agi=3, wis=2, hp=25, value=4400, rec_level=21, no_drop=True,
     lore=True, wear="leather_cap")
item("cataract_pendant", "Cataract Pendant", slot="neck", ac=2, wis=3, int=3, mana=30, value=3000, rec_level=20, no_drop=True, lore=True)
item("stormcut_staff", "Stormcut Staff", slot="primary", dmg=14, delay=3.1, verb=["crush", "crushes"], model="staff", skill="2h_blunt",
     int=5, wis=5, mana=50, value=6000, rec_level=22, no_drop=True, lore=True,
     classes=["cleric", "wizard", "magician", "necromancer", "shaman"])


# ================================================================ THE BROKEN MARCH

POST = [20, 10]  # Marchwarden's Post, at the crossroads


def broken_march():
    passes, lines = borders("broken_march")
    L = [{"type": "outpost", "pos": POST},
         {"type": "camp", "pos": [POST[0] + 14, POST[1] + 8]},
         {"type": "signpost", "pos": [-202, 8], "face": [-224, 8], "labels": ["The Wallow"]},
         {"type": "signpost", "pos": [8, 202], "face": [8, 224], "labels": ["Duskwood"]},
         {"type": "signpost", "pos": [202, -8], "face": [224, -8], "labels": ["Stormcut Gorge", "Rainhold"]}]
    # the broken keep of the old war, north-west
    L.append({"type": "watchtower", "pos": [-130, -120]})
    L.append({"type": "ruins", "pos": [-100, -150]})
    L.append({"type": "ruins", "pos": [-160, -90]})
    for spot, face in [([-118, -96], [-130, -120]), ([-150, -140], [-130, -120])]:
        L.append(prop("fog_ruin_tower", spot, face=face, collide="mesh"))
    L.append(prop("tombstone_cluster", [-80, -110], collide="box"))
    L.append(prop("tombstone_cluster", [-95, -80], collide="box"))
    # the highwaymen's camp, south-west
    for spot in [[-140, 110], [-120, 130], [-155, 135]]:
        L.append(prop("tent", spot, face=[-135, 122], collide="box"))
    L.append(prop("campfire", [-135, 122], collide="none"))
    L.append(prop("banner_pole", [-112, 108], collide="box"))
    # the crags, north-east: the wyverns' rookery
    for spot in [[120, -130], [150, -110], [140, -160], [170, -140], [100, -165]]:
        L.append(prop("crag_rock", spot, collide="mesh"))
    # standing stones and cairns on the heath
    for spot in [[60, 120], [90, 150], [-40, 60], [150, 60]]:
        L.append(prop("standing_stone", spot, collide="box"))
    for spot in [[-20, -60], [110, 40], [-60, 170]]:
        L.append(prop("giant_cairn", spot, collide="box"))
    L = [l for l in L if l]
    npcs = [
        {"id": npc("marchwarden_hale", "Marchwarden Tomas Hale", NEUTRAL, "human", "knight", {
            "hail": "Welcome to the March, {name}, whoever sent you. Rainhold keeps this post for anyone who'll keep the peace: bog folk, cave folk, city folk. Our trouble is [wolves], [highwaymen] and the wyvern [Scythewing].",
            "wolves": "The march wolves run the heath in packs. Four pelts and I'll pay you, every time you bring them.",
            "highwaymen": "The Marchreavers. They camp in the south-west and rob everyone who crosses. Three of their tokens and I pay. Their leader, [Corvel], I want answered for.",
            "corvel": "Redhand Corvel. He wears a signet he cut off a Rainhold magistrate's finger. Bring it back to me.",
            "scythewing": "The great wyvern of the north-east crags. Bring me a talon and I'll see you're paid for the fright.",
            "unknown": "Ask Ossa about the dead. I only deal with the living."}, title="Warden of the March", weapon="sword_1handed", level=35),
         "pos": [POST[0] - 6, POST[1] + 10], "face": [POST[0] - 6, POST[1] + 30]},
        {"id": npc("gravekeeper_ossa", "Gravekeeper Ossa", NEUTRAL, "human", "necromancer", {
            "hail": "Both sides buried their dead in this ground, {name}, and neither buried them deep enough. The old keep in the north-west is full of the [restless].",
            "restless": "Soldiers of a war nobody remembers the reason for. Their armor rots, but the grave-iron in it doesn't. Three shards and I'll pay. Their [Marshal] rises at night.",
            "marshal": "The Hollow Marshal. He walks the keep after dark and still carries his seal of command. Bring it to me and the rest may finally lie down.",
            "unknown": "Ask the Marchwarden. He loves to talk."}, title="Keeper of the March Graves", weapon="staff", gender="female", level=35),
         "pos": [POST[0] + 8, POST[1] + 14], "face": [POST[0] + 8, POST[1] + 34]},
        {"id": npc("march_sutler", "Sutler Brannoc", NEUTRAL, "dwarf", "barbarian", {
            "hail": "Food, thread, arrows and a draught to get you home, {name}. Press G.", "unknown": "Buying or not?"},
            title="Sutler", weapon="axe_1handed", level=25, merchant={"sells": bw.SUPPLIES + ["crude_arrow", "sling_stone"], "buy_rate": 0.5}),
         "pos": [POST[0] + 18, POST[1] - 2], "face": [POST[0] + 18, POST[1] + 20]},
    ]
    F = {NEUTRAL: 10}
    quest("march_pelts", "Wolves of the March", "marchwarden_hale", {"march_wolf_pelt": 4}, 900, 150, "wardens_march_cloak",
          "You have taken on a task: Wolves of the March. Bring Marchwarden Hale four march wolf pelts.",
          "Pelts? Let's see them.", "Four fewer wolves on the road.", "Take this cloak. Wardens wear them; you've earned one.",
          dict(F), keyword="wolves", repeatable=True)
    quest("march_tokens", "The Marchreavers", "marchwarden_hale", {"highwayman_token": 3}, 1100, 200, "reaverhide_boots",
          "You have taken on a task: The Marchreavers. Bring Marchwarden Hale three Marchreaver's tokens.",
          "Tokens. Good.", "Three reavers who won't rob anyone again.", "Their own boots. Fitting, I think.",
          {NEUTRAL: 15, "marchreavers": -10}, keyword="highwaymen", repeatable=True)
    quest("march_corvel", "Redhand Corvel", "marchwarden_hale", {"corvels_signet": 1}, 2600, 600, "corvels_red_glove",
          "You have taken on a task: Redhand Corvel. Bring Marchwarden Hale Corvel's signet.",
          "The magistrate's signet!", "Rainhold will want this back. The March is quieter already.", "His red glove. Wash it first.",
          {NEUTRAL: 30, "marchreavers": -30}, keyword="corvel")
    quest("march_scythewing", "Scythewing", "marchwarden_hale", {"scythewings_talon": 1}, 3000, 700, "scythewing_charm",
          "You have taken on a task: Scythewing. Bring Marchwarden Hale one of Scythewing's talons.",
          "That talon's as long as my arm.", "The crags are ours again, for a while.", "Wear it on a cord. Wyverns will know.",
          {NEUTRAL: 25}, keyword="scythewing")
    quest("march_grave_iron", "Grave-Iron", "gravekeeper_ossa", {"grave_iron": 3}, 1000, 180, "gravewardens_band",
          "You have taken on a task: Grave-Iron. Bring Gravekeeper Ossa three grave-iron shards.",
          "Grave-iron. Careful, it's cold.", "Three soldiers who can rest.", "I bent a band from the first of it. Wear it.",
          dict(F), keyword="restless", repeatable=True)
    quest("march_marshal", "The Hollow Marshal", "gravekeeper_ossa", {"hollow_marshals_seal": 1}, 2800, 650, "marshals_broken_blade",
          "You have taken on a task: The Hollow Marshal. Bring Gravekeeper Ossa the Hollow Marshal's seal.",
          "His seal. You fought him in the dark?", "The keep will be quieter tonight.", "His blade broke on your armor, maybe. It still cuts.",
          {NEUTRAL: 25}, keyword="marshal")
    mob("march_wolf", "a march wolf", (14, 16), "moor_wolf", loot=[("march_wolf_pelt", 0.55), ("raw_meat", 0.3)], social=True, speed=7.0)
    mob("brambleback_boar", "a brambleback boar", (14, 16), "boar", verb=("gore", "gores"), loot=[("boar_bristles", 0.5), ("raw_meat", 0.4)],
        aggressive=False)
    mob("marchreaver_cutthroat", "a Marchreaver cutthroat", (15, 17), "brigand", faction="marchreavers", verb=("slash", "slashes"),
        social=True, loot=[("highwayman_token", 0.5)], coin=(20, 80), extra={"weapon": "dagger"})
    mob("marchreaver_bowman", "a Marchreaver bowman", (15, 17), "brigand", faction="marchreavers", verb=("shoot", "shoots"),
        social=True, loot=[("highwayman_token", 0.5)], coin=(20, 80), extra={"weapon": "bow"})
    mob("restless_soldier", "a restless march-soldier", (16, 18), "skeleton_warrior", faction="undead", verb=("hack", "hacks"),
        loot=[("grave_iron", 0.5), ("bone_chips", 0.4)], coin=(10, 50))
    mob("restless_knight", "a restless march-knight", (17, 19), "skeleton_knight", faction="undead", verb=("slash", "slashes"),
        loot=[("grave_iron", 0.6), ("bone_chips", 0.3)], coin=(15, 60))
    mob("crag_wyvern", "a crag wyvern", (18, 20), "moor_wyvern", verb=("rake", "rakes"), loot=[("wyvern_scale", 0.5)])
    mob("redhand_corvel", "Redhand Corvel", (18, 18), "brigand_captain", faction="marchreavers", verb=("slash", "slashes"), social=True,
        named=True, loot=[("corvels_signet", 1.0)], coin=(200, 500), extra={"weapon": "sword_1handed"})
    mob("hollow_marshal", "the Hollow Marshal", (19, 19), "skeleton_knight", faction="undead", verb=("cleave", "cleaves"), named=True,
        loot=[("hollow_marshals_seal", 1.0), ("grave_iron", 1.0)], coin=(200, 550), scale=1.3)
    mob("scythewing", "Scythewing", (20, 20), "moor_wyvern", verb=("rake", "rakes"), named=True, loot=[("scythewings_talon", 1.0)],
        scale=1.45)
    spawns = []

    def spawn(pool, spots, respawn=90, wander=14, when=None):
        for s in spots:
            e = {"pos": s, "pool": pool, "respawn": respawn, "wander": wander}
            if when:
                e["when"] = when
            spawns.append(e)
    spawn({"march_wolf": 1}, [[60, 90], [100, 130], [140, 100], [30, 160], [170, 40], [-40, 100]], 75, 18)
    spawn({"brambleback_boar": 1}, [[80, 60], [130, 150], [-20, 140], [180, 120], [50, -40]], 70, 12)
    spawn({"marchreaver_cutthroat": 2, "marchreaver_bowman": 1}, [[-130, 100], [-150, 125], [-115, 140], [-165, 105], [-100, 120]], 100, 8)
    spawn({"restless_soldier": 2, "restless_knight": 1}, [[-120, -110], [-140, -130], [-100, -140], [-150, -100], [-90, -100]], 110, 10)
    spawn({"restless_soldier": 1}, [[-70, -120], [-110, -70], [-160, -160]], 110, 12, "night")
    spawn({"crag_wyvern": 1}, [[120, -115], [150, -130], [130, -165], [165, -160], [95, -145]], 120, 12)
    spawn({"redhand_corvel": 1}, [[-138, 118]], 1200, 4)
    spawn({"hollow_marshal": 1}, [[-130, -118]], 1500, 6, "night")
    spawn({"scythewing": 1}, [[145, -145]], 1500, 8)
    return {"name": "The Broken March", "levels": [14, 20], "music": "broken_march", "seed": 7361, "size": 448, "bind_point": [POST[0], POST[1] + 20],
            "height_amplitude": 7.0, "flat_radius": 22, "trees": 60,
            "tree_mix": [bw.art("wind_bent_tree") or "pine_a", "pine_a", bw.art("wind_bent_tree") or "pine_b", "lone_tree"],
            "groves": 0.2, "rocks": 90, "grass_colors": ["#6a6a44", "#7a7050"], "fog_density": 0.006, "fog_color": "#a4a494",
            "sun_energy": 0.85, "passes": passes, "zone_lines": lines,
            "roads": [{"points": [[-224, 0], [-120, 10], [-40, 0], [POST[0], POST[1]], [120, -10], [224, 0]], "width": 3.2},
                      {"points": [[POST[0], POST[1]], [10, 80], [0, 160], [0, 224]], "width": 3.0}],
            "clutter": {"grass_a": {"density": 0.28, "patch": 0.5, "sway": 0.3, "range": 55, "tint": "ground", "scale": [0.8, 1.2]},
                        "heather": {"density": 0.05, "patch": 0.7, "sway": 0.12, "range": 55, "scale": [0.8, 1.3]}},
            "landmarks": L, "npcs": npcs, "spawns": spawns}


# ================================================================ STORMCUT GORGE

WATCH = [140, 24]  # the Cutwatch, by the road in from Rainhold
RIVER_BENDS = [[40, 196], [24, 120], [-6, 40], [0, -40], [-40, -120], [-60, -186]]  # downstream: off the south falls, north toward Reedmere


def _dense(pts, step=16.0):
    """A point every `step` m along a course: a river's level is set at each
    point and drawn straight between them, so on hilly ground a sparse course
    leaves the water hanging over the dips."""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) // step))
        for k in range(1, n + 1):
            out.append([round(a[0] + (b[0] - a[0]) * k / n, 1), round(a[1] + (b[1] - a[1]) * k / n, 1)])
    return out


RIVER = _dense(RIVER_BENDS)


def stormcut_gorge():
    passes, lines = borders("stormcut_gorge")
    L = [{"type": "outpost", "pos": WATCH},
         {"type": "camp", "pos": [WATCH[0] - 14, WATCH[1] + 10]},
         {"type": "signpost", "pos": [202, 8], "face": [224, 8], "labels": ["Rainhold"]},
         {"type": "signpost", "pos": [-202, -8], "face": [-224, -8], "labels": ["The Broken March"]},
         {"type": "signpost", "pos": [12, -202], "face": [12, -224], "labels": ["Reedmere"]},
         {"type": "bridge", "pos": [-5, 0], "face": [60, 0]}]
    # the falls: the river's head in the south cliff, and two more off the canyon walls
    for pos, yaw in [([40, 206], 180), ([-196, -70], 90), ([198, 110], -90)]:
        L.append({"type": "prop", "pos": pos, "id": "waterfall", "yaw": yaw, "collide": "mesh"})
        L.append({"type": "prop", "pos": pos, "id": "waterfall_water", "yaw": yaw, "collide": "none"})
    # the canyon walls: a line of mesas (20 m across, 11 high) down both sides and across the south, crags in the gaps,
    # open where the roads come through (west and east at z 0) and where the falls spill
    for side in (-1, 1):
        for z in range(-190, 200, 34):
            if abs(z) < 34 or (side == -1 and abs(z + 70) < 20) or (side == 1 and abs(z - 110) < 20):
                continue
            x = side * (186 + (z * 7) % 9)
            L.append(prop("mesa" if (z // 34) % 2 == 0 else "crag_rock", [x, z], collide="mesh", yaw=(z * 37) % 360))
    for x in range(-150, 170, 36):
        if abs(x - 40) < 22:
            continue  # the south falls
        L.append(prop("mesa" if (x // 36) % 2 == 0 else "crag_rock", [x, 196 + (x * 5) % 8], collide="mesh", yaw=(x * 53) % 360))
    for spot in [[110, -120], [140, -140], [125, -170], [160, -110]]:  # the griffons' crags
        L.append(prop("crag_rock", spot, collide="mesh"))
    # the Stonefist trolls' camp on the west bank
    for spot in [[-110, 90], [-135, 70], [-95, 115]]:
        L.append(prop("troll_hut", spot, face=[-115, 95], collide="mesh"))
    L.append(prop("campfire", [-115, 95], collide="none"))
    L = [l for l in L if l]
    npcs = [
        {"id": npc("ropewarden_mbeki", "Ropewarden Kofi Mbeki", NEUTRAL, "human", "ranger_class", {
            "hail": "Mind the edge, {name}. The Cutwatch keeps the gorge road open for Rainhold, and it isn't easy. The [trolls] want the river, the [griffons] want everything else.",
            "trolls": "The Stonefist trolls on the west bank. Three of their tusks and I'll pay, as often as you bring them. Their chief, [Grukk], wears a knuckle-bone for a charm; bring me that.",
            "grukk": "Chief Grukk Stonefist. The biggest troll in the camp across the river.",
            "griffons": "They nest on the crags to the north-east and take our goats and our scouts. Four feathers and I pay. The great one is [Stormcrest].",
            "stormcrest": "A griffon as big as a boat, crest like a storm cloud. Bring me that crest plume.",
            "unknown": "Ask Lirien. She talks to the water."}, title="Ropewarden of the Cutwatch", weapon="bow", level=35),
         "pos": [WATCH[0] - 8, WATCH[1] + 12], "face": [WATCH[0] - 8, WATCH[1] + 32]},
        {"id": npc("tidepriestess_lirien", "Tidepriestess Lirien", NEUTRAL, "high_elf", "mage", {
            "hail": "Jalendra's water falls three times into this gorge, {name}, and something has woken in it. The [spirits] of the falls are angry.",
            "spirits": "Water spirits, risen from the falls. Their essence is holy to Jalendra; bring me three and I'll pay each time. What woke them is the [Voice].",
            "voice": "The Voice of the Falls, at the great cascade in the south. Bring me its heart and the water will be still again.",
            "unknown": "The water knows. I only listen."}, title="Priestess of Jalendra", weapon="staff", gender="female", level=35),
         "pos": [WATCH[0] + 6, WATCH[1] + 16], "face": [WATCH[0] + 6, WATCH[1] + 36]},
    ]
    F = {NEUTRAL: 10}
    quest("gorge_tusks", "Stonefist Tusks", "ropewarden_mbeki", {"stonefist_tusk": 3}, 1400, 250, "ropewalkers_gloves",
          "You have taken on a task: Stonefist Tusks. Bring Ropewarden Mbeki three Stonefist troll tusks.",
          "Tusks. Heavy ones.", "Three trolls who won't foul the river.", "Ropewalker's gloves. You'll want them on the bridges.",
          {NEUTRAL: 15, "stonefist_trolls": -10}, keyword="trolls", repeatable=True)
    quest("gorge_grukk", "Chief Grukk Stonefist", "ropewarden_mbeki", {"grukks_knuckle": 1}, 3600, 800, "stonefist_girdle",
          "You have taken on a task: Chief Grukk Stonefist. Bring Ropewarden Mbeki Chief Grukk's knuckle-bone.",
          "Grukk's charm!", "The camp will fight over his place for a season. Good.", "His girdle. Trolls make good leather, it turns out.",
          {NEUTRAL: 30, "stonefist_trolls": -30}, keyword="grukk")
    quest("gorge_feathers", "Griffon Feathers", "ropewarden_mbeki", {"griffon_feather": 4}, 1500, 260, "griffon_feather_mantle",
          "You have taken on a task: Griffon Feathers. Bring Ropewarden Mbeki four griffon feathers.",
          "Feathers. The fletchers will be pleased.", "Four griffons fewer over our goats.", "A mantle of their feathers. Light as rain.",
          dict(F), keyword="griffons", repeatable=True)
    quest("gorge_stormcrest", "Stormcrest", "ropewarden_mbeki", {"stormcrest_plume": 1}, 4000, 900, "stormcrest_plumed_cap",
          "You have taken on a task: Stormcrest. Bring Ropewarden Mbeki Stormcrest's crest plume.",
          "The plume! It still crackles.", "The north-east crags are quiet.", "Wear it. Every griffon in the Monsoon will know what you did.",
          {NEUTRAL: 25}, keyword="stormcrest")
    quest("gorge_essence", "Spirits of the Falls", "tidepriestess_lirien", {"falls_essence": 3}, 1500, 260, "cataract_pendant",
          "You have taken on a task: Spirits of the Falls. Bring Tidepriestess Lirien three essences of the falls.",
          "Essence. It's still cold.", "Three spirits at rest.", "Jalendra's pendant. The water will know you.",
          dict(F), keyword="spirits", repeatable=True)
    quest("gorge_voice", "The Voice of the Falls", "tidepriestess_lirien", {"heart_of_the_cataract": 1}, 4200, 950, "stormcut_staff",
          "You have taken on a task: The Voice of the Falls. Bring Tidepriestess Lirien the Heart of the Cataract.",
          "The heart. Gently, {name}.", "Listen: the falls have gone quiet.", "A staff cut from the gorge's own stone. It hums when it rains.",
          {NEUTRAL: 30}, keyword="voice")
    mob("canyon_adder", "a canyon adder", (18, 19), "cobra", verb=("bite", "bites"), loot=[("adder_venom_sac", 0.5)], aggressive=False,
        extra={"proc": {"spell": "cobra_venom", "chance": 0.12, "text": "%s's fangs sink %s into you!"}})
    mob("gorge_croc", "a gorge crocodile", (19, 21), "river_croc", verb=("bite", "bites"), loot=[("gorge_croc_hide", 0.5), ("raw_meat", 0.3)])
    mob("stonefist_troll", "a Stonefist troll", (19, 21), "mountain_troll", faction="stonefist_trolls", verb=("smash", "smashes"), social=True,
        loot=[("stonefist_tusk", 0.5)], coin=(25, 90), extra={"hp_regen": 14})
    mob("stonefist_shaman", "a Stonefist mudcaller", (19, 21), "river_troll", faction="stonefist_trolls", verb=("strike", "strikes"),
        social=True, loot=[("stonefist_tusk", 0.5)], coin=(25, 95), extra={"hp_regen": 14})
    mob("gorge_griffon", "a gorge griffon", (20, 22), "griffon", verb=("rake", "rakes"), loot=[("griffon_feather", 0.55)])
    mob("falls_spirit", "a spirit of the falls", (20, 22), "water_elemental", faction="wildlife", verb=("crash", "crashes"),
        loot=[("falls_essence", 0.5)], aggressive=True)
    mob("chief_grukk", "Chief Grukk Stonefist", (22, 22), "troll_chieftain", faction="stonefist_trolls", verb=("smash", "smashes"),
        social=True, named=True, loot=[("grukks_knuckle", 1.0)], coin=(250, 650), extra={"hp_regen": 30})
    mob("stormcrest", "Stormcrest", (22, 22), "griffon_matriarch", verb=("rake", "rakes"), named=True, loot=[("stormcrest_plume", 1.0)])
    mob("voice_of_the_falls", "the Voice of the Falls", (22, 22), "water_elemental", faction="wildlife", verb=("crash", "crashes"),
        named=True, loot=[("heart_of_the_cataract", 1.0), ("falls_essence", 1.0)], scale=1.6)
    spawns = []

    def spawn(pool, spots, respawn=100, wander=14, when=None):
        for s in spots:
            e = {"pos": s, "pool": pool, "respawn": respawn, "wander": wander}
            if when:
                e["when"] = when
            spawns.append(e)
    spawn({"canyon_adder": 1}, [[60, 60], [90, -40], [-60, 20], [40, -90], [70, 150], [-30, -160]], 80, 12)
    spawn({"gorge_croc": 1}, [[24, 110], [-2, 60], [-10, -60], [-40, -110], [-55, -170], [14, 150]], 100, 10)
    spawn({"stonefist_troll": 2, "stonefist_shaman": 1}, [[-110, 80], [-130, 100], [-100, 120], [-140, 60], [-90, 90]], 110, 8)
    spawn({"gorge_griffon": 1}, [[115, -110], [145, -130], [120, -160], [160, -100], [95, -140]], 120, 14)
    spawn({"falls_spirit": 1}, [[40, 180], [20, 170], [60, 170], [-180, -70], [180, 110]], 120, 10)
    spawn({"falls_spirit": 1}, [[0, 130], [30, 140]], 120, 12, "night")
    spawn({"chief_grukk": 1}, [[-118, 96]], 1500, 4)
    spawn({"stormcrest": 1}, [[135, -150]], 1500, 8)
    spawn({"voice_of_the_falls": 1}, [[40, 188]], 1500, 4)
    return {"name": "Stormcut Gorge", "levels": [18, 22], "music": "stormcut_gorge", "seed": 7371, "size": 448,
            "bind_point": [WATCH[0], WATCH[1] + 20], "height_amplitude": 4.5, "flat_radius": 22, "trees": 150,
            "tree_mix": ["jungle_tree", "pine_a", "jungle_tree", "pine_b"], "groves": 0.45, "rocks": 80,
            "grass_colors": ["#3e5a3a", "#4a6a40"], "fog_density": 0.012, "fog_color": "#7a8a8a", "sun_energy": 0.65,
            "rain": {"amount": 2600}, "passes": passes, "zone_lines": lines,
            "rivers": [{"points": RIVER, "width": 10, "depth": 1.4, "bank": 12, "flow": 1.2}],
            "roads": [{"points": [[-224, 0], [-120, 6], [-5, 0], [60, 10], [WATCH[0], WATCH[1]], [224, 0]], "width": 3.2},
                      {"points": [[60, 10], [40, -80], [20, -160], [12, -224]], "width": 3.0}],
            "fish": {"mud_carp": 4, "monsoon_eel": 2, "lagoon_snapper": 2},
            "clutter": {"grass_b": {"density": 0.3, "patch": 0.5, "sway": 0.2, "range": 55, "tint": "ground", "scale": [0.8, 1.3]},
                        "fern": {"density": 0.05, "patch": 0.8, "sway": 0.1, "range": 50, "scale": [0.9, 1.6]}},
            "landmarks": L, "npcs": npcs, "spawns": spawns}


# ================================================================ REEDMERE's south pass

def reedmere():
    path = f"{ROOT}/data/zones/reedmere.json"
    z = json.load(open(path))
    z["passes"], z["zone_lines"] = borders("reedmere")
    signs = [l for l in z["landmarks"] if not (l["type"] == "signpost" and l.get("labels") == ["Stormcut Gorge"])]
    signs.append({"type": "signpost", "pos": [12, 232], "face": [12, 256], "labels": ["Stormcut Gorge"]})  # holds the pass's ground level
    z["landmarks"] = signs
    json.dump(z, open(path, "w"), indent=2)
    open(path, "a").write("\n")


def factions():
    path = f"{ROOT}/data/factions.json"
    t = open(path).read()
    add = {
        "marchreavers": {"name": "The Marchreavers", "default": -800, "kos_at": -750, "on_kill": {"marchreavers": -10, "rainhold": 2}},
        "stonefist_trolls": {"name": "The Stonefist Trolls", "default": -800, "kos_at": -750, "on_kill": {"stonefist_trolls": -10, "rainhold": 2}},
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
    zones = {"broken_march": broken_march(), "stormcut_gorge": stormcut_gorge()}
    for zid, z in zones.items():
        with open(f"{ROOT}/data/zones/{zid}.json", "w") as f:
            f.write(json.dumps(z, indent=2) + "\n")
    reedmere()
    bw.merge(f"{ROOT}/data/npcs.json", bw.NPCS)
    bw.merge(f"{ROOT}/data/mobs.json", bw.MOBS)
    bw.merge(f"{ROOT}/data/quests.json", bw.QUESTS)
    with open(f"{ROOT}/data/items/west_march.json", "w") as f:
        f.write(json.dumps(bw.ITEMS, indent=2) + "\n")
    factions()
    missing = [l["id"] for z in zones.values() for l in z["landmarks"] if l.get("type") == "prop" and l["id"] not in bw.MODELS["props"]]
    models = set(bw.MODELS["characters"])
    bad = sorted({m["model"] for m in bw.MOBS.values() if m["model"] not in models} | {n["model"] for n in bw.NPCS.values() if n["model"] not in models})
    print("wrote %s; %d npcs, %d mobs, %d quests, %d items%s%s" % (", ".join(zones), len(bw.NPCS), len(bw.MOBS), len(bw.QUESTS), len(bw.ITEMS),
          "; MISSING props: %s" % sorted(set(missing)) if missing else "", "; UNKNOWN models: %s" % bad if bad else ""))


if __name__ == "__main__":
    main()
