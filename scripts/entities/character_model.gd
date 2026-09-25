class_name CharacterModel
extends Node3D
## A rigged character. Game code asks for actions ("idle", "walk", "attack"...)
## and each rig maps them to its own clips. KayKit Rig_Medium models share one
## animation library and carry weapons on the right-hand slot bone; models with
## `"rig": "own"` in models.json (our Blender creatures) bring their own clips,
## named after the actions directly.

const KAYKIT_SCALE := 0.75
const BLEND := 0.18
const LOOPING: Array[String] = ["idle", "walk", "run", "cast", "jump", "sit"]
const KAYKIT_ANIMS := {
	"idle": "Idle_A", "walk": "Walking_A", "run": "Running_A", "jump": "Jump_Idle",
	"attack": "Throw", "hit": "Hit_A", "death": "Death_A", "dead": "Death_A_Pose",
	"sit": "Sit_Floor_Idle", "sit_down": "Sit_Floor_Down", "cast": "Use_Item",  # the sits are ours (tools/blender/anims.py)
}

static var _library: AnimationLibrary
static var _part_sources: Dictionary = {}  # model path -> an instance to copy body parts from

var anim: AnimationPlayer
var skeleton: Skeleton3D
var _clips: Dictionary = {}  # action -> clip name in `anim`
var _held: Dictionary = {}  # hand bone -> [model id, holder node]
var _followers: Array = []  # [holder, position bone, orientation bone, offset on the position bone, offset in the orientation bone's frame]
var _worn: Dictionary = {}  # slot -> [gear id, [nodes added for it], [body regions it covers], how shown]
var _model: Node3D
var _spec: Dictionary = {}
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
	_model = model
	_spec = spec
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


## Gear a character is wearing, {slot: gear id}. The body's own headgear
## ("headgear_parts") comes off the first time this is called, so a player
## shows exactly what they wear: bare-headed, or the cap.
## A wearable in models.json "body_parts" swaps in another KayKit model's
## skinned parts (the knight's legs, the rogue's jerkin), hiding the body's own
## parts in the regions it covers, the way EverQuest reskinned armor. Models
## limit that to their "part_swaps" slots (a skeleton would grow flesh hands);
## otherwise, and for wearables with no body parts, the rigid pieces from
## gear.py ("gear") are pinned to bones instead.
func set_worn(worn: Dictionary) -> void:
	if skeleton == null:
		return
	for part: String in _spec.get("headgear_parts", []):
		var n := _model.find_child(part, true, false)
		if n != null:
			n.queue_free()
	var swaps: Array = _spec.get("part_swaps", ["head", "chest", "arms", "hands", "legs", "feet", "waist"])
	var looks: Dictionary = GameData.models.get("body_parts", {})
	var how := {}  # slot -> "parts", "pieces" or "" (hidden under another slot's parts)
	for slot: String in worn:
		how[slot] = "parts" if looks.has(str(worn[slot])) and slot in swaps else "pieces"
	# KayKit arms end in hands and legs in feet: sleeves and pants show, and
	# gloves and boots only take over those parts when nothing covers them
	for pair: Array in [["hands", "arms"], ["feet", "legs"]]:
		if how.get(pair[0], "") == "parts" and how.get(pair[1], "") == "parts":
			how[pair[0]] = ""
	for slot: String in _worn.keys():
		if str(worn.get(slot, "")) != _worn[slot][0] or how.get(slot, "") != _worn[slot][3]:
			for node: Node in _worn[slot][1]:
				node.queue_free()
			_worn.erase(slot)
	for slot: String in worn:
		var gear_id := str(worn[slot])
		if _worn.has(slot):
			continue
		match how[slot]:
			"parts":
				_worn[slot] = [gear_id, _swap_parts(looks[gear_id]), looks[gear_id].get("covers", []), "parts"]
			"pieces":
				_worn[slot] = [gear_id, _pin_pieces(gear_id), [], "pieces"]
			_:
				_worn[slot] = [gear_id, [], [], ""]
	_show_covered()


