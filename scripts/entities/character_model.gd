class_name CharacterModel
extends Node3D
## A rigged character. Game code asks for actions ("idle", "walk", "attack"...)
## and each rig maps them to its own clips. KayKit Rig_Medium models share one
## animation library and carry weapons on the right-hand slot bone; models with
## `"rig": "own"` in models.json (our Blender creatures) bring their own clips,
## named after the actions directly.

const KAYKIT_SCALE := 0.75
const BLEND := 0.18
const SIT_FRAME := 0.55
const LOOPING: Array[String] = ["idle", "walk", "run", "cast", "jump"]
const KAYKIT_ANIMS := {
	"idle": "Idle_A", "walk": "Walking_A", "run": "Running_A", "jump": "Jump_Idle",
	"attack": "Throw", "hit": "Hit_A", "death": "Death_A", "dead": "Death_A_Pose",
	"sit": "PickUp", "cast": "Use_Item",
}

static var _library: AnimationLibrary

var anim: AnimationPlayer
var skeleton: Skeleton3D
var _clips: Dictionary = {}  # action -> clip name in `anim`
var _weapon_slot: BoneAttachment3D
var _weapon_id := ""
var _one_shot_left := 0.0
var _posed_dead := false


static func library() -> AnimationLibrary:
	if _library == null:
		_library = AnimationLibrary.new()
		var looping: Array = LOOPING.map(func(a: String) -> String: return KAYKIT_ANIMS[a])
		for src: String in GameData.models["animations"]:
			var inst: Node = (load(src) as PackedScene).instantiate()
			var ap := inst.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
			for anim_name in ap.get_animation_list():
				if _library.has_animation(anim_name):
					continue
				var a := ap.get_animation(anim_name).duplicate() as Animation
				if anim_name in looping:
					a.loop_mode = Animation.LOOP_LINEAR
				_library.add_animation(anim_name, a)
			inst.free()
	return _library


## `gear` lists the slots (head, chest...) the wearer has gear in; parts named
## for other slots under "gear_parts" in models.json are hidden. Null leaves
## the model as authored.
func setup(model_id: String, weapon_id: String, body_scale: float, gear: Variant = null) -> void:
	var entry: Variant = GameData.models["characters"][model_id]
	var spec: Dictionary = entry if entry is Dictionary else {"path": entry}
	var own_rig := str(spec.get("rig", "")) == "own"
	var model: Node3D = (load(spec["path"]) as PackedScene).instantiate()
	model.rotation.y = PI  # glTF faces +Z; Godot's forward is -Z
	add_child(model)
	scale = Vector3.ONE * float(spec.get("scale", 1.0 if own_rig else KAYKIT_SCALE)) * body_scale
	skeleton = model.find_child("Skeleton3D", true, false) as Skeleton3D
	_customize(model, spec)
	if gear is Array:
		var parts: Dictionary = spec.get("gear_parts", {})
		for slot: String in parts:
			if not slot in gear:
				for part: String in parts[slot]:
					var n := model.find_child(part, true, false)
					if n != null:
						n.queue_free()
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	if own_rig:
		anim = model.find_children("*", "AnimationPlayer", true, false)[0] as AnimationPlayer
		for clip in anim.get_animation_list():
			_clips[clip] = clip
			if clip in LOOPING:
				anim.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	else:
		anim = AnimationPlayer.new()
		model.add_child(anim)
		anim.root_node = NodePath("..")
		anim.add_animation_library("", library())
		_clips = KAYKIT_ANIMS
	set_weapon(weapon_id)


