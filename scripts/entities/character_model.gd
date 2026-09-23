class_name CharacterModel
extends Node3D
## A rigged KayKit character. Every Rig_Medium model shares one animation
## library, a weapon rides on the right-hand slot bone, and the animation is
## chosen each frame from the owning Entity's state.

const MODEL_SCALE := 0.75
const BLEND := 0.18
const LOOPING: Array[String] = ["Idle_A", "Idle_B", "Walking_A", "Walking_B", "Running_A", "Running_B", "Use_Item", "Jump_Idle"]
const ATTACK_ANIM := "Throw"
const HIT_ANIM := "Hit_A"
const SIT_ANIM := "PickUp"
const SIT_FRAME := 0.55

static var _library: AnimationLibrary

var anim: AnimationPlayer
var skeleton: Skeleton3D
var _weapon_slot: BoneAttachment3D
var _weapon_id := ""
var _one_shot_left := 0.0
var _posed_dead := false


static func library() -> AnimationLibrary:
	if _library == null:
		_library = AnimationLibrary.new()
		for src: String in GameData.models["animations"]:
			var inst: Node = (load(src) as PackedScene).instantiate()
			var ap := inst.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
			for anim_name in ap.get_animation_list():
				if _library.has_animation(anim_name):
					continue
				var a := ap.get_animation(anim_name).duplicate() as Animation
				if anim_name in LOOPING:
					a.loop_mode = Animation.LOOP_LINEAR
				_library.add_animation(anim_name, a)
			inst.free()
	return _library


func setup(model_id: String, weapon_id: String, body_scale: float) -> void:
	var path: String = GameData.models["characters"][model_id]
	var model: Node3D = (load(path) as PackedScene).instantiate()
	model.rotation.y = PI  # glTF faces +Z; Godot's forward is -Z
	add_child(model)
	scale = Vector3.ONE * MODEL_SCALE * body_scale
	skeleton = model.find_child("Skeleton3D", true, false) as Skeleton3D
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	anim = AnimationPlayer.new()
	model.add_child(anim)
	anim.root_node = NodePath("..")
	anim.add_animation_library("", library())
	set_weapon(weapon_id)


func set_weapon(weapon_id: String) -> void:
	if weapon_id == _weapon_id or skeleton == null:
		return
	_weapon_id = weapon_id
	if _weapon_slot != null:
		_weapon_slot.queue_free()
		_weapon_slot = null
	if weapon_id == "" or not GameData.models["weapons"].has(weapon_id):
		return
	_weapon_slot = BoneAttachment3D.new()
	_weapon_slot.bone_name = "handslot.r"
	skeleton.add_child(_weapon_slot)
	_weapon_slot.add_child((load(GameData.models["weapons"][weapon_id]) as PackedScene).instantiate())


## Plays a non-looping animation over the idle (attack swing, flinch, spawn).
func play_once(anim_name: String, speed := 1.0, interrupt := true) -> void:
	if _posed_dead or not anim.has_animation(anim_name):
		return
	if not interrupt and _one_shot_left > 0.0:
		return
	anim.play(anim_name, BLEND * 0.5, speed)
	_one_shot_left = anim.get_animation(anim_name).length / speed


## Falls over and stays down (corpses).
func pose_dead(instant := false) -> void:
	_posed_dead = true
	if instant:
		anim.play("Death_A_Pose")
	else:
		anim.play("Death_A", 0.1)


func _process(delta: float) -> void:
	if _posed_dead:
		return
	var e := get_parent() as Entity
	if e == null:
		return
	_one_shot_left -= delta
	var moving := Vector2(e.velocity.x, e.velocity.z).length()
	if not e.is_on_floor() and absf(e.velocity.y) > 2.0:
		_loop("Jump_Idle")
	elif moving > 4.2:
		_loop("Running_A")
	elif moving > 0.3:
		_loop("Walking_A")
	elif _one_shot_left > 0.0:
		return
	elif not e.cast.is_empty():
		_loop("Use_Item")
	elif e.sitting:
		if anim.assigned_animation != SIT_ANIM or anim.is_playing():
			anim.play(SIT_ANIM, 0.0)  # no blend: pausing mid-blend would freeze the old pose
			anim.seek(SIT_FRAME, true)
			anim.pause()
	else:
		_loop("Idle_A")


func _loop(anim_name: String) -> void:
	_one_shot_left = 0.0
	if anim.current_animation != anim_name or not anim.is_playing():
		anim.play(anim_name, BLEND)