## Copies a wearable's skinned parts from their KayKit model onto this skeleton.
## A part replacing one of ours takes on our tint (a gnoll's fur-tinted arms
## stay furry in a jerkin's sleeves).
func _swap_parts(look: Dictionary) -> Array:
	var entry: Variant = GameData.models["characters"][look["model"]]
	var path: String = entry["path"] if entry is Dictionary else str(entry)
	if not _part_sources.has(path):  # kept under GameData so it lives as long as the game does
		var src_model: Node = (load(path) as PackedScene).instantiate()
		GameData.add_child(src_model)
		# GameData is an autoload under /root, and /root is a Viewport with the
		# default World3D - so these sources DO draw, standing at the origin,
		# unanimated and untargetable. Hide the root; the parts underneath keep
		# visible = true, so the copies we take from them still show.
		(src_model as Node3D).hide()
		_part_sources[path] = src_model
	var source: Node = _part_sources[path]
	var ours := _body_parts()
	var tints: Dictionary = _spec.get("tint", {})
	var added: Array = []
	for part_name: String in look.get("parts", []):
		var src := source.find_child(part_name, true, false) as MeshInstance3D
		if src == null:
			continue
		var mi := src.duplicate() as MeshInstance3D
		mi.name = "Worn_" + part_name
		var node: Node3D = mi
		if src.get_parent() is BoneAttachment3D:  # a rigid part (the Skeletons pack's hats) rides its bone
			node = BoneAttachment3D.new()
			(node as BoneAttachment3D).bone_name = (src.get_parent() as BoneAttachment3D).bone_name
			node.add_child(mi)
			skeleton.add_child(node)
		else:
			skeleton.add_child(mi)
			mi.skeleton = NodePath("..")
			mi.skin = _skin_by_name(src)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		var color := Color.html(str(look["tint"])) if look.has("tint") else Color.WHITE
		var region := _region_of(part_name)
		if ours.has(region) and tints.has(str(ours[region].name)):
			color *= Color.html(tints[str(ours[region].name)])
		if color != Color.WHITE:
			var base := mi.get_active_material(0) as BaseMaterial3D
			if base != null:
				var mat := base.duplicate() as BaseMaterial3D
				mat.albedo_color = color
				mi.material_override = mat
		Entity.use_entity_layer(node)
		added.append(node)
	return added


## A part's skin, bound by bone name: the Skeletons pack numbers the shared
## rig's bones in another order than the Adventurers pack does.
static func _skin_by_name(src: MeshInstance3D) -> Skin:
	var from := src.get_node_or_null(src.skeleton) as Skeleton3D
	if src.skin == null or from == null:
		return src.skin
	var skin := src.skin.duplicate() as Skin
	for i in skin.get_bind_count():
		if skin.get_bind_name(i) == &"":
			skin.set_bind_name(i, from.get_bone_name(skin.get_bind_bone(i)))
	return skin