## Reskins a stock body from its models.json entry: "hide" drops mesh parts,
## "tint" multiplies a part's texture by a color (skin becomes fur, gear gets
## grimier), and "attach" pins extra scenes to bones.
## Attachments are authored in the model's mesh space, so each is offset by its
## bone's inverse rest pose to land where it was modeled.
func _customize(model: Node3D, spec: Dictionary) -> void:
	for part: String in spec.get("hide", []):
		var n := model.find_child(part, true, false)
		if n != null:
			n.queue_free()
	var tint: Dictionary = spec.get("tint", {})
	for part: String in tint:
		var mi := model.find_child(part, true, false) as MeshInstance3D
		var base := mi.get_active_material(0) as BaseMaterial3D if mi != null else null
		if base != null:
			var mat := base.duplicate() as BaseMaterial3D
			mat.albedo_color = Color.html(tint[part])
			mi.material_override = mat
	for a: Dictionary in spec.get("attach", []):
		var bone := skeleton.find_bone(a["bone"]) if skeleton != null else -1
		if bone < 0:
			continue
		var slot := BoneAttachment3D.new()
		slot.bone_name = a["bone"]
		skeleton.add_child(slot)
		var part: Node3D = (load(a["path"]) as PackedScene).instantiate()
		part.transform = skeleton.get_bone_global_rest(bone).affine_inverse()
		slot.add_child(part)


func set_weapon(weapon_id: String) -> void:
	if weapon_id == _weapon_id or skeleton == null:
		return
	_weapon_id = weapon_id
	if _weapon_slot != null:
		_weapon_slot.queue_free()
		_weapon_slot = null
	if weapon_id == "" or not GameData.models["weapons"].has(weapon_id):
		return
	if skeleton.find_bone("handslot.r") < 0:
		return
	_weapon_slot = BoneAttachment3D.new()
	_weapon_slot.bone_name = "handslot.r"
	skeleton.add_child(_weapon_slot)
	_weapon_slot.add_child((load(GameData.models["weapons"][weapon_id]) as PackedScene).instantiate())
	Entity.use_entity_layer(_weapon_slot)


## Clip for an action, or a raw clip name (e.g. "Spawn_Ground"); "" if the rig lacks it.
func _clip(action: String) -> String:
	var c: String = _clips.get(action, action)
	return c if anim.has_animation(c) else ""


## Plays a non-looping action over the idle (attack swing, flinch, spawn).
func play_once(action: String, speed := 1.0, interrupt := true) -> void:
	var c := _clip(action)
	if _posed_dead or c == "":
		return
	if not interrupt and _one_shot_left > 0.0:
		return
	anim.play(c, BLEND * 0.5, speed)
	_one_shot_left = anim.get_animation(c).length / speed


## Falls over and stays down (corpses).
func pose_dead(instant := false) -> void:
	_posed_dead = true
	var death := _clip("death")
	if not instant and death != "":
		anim.play(death, 0.1)
	elif _clip("dead") != "":
		anim.play(_clip("dead"))
	elif death != "":
		anim.play(death)
		anim.seek(anim.get_animation(death).length, true)


func _process(delta: float) -> void:
	if _posed_dead:
		return
	var e := get_parent() as Entity
	if e == null:
		return
	_one_shot_left -= delta
	var moving := Vector2(e.velocity.x, e.velocity.z).length()
	if not e.is_on_floor() and absf(e.velocity.y) > 2.0:
		_loop("jump")
	elif moving > 4.2:
		_loop("run")
	elif moving > 0.3:
		_loop("walk")
	elif _one_shot_left > 0.0:
		return
	elif not e.cast.is_empty():
		_loop("cast")
	elif e.sitting and _clip("sit") != "":
		var sit := _clip("sit")
		if anim.assigned_animation != sit or anim.is_playing():
			anim.play(sit, 0.0)  # no blend: pausing mid-blend would freeze the old pose
			anim.seek(SIT_FRAME, true)
			anim.pause()
	else:
		_loop("idle")


## Loops an action, falling back to idle when the rig doesn't have it.
func _loop(action: String) -> void:
	var c := _clip(action)
	if c == "":
		c = _clip("idle")
		if c == "":
			return
	_one_shot_left = 0.0
	if anim.current_animation != c or not anim.is_playing():
		anim.play(c, BLEND)
