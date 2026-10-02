"""Writes The Tuskway (2026-10-01): the old pilgrims' road, levels 9-14.

    python3 tools/zones/the_tuskway.py

The Emberlands' cell between Harrowfield and Dewstep, under Sunward Steps:
Dewstep's way out (it had none but Lanternhold, into Sunward Steps at 14) and
Harrowfield's road east. An ancient pilgrim road climbs a valley of red earth
and bamboo toward the Dawn-Tusk's shrines in Sunward Steps, lined with great
weathered stone elephants. The pilgrims stopped coming when bandits took it.

The Old Caravanserai at the crossroads (the Dawn pilgrims hold it again: a
keeper, a priest of the Dawn-Tusk, a huntress, a herbalist who sells, a
warden), the Dawnward Watch near the north end (a scout who takes the far
quests' hand-ins, a sutler, a sentry), a guard hut on the west road; bamboo
monkeys stealing offerings and red-earth jackals by the two ends, road beetles
and king cobras in the groves, striped tigers in the north-west bamboo
(Saffronclaw), the Ochre Hand's wagon camp south-west (Captain Rhaz
Ochrehand), and at the Fallen Tusk, the greatest statue lying broken, the
restless pilgrims at night (the Lost Abbess).

Also opens Harrowfield's east pass, Dewstep's west pass and Sunward Steps'
south pass onto it. Reuses blackwater.py's helpers (borders from the layout,
the monster curve, npc/mob/quest/item and the text merge). Rerun it after
changing anything here: it replaces what it wrote before. Then run
tools/zones/outline.py.
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blackwater as bw  # noqa: E402
import scale_zone  # noqa: E402  (its dumps(): the zone files' own layout, so a rewrite changes only what changed)

ROOT = bw.ROOT
bw.MOBS, bw.ITEMS, bw.NPCS, bw.QUESTS = {}, {}, {}, {}
mob, item, drop, npc, quest, prop, borders = bw.mob, bw.item, bw.drop, bw.npc, bw.quest, bw.prop, bw.borders
ZID = "the_tuskway"
F = "dawn_pilgrims"
HALF = 336
CAMP = [10, 40]          # the Old Caravanserai, at the crossroads
WATCH = [-50, -230]      # the Dawnward Watch, near the north end
WATCH_FACE = [-5, -232]
HUT = [-170, 52]         # a guard hut on the west road
TUSK = [170, -150]       # the Fallen Tusk
OCHRE = [-170, 170]      # the Ochre Hand's camp
GROVE = [-200, -160]     # the tigers' bamboo
ROAD_MAIN = [[-HALF, 0], [-250, 8], [-150, 30], [-60, 36], CAMP, [50, -20], [40, -120], [10, -200], [-10, -270], [0, -HALF]]
ROAD_EAST = [CAMP, [100, 55], [200, 30], [280, 8], [HALF, 0]]
ROAD_TUSK = [[40, -120], [100, -140], [TUSK[0] - 18, TUSK[1] + 6]]

# ---------------------------------------------------------------- items

drop("tw_stolen_offering", "Stolen Pilgrim's Offering", 8)
drop("tw_red_jackal_hide", "Red-Earth Jackal Hide", 9)
drop("tw_road_beetle_shell", "Road Beetle Shell", 10)
drop("tw_king_cobra_fang", "King Cobra Fang", 12)
drop("tw_striped_pelt", "Striped Tiger Pelt", 14)
drop("tw_ochre_token", "Ochre Hand Token", 14)
drop("tk_prayer_bead", "Pilgrim's Prayer Bead", 12)
item("tw_saffronclaws_pelt", "Saffronclaw's Pelt", value=60, lore=True)
item("tw_rhaz_seal", "Captain Rhaz's Ochre Seal", value=60, lore=True)
item("tw_abbess_wheel", "The Lost Abbess's Prayer Wheel", value=60, lore=True)
for iid, src in [("tw_stolen_offering", "elephant_charm"), ("tw_red_jackal_hide", "jackal_pelt"), ("tw_road_beetle_shell", "rice_beetle_shell"),
                 ("tw_king_cobra_fang", "cobra_fang"), ("tw_striped_pelt", "tiger_pelt"), ("tw_ochre_token", "highwayman_token"),
                 ("tk_prayer_bead", "bone_chips"), ("tw_saffronclaws_pelt", "tiger_pelt"), ("tw_rhaz_seal", "corvels_signet"),
                 ("tw_abbess_wheel", "lantern_widows_lamp")]:
    if os.path.exists(f"{ROOT}/assets/icons/{src}.png"):
        bw.ITEMS[iid]["icon"] = src


def reward(iid, name, level, slot, stats, **kw):
    """A quest reward for its level, on the same straight line hubs.py's are (tools/item_curve.py checks it)."""
    L = level
    per = {"chest": 0.8, "legs": 0.62, "head": 0.48, "ring": 0.16, "neck": 0.16}.get(slot, 0.3)  # the big pieces carry more armor
    ac = round(per * L) + 1
    big = 1.5 if slot in ("chest", "legs", "head") else 1.0
    d = {"slot": slot, "ac": ac, stats[0]: round(L / 6.5 * big) + 1, stats[1]: round(L / 8 * big) + 1, "hp": round(L * 1.1 * big) + 4,
         "value": L * L * 12, "rec_level": L, "no_drop": True, "lore": True}
    d.update(kw)
    return item(iid, name, **d)


