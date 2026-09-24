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
	return str(items.get(item_id, {}).get("name", item_id))


func _load(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Failed to parse %s" % path)
		return {}
	return parsed
