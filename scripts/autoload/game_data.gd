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
var factions: Dictionary = {}
var deities: Dictionary = {}
var loot: Dictionary = {}


func _ready() -> void:
	config = _load("res://data/config.json")
	classes = _load("res://data/classes.json")
	spells = _load("res://data/spells.json")
	mobs = _load("res://data/mobs.json")
	items = _load("res://data/items.json")
	models = _load("res://data/models.json")
	npcs = _load("res://data/npcs.json")
	quests = _load("res://data/quests.json")
	factions = _load("res://data/factions.json")
	deities = _load("res://data/deities.json")
	loot = _load("res://data/loot.json")


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
	for stat: String in ["dmg", "ac", "hp", "mana"]:
		if out.has(stat):
			var v := int(out[stat])
			# every better tier adds at least one point, every worse one keeps at least one
			out[stat] = maxi(v + 1, roundi(v * mult)) if mult > 1.0 else maxi(mini(v, 1), roundi(v * mult))
	out["value"] = roundi(float(base.get("value", 0)) * float(tier["value_mult"]))
	return out


## The item id without its quality ("iron_dagger@fine" -> "iron_dagger").
func base_item(item_id: String) -> String:
	return item_id.get_slice("@", 0)


## The quality tier of an item id, or {} for plain items.
func quality_tier(item_id: String) -> Dictionary:
	var q := item_id.get_slice("@", 1) if item_id.contains("@") else ""
	for tier: Dictionary in loot.get("quality", {}).get("tiers", []):
		if str(tier["id"]) == q:
			return tier
	return {}


## Display color for an item's name, by quality.
func item_color(item_id: String) -> Color:
	var tier := quality_tier(item_id)
	return Color.html(str(tier.get("color", "#e6e0d2")))


func _load(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Failed to parse %s" % path)
		return {}
	return parsed