reward("tw_pilgrims_sandals", "Pilgrim's Sandals", 10, "feet", ("agi", "sta"), wear="sandals")
reward("tw_roadwardens_belt", "Roadwarden's Belt", 11, "waist", ("str", "sta"), wear="leather_belt")
reward("tw_ochre_cloak", "Cloak of the Ochre Road", 12, "arms", ("agi", "sta"), wear="leather_sleeves")
item("tw_rhaz_saber", "Rhaz's Curved Saber", slot="primary", dmg=10, delay=2.6, verb=["slash", "slashes"], model="sword_1handed",
     skill="1h_slashing", str=2, agi=2, hp=12, value=2600, rec_level=14, no_drop=True, lore=True,
     classes=["warrior", "rogue", "ranger", "shaman"])
reward("tw_bead_necklace", "Pilgrim's Bead Necklace", 12, "neck", ("wis", "int"), mana=20)
reward("tw_abbess_ring", "The Abbess's Ring", 14, "ring", ("wis", "int"), mana=25)
reward("tw_tigerhide_sleeves", "Tigerhide Sleeves", 12, "arms", ("str", "agi"), wear="leather_sleeves")
reward("tw_saffron_mantle", "Saffron Mantle", 14, "chest", ("agi", "sta"), wear="leather_tunic")
reward("tw_snake_charmers_gloves", "Snake-Charmer's Gloves", 12, "hands", ("agi", "wis"), wear="leather_gloves")
reward("tw_beetle_shell_cap", "Beetle-Shell Cap", 11, "head", ("sta", "str"), wear="leather_cap")


# ---------------------------------------------------------------- the zone

def _along(path, every, off, start=40.0):
    """Points every `every` m along a polyline, `off` m to alternating sides, each facing the road."""
    out = []
    seg_lens = [math.dist(a, b) for a, b in zip(path, path[1:])]
    total = sum(seg_lens)
    d, side = start, 1
    while d < total - 30:
        rem, i = d, 0
        while rem > seg_lens[i]:
            rem -= seg_lens[i]
            i += 1
        a, b = path[i], path[i + 1]
        t = rem / seg_lens[i]
        p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
        nx, nz = -(b[1] - a[1]) / seg_lens[i], (b[0] - a[0]) / seg_lens[i]
        out.append(([p[0] + nx * off * side, p[1] + nz * off * side], p))
        d += every
        side = -side
    return out


def guard_npc(nid, name, title):
    return npc(nid, name, F, "human", "knight", {"hail": "The road's open again, {name}, as long as we hold it.", "unknown": "Ask at the Caravanserai."},
               title=title, weapon="sword_1handed", level=35,
               guard=dict(bw.GUARD, shouts=["Hold, {name}!", "For the Dawn-Tusk!"], hunt_shouts=["Not on this road!"],
                          shouts_player=["Halt, {name}!"]), combat=dict(bw.GUARD_COMBAT))


