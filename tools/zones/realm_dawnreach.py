"""Prabhagaj's line to the Grove ("The Last Dawn") and the first zone of his
realm, the Dawnreach (docs/grove-questline.md).

Writes data/zones/dawnreach.json and data/items/dawn_line.json, and adds or
replaces its own entries in quests.json, mobs.json, npcs.json, spells.json and
factions.json by text (other people's entries are left exactly as they are).
It also gives five existing monsters their relic, a drop only someone on that
step finds. Change the line here and rerun, never the JSON:

    python3 tools/zones/realm_dawnreach.py
    python3 tools/zones/outline.py && python3 tools/zones/spawn_fill.py
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIZE = 576
H = SIZE // 2


def merge(path, new):
    """Adds or replaces these entries in a shared data file by text, touching
    nothing else (the files mix formats; re-dumping would reformat them)."""
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
            nxt = t.find("\n  \"", start + 1)
            stop = nxt if nxt >= 0 else t.rstrip().rfind("\n}")
            comma = "," if t[start:stop].rstrip().endswith(",") else ""
            t = t[:start] + "\n  %s: %s%s" % (json.dumps(k), block, comma) + t[stop:]
        d = json.loads(t)
    assert all(d[k] == v for k, v in new.items()), path
    open(path, "w").write(t)


def add_loot(mobs_path, mob_id, entry):
    """Gives an existing monster one more loot entry (its relic), by text."""
    t = open(mobs_path).read()
    d = json.loads(t)
    loot = d[mob_id].get("loot", [])
    if any(e.get("item") == entry["item"] for e in loot):
        return
    merge(mobs_path, {mob_id: {**d[mob_id], "loot": loot + [entry]}})


# --- items ------------------------------------------------------------------

ITEMS = {
    "dl_grandmothers_memory": {"name": "The Grandmother's Memory", "no_drop": True, "lore": True, "value": 0, "weight": 0.2,
                               "desc": "A pale light caught in a fold of ghost-hide. It remembers a morning a very long time ago."},
    "dl_dawn_mote": {"name": "Dawn-Pale Mote", "no_drop": True, "stack": 20, "value": 0, "weight": 0.1,
                     "desc": "A speck of old morning that a herd-spirit carried in its bones."},
    "dl_ysmoor_sunstone": {"name": "Ysmoor's Sunstone", "no_drop": True, "lore": True, "value": 0, "weight": 1.0,
                           "desc": "A dull amber stone. Held up, it's warm on the side facing east, wherever east is."},
    "dl_attuned_sunstone": {"name": "Attuned Sunstone", "no_drop": True, "lore": True, "value": 0, "weight": 1.0,
                            "desc": "Ysmoor's Sunstone, woken by Evander's reading. A faint sunrise moves inside it."},
    "dl_last_dawn_lamp": {"name": "The Last Dawn-Lamp", "no_drop": True, "lore": True, "value": 0, "weight": 1.5,
                          "desc": "A brass lamp, cold and black inside. Its wick was lit from the Dawn-Tusk's own fire."},
    "dl_lit_dawn_lamp": {"name": "The Dawn-Lamp, Relit", "no_drop": True, "lore": True, "value": 0, "weight": 1.5,
                         "desc": "Solenne relit it from the Lampward's oldest flame. It burns gold, and the dark leans away from it."},
    "dl_dawnspear_head": {"name": "The Dawnspear's Head", "no_drop": True, "lore": True, "value": 0, "weight": 3.0,
                          "desc": "A spearhead of white stone, broken from the Dawn-Tusk's champion's hand on Lastwalk."},
    "dl_hallowed_spearhead": {"name": "Hallowed Dawnspear Head", "no_drop": True, "lore": True, "value": 0, "weight": 3.0,
                              "desc": "The Dawnspear's head, hallowed by Wilhelmina. It points north whatever way you hold it."},
    "dl_ember_of_first_light": {"name": "The Ember of First Light", "no_drop": True, "lore": True, "value": 0, "weight": 0.2,
                                "desc": "The first morning's last coal, taken back from the Dimming. Too bright to look at; warm as a held hand."},
    "dl_pendant_of_the_last_dawn": {"name": "Pendant of the Last Dawn", "no_drop": True, "lore": True, "slot": "neck",
                                    "ac": 15, "str": 8, "sta": 10, "wis": 10, "int": 8, "hp": 120, "mana": 90,
                                    "value": 60000, "rec_level": 50, "deities": ["light"], "icon": "godforged_heart_amulet",
                                    "desc": "The Dawn-Tusk's thanks: a sliver of the first morning on a gold chain."},
}

# --- quests -------------------------------------------------------------------

FACTION = {"lanternhold": 20, "dawn_pilgrims": 20}
QUESTS = {
    "dawn_1": {
        "name": "The Last Dawn (1 of 6): A Stirring at the Shrine", "starter": "dawnpriest_amaru", "giver": "sister_imelda",
        "start_keyword": "stirring", "deities": ["light"], "min_level": 46,
        "offer_text": "Wait, {name}. You follow the Dawn-Tusk; you'll have felt it too, at the edge of sleep. Something [stirring].",
        "refuse_text": "It isn't yours to carry, {name}. Not yet, or not from your god.",
        "wants": {"dl_grandmothers_memory": 1, "dl_dawn_mote": 4},
        "reward": {"xp": 50000, "coin": 6000},
        "accept_text": "You have taken on a task: The Last Dawn. Somewhere beyond the world the Dawn-Tusk's light is failing. In the Ivory Field, the ghosts of the great herds still remember him: bring Sister Imelda at Tuskwatch the Grandmother of Herds' memory and four dawn-pale motes from the herd-spirits.",
        "ready_text": "You've brought her memory? Gently, {name}. Give it here.",
        "complete_text": "Imelda holds the memory to her ear like a shell, and her face goes still. \"A morning. The first one. He stood at its edge, and the herds walked out into it.\"",
        "first_complete_text": "\"It's being eaten, {name}. The light he made. I could hear it going out.\" She presses the motes back into your hand to warm it. \"Ysmoor's queens kept a stone that held a sunrise. Queen Ismay still walks Fogfall at night, and she never let it go. Take it from her, and take it to Loremaster Evander at the Lanternwatch.\"",
        "next": "dawn_2", "faction": FACTION,
    },
    "dawn_2": {
        "name": "The Last Dawn (2 of 6): The Sunstone of Ysmoor", "giver": "loremaster_evander",
        "wants": {"dl_ysmoor_sunstone": 1}, "reward": {"xp": 55000, "coin": 6000}, "first_reward_item": "dl_attuned_sunstone",
        "accept_text": "Queen Ismay walks Fogfall's ruins at night with Ysmoor's Sunstone. Take it from her and bring it to Loremaster Evander at the Lanternwatch.",
        "ready_text": "Is that... the Sunstone? Here, {name}, quickly, before the fog gets at it.",
        "complete_text": "Evander turns the stone in his hands, reading lines nobody else can see. Then he breathes on it, and something gold wakes inside.",
        "first_complete_text": "\"Keep it. It's awake now: it'll know the way home when you need it.\" He frowns at the north. \"The last lamp lit from the Dawn-Tusk's own fire went into the dark, {name}. The Pale Keeper in the Unlit took it. Bring it to Lampwarden Solenne; if anyone can relight it, she can.\"",
        "next": "dawn_3", "faction": FACTION,
    },
    "dawn_3": {
        "name": "The Last Dawn (3 of 6): A Lamp in the Unlit", "giver": "lampwarden_solenne",
        "wants": {"dl_last_dawn_lamp": 1}, "reward": {"xp": 60000, "coin": 7000}, "first_reward_item": "dl_lit_dawn_lamp",
        "accept_text": "The Pale Keeper in the Unlit holds the last lamp lit from the Dawn-Tusk's fire. Take it and bring it to Lampwarden Solenne at the Lampward.",
        "ready_text": "That lamp. Oh, {name}. Give it to me.",
        "complete_text": "Solenne tips the lamp to the Lampward's oldest flame. For a long moment nothing happens. Then the wick takes, and the light that comes out of it is gold, not white.",
        "first_complete_text": "\"Carry it carefully.\" She doesn't let go at once. \"His champion stands on Lastwalk, turned to stone with his spear still in his hand. The Unmoving Champion, they call him now. Break the spearhead from him and take it to Relic-Keeper Wilhelmina at the Vigil.\"",
        "next": "dawn_4", "faction": FACTION,
    },
    "dawn_4": {
        "name": "The Last Dawn (4 of 6): The Champion's Spear", "giver": "relic_keeper_wilhelmina",
        "wants": {"dl_dawnspear_head": 1}, "reward": {"xp": 65000, "coin": 7000}, "first_reward_item": "dl_hallowed_spearhead",
        "accept_text": "The Dawn-Tusk's champion stands turned to stone on Lastwalk. Take the Dawnspear's head from the Unmoving Champion and bring it to Relic-Keeper Wilhelmina at the Pilgrim's Vigil.",
        "ready_text": "The Dawnspear. I never thought I'd hold it. Give it here, {name}.",
        "complete_text": "Wilhelmina washes the spearhead in water from a small flask and says words over it in a language older than Lanternhold. The white stone warms.",
        "first_complete_text": "\"Lamp, stone and spear. That's all three, {name}.\" She folds your hands round it. \"Take them home to the Dawnpriest. He'll know what they open.\"",
        "next": "dawn_5", "faction": FACTION,
    },
    "dawn_5": {
        "name": "The Last Dawn (5 of 6): The Way Opened", "giver": "dawnpriest_amaru",
        "wants": {"dl_attuned_sunstone": 1, "dl_lit_dawn_lamp": 1, "dl_hallowed_spearhead": 1}, "reward": {"xp": 70000, "coin": 8000},
        "accept_text": "Take the Attuned Sunstone, the relit Dawn-Lamp and the hallowed Dawnspear head home to Dawnpriest Amaru in Lanternhold.",
        "ready_text": "Lamp, stone and spear. Lay them on the shrine, {name}.",
        "complete_text": "Amaru sets the lamp before the Dawn-Tusk's statue, the stone at its feet, the spear across them. The plaza goes quiet. The light that rises off them isn't Lanternhold's: it's colder, and older, and it's coming from somewhere else.",
        "first_complete_text": "\"There. That's his realm, {name}, the Dawnreach, where he keeps the first morning. Something's in it, eating the light. When you're ready, and not alone, say [dawn] and I'll open the way. Bring friends. Bring the best you know.\"",
        "next": "dawn_6", "faction": FACTION,
    },
    "dawn_6": {
        "name": "The Last Dawn (6 of 6): The Dawn-Eater", "giver": "dawn_avatar",
        "wants": {"dl_ember_of_first_light": 1},
        "reward": {"xp": 150000, "coin": 15000, "grove_deity": "light"}, "first_reward_item": "grove_seed",
        "accept_text": "In the Dawnreach a hunger called the Dimming is eating the Dawn-Tusk's light. Take the Ember of First Light back from it and bring it to the Dawn-Tusk at his temple. Say [dawn] to Dawnpriest Amaru when your group is ready.",
        "ready_text": "The ember. You brought it back, little one. Hold it up.",
        "complete_text": "The Dawn-Tusk lowers his trunk and breathes on the ember. It catches, and the whole Dawnreach catches with it: the light runs back to the edges like water filling a bowl.",
        "first_complete_text": "\"You walked a long road for a morning, {name}. Take this.\" A seed falls from the ember into your hand, warm as a held hand. \"It opens the Grove, where the five of us stand. I'll be there now, on my dais, whenever you come. Bring the ones who walked with you.\"",
        "faction": FACTION,
    },
}
# the finale's pendant too, beside the seed
QUESTS["dawn_6"]["reward"]["items"] = ["dl_pendant_of_the_last_dawn"]

# --- relics on existing monsters (only someone on that step finds them) ----------

RELICS = [
    ("herd_grandmother", {"item": "dl_grandmothers_memory", "chance": 1.0, "quest": "dawn_1"}),
    ("herd_spirit", {"item": "dl_dawn_mote", "chance": 0.45, "quest": "dawn_1"}),
    ("queen_ismay", {"item": "dl_ysmoor_sunstone", "chance": 1.0, "quest": "dawn_2"}),
    ("un_pale_keeper", {"item": "dl_last_dawn_lamp", "chance": 1.0, "quest": "dawn_3"}),
    ("unmoving_champion", {"item": "dl_dawnspear_head", "chance": 1.0, "quest": "dawn_4"}),
]

# --- the Dawnreach's monsters ---------------------------------------------------


def ordinary(name, lv, model, verb, faction, aggressive=True, scale=1.0, proc=None, loot=None, social=True):
    lo, hi = lv
    m = {"name": name, "level": [lo, hi], "hp_base": 372, "hp_per_level": 49, "dmg_min": 35, "dmg_max": 67,
         "attack_delay": 2.7, "ac": 93, "speed": 6.4, "aggressive": aggressive, "aggro_radius": 16, "social": social,
         "flees": False, "verb": verb, "shape": "humanoid", "color": "#e8d8a0", "scale": scale,
         "coin": [120, 400], "loot": loot or [], "model": model}
    if faction:
        m["faction"] = faction
    if proc:
        m["proc"] = proc
    return m


def named(name, lv, model, verb, faction, loot, scale=1.0, proc=None, **extra):
    m = {"name": name, "level": [lv, lv], "hp_base": 12400, "hp_per_level": 0, "dmg_min": 52, "dmg_max": 100,
         "attack_delay": 3.0, "ac": 120, "speed": 6.6, "aggressive": True, "aggro_radius": 18, "social": True,
         "flees": False, "faction": faction, "verb": verb, "shape": "humanoid", "color": "#e8d8a0", "scale": scale,
         "coin": [2000, 5000], "loot": loot, "model": model, "named": True, "xp_bonus": 2.3}
    if proc:
        m["proc"] = proc
    m.update(extra)
    return m


DIM_PROC = {"spell": "dimming_touch", "chance": 0.15, "text": "%s's touch carries %s!"}
MOBS = {
    # the Dimmed: what the hunger has eaten, still walking
    "dr_dimmling": ordinary("a dimmling", (49, 51), "shade", ["claw", "claws"], "the_dimmed", proc=DIM_PROC,
                            loot=[{"item": "dr_dimmed_ash", "chance": 0.5}]),
    "dr_hollow_light": ordinary("a hollow light", (49, 50), "lantern_wisp", ["sear", "sears"], "the_dimmed", scale=1.3,
                                loot=[{"item": "dr_dimmed_ash", "chance": 0.4}]),
    "dr_dimmed_sentinel": ordinary("a dimmed dawn-sentinel", (50, 51), "stone_guardian", ["strike", "strikes"], "the_dimmed",
                                   loot=[{"item": "dr_sunstone_chip", "chance": 0.5}]),
    "dimming_shard": ordinary("a shard of the Dimming", (51, 52), "shade", ["rend", "rends"], "the_dimmed", scale=1.3, proc=DIM_PROC,
                              loot=[{"item": "dr_dimmed_ash", "chance": 1.0}]),
    # the realm's own wild things
    "dr_dawnwing": ordinary("a dawnwing", (49, 50), "sunhawk", ["rake", "rakes"], "", social=False,
                            loot=[{"item": "dr_gilded_feather", "chance": 0.6}]),
    "dr_gilded_ram": ordinary("a gilded ram", (49, 50), "mountain_ram", ["butt", "butts"], "", aggressive=False, social=False,
                              loot=[{"item": "dr_gilded_fleece", "chance": 0.6}]),
    "dr_sunwyrm": ordinary("a sunwyrm", (50, 51), "cinder_drake", ["bite", "bites"], "", scale=1.2, social=False,
                           loot=[{"item": "dr_sunwyrm_scale", "chance": 0.6}]),
    # named
    "dr_goldmaw": named("Goldmaw the Dawnwyrm", 52, "cinder_drake", ["bite", "bites"], "", scale=1.8,
                        loot=[{"item": "dr_goldmaw_fang", "chance": 1.0}, {"item": "dr_sunwyrm_scale", "chance": 1.0, "count": [2, 3]}],
                        min_players=3, toughness=1.8, xp_bonus=3.0),
    "dr_hollow_abbot": named("the Hollow Abbot", 52, "fallen_abbot", ["strike", "strikes"], "the_dimmed", proc=DIM_PROC,
                             loot=[{"item": "dr_abbots_prayer_beads", "chance": 1.0}, {"item": "dr_dimmed_ash", "chance": 1.0, "count": [2, 3]}],
                             min_players=3, toughness=1.8, xp_bonus=3.0),
    # the Dawn-Eater: a group fight, its court about it
    "the_dimming": named("the Dimming", 52, "nameless_shade", ["devour", "devours"], "the_dimmed", scale=2.2,
                         proc={"spell": "dimming_touch", "chance": 0.3, "text": "%s reaches into your light; %s takes hold!"},
                         loot=[{"item": "dl_ember_of_first_light", "chance": 1.0, "quest": "dawn_6"},
                               {"item": "dr_dimmed_ash", "chance": 1.0, "count": [3, 5]},
                               {"item": "dr_heart_of_the_dimming", "chance": 0.35}],
                         min_players=3, toughness=2.2, xp_bonus=4.0, aggro_radius=22, always_up=True),
}
for k in ("dr_dawnwing", "dr_gilded_ram", "dr_sunwyrm", "dr_goldmaw"):
    MOBS[k]["faction"] = "wildlife"  # the realm's own beasts, like any other

# what they drop that isn't the line's (sold, or for later work)
ITEMS.update({
    "dr_dimmed_ash": {"name": "Dimmed Ash", "stack": 20, "value": 900, "weight": 0.1, "desc": "What light leaves when something eats it."},
    "dr_sunstone_chip": {"name": "Sunstone Chip", "stack": 20, "value": 1400, "weight": 0.2, "desc": "Chipped from a dawn-sentinel; still faintly warm."},
    "dr_gilded_feather": {"name": "Gilded Feather", "stack": 20, "value": 1100, "weight": 0.1, "desc": "A dawnwing's flight feather, gold at the tip."},
    "dr_gilded_fleece": {"name": "Gilded Fleece", "stack": 20, "value": 1200, "weight": 0.5, "desc": "Wool that holds the morning; warm in any weather."},
    "dr_sunwyrm_scale": {"name": "Sunwyrm Scale", "stack": 20, "value": 1600, "weight": 0.5, "desc": "A sunwyrm's scale, amber and hard as bronze."},
    "dr_goldmaw_fang": {"name": "Goldmaw's Fang", "slot": "primary", "skill": "piercing", "dmg": 29, "delay": 2.1,
                        "agi": 9, "str": 7, "hp": 60, "value": 52000, "rec_level": 50, "lore": True, "icon": "dragontooth_dagger",
                        "model": "dagger", "desc": "A fang longer than a hand, gold at the root."},
    "dr_abbots_prayer_beads": {"name": "Hollow Abbot's Prayer Beads", "slot": "neck", "ac": 12, "wis": 11, "int": 9, "mana": 120, "hp": 60,
                               "value": 48000, "rec_level": 50, "lore": True, "icon": "godforged_heart_amulet",
                               "desc": "Sunstone beads gone dull, all but one."},
    "dr_heart_of_the_dimming": {"name": "Heart of the Dimming", "slot": "ring", "ac": 10, "str": 9, "sta": 9, "agi": 9, "hp": 90,
                                "value": 62000, "rec_level": 51, "lore": True, "no_drop": True, "icon": "ring_of_the_empty_chair",
                                "desc": "A ring of black glass with nothing at all inside it. Your hand looks dimmer wearing it."},
})

SPELLS = {
    "dimming_touch": {"name": "The Dimming's Touch", "type": "dot", "target": "enemy", "mana": 0, "cast_time": 0, "recast": 0,
                      "range": 8, "tick": 26, "ticks": 4, "per_level": 0.7, "classes": {},
                      "dot_text": "%s's light gutters and dims.", "land_text": "Something cold reaches into you and eats the light.",
                      "desc": "The Dimming's hunger.", "fx": {"kind": "dot", "color": "#2a2a40"}},
}
FACTIONS = {
    "the_dimmed": {"name": "The Dimmed", "default": -800, "kos_at": -750, "on_kill": {"the_dimmed": -5, "lanternhold": 2, "dawn_pilgrims": 2}},
}

# --- people ---------------------------------------------------------------------

NPCS = {
    "dawnkeeper_ilaya": {
        "name": "Dawnkeeper Ilaya", "title": "Keeper of the Dawngate", "level": 60, "model": "mage", "weapon": "staff",
        "faction": "lanternhold", "sacred": True, "grove_return": True, "race": "high_elf", "gender": "female",
        "dialogue": {
            "hail": "You came through the gate, {name}. Few do now. This is the Dawnreach, where the Dawn-Tusk keeps the first morning, or did, before the [Dimming] came. When you want to go home, say [return] and I'll walk you back to where you stood.",
            "dimming": "A hunger from outside the world. It came in through the crater at the realm's heart and it eats light: the sentinels, the lamps, the morning itself. It took the [ember] he kept, and now the edges are going dark.",
            "ember": "The Ember of First Light, the first morning's last coal. Take it back and carry it to the Dawn-Tusk at his [temple], north past the crater. You won't do it alone. Nobody has.",
            "temple": "The Temple of the First Dawn, at the realm's north end. He stands there still, waiting.",
            "return": "Close your eyes, {name}. Mind the step.",
            "unknown": "The light's too thin here for riddles, {name}.",
        },
    },
    "sister_ashvara": {
        "name": "Sister Ashvara", "title": "the First Dawnpriest", "level": 60, "model": "mage", "weapon": "staff",
        "faction": "lanternhold", "sacred": True, "race": "human", "gender": "female", "hair": ["long", "white"],
        "dialogue": {
            "hail": "I was the first to keep his shrine in Lanternhold, {name}, longer ago than the city remembers. He let me stay when it was done. I watch the [sentinels] now.",
            "sentinels": "They kept the paths for him: stone that loved the light. The Dimming got into them. Some of them still turn east at dawn, as if they remember. Put them down kindly; it's what they'd want.",
            "unknown": "Ask Ilaya, child. She knows the roads.",
        },
    },
    "dawn_avatar": {
        "name": "Prabhagaj", "title": "The Dawn-Tusk", "level": 99, "model": "deity_light", "faction": "lanternhold",
        "sacred": True, "fixed": True, "size": [3.0, 8.5], "name_height": 9.5,
        "dialogue": {
            "hail": "Little one. You came all this way, and you came with others, which is the right way to come. Something is eating my morning. It took the [ember] I kept.",
            "ember": "The Ember of First Light. The Dimming holds it in the crater, south of here. Take it back, and bring it to me. Then I'll give you something to open the Grove with.",
            "grove": "Where the five of us stand when the world doesn't need us standing somewhere else. You'll see it.",
            "unknown": "I've watched a great many mornings, {name}. Not many words.",
        },
    },
}
NPC_PATCH = {  # Amaru opens the way, once the lamp, stone and spear are on his shrine
    "dawnpriest_amaru": {"opens_realm": {"zone": "dawnreach", "keyword": "dawn", "after": "dawn_5",
                                         "text": "Then go, {name}, and the Dawn-Tusk go with you. Hold on to each other.",
                                         "refuse": "The way to the Dawnreach doesn't open yet, {name}. Not for you."}},
}

# --- the zone --------------------------------------------------------------------


def prop(pid, pos, face=None, collide="box", scale=None, **extra):
    lm = {"type": "prop", "pos": [round(pos[0], 1), round(pos[1], 1)], "id": pid, "collide": collide}
    if face is not None:
        lm["face"] = face
    if scale is not None:
        lm["scale"] = scale
    lm.update(extra)
    return lm


def ring(center, r, n, start=0.0):
    return [(center[0] + r * math.cos(start + k * math.tau / n), center[1] + r * math.sin(start + k * math.tau / n)) for k in range(n)]


GATE = (0, 228)        # where the way opens, south
CRATER = (0, -40)      # the Dimming's wound, the realm's heart
TEMPLE = (0, -218)     # the Temple of the First Dawn, north
ROOST = (-175, 30)     # the sunwyrms, west
CLOISTER = (175, 30)   # the dimmed cloister, east

landmarks = [
    {"type": "sun_shrine", "pos": list(TEMPLE), "great": True, "face": list(CRATER)},
    prop("dawn_beacon", (GATE[0] - 9, GATE[1] - 6), face=list(CRATER)),
    prop("dawn_beacon", (GATE[0] + 9, GATE[1] - 6), face=list(CRATER)),
    prop("elephant_statue", (GATE[0], GATE[1] + 10), face=list(CRATER), scale=1.6),
    {"type": "ruins", "pos": list(CLOISTER)},
    {"type": "ruins", "pos": [120, -120]},
    {"type": "ruins", "pos": [-110, 150]},
    {"type": "obelisk", "pos": [-60, 120]},
    {"type": "obelisk", "pos": [70, 130]},
]
for x, z in ring(TEMPLE, 26, 8, math.pi / 8):
    landmarks.append(prop("sun_pillar", (x, z), face=list(TEMPLE), collide="trunk", scale=1.4))
for x, z in ring(CRATER, 30, 6):
    landmarks.append(prop("broken_pillar", (x, z), face=list(CRATER), collide="trunk", scale=1.2))
for side in (-1, 1):
    for k in range(5):  # elephant statues lining the last of the road to the temple
        landmarks.append(prop("elephant_statue", (side * 9, -95 - k * 18), face=[0, -95 - k * 18], scale=1.1))
for x, z in [(-150, -160), (165, -175), (-215, 130), (210, 150), (-40, 200), (60, 210)]:
    landmarks.append(prop("floating_isle" if (x + z) % 3 else "floating_isle_b", (x, z), collide="none", scale=1.3))
for x, z in [(-120, 60), (110, 70), (-80, -110), (85, -95), (-30, 160), (40, 120)]:
    landmarks.append(prop("stone_lantern", (x, z), collide="box"))
for x, z in [(-190, 10), (-160, 55), (-200, 60)]:
    landmarks.append(prop("shrine_broken", (x, z), face=list(ROOST)))

roads = [
    {"points": [list(GATE), [0, 150], [0, 60], [-14, 0], [0, -60]], "width": 3.4},   # down from the gate, past the crater's lip
    {"points": [[0, -60], [0, -180]], "width": 3.4},                                  # on to the temple
    {"points": [[0, 110], [-90, 70], list(ROOST)], "width": 2.6},
    {"points": [[0, 110], [90, 70], list(CLOISTER)], "width": 2.6},
]

npcs = [
    {"id": "dawnkeeper_ilaya", "pos": [GATE[0] - 5, GATE[1] - 9], "face": [0, 200]},
    {"id": "sister_ashvara", "pos": [GATE[0] + 6, GATE[1] - 11], "face": [0, 200]},
    {"id": "dawn_avatar", "pos": [TEMPLE[0], TEMPLE[1] + 24], "face": [0, 0]},  # before his temple, looking down the road
]


def spawn(pos, pool, respawn=420, wander=6, **extra):
    s = {"pos": [round(pos[0], 1), round(pos[1], 1)], "pool": pool, "respawn": respawn, "wander": wander}
    s.update(extra)
    return s


spawns = [spawn(CRATER, {"the_dimming": 1}, respawn=2400, wander=0)]
for x, z in ring(CRATER, 9, 2, math.pi / 2):          # its court, close about it (two: each is an elite)
    spawns.append(spawn((x, z), {"dimming_shard": 1}, respawn=900, wander=2))
for x, z in ring(CRATER, 44, 7, 0.3):                 # what it's eaten, round the crater
    spawns.append(spawn((x, z), {"dr_dimmling": 3, "dr_hollow_light": 1}))
for x, z in ring(CLOISTER, 26, 6):
    spawns.append(spawn((x, z), {"dr_dimmed_sentinel": 2, "dr_hollow_light": 1}))
spawns.append(spawn(CLOISTER, {"dr_hollow_abbot": 1}, respawn=1800, wander=0))
for x, z in ring(ROOST, 30, 6, 0.4):
    spawns.append(spawn((x, z), {"dr_sunwyrm": 1}, wander=8))
spawns.append(spawn(ROOST, {"dr_goldmaw": 1}, respawn=1800, wander=0))
for x, z in [(-80, 170), (80, 175), (-130, 110), (130, 120), (-60, 60), (60, 40), (-150, -60), (150, -60), (-110, -150), (110, -150),
             (-200, -100), (200, -100)]:
    spawns.append(spawn((x, z), {"dr_dawnwing": 2, "dr_gilded_ram": 1}, wander=12))
for x, z in [(-50, -130), (50, -130), (-70, -170), (70, -170)]:   # the temple's approach, gone dim
    spawns.append(spawn((x, z), {"dr_dimmed_sentinel": 1, "dr_dimmling": 1}))

ZONE = {
    "name": "The Dawnreach",
    "realm": "dawnreach",
    "levels": [50, 52],
    # group content throughout (2026-10-03, Tyson: "the 50+ zones shouldn't be soloable"): every ordinary
    # monster here is an elite (Mob.make_elite). Measured with tools/balance.py --elite 4.5,2.6 --levels 50:
    # no class wins alone more than 3 fights in 12, and those spend 80% of their health and all their mana.
    "elite": {"health": 4.5, "damage": 2.6},
    "music": "grove",
    "seed": 2421,
    "size": SIZE,
    "height_amplitude": 4.0,
    "bind_point": [GATE[0], GATE[1] - 14],
    "flat_radius": 18,
    "fixed_hour": 6.4,
    "trees": 26,
    "tree_mix": ["grove_tree_a", "tree_round"],
    "groves": 0.2,
    "rocks": 50,
    "grass_colors": ["#9aae4a", "#cfc266"],
    "fog_density": 0.0025,
    "fog_color": "#f8dcc8",
    "sun_energy": 1.3,
    "clutter": {
        "grass_a": {"density": 0.35, "patch": 0.5, "sway": 0.16, "range": 50, "tint": "ground", "scale": [0.8, 1.3]},
        "flowers_yellow": {"density": 0.02, "patch": 0.8, "sway": 0.12, "range": 60, "scale": [0.9, 1.3]},
        "flowers_white": {"density": 0.015, "patch": 0.8, "sway": 0.12, "range": 60, "scale": [0.9, 1.3]},
    },
    "ground_patches": [
        {"pos": list(CRATER), "radius": 34, "color": "#2e2a36", "flatten": 0.7, "bare": True},   # the wound
        {"pos": [-250, 0], "radius": 60, "color": "#f4ece0", "flatten": 0.0, "bare": True},       # cloud banked against the west
        {"pos": [250, 0], "radius": 60, "color": "#f4ece0", "flatten": 0.0, "bare": True},
    ],
    "passes": [],
    "roads": roads,
    "road_lamps": 30,
    "zone_lines": [],
    "landmarks": landmarks,
    "npcs": npcs,
    "spawns": spawns,
}


def main():
    path = f"{ROOT}/data/items/dawn_line.json"
    with open(path, "w") as f:
        f.write("{\n" + ",\n".join("  %s: %s" % (json.dumps(k), json.dumps(v)) for k, v in ITEMS.items()) + "\n}\n")
    merge(f"{ROOT}/data/quests.json", QUESTS)
    merge(f"{ROOT}/data/mobs.json", MOBS)
    for mob_id, entry in RELICS:
        add_loot(f"{ROOT}/data/mobs.json", mob_id, entry)
    merge(f"{ROOT}/data/spells.json", SPELLS)
    merge(f"{ROOT}/data/factions.json", FACTIONS)
    merge(f"{ROOT}/data/npcs.json", NPCS)
    npcs_all = json.load(open(f"{ROOT}/data/npcs.json"))
    merge(f"{ROOT}/data/npcs.json", {k: {**npcs_all[k], **v} for k, v in NPC_PATCH.items()})
    with open(f"{ROOT}/data/zones/dawnreach.json", "w") as f:
        json.dump(ZONE, f, indent=2)
        f.write("\n")
    print(f"the Dawnreach: {len(spawns)} spawns, {len(landmarks)} landmarks; {len(QUESTS)} quests, {len(ITEMS)} items, {len(MOBS)} monsters")


if __name__ == "__main__":
    main()
