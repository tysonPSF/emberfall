class_name Rain
extends Node3D
## Monsoon rain: streaks falling in a box that follows the camera, so it rains
## wherever you look without filling the whole zone. A zone turns it on with
## "rain": {"amount", "color"}; only machines that draw build it.

const BOX := Vector3(34, 1, 34)  # where drops start, around and above the camera
const HEIGHT := 16.0

var _drops: GPUParticles3D


func _init(settings: Dictionary) -> void:
	_drops = GPUParticles3D.new()
	_drops.amount = int(settings.get("amount", 2600))
	_drops.lifetime = 1.1
	_drops.preprocess = 1.1  # already raining when you arrive
	_drops.fixed_fps = 30
	_drops.visibility_aabb = AABB(Vector3(-BOX.x, -HEIGHT - 4.0, -BOX.z), Vector3(BOX.x * 2.0, HEIGHT + 8.0, BOX.z * 2.0))
	_drops.local_coords = false
	var mat := ParticleProcessMaterial.new()
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	mat.emission_box_extents = BOX
	mat.direction = Vector3(0.08, -1, 0.04)
	mat.spread = 2.0
	mat.initial_velocity_min = 15.0
	mat.initial_velocity_max = 18.0
	mat.gravity = Vector3(0, -6, 0)
	_drops.process_material = mat
	var streak := QuadMesh.new()
	streak.size = Vector2(0.025, 0.7)
	var look := StandardMaterial3D.new()
	look.shading_mode = BaseMaterial3D.SHADING_MODE_PER_VERTEX  # lit, so it darkens at night instead of glowing like snow
	look.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	look.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y  # faces you, stays upright along the fall
	look.albedo_color = Color.html(str(settings.get("color", "#c8d4dccc")))
	look.cull_mode = BaseMaterial3D.CULL_DISABLED
	streak.material = look
	_drops.draw_pass_1 = streak
	add_child(_drops)


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam != null:
		_drops.global_position = cam.global_position + Vector3.UP * HEIGHT * 0.6