def the_tuskway():
    passes, lines = borders(ZID)
    L = []
    # the road's stone elephants, every 70 m, alternating sides, facing the road; the north end's last ones larger
    for k, (spot, road_at) in enumerate(_along(ROAD_MAIN, 70, 14)):
        L.append(prop("elephant_statue", spot, face=road_at, collide="box", scale=1.6 if k % 3 else 1.9))
    for spot, road_at in _along(ROAD_EAST, 80, 13, 60):
        L.append(prop("elephant_statue", spot, face=road_at, collide="box", scale=1.5))
    for spot, road_at in _along(ROAD_MAIN, 35, 6, 20)[::2]:
        L.append(prop("stone_lantern", spot, face=road_at, collide="box"))
    # the Old Caravanserai: a walled yard of shelters round a stupa, half fallen
    L.append({"type": "waystation", "pos": CAMP, "face": [CAMP[0], CAMP[1] + 40]})
    for dx, dz, yaw in [(-22, -10, 90), (22, -10, 270), (-22, 14, 90)]:
        L.append(prop("pilgrim_shelter", [CAMP[0] + dx, CAMP[1] + dz], collide="mesh", yaw=yaw))
    L.append(prop("stupa", [CAMP[0] + 4, CAMP[1] - 26], collide="box"))
    L.append(prop("temple_arch_ruin", [CAMP[0] - 30, CAMP[1] - 2], collide="mesh", yaw=90))
    L.append(prop("temple_arch_ruin", [CAMP[0] + 30, CAMP[1] + 4], collide="mesh", yaw=270))
    L.append(prop("caravan_wagon", [CAMP[0] + 18, CAMP[1] + 22], collide="box", yaw=30))
    L.append(prop("pilgrim_brazier", [CAMP[0] - 6, CAMP[1] + 2], collide="box"))
    L.append(prop("well", [CAMP[0] + 10, CAMP[1] - 6], collide="box"))
    L.append(prop("broken_pillar", [CAMP[0] - 26, CAMP[1] + 30], collide="mesh"))
    # the Dawnward Watch
    L.append({"type": "waystation", "pos": WATCH, "face": WATCH_FACE})
    L.append(prop("scout_tent", [WATCH[0] - 10, WATCH[1] - 4], collide="box", yaw=45))
    L.append(prop("campfire", [WATCH[0] + 2, WATCH[1] + 6], collide="none"))
    # the guard hut on the west road
    L.append({"type": "outpost", "pos": HUT})
    # the Fallen Tusk: the greatest statue, broken, with a ring of lanterns gone cold
    L.append({"type": "ruins", "pos": [TUSK[0] + 30, TUSK[1] - 28]})  # behind it, seen from the road
    L.append(prop("fallen_elephant_statue", TUSK, collide="mesh", yaw=30, scale=1.3))
    for k in range(6):
        a = k * math.tau / 6
        L.append(prop("stone_lantern", [TUSK[0] + math.cos(a) * 22, TUSK[1] + math.sin(a) * 22], face=TUSK, collide="box"))
    L.append(prop("shrine_broken", [TUSK[0] + 26, TUSK[1] - 14], collide="box"))
    # the Ochre Hand's camp: wagons and tents, a fire in the middle
    L.append({"type": "camp", "pos": OCHRE, "style": "wagons", "size": 1.8})
    # the tigers' bamboo, north-west: a dense stand and a few old statues lost in it
    L.append(prop("elephant_statue", [GROVE[0] + 30, GROVE[1] + 20], face=[GROVE[0] + 40, GROVE[1] + 60], collide="box", scale=1.4))
    L.append(prop("broken_pillar", [GROVE[0] - 20, GROVE[1] + 30], collide="mesh"))
    # thick stands of bamboo where the tigers and cobras live (the zone's own trees are scattered)
    import random
    rng = random.Random(9142)
    for c, r, n in [(GROVE, 60, 34), ([-120, -80], 26, 10), ([-60, -150], 26, 10), ([120, 180], 26, 10), ([200, 180], 26, 10), ([-250, 60], 22, 6)]:
        for k in range(n):
            a = rng.uniform(0, math.tau)
            d = r * math.sqrt(rng.random())
            L.append(prop("bamboo_clump" if rng.random() < 0.75 else "bamboo_clump_b", [c[0] + math.cos(a) * d, c[1] + math.sin(a) * d],
                          collide="trunk", yaw=rng.randint(0, 359), scale=round(rng.uniform(0.85, 1.25), 2)))
    # signposts: they hold the passes' ground level (an opened pass can come back a ridge otherwise)
    L.append({"type": "signpost", "pos": [-HALF + 22, 10], "face": [-HALF, 10], "labels": ["Harrowfield"]})
    L.append({"type": "signpost", "pos": [HALF - 22, 10], "face": [HALF, 10], "labels": ["Dewstep", "Lanternhold"]})
    L.append({"type": "signpost", "pos": [10, -HALF + 22], "face": [10, -HALF], "labels": ["Sunward Steps"]})
    L.append({"type": "signpost", "pos": [CAMP[0] - 14, CAMP[1] - 18], "face": [CAMP[0] - 30, CAMP[1] - 18], "labels": ["The Old Caravanserai"]})
    L = [l for l in L if l]

    def at(base, dx, dz):
        return [base[0] + dx, base[1] + dz]
    npcs = [
        {"id": npc("tw_keeper_anvesha", "Keeper Anvesha", F, "human", "barbarian", {
            "hail": "Welcome to the Old Caravanserai, {name}. A hundred years of pilgrims slept under this roof on the way to the Dawn-Tusk's shrines. We've opened it again, and the road's trouble came to the door: [monkeys] and [jackals].",
            "monkeys": "Bamboo monkeys. They snatch the offerings pilgrims leave at the statues. Four back and I'll pay you, every time.",
            "jackals": "The red-earth jackals hunt the road's ends. Four hides and I'll pay; we patch the shelters with them.",
            "unknown": "Ask Brother Kesav about the shrines, Huntress Devi about the bamboo, or the Warden about the bandits."},
            title="Keeper of the Caravanserai", weapon="", gender="female", level=30), "pos": at(CAMP, -8, 8), "face": at(CAMP, -8, 30)},
        {"id": npc("tw_brother_kesav", "Brother Kesav", F, "human", "mage", {
            "hail": "The Dawn-Tusk watches this road, {name}, in every stone elephant along it. North-east lies the greatest of them, the [Fallen Tusk], and those who died waiting by it.",
            "fallen tusk": "It fell in an earthquake, and the pilgrims sheltering under it with it. At night the [restless] walk there still.",
            "restless": "Restless pilgrims, at their prayers forever. Their prayer beads hold them here. Bring me three and I'll pay, every time, and see the beads blessed.",
            "abbess": "The Lost Abbess led them. Her prayer wheel still turns in the dark at the Fallen Tusk. Bring it to me and let her rest.",
            "unknown": "Ask Keeper Anvesha. I only keep the prayers."}, title="Priest of the Dawn-Tusk", weapon="staff", level=32),
         "pos": at(CAMP, 6, -16), "face": at(CAMP, 6, 10)},
        {"id": npc("tw_huntress_devi", "Huntress Devi", F, "human", "ranger_class", {
            "hail": "The bamboo north-west is tiger country, {name}. Striped [tigers], and the old queen, [Saffronclaw].",
            "tigers": "Four striped pelts and I'll pay, every time. The pilgrims' road is safer with fewer of them.",
            "saffronclaw": "Saffronclaw. Gold as saffron, old as the road's trouble. She's taken three of my hounds. Bring me her pelt.",
            "unknown": "Ask the Keeper. I watch the bamboo."}, title="Huntress", weapon="bow", gender="female", level=32),
         "pos": at(CAMP, 16, 6), "face": at(CAMP, 30, 6)},
        {"id": npc("tw_herbalist_ila", "Herbalist Ila", F, "human", "rogue", {
            "hail": "Remedies and road supplies, {name}. Press G to trade. And I'm short of [fangs] and [shells].",
            "fangs": "King cobra fangs, for antivenom. The cobras nest in the groves. Four and I'll pay, every time.",
            "shells": "Road beetle shells: ground fine they make lamp-black for the shrines. Four and I'll pay, every time.",
            "unknown": "Buying or selling?"}, title="Herbalist", weapon="dagger", gender="female", level=28,
            merchant={"sells": bw.SUPPLIES + ["crude_arrow", "sling_stone"], "buy_rate": 0.5}), "pos": at(CAMP, -14, -8), "face": at(CAMP, 0, -8)},
        {"id": npc("tw_warden_tarun", "Roadwarden Tarun", F, "human", "knight", {
            "hail": "The [Ochre Hand] took this road when the pilgrims stopped coming, {name}. We mean to take it back.",
            "ochre hand": "Bandits. They camp south-west with their wagons and rob anyone walking to the shrines. Three of their tokens and I'll pay, every time. And their captain, [Rhaz].",
            "rhaz": "Captain Rhaz Ochrehand. He wears an ochre seal stamped on every pilgrim he's robbed. Bring it to me.",
            "unknown": "Ask the Keeper."}, title="Roadwarden", weapon="sword_1handed", level=35), "pos": at(CAMP, 20, -4), "face": at(CAMP, 40, -4)},
        {"id": guard_npc("tw_caravanserai_guard", "a Caravanserai warden", "Dawn Pilgrims"), "pos": at(CAMP, 0, 28), "face": at(CAMP, 0, 60)},
        {"id": npc("tw_scout_meera", "Scout Meera", F, "human", "ranger_class", {
            "hail": "Dawnward Watch, {name}: the last fire before Sunward Steps. The Caravanserai's work up this end, you can hand in here: Devi's tigers, Kesav's beads, Ila's fangs.",
            "unknown": "Ask at the Caravanserai, south down the road."}, title="Dawn Pilgrims' Scout", weapon="bow", gender="female", level=32),
         "pos": at(WATCH, 4, 3), "face": WATCH_FACE},
        {"id": npc("tw_sutler_omkar", "Sutler Omkar", F, "human", "barbarian", {
            "hail": "Arrows, food, water, {name}. Press G.", "unknown": "Buying or not?"}, title="Sutler", weapon="axe_1handed", level=25,
            merchant={"sells": ["crude_arrow", "sling_stone", "loaf_of_bread", "water_flask", "draught_of_homecoming", "fishing_bait"], "buy_rate": 0.5}),
         "pos": at(WATCH, -5, 4), "face": WATCH_FACE},
        {"id": guard_npc("tw_watch_sentry", "a Dawnward sentry", "Dawn Pilgrims"), "pos": at(WATCH, 2, -8), "face": WATCH_FACE},
        {"id": guard_npc("tw_hut_guard", "a road sentry", "Dawn Pilgrims"), "pos": [HUT[0], HUT[1] - 14], "face": [HUT[0], HUT[1] - 30]},
    ]
    near = ["tw_scout_meera"]
    Fh = {F: 10}
    def q(qid, name, giver, wants, xp, coin, reward_id, accept, ready, done, first, fac, kw, rep=False, also=()):
        quest(qid, name, giver, wants, xp, coin, reward_id, accept, ready, done, first, fac, keyword=kw, repeatable=rep)
        if also:
            bw.QUESTS[qid]["also_taken_by"] = list(also)
    q("tw_offerings", "Stolen Offerings", "tw_keeper_anvesha", {"tw_stolen_offering": 4}, 560, 90, "tw_pilgrims_sandals",
      "You have taken on a task: Stolen Offerings. Bring Keeper Anvesha four stolen pilgrim's offerings.",
      "Offerings! The statues will have them back.", "Four offerings home.", "Pilgrim's sandals. The road's kinder in them.", dict(Fh), "monkeys", rep=True)
    q("tw_jackal_hides", "Hides for the Shelters", "tw_keeper_anvesha", {"tw_red_jackal_hide": 4}, 600, 100, "tw_roadwardens_belt",
      "You have taken on a task: Hides for the Shelters. Bring Keeper Anvesha four red-earth jackal hides.",
      "Hides. Good and thick.", "That's another roof patched.", "A roadwarden's belt. We give them to friends of the road.", dict(Fh), "jackals", rep=True)
    q("tw_ochre_tokens", "The Ochre Hand", "tw_warden_tarun", {"tw_ochre_token": 3}, 800, 140, "tw_ochre_cloak",
      "You have taken on a task: The Ochre Hand. Bring Roadwarden Tarun three Ochre Hand tokens.",
      "Tokens. Good.", "Three bandits who won't rob pilgrims again.", "Wear their road's cloak, and let them see it.", {F: 15, "ochre_hand": -10}, "ochre hand", rep=True)
    q("tw_rhaz", "Captain Rhaz Ochrehand", "tw_warden_tarun", {"tw_rhaz_seal": 1}, 2000, 400, "tw_rhaz_saber",
      "You have taken on a task: Captain Rhaz Ochrehand. Bring Roadwarden Tarun Captain Rhaz's ochre seal.",
      "His seal!", "The Ochre Hand's broken. The road's ours.", "His saber. It's robbed its last pilgrim.", {F: 30, "ochre_hand": -30}, "rhaz")
    q("tw_beads", "Restless Pilgrims", "tw_brother_kesav", {"tk_prayer_bead": 3}, 700, 110, "tw_bead_necklace",
      "You have taken on a task: Restless Pilgrims. Bring Brother Kesav three pilgrim's prayer beads.",
      "Their beads. Let me bless them.", "Three pilgrims who can go on now.", "Wear the first of them. It remembers its prayers.", dict(Fh), "restless", rep=True, also=near)
    q("tw_abbess", "The Lost Abbess", "tw_brother_kesav", {"tw_abbess_wheel": 1}, 2200, 420, "tw_abbess_ring",
      "You have taken on a task: The Lost Abbess. Bring Brother Kesav the Lost Abbess's prayer wheel.",
      "Her wheel. It's stopped turning.", "She rests. The Fallen Tusk is quiet.", "Her ring. She'd want it on the road.", {F: 30}, "abbess", also=near)
    q("tw_tiger_pelts", "Striped Pelts", "tw_huntress_devi", {"tw_striped_pelt": 4}, 760, 130, "tw_tigerhide_sleeves",
      "You have taken on a task: Striped Pelts. Bring Huntress Devi four striped tiger pelts.",
      "Pelts! Clean work.", "Four fewer in the bamboo.", "Tigerhide sleeves. I made them from the first ones.", dict(Fh), "tigers", rep=True, also=near)
    q("tw_saffronclaw", "Saffronclaw", "tw_huntress_devi", {"tw_saffronclaws_pelt": 1}, 2200, 420, "tw_saffron_mantle",
      "You have taken on a task: Saffronclaw. Bring Huntress Devi Saffronclaw's pelt.",
      "Saffronclaw's pelt. Gold as they said.", "The old queen's gone. The bamboo's ours.", "A saffron mantle. Wear her colors.", {F: 30}, "saffronclaw", also=near)
    q("tw_cobra_fangs", "Antivenom", "tw_herbalist_ila", {"tw_king_cobra_fang": 4}, 700, 110, "tw_snake_charmers_gloves",
      "You have taken on a task: Antivenom. Bring Herbalist Ila four king cobra fangs.",
      "Fangs. Careful how you hold them.", "Enough antivenom for a month of pilgrims.", "A snake-charmer's gloves. Nothing bites through them.", dict(Fh), "fangs", rep=True, also=near)
    q("tw_beetle_shells", "Lamp-Black", "tw_herbalist_ila", {"tw_road_beetle_shell": 4}, 620, 100, "tw_beetle_shell_cap",
      "You have taken on a task: Lamp-Black. Bring Herbalist Ila four road beetle shells.",
      "Shells! The shrines' lamps will thank you.", "Four shells' worth of lamp-black.", "A cap from the biggest of them. Harder than it looks.", dict(Fh), "shells", rep=True)
    # monsters: gentler at the two ends, harder toward the north
    mob("tw_bamboo_monkey", "a bamboo monkey", (9, 10), "temple_monkey", verb=("scratch", "scratches"), aggressive=False, social=True,
        loot=[("tw_stolen_offering", 0.55)], coin=(5, 20), speed=7.2)
    mob("tw_red_jackal", "a red-earth jackal", (9, 11), "jackal", social=True, loot=[("tw_red_jackal_hide", 0.55), ("raw_meat", 0.3)], speed=7.0)
    mob("tw_road_beetle", "a road beetle", (10, 12), "rice_beetle", verb=("pinch", "pinches"), aggressive=False,
        loot=[("tw_road_beetle_shell", 0.55)], scale=1.6, color="#5a4a30")
    mob("tw_king_cobra", "a king cobra", (11, 13), "cobra", verb=("strike", "strikes"), loot=[("tw_king_cobra_fang", 0.55)], scale=1.3,
        extra={"proc": {"spell": "cobra_venom", "chance": 0.15, "text": "%s's fangs deliver %s!"}})
    mob("tw_striped_tiger", "a striped tiger", (11, 13), "tiger", verb=("claw", "claws"), loot=[("tw_striped_pelt", 0.55), ("raw_meat", 0.3)],
        speed=7.2, scale=1.1)
    mob("tw_ochre_cutthroat", "an Ochre Hand cutthroat", (11, 13), "brigand", faction="ochre_hand", verb=("slash", "slashes"), social=True,
        loot=[("tw_ochre_token", 0.5)], coin=(15, 60), extra={"weapon": "dagger"})
    mob("tw_ochre_archer", "an Ochre Hand archer", (12, 14), "brigand", faction="ochre_hand", verb=("shoot", "shoots"), social=True,
        loot=[("tw_ochre_token", 0.5)], coin=(15, 60), extra={"weapon": "bow"})
    mob("tw_pilgrim_shade", "a restless pilgrim", (12, 14), "hungry_ghost", faction="undead", verb=("wail at", "wails at"),
        loot=[("tk_prayer_bead", 0.55)], coin=(5, 30))
    mob("tw_saffronclaw", "Saffronclaw", (14, 14), "tigress", verb=("maul", "mauls"), named=True, loot=[("tw_saffronclaws_pelt", 1.0)],
        scale=1.35, speed=7.4)
    mob("tw_rhaz_ochrehand", "Captain Rhaz Ochrehand", (15, 15), "brigand_captain", faction="ochre_hand", verb=("slash", "slashes"), social=True,
        named=True, loot=[("tw_rhaz_seal", 1.0)], coin=(150, 400), extra={"weapon": "sword_1handed"})
    mob("tw_lost_abbess", "the Lost Abbess", (15, 15), "lantern_widow", faction="undead", verb=("wail at", "wails at"), named=True,
        loot=[("tw_abbess_wheel", 1.0), ("tk_prayer_bead", 1.0)], coin=(80, 250), scale=1.15)
    spawns = []

    def spawn(pool, spots, respawn=80, wander=14, when=None):
        for s in spots:
            e = {"pos": [round(s[0], 1), round(s[1], 1)], "pool": pool, "respawn": respawn, "wander": wander}
            if when:
                e["when"] = when
            spawns.append(e)

    def ring(c, r, n, turn=0.0):
        return [[c[0] + math.cos(turn + k * math.tau / n) * r, c[1] + math.sin(turn + k * math.tau / n) * r] for k in range(n)]
    spawn({"tw_bamboo_monkey": 1}, [[170, 90], [210, 70], [250, 50], [150, 120], [230, 110], [270, -40], [200, -20], [120, 100]], 55, 16)
    spawn({"tw_red_jackal": 1}, [[-250, 90], [-270, -60], [-220, 120], [-290, 40], [-240, -20], [-200, 90], [-280, 140]], 60, 16)
    spawn({"tw_road_beetle": 1}, [[-100, 0], [60, 90], [90, -60], [-40, 100], [-110, 80], [100, 10], [-60, -60], [30, 140]], 70, 12)
    spawn({"tw_king_cobra": 1}, [[-120, -80], [120, 180], [-60, -150], [200, 180], [-20, -110], [80, 210], [150, 230]], 80, 10)
    spawn({"tw_striped_tiger": 1}, [[-180, -120], [-220, -200], [-150, -200], [-260, -150], [-120, -180], [-200, -250], [-270, -230]], 90, 16)
    spawn({"tw_ochre_cutthroat": 2, "tw_ochre_archer": 1}, ring(OCHRE, 26, 6, 0.4) + [[OCHRE[0] + 4, OCHRE[1] - 8]], 100, 6)
    spawn({"tw_pilgrim_shade": 1}, ring(TUSK, 32, 6), 90, 12, "night")
    spawn({"tw_saffronclaw": 1}, [[GROVE[0] - 30, GROVE[1] - 30]], 1500, 8)
    spawn({"tw_rhaz_ochrehand": 1}, [[OCHRE[0] + 2, OCHRE[1] + 2]], 1500, 3)
    spawn({"tw_lost_abbess": 1}, [[TUSK[0] - 10, TUSK[1] + 12]], 1500, 6, "night")
    return {"name": "The Tuskway", "levels": [9, 14], "music": "the_tuskway", "seed": 9141, "size": 672, "bind_point": [CAMP[0], CAMP[1] + 16],
            "height_amplitude": 6.0, "flat_radius": 30, "trees": 380,
            "tree_mix": ["bamboo_clump", "bamboo_clump", "bamboo_clump", "bamboo_clump", "bamboo_clump_b", "bamboo_clump_b", "lone_tree", "tree_round"],
            "groves": 0.7, "rocks": 50, "grass_colors": ["#6a7a36", "#7f8c42"], "fog_density": 0.004, "fog_color": "#d8c8a6",
            "sun_energy": 1.0, "passes": passes, "zone_lines": lines,
            "ground_patches": [{"pos": [CAMP[0], CAMP[1]], "radius": 34, "color": "#9a5e3c", "flatten": 0.4},
                               {"pos": TUSK, "radius": 30, "color": "#8e5a3a", "flatten": 0.5},
                               {"pos": OCHRE, "radius": 30, "color": "#94603e", "flatten": 0.5},
                               {"pos": [-90, 40], "radius": 40, "color": "#a0623e", "flatten": 0.2},
                               {"pos": [120, 30], "radius": 36, "color": "#a0623e", "flatten": 0.2},
                               {"pos": [30, -170], "radius": 40, "color": "#9c5c3a", "flatten": 0.2}],
            "roads": [{"points": ROAD_MAIN, "width": 3.6}, {"points": ROAD_EAST, "width": 3.2}, {"points": ROAD_TUSK, "width": 2.6}],
            "clutter": {"grass_b": {"density": 0.28, "patch": 0.5, "sway": 0.25, "range": 55, "tint": "ground", "scale": [0.8, 1.3]},
                        "fern": {"density": 0.04, "patch": 0.8, "sway": 0.1, "range": 50, "scale": [0.9, 1.5]},
                        "bush_a": {"density": 0.004, "patch": 0.7, "range": 90, "shadow": True, "scale": [0.7, 1.1]}},
            "landmarks": L, "npcs": npcs, "spawns": spawns}


