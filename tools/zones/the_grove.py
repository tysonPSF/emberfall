"""Writes data/zones/the_grove.json and the Grove's npcs into data/npcs.json.

The daises, the gods standing on them and their attendants all come from the
same bearings, so they can't drift apart. --placeholder swaps the Grove's own
art for existing pieces (for testing before the art lands).
"""
import json, math, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLACEHOLDER = "--placeholder" in sys.argv

POND_R = 19.0
DAIS_R = 37.0          # dais centers from the pond's center
DAIS_TOP = float(os.environ.get("DAIS_TOP", "0.8"))
GOD_SIZE = [float(x) for x in os.environ.get("GOD_SIZE", "3.0,8.5").split(",")]
ARRIVE = (0.0, 92.0)
ARCH = (0.0, 103.0)

# bearing: 0 = east, 90 = north (engine -z). Light opposite the arch, the
# rest every 72 degrees; the arch looks in through the gap between the
# Tide-Trunked (southwest) and the Unlit (southeast).
GODS = [
    ("light", 90), ("wind", 18), ("dark", 306), ("water", 234), ("fire", 162),
]


def at(bearing, r):
    a = math.radians(bearing)
    return [round(r * math.cos(a), 2), round(-r * math.sin(a), 2)]


def prop(pid, pos, face=None, yaw=None, collide="box", scale=None):
    lm = {"type": "prop", "pos": pos, "id": pid, "collide": collide}
    if face is not None:
        lm["face"] = face
    if yaw is not None:
        lm["yaw"] = yaw
    if scale is not None:
        lm["scale"] = scale
    return lm


def art(pid):
    if not PLACEHOLDER:
        return pid
    return {"grove_tree_a": "jungle_tree", "grove_tree_b": "tree_round", "tusk_arch": "temple_arch_ruin"}.get(pid)


landmarks = [{"type": "grove", "pos": [0, 0], "radius": POND_R, "lotus": 22}]
npcs = []

for deity, b in GODS:
    d = at(b, DAIS_R)
    if art(f"grove_dais_{deity}"):
        landmarks.append(prop(f"grove_dais_{deity}", d, face=[0, 0], collide="mesh"))
    npcs.append({"id": f"grove_{deity}", "pos": d, "face": [0, 0], "y": DAIS_TOP + 0.1})
    npcs.append({"id": f"grove_{deity}_attendant", "pos": at(b + 11, DAIS_R - 9.5), "face": [0, 0]})

# the ancient trees ringing the clearing
for k in range(12):
    b = k * 30 + 15 + (7 if k % 2 else -5)
    pid = art("grove_tree_a" if k % 2 == 0 else "grove_tree_b")
    if pid:
        landmarks.append(prop(pid, at(b, 66 + (k * 7) % 11), yaw=(k * 47) % 360, collide="mesh",
                              scale=1.0 if not PLACEHOLDER else 2.2))

# the arrival: the tusk arch, a stepping-stone path to the water
if art("tusk_arch"):
    landmarks.append(prop(art("tusk_arch"), list(ARCH), face=[0, 0], collide="mesh"))
if art("grove_stepping_stone"):
    z = ARRIVE[1] - 5
    k = 0
    while z > POND_R + 4:
        landmarks.append(prop("grove_stepping_stone", [round(0.9 * math.sin(k * 1.7), 2), round(z, 2)], yaw=(k * 53) % 360, collide="none"))
        z -= 2.6
        k += 1

npcs.append({"id": "grove_keeper", "pos": [5.5, 88.0], "face": [0, 92]})

pond = [at(i * 360 / 20, POND_R * (1.0 + 0.06 * math.sin(i * 2.3))) for i in range(20)]

