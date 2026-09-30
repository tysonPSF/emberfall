class_name StatPicker
extends VBoxContainer
## EverQuest-style starting stats: every stat starts at `stat_base` (75) and
## you spend `stat_points` (25) on top, at most `stat_point_max` (15) in one.
## A row per stat shows its value, - and + buttons and what the points do; the
## class's key stats are gold, "Recommended" fills in the class's spread and
## "Reset" empties it. Used by character creation and, for characters from
## before stats, by the HUD's one-time window. `points` is what to save.

signal changed

const STATS := ["str", "sta", "agi", "wis", "int"]
const NAMES := {"str": "Strength", "sta": "Stamina", "agi": "Agility", "wis": "Wisdom", "int": "Intelligence"}

var points := {}
var class_id := "warrior"
var race_id := "human"  # the race's stats are where each row starts
var _rows := {}  # stat -> [name label, value label, minus, plus, effect label]
var _left: Label


func _init() -> void:
	add_theme_constant_override("separation", 3)


func _ready() -> void:
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 8)
	_left = UIKit.label("", 14, UIKit.GOLD)
	_left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(_left)
	var rec := UIKit.button("Recommended", Vector2(0, 26))
	rec.add_theme_font_size_override("font_size", 12)
	rec.tooltip_text = "Spend the points the way this class usually does."
	rec.pressed.connect(func() -> void: set_class(class_id, true))
	UIKit.frame(rec)
	head.add_child(rec)
	var reset := UIKit.button("Reset", Vector2(0, 26))
	reset.add_theme_font_size_override("font_size", 12)
	reset.pressed.connect(func() -> void:
		points = {}
		_refresh())
	UIKit.frame(reset)
	head.add_child(reset)
	add_child(head)
	for stat: String in STATS:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)
		var name := UIKit.label(NAMES[stat], 14)
		name.custom_minimum_size.x = 104
		var value := UIKit.label("", 15, UIKit.TEXT)
		value.custom_minimum_size.x = 64
		var minus := UIKit.button("-", Vector2(28, 26))
		var plus := UIKit.button("+", Vector2(28, 26))
		var effect := UIKit.label("", 12, UIKit.DIM)
		effect.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		minus.pressed.connect(func() -> void: _add(stat, -1))
		plus.pressed.connect(func() -> void: _add(stat, 1))
		for b: Button in [minus, plus]:
			UIKit.frame(b)
			b.add_theme_font_size_override("font_size", 14)
		row.add_child(name)
		row.add_child(minus)
		row.add_child(value)
		row.add_child(plus)
		row.add_child(effect)
		add_child(row)
		_rows[stat] = [name, value, minus, plus, effect]
	_refresh()


## Switches to a class; its recommended spread fills in when `preset` (or when nothing is spent yet).
func set_class(id: String, preset := false) -> void:
	class_id = id
	if preset or points.is_empty():
		points = {}
		var spread: Dictionary = GameData.classes[id].get("stat_preset", {})
		for stat: String in spread:
			points[stat] = int(spread[stat])
	if is_inside_tree() and not _rows.is_empty():
		_refresh()


func set_race(id: String) -> void:
	race_id = id if GameData.races.has(id) else "human"
	if is_inside_tree() and not _rows.is_empty():
		_refresh()


func base(stat: String) -> int:
	return int(GameData.races.get(race_id, {}).get("stats", {}).get(stat, World.cfg("stat_base", 75)))


func points_left() -> int:
	var spent := 0
	for n: int in points.values():
		spent += n
	return int(World.cfg("stat_points", 25)) - spent


func _add(stat: String, by: int) -> void:
	var n := int(points.get(stat, 0)) + by
	if n < 0 or n > int(World.cfg("stat_point_max", 15)) or (by > 0 and points_left() <= 0):
		return
	if n == 0:
		points.erase(stat)
	else:
		points[stat] = n
	_refresh()


func _refresh() -> void:
	var cls: Dictionary = GameData.classes.get(class_id, {})
	var key: Array = cls.get("key_stats", [])
	var cap := int(World.cfg("stat_point_max", 15))
	_left.text = "Points to spend: %d" % points_left()
	for stat: String in STATS:
		var r: Array = _rows[stat]
		var n := int(points.get(stat, 0))
		(r[0] as Label).add_theme_color_override("font_color", UIKit.GOLD if stat in key else UIKit.TEXT)
		(r[0] as Label).tooltip_text = "A key stat for your class." if stat in key else ""
		(r[1] as Label).text = "%d%s" % [base(stat) + n, "  (+%d)" % n if n > 0 else ""]
		(r[2] as Button).disabled = n <= 0
		(r[3] as Button).disabled = n >= cap or points_left() <= 0
		(r[4] as Label).text = effect_text(stat, n, cls)
	changed.emit()


## What `n` points in a stat do for this class, in plain words.
static func effect_text(stat: String, n: int, cls: Dictionary) -> String:
	match stat:
		"str":
			return "+%d max damage, carry +%d" % [n / 5, roundi(n * float(World.cfg("carry_per_str", 3)))] if n > 0 else "damage and carrying"
		"sta":
			return "+%d health, +%d stamina" % [n, n] if n > 0 else "health and stamina"
		"agi":
			return "+%d armor" % (n / 2) if n > 0 else "armor"
		"wis", "int":
			if str(cls.get("caster_stat", "")) != stat:
				return "(your class doesn't cast with it)"
			if n <= 0:
				return "mana, regen, spell power"
			var text := "+%d mana, +%s%% spell power" % [n, str(snappedf(n * float(World.cfg("caster_power_per_point", 0.001)) * 100.0, 0.1))]
			var regen := n / maxi(1, int(World.cfg("caster_regen_per", 20)))
			return text + (", +%d mana regen" % regen if regen > 0 else ", fewer fizzles")
	return ""