# ---------------------------------------------------------------- the neighbors' new passes

def open_onto(zid, edge, label):
    """zid's pass and zone line onto the Tuskway (derived from the layout), and a signpost in the gap."""
    path = f"{ROOT}/data/zones/{zid}.json"
    t = open(path).read()
    z = json.loads(t)
    pass_ = bw.edge_pass(zid, edge)
    line = bw.zone_line(zid, edge, ZID, {"west": "east", "east": "west", "north": "south", "south": "north"}[edge])
    z["passes"] = [p for p in z.get("passes", []) if p != pass_] + [pass_]
    z["zone_lines"] = [l for l in z.get("zone_lines", []) if l.get("to") != ZID] + [line]
    h = bw.half(zid, edge)
    inward = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}[edge]
    base = {"north": (0, -h), "south": (0, h), "east": (h, 0), "west": (-h, 0)}[edge]
    sign_at = [base[0] + inward[0] * 22 + (10 if edge in ("north", "south") else 0), base[1] + inward[1] * 22 + (10 if edge in ("east", "west") else 0)]
    z["landmarks"] = [l for l in z["landmarks"] if not (l["type"] == "signpost" and l.get("labels") == [label])]
    z["landmarks"].append({"type": "signpost", "pos": sign_at, "face": [base[0] + (10 if edge in ("north", "south") else 0), base[1] + (10 if edge in ("east", "west") else 0)],
                           "labels": [label]})
    with open(path, "w") as f:
        f.write(scale_zone.dumps(z) + "\n")


