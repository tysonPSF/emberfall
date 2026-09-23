class_name SpawnPoint
extends Node3D
## Keeps one mob alive at this spot, picking from a weighted pool and
## respawning it a while after it dies.

var zone: Zone
var pool: Dictionary = {}  # mob_id -> weight
var respawn_time := 60.0
var wander_radius := 8.0
var mob: Mob = null
var _timer := 0.0


func _ready() -> void:
	spawn()


func _process(delta: float) -> void:
	if mob != null:
		return
	_timer -= delta
	if _timer <= 0.0:
		spawn()


func spawn() -> void:
	var mob_id := _pick()
	mob = Mob.new()
	mob.setup(mob_id, GameData.mobs[mob_id], self)
	mob.position = position + Vector3.UP * 0.3
	mob.rotation.y = randf() * TAU
	zone.add_child(mob)


func on_mob_died() -> void:
	mob = null
	_timer = respawn_time * randf_range(0.85, 1.15)


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