zone = {
    "name": "The Grove",
    "music": "grove",
    "seed": 5151,
    "size": 256,
    "fixed_hour": 7.1,
    "height_amplitude": 1.4,
    "bind_point": list(ARRIVE),
    "flat_radius": 30,
    "clear_radius": 60,
    "trees": 70,
    "tree_mix": ["jungle_tree", "tree_round", "tree_round", "jungle_tree"],
    "groves": 0.35,
    "rocks": 14,
    "grass_colors": ["#6f9a3c", "#8fae4a"],
    "fog_density": 0.0025,
    "fog_color": "#f4e4c4",
    "sun_energy": 1.5,
    "clutter": {
        "grass_a": {"density": 0.36, "patch": 0.5, "sway": 0.2, "range": 55, "tint": "ground", "scale": [0.8, 1.3]},
        "grass_b": {"density": 0.26, "patch": 0.4, "sway": 0.18, "range": 50, "tint": "ground", "scale": [0.8, 1.25]},
        "flowers_white": {"density": 0.02, "patch": 0.7, "sway": 0.12, "range": 50, "scale": [0.8, 1.2]},
        "flowers_yellow": {"density": 0.018, "patch": 0.7, "sway": 0.12, "range": 50, "scale": [0.8, 1.2]},
        "fern": {"density": 0.02, "patch": 0.8, "sway": 0.08, "range": 50, "scale": [0.9, 1.5]},
    },
    "lakes": [{"points": pond, "depth": 2.2, "shelf": 5, "bank": 6}],
    "landmarks": landmarks,
    "npcs": npcs,
    "spawns": [],
}

with open(f"{ROOT}/data/zones/the_grove.json", "w") as f:
    json.dump(zone, f, indent=2)
    f.write("\n")

# ---------------------------------------------------------------- npcs

GOD_TEXT = {
    "light": {
        "hail": "You found the way here, {name}, and the light found you on the way. I am Prabhagaj, the Dawn-Tusk. I stood at the edge of the first morning and watched the world decide to be seen. Rest by the [water]. Everything here is looked at by me, and none of it minds.",
        "water": "Jalendra's. She let me put the morning on it. She lets very few things touch it, so I am careful with the light.",
        "grove": "This is where the five of us stand when the world does not need us standing somewhere else. It is a [circle] for a reason: none of us is first.",
        "circle": "Five places around the water. Mine faces the way you came in, so the first thing anyone sees here is the light. The others would tell you that was my idea. It was.",
        "unknown": "Say it again, slower. I see well; I listen less well than I should.",
    },
    "water": {
        "hail": "The water made room for you before you arrived, {name}. That is my welcome; I do not give another. I am Jalendra, the Tide-Trunked. The [pond] is mine, and the rain that feeds it, and every river that leaves here for the world.",
        "pond": "Look into it. Not at your face; past it. Every river in the world starts here as a thought. Most of them do not know it.",
        "grove": "We come here to be still. It is harder for some of us than others. Vayuketh has never stood still in his life.",
        "unknown": "The water does not answer that. Neither will I.",
    },
    "fire": {
        "hail": "Stand closer, {name}. Warmth is wasted on the cautious. I am Agnavar, the Ember-Tusked. Every [flame] that refused to go out has had my name in it, whether the one tending it knew or not.",
        "flame": "The forge in Forgehold. The hearth in Emberhold. A campfire in the rain that a tired traveler would not let die. Mine, all of them. I keep count.",
        "grove": "The others like the morning here. I like that it never becomes day. Nothing here ever finishes burning.",
        "unknown": "Mm. Speak up. The fire is loud.",
    },
    "wind": {
        "hail": "Breathe, {name}. No, deeper. There. That was me, going in and coming out again. I am Vayuketh, He Who Breathes the Plains. I never stay anywhere long, but I always come back to the [grass] by this water.",
        "grass": "It bends when I exhale. That is not obedience; it is agreement. Remember the difference.",
        "grove": "The one place I stop. Do not tell the others it is my favorite. They each think it is theirs.",
        "unknown": "Gone past me on the wind, that one. Try again.",
    },
    "dark": {
        "hail": "{name}. I have your name already; I keep every one. I am Timiraj, the Unlit. The others stand in the morning here. I stand where it has not reached yet. Do not be afraid of the [dark]. It is only where you rest.",
        "dark": "Every elephant comes to me at the end. I remember each of them. That is not the comfort it sounds like, but it is not nothing.",
        "grove": "Even here the morning never quite arrives at my side of the water. That is how I like it, and the Dawn-Tusk has stopped trying.",
        "unknown": "Silence answers most things better. It answers that one too.",
    },
}

