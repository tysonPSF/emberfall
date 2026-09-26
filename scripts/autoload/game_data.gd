extends Node
## Static game content loaded from res://data. Content lives in JSON so it can
## be tuned without touching code, and so a future dedicated server loads
## exactly the same data as the client.

var config: Dictionary = {}
var classes: Dictionary = {}
var spells: Dictionary = {}
var mobs: Dictionary = {}
var items: Dictionary = {}
var models: Dictionary = {}
var npcs: Dictionary = {}
var quests: Dictionary = {}
var recipes: Dictionary = {}  # data/recipes.json: "recipes" and "containers"
var pets: Dictionary = {}  # data/pets.json: tiers, base stats, kinds
var factions: Dictionary = {}
var deities: Dictionary = {}
var loot: Dictionary = {}
var skills: Dictionary = {}
var _icons: Dictionary = {}  # base item id -> Texture2D or null


func _ready() -> void:
	config = _load("res://data/config.json")
	classes = _load("res://data/classes.json")
	spells = _load("res://data/spells.json")
	mobs = _load("res://data/mobs.json")
	items = _load_dir("res://data/items")
	models = _load("res://data/models.json")
	npcs = _load("res://data/npcs.json")
	quests = _load("res://data/quests.json")
	recipes = _load("res://data/recipes.json")
	pets = _load("res://data/pets.json")
	factions = _load("res://data/factions.json")
	deities = _load("res://data/deities.json")
	loot = _load("res://data/loot.json")
	skills = _load("res://data/skills.json")


## A deity's benefit, or 0 when the player has none or it grants something else.
func deity_bonus(deity_id: String, key: String) -> float:
	return float(deities.get(deity_id, {}).get("bonus", {}).get(key, 0))


## A deity's portrait, cut from the shared atlas.
func deity_portrait(deity_id: String) -> AtlasTexture:
	var tex := AtlasTexture.new()
	tex.atlas = load("res://assets/deities/deities_128.png")
	var at: Array = deities[deity_id]["portrait"]
	tex.region = Rect2(float(at[0]), float(at[1]), 128, 128)
	return tex


func load_zone(zone_id: String) -> Dictionary:
	return _load("res://data/zones/%s.json" % zone_id)


## How high a class can raise a skill at a level: per_level x (level + 1),
## never above the table's max; 0 if the class can't learn it.
func skill_cap(cls: String, skill_id: String, level: int) -> int:
	var spec: Dictionary = skills.get("skills", {}).get(skill_id, {})
	if spec.has("flat"):  # tradeskills: the same cap for everyone at every level
		return int(spec["flat"])
	if level < int(spec.get("from", {}).get(cls, 0)):
		return 0  # learned later (Dual Wield at 13)
	var per := int(spec.get("caps", {}).get(cls, 0))
	return mini(per * (level + 1), int(skills["tuning"]["max"]))


## An item's inventory icon (rendered by tools/blender/icons.py), shared by
## every quality of it; null if there is none.
func item_icon(item_id: String) -> Texture2D:
	return icon(base_item(item_id))


## Any rendered icon in assets/icons by name ("gnoll_fang", "spell_kick",
## "action_attack"), or null. Loaded once.
func icon(icon_name: String) -> Texture2D:
	if not _icons.has(icon_name):
		var path := "res://assets/icons/%s.png" % icon_name
		_icons[icon_name] = load(path) if ResourceLoader.exists(path) else null
		for prefix: String in ["spell_meal_", "spell_potion_"]:  # a meal's or potion's buff shows the dish or the bottle
			if _icons[icon_name] == null and icon_name.begins_with(prefix):
				_icons[icon_name] = icon(icon_name.trim_prefix(prefix))
	return _icons[icon_name]


func skill_name(skill_id: String) -> String:
	return str(skills.get("skills", {}).get(skill_id, {}).get("name", skill_id))


func item_name(item_id: String) -> String:
	return str(item(item_id).get("name", item_id))


