class_name SpawnPoint
extends Node3D
## Keeps one mob alive at this spot, picking from a weighted pool and
## respawning it a while after it dies.
##
## A quest boss's spot is a rare spawn, EverQuest style (Zone._build_spawns
## sets `rare`): mostly it puts up a placeholder (the `pool`, an ordinary
## monster of the camp around it), and each time it comes back there's a
## `rare_chance` the named comes instead; after `rare_pity` placeholders in a
## row the next is always the named.

## Tests (the autotest) keep the named always up, so older checks find them where they stand.
static var always_rare := "--autotest" in OS.get_cmdline_user_args()

var zone: Zone
var pool: Dictionary = {}  # mob_id -> weight
var respawn_time := 60.0
var wander_radius := 8.0
var when := ""  # "night" or "day": only up then (zone data "when"); at the turn a calm mob leaves
var mob: Mob = null
var yaw := NAN  # which way what spawns here faces (zone data "face": a web across a passage); else any way
var _timer := 0.0
var rare := ""  # the named this spot may put up instead of its placeholder; "" for an ordinary spot
var rare_misses := 0  # placeholders in a row since the named last came


func _ready() -> void:
	if active():
		spawn()


func active() -> bool:
	return when == "" or (when == "night") == World.is_night()


func _process(delta: float) -> void:
	if mob != null:
		if not active() and is_instance_valid(mob) and not mob.dead and mob.state != Mob.State.COMBAT and mob.hate.is_empty():
			mob.queue_free()  # the night's dead go back to their graves at dawn
			mob = null
			_timer = 0.0
		return
	if not active():
		return
	_timer -= delta
	if _timer <= 0.0:
		spawn()


func spawn() -> void:
	var mob_id := _pick()
	if rare != "":
		var chance := float(World.cfg("rare_chance", 0.2))
		if always_rare or rare_misses >= int(World.cfg("rare_pity", 8)) or randf() < chance:
			mob_id = rare
			rare_misses = 0
		else:
			rare_misses += 1
	mob = Mob.new()
	mob.setup(mob_id, GameData.mobs[mob_id], self)
	mob.position = position + Vector3.UP * 0.3
	mob.rotation.y = randf() * TAU if is_nan(yaw) else yaw
	zone.add_child(mob)


func on_mob_died() -> void:
	mob = null
	_timer = INF if respawn_time < 0.0 else respawn_time * randf_range(0.85, 1.15)  # < 0: never, until the zone is built again


## Whether a zone's spawn entry is a quest boss's rare spot, and if so
## {named, pool (its placeholder), alone (the named had the spot to itself)};
## empty when it isn't. The placeholder is the monsters of the nearest
## ordinary spawn up at the same time of day (or the rest of its pool, where
## the named was weighted into its camp's, as Grolthar's), unless the entry
## names its own "placeholder" {mob: weight}. Group bosses ("min_players")
## and finales ("always_up") stand always. The rules (Zone._make_rare) and
## the quest hints (QuestHints) both read it, so they never disagree.
static func rare_spot(spawns: Array, entry: Dictionary) -> Dictionary:
	var pool: Dictionary = entry["pool"]
	var bosses := pool.keys().filter(func(id: String) -> bool: return GameData.is_quest_boss(id))
	if bosses.size() != 1 or entry.get("always_up", false):
		return {}
	var named := str(bosses[0])
	var m: Dictionary = GameData.mobs[named]
	if m.has("min_players") or m.get("always_up", false):
		return {}
	var ph: Dictionary = entry.get("placeholder", {})
	var alone := pool.size() == 1
	if ph.is_empty() and not alone:
		ph = pool.duplicate()
		ph.erase(named)
	if ph.is_empty():
		var at := Vector2(float(entry["pos"][0]), float(entry["pos"][1]))
		var best := INF
		for other: Dictionary in spawns:
			var opool: Dictionary = other["pool"]
			if opool.keys().any(func(id: String) -> bool: return not GameData.mobs.has(id) or bool(GameData.mobs[id].get("named", false))):
				continue
			var d := at.distance_to(Vector2(float(other["pos"][0]), float(other["pos"][1])))
			if str(other.get("when", "")) != str(entry.get("when", "")):
				d += 1000.0  # a day spawn only stands in for a night named when nothing else will
			if d < best:
				best = d
				ph = opool
	if ph.is_empty():
		return {}
	return {"named": named, "pool": ph, "alone": alone}


func _pick() -> String:
	var total := 0.0
	for w: float in pool.values():
		total += w
	var roll := randf() * total
	for id: String in pool:
		roll -= float(pool[id])
		if roll <= 0.0:
			return id
	return pool.keys()[0]