ATTENDANTS = {
    "light": ("Dawn-Herald Mireya", "Herald of the Dawn-Tusk", "knight", "sword_1handed",
              "Morning, {name}. It is always morning here; you'll stop noticing. I carry Prabhagaj's word when he's busy looking at something, which is always."),
    "water": ("Tide-Singer Neelam", "Voice of the Tide-Trunked", "mage", "staff",
              "Softly, {name}. She hears everything the water touches, and the water here touches everything. I sing to it so she knows who is coming."),
    "fire": ("Ember-Warden Brask", "Warden of the Ember-Tusked", "barbarian", "axe_2handed",
             "Warm yourself, {name}. I keep the embers on his dais fed. He'd do it himself, but a god tending his own fire looks like vanity."),
    "wind": ("Wind-Runner Saoirse", "Runner for He Who Breathes", "ranger", "bow",
             "You made it, {name}! I carry his messages. He never gives them to me here, of course; he gives them to me halfway across the world and expects me to be quick."),
    "dark": ("Night-Sister Oona", "Keeper of the Unlit's Names", "necromancer", "staff",
             "Quietly, {name}. I write down the names he remembers, so he does not have to carry every one alone. Yours is in the book already. Everyone's is."),
}

GOD_LOOK = {"light": "deity_light", "water": "deity_water", "fire": "deity_fire", "wind": "deity_wind", "dark": "deity_dark"}

CHARACTERS = json.load(open(f"{ROOT}/data/models.json"))["characters"]
path = f"{ROOT}/data/npcs.json"
all_npcs = json.load(open(path))
deities = json.load(open(f"{ROOT}/data/deities.json"))
for deity, _ in GODS:
    god = deities[deity]
    all_npcs[f"grove_{deity}"] = {
        "name": god["name"],
        "title": god["title"][0].upper() + god["title"][1:],
        "level": 99,
        "model": GOD_LOOK[deity] if GOD_LOOK[deity] in CHARACTERS else "herd_grandmother",
        "faction": "grove",
        "grove_deity": deity,
        "sacred": True,
        "fixed": True,
        "size": GOD_SIZE,
        "dialogue": GOD_TEXT[deity],
    }
    name, title, model, weapon, hail = ATTENDANTS[deity]
    all_npcs[f"grove_{deity}_attendant"] = {
        "name": name,
        "title": title,
        "level": 60,
        "model": model,
        "weapon": weapon,
        "faction": "grove",
        "grove_deity": deity,
        "sacred": True,
        "dialogue": {"hail": hail, "unknown": "Ask the god, {name}. I only carry the words."},
    }
all_npcs["grove_keeper"] = {
    "name": "Mahout Anandi",
    "title": "Keeper of the Grove",
    "level": 60,
    "model": "ranger",
    "weapon": "staff",
    "faction": "grove",
    "sacred": True,
    "grove_return": True,
    "dialogue": {
        "hail": "Welcome to the Grove, {name}. Mind the water; it's older than the gods standing round it. I keep the path and the arch. The gods come to the [circle] when they're ready to meet you, and when you want to go, say [return] and I'll walk you back the way you came.",
        "circle": "Five daises round the pond, one for each of them. Some stand empty for a traveler until they've earned the god who stands there. It is not a slight; it's an invitation.",
        "return": "Hold my arm, {name}. Eyes shut. ...There.",
        "unknown": "I'm only the keeper, {name}. The gods know more than I do, and say less.",
    },
}
with open(path, "w") as f:
    f.write(json.dumps(all_npcs, indent=2) + "\n")
print("wrote the_grove.json (%d landmarks, %d npcs)%s" % (len(landmarks), len(npcs), " with placeholders" if PLACEHOLDER else ""))