## An item's stats. Dropped gear carries a quality after an "@" in its id
## ("iron_dagger@fine"), which renames it and scales its damage, armor, hit
## points, mana and value by that tier in data/loot.json.
func item(item_id: String) -> Dictionary:
	var at := item_id.find("@")
	if at < 0:
		return items.get(item_id, {})
	var base: Dictionary = items.get(item_id.left(at), {})
	var tier := quality_tier(item_id)
	if base.is_empty() or tier.is_empty():
		return base
	var out := base.duplicate()
	out["name"] = "%s %s" % [tier["name"], base["name"]]
	var mult := float(tier["stat_mult"])
	for stat: String in ["dmg", "ac", "hp", "mana", "str", "sta", "agi", "wis", "int", "haste", "hp_regen", "mana_regen"]:
		if out.has(stat):
			var v := int(out[stat])
			# every better tier adds at least one point, every worse one keeps at least one
			out[stat] = maxi(v + 1, roundi(v * mult)) if mult > 1.0 else maxi(mini(v, 1), roundi(v * mult))
	out["value"] = roundi(float(base.get("value", 0)) * float(tier["value_mult"]))
	return out


## The item id without its quality ("iron_dagger@fine" -> "iron_dagger").
## How much one of an item weighs: its own "weight", or a sensible default for
## what it is (a dagger 1.5, a sword 4, plate much more than cloth, a pelt
## 1.5, jewelry and arrows next to nothing).
func item_weight(item_id: String) -> float:
	var it := item(item_id)
	if it.has("weight"):
		return float(it["weight"])
	var slot := str(it.get("slot", ""))
	var name_ := str(it.get("name", "")).to_lower()
	var skill := str(it.get("skill", ""))
	if it.has("bag"):
		return 0.6 if int(it["bag"]) <= 4 else 1.5
	if it.has("ammo_type"):
		return 0.1
	if slot == "primary":
		if skill == "piercing":
			return 1.5
		if skill.begins_with("2h") or "staff" in name_:
			return 6.0
		return 5.0 if "axe" in name_ or "cleaver" in name_ else 4.0
	if slot == "range":
		return 3.0 if str(it.get("skill", "")) == "archery" else 0.5
	if slot == "secondary":
		return 8.0 if "kite" in name_ or "steel" in name_ else 6.0
	if slot in ["neck", "ring"]:
		return 0.1
	if slot != "":
		var wear := str(it.get("wear", ""))
		var heavy := "iron" in wear or "steel" in name_ or "iron" in name_ or "plate" in name_
		var light := "cloth" in wear or "patchwork" in wear or "robe" in name_ or "weave" in name_ or "floppy" in wear or "sandal" in wear or "rope" in wear
		var base: float = {"chest": 5.0, "legs": 4.0, "arms": 2.0, "head": 1.5, "hands": 1.0, "feet": 2.0, "waist": 0.5}.get(slot, 1.0)
		return base * (2.4 if heavy else (0.4 if light else 1.0))
	for bulky: String in ["pelt", "hide", "fleece", "shell", "skin"]:
		if bulky in name_:
			return 1.5
	return 0.2


func base_item(item_id: String) -> String:
	return item_id.get_slice("@", 0)


## The quality tier of an item id, or {} for plain items.
func quality_tier(item_id: String) -> Dictionary:
	var q := item_id.get_slice("@", 1) if item_id.contains("@") else ""
	for tier: Dictionary in loot.get("quality", {}).get("tiers", []):
		if str(tier["id"]) == q:
			return tier
	return {}


## {slot: tier id} for the equipped items that have a quality, for the look.
func gear_tiers(equipped: Dictionary) -> Dictionary:
	var out := {}
	for slot: String in equipped:
		var id := str(equipped[slot])
		if id.contains("@"):
			out[slot] = id.get_slice("@", 1)
	return out


## How a quality tier finishes gear on a character ({} for plain).
func tier_finish(tier_id: String) -> Dictionary:
	if tier_id == "":
		return {}
	for tier: Dictionary in loot.get("quality", {}).get("tiers", []):
		if str(tier["id"]) == tier_id:
			return tier.get("finish", {})
	return {}


## Display color for an item's name, by quality.
func item_color(item_id: String) -> Color:
	var tier := quality_tier(item_id)
	return Color.html(str(tier.get("color", "#e6e0d2")))


## Merges every .json file in a folder, so content can be split by topic (and
## by author) without merge conflicts. An id defined twice is an error.
func _load_dir(dir: String) -> Dictionary:
	var out := {}
	var files := Array(DirAccess.get_files_at(dir)).filter(func(f: String) -> bool: return f.get_extension() == "json")
	files.sort()
	for f: String in files:
		var part := _load(dir.path_join(f))
		for id: String in part:
			if out.has(id):
				push_error("%s: %s is already defined in another file" % [f, id])
			out[id] = part[id]
	return out


func _load(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Failed to parse %s" % path)
		return {}
	return parsed