def factions():
    path = f"{ROOT}/data/factions.json"
    t = open(path).read()
    add = {"ochre_hand": {"name": "The Ochre Hand", "default": -800, "kos_at": -750, "on_kill": {"ochre_hand": -10, F: 3}}}
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
    z = the_tuskway()
    import spawn_fill
    known = dict(json.load(open(f"{ROOT}/data/mobs.json")), **bw.MOBS)
    z["spawns"] += spawn_fill.fill(z, known, ZID)
    with open(f"{ROOT}/data/zones/{ZID}.json", "w") as f:
        f.write(scale_zone.dumps(z) + "\n")
    open_onto("harrowfield", "east", "The Tuskway")
    open_onto("dewstep", "west", "The Tuskway")
    open_onto("sunward_steps", "south", "The Tuskway")
    bw.merge(f"{ROOT}/data/npcs.json", bw.NPCS)
    bw.merge(f"{ROOT}/data/mobs.json", bw.MOBS)
    bw.merge(f"{ROOT}/data/quests.json", bw.QUESTS)
    with open(f"{ROOT}/data/items/the_tuskway.json", "w") as f:
        f.write(json.dumps(bw.ITEMS, indent=2) + "\n")
    factions()
    missing = sorted({l["id"] for l in z["landmarks"] if l.get("type") == "prop" and l["id"] not in bw.MODELS["props"]})
    models = set(bw.MODELS["characters"])
    bad = sorted({m["model"] for m in bw.MOBS.values() if m["model"] not in models} | {n["model"] for n in bw.NPCS.values() if n["model"] not in models})
    print("wrote %s; %d npcs, %d mobs, %d quests, %d items, %d spawns%s%s" % (ZID, len(bw.NPCS), len(bw.MOBS), len(bw.QUESTS), len(bw.ITEMS), len(z["spawns"]),
          "; MISSING props: %s" % missing if missing else "", "; UNKNOWN models: %s" % bad if bad else ""))
    print("Now run python3 tools/zones/outline.py (the mountains) and check the borders both ways.")


if __name__ == "__main__":
    main()
