class_name Projectile
extends Node3D
## What a ranged attack looks like: an arrow or stone flying from the shooter
## to the target (the hit or miss is already decided; this is only the
## picture). Kinds are models.json "projectiles": a scene path, or "" for a
## plain stone.

const SPEED := 38.0
const ARC := 0.08  # rise per meter flown, at the midpoint

var _to: Entity
var _start: Vector3
var _dist := 1.0
var _flown := 0.0


## World.shot_fired lands here on every machine that draws (never a server).
static func launch(from: Entity, to: Entity, kind: String) -> void:
	var zone := World.zone_of(from)
	if zone == null or zone != World.zone_of(to):
		return
	var p := Projectile.new()
	p._to = to
	p._start = from.global_position + Vector3.UP * 1.1 + from.global_basis.z * -0.4
	var path := str(GameData.models.get("projectiles", {}).get(kind, ""))
	if path != "":
		var model: Node3D = (load(path) as PackedScene).instantiate()
		model.rotation_degrees.x = -90.0  # the arrow model points up; fly it nose first
		model.scale = Vector3.ONE * 0.75
		p.add_child(model)
	else:
		var stone := MeshInstance3D.new()
		var mesh := SphereMesh.new()
		mesh.radius = 0.1
		mesh.height = 0.18
		stone.mesh = mesh
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.45, 0.43, 0.4)
		stone.material_override = mat
		p.add_child(stone)
	zone.add_child(p)
	p.global_position = p._start


func _process(delta: float) -> void:
	if not is_instance_valid(_to):
		queue_free()
		return
	var end := _to.global_position + Vector3.UP * 0.7
	_dist = maxf(_start.distance_to(end), 0.5)
	_flown += SPEED * delta
	var f := minf(_flown / _dist, 1.0)
	var pos := _start.lerp(end, f) + Vector3.UP * ARC * _dist * 4.0 * f * (1.0 - f)
	if pos.distance_to(global_position) > 0.001:
		look_at(pos, Vector3.UP)
	global_position = pos
	if f >= 1.0:
		queue_free()