## Pins a wearable's rigid gear.py pieces to their bones.
func _pin_pieces(gear_id: String) -> Array:
	var spec: Dictionary = GameData.models.get("gear", {}).get(gear_id, {})
	var holders: Array = []
	for p: Dictionary in spec.get("pieces", []):  # a wearable is one or more pieces, each on a bone
		var bone := skeleton.find_bone(str(p.get("bone", "head")))
		if bone < 0:
			continue
		var holder := BoneAttachment3D.new()
		holder.bone_name = str(p.get("bone", "head"))
		skeleton.add_child(holder)
		var piece: Node3D = (load(p["path"]) as PackedScene).instantiate()
		piece.transform = skeleton.get_bone_global_rest(bone).affine_inverse()  # authored in mesh space
		holder.add_child(piece)
		Entity.use_entity_layer(holder)
		for mi in piece.find_children("*", "MeshInstance3D", true, false):
			(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		holders.append(holder)
	return holders


## Hides the body's own parts under swapped-in gear, and shows them again when
## it comes off.
func _show_covered() -> void:
	var covered: Array = []
	for slot: String in _worn:
		covered.append_array(_worn[slot][2])
	var ours := _body_parts()
	for region: String in ours:
		(ours[region] as MeshInstance3D).visible = not region in covered


## This model's own body meshes by region ("Body", "ArmLeft", "Cape"...).
func _body_parts() -> Dictionary:
	var out := {}
	for mi in _model.find_children("*", "MeshInstance3D", true, false):
		if not mi.name.begins_with("Worn_") and mi.get_parent() == skeleton:
			out[_region_of(str(mi.name))] = mi
	return out


static func _region_of(part_name: String) -> String:
	return part_name.get_slice("_", part_name.get_slice_count("_") - 1)


func set_weapon(weapon_id: String) -> void:
	_hold("handslot.r", weapon_id)


## A shield (or other off-hand model) in the left hand.
func set_offhand(model_id: String) -> void:
	_hold("handslot.l", model_id)


## Puts a models.json "weapons" entry in a hand, replacing what was there.
func _hold(bone: String, model_id: String) -> void:
	var cur: Array = _held.get(bone, ["", null])
	if model_id == cur[0] or skeleton == null:
		return
	if cur[1] != null:
		(cur[1] as Node).queue_free()
	_held.erase(bone)
	if model_id == "" or not GameData.models["weapons"].has(model_id) or skeleton.find_bone(bone) < 0:
		return
	var grip: Dictionary = GameData.models.get("grips", {}).get(model_id, {})  # how it sits in the hand, if not as modeled
	var held: Node3D = (load(GameData.models["weapons"][model_id]) as PackedScene).instantiate()
	var r: Array = grip.get("rot", [0, 0, 0])
	var at: Array = grip.get("pos", [0, 0, 0])
	held.rotation_degrees = Vector3(r[0], r[1], r[2])
	var slot: Node3D
	if grip.has("orient"):
		# rides one bone (the forearm) but keeps another's orientation (the chest):
		# a shield moves with the arm yet always hangs upright at your side,
		# whatever twist the walk or swing puts in the wrist
		slot = Node3D.new()
		skeleton.add_child(slot)
		var out: Array = grip.get("out", [0, 0, 0])
		_followers.append([slot, skeleton.find_bone(str(grip.get("bone", bone))), skeleton.find_bone(str(grip["orient"])),
				Vector3(at[0], at[1], at[2]), Vector3(out[0], out[1], out[2])])
		if not skeleton.skeleton_updated.is_connected(_follow):
			skeleton.skeleton_updated.connect(_follow)
		_follow()
	else:
		slot = BoneAttachment3D.new()
		(slot as BoneAttachment3D).bone_name = str(grip.get("bone", bone))
		skeleton.add_child(slot)
		held.position = Vector3(at[0], at[1], at[2])
	slot.add_child(held)
	Entity.use_entity_layer(slot)
	_held[bone] = [model_id, slot]


func _follow() -> void:
	_followers = _followers.filter(func(f: Array) -> bool: return is_instance_valid(f[0]) and not (f[0] as Node).is_queued_for_deletion())
	for f: Array in _followers:
		var at := skeleton.get_bone_global_pose(f[1])
		var basis := skeleton.get_bone_global_pose(f[2]).basis.orthonormalized()
		(f[0] as Node3D).transform = Transform3D(basis, at * (f[3] as Vector3) + basis * (f[4] as Vector3))


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
		var down := _clip("sit_down")
		if anim.current_animation != sit and anim.current_animation != down:
			if down != "":
				anim.play(down, BLEND)  # sink to the ground, then settle into the seated loop
				anim.queue(sit)
			else:
				anim.play(sit, BLEND)
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
