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
	"kick": "Kick", "bash": "Shield_Bash", "shoot": "Bow_Shoot",  # so are these
}

static var _library: AnimationLibrary
static var _part_sources: Dictionary = {}  # model path -> an instance to copy body parts from

var anim: AnimationPlayer
var skeleton: Skeleton3D
var _clips: Dictionary = {}  # action -> clip name in `anim`
var _held: Dictionary = {}  # hand bone -> [model id, holder node]
var _tiers: Dictionary = {}  # slot -> quality tier id of what's there, for its finish
var _followers: Array = []  # [holder, position bone, orientation bone, offset on the position bone, offset in the orientation bone's frame]
var _worn: Dictionary = {}  # slot -> [gear id, [nodes added for it], [body regions it covers], how shown]
var _model: Node3D
var _spec: Dictionary = {}
var _one_shot_left := 0.0
var _ranged: Node3D  # a bow shown in the left hand for a shot, the usual held gear hidden meanwhile
var _ranged_left := 0.0
var _posed_dead := false
var _race := ""  # data/races.json id: its skin on the outfit's skin cells, its bolt-ons (ears, beards, tusks)
var _gender := ""  # "male" / "female": a body of the other gender wears models.json "genders" head
var _hair := ""  # models.json "hair_colors" id painted on the head's hair cells, "" for the head's own
var _model_id := ""
static var _race_textures: Dictionary = {}  # "texture path|race" -> the recolored ImageTexture, made once


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
	_model_id = model_id
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


## Dresses the body as a race: its skin on every skin cell of the outfit's
## texture (models.json "skin_cells": {texture path: [[col, row]...]}, the
## same 8x4 palette grid the Blender repaints use), and its bolt-ons
## (models.json "race_parts": {id: {path, bone, skin}}) pinned to their bones,
## tinted to the skin when "skin" is set. Height is the caller's (the body's
## scale). Call it right after setup, before tiers and worn gear.
func set_race(race_id: String) -> void:
	if race_id == _race or not GameData.races.has(race_id):
		return
	_race = race_id
	var race: Dictionary = GameData.races[race_id]
	for mi: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		_skin(mi)
	if skeleton == null:
		return
	var parts: Dictionary = GameData.models.get("race_parts", {})
	for part_id: String in race.get("attach", []):
		var spec: Dictionary = parts.get(part_id, {})
		if spec.get("male_only", false) and _gender == "female":  # beards
			continue
		var bone := skeleton.find_bone(str(spec.get("bone", "head"))) if not spec.is_empty() else -1
		if bone < 0:
			continue
		var slot := BoneAttachment3D.new()
		slot.bone_name = str(spec.get("bone", "head"))
		skeleton.add_child(slot)
		var part: Node3D = (load(spec["path"]) as PackedScene).instantiate()
		part.transform = skeleton.get_bone_global_rest(bone).affine_inverse()
		slot.add_child(part)
		if spec.get("hair", false) and _hair != "":  # a beard in the chosen hair color
			var hair := Color("#" + str(GameData.models["hair_colors"][_hair]["light"]))
			for mi: MeshInstance3D in part.find_children("*", "MeshInstance3D", true, false):
				var base := mi.get_active_material(0) as BaseMaterial3D
				if base != null:
					var mat := base.duplicate() as BaseMaterial3D
					mat.albedo_texture = null
					mat.albedo_color = hair
					mi.material_override = mat
		if spec.get("skin", false) and race.get("skin") is Array:
			var tone := Color("#" + str(race["skin"][0]))
			for mi: MeshInstance3D in part.find_children("*", "MeshInstance3D", true, false):
				var base := mi.get_active_material(0) as BaseMaterial3D
				if base != null:
					var mat := base.duplicate() as BaseMaterial3D
					mat.albedo_color = mat.albedo_color * tone
					mi.material_override = mat


## Dresses the body as a man or a woman. Each body is one or the other as
## KayKit made it (models.json "genders" "bodies", default male); for the
## other, its head (face and hair) is swapped for "heads"[gender]. Call it
## right after setup, before set_hair and set_race (beards are "male_only").
func set_gender(gender: String) -> void:
	if skeleton == null or not gender in ["male", "female"] or gender == _gender:
		return
	_gender = gender
	var genders: Dictionary = GameData.models.get("genders", {})
	if gender == str(genders.get("bodies", {}).get(_model_id, "male")):
		return
	var head: Dictionary = genders.get("heads", {}).get(gender, {})
	if not head.is_empty():
		_swap_head(str(head["model"]), str(head["part"]))


## A chosen hairstyle and color: `style` a models.json "hair_styles" id (one
## of the KayKit heads, any gender; "" keeps the head the body and gender
## give), `color` a "hair_colors" id painted over the head's hair cells
## ("hair_cells", the same palette grid as the skin; "" keeps it) and over
## hair-colored race parts (beards). After set_gender, before set_race.
func set_hair(style: String, color: String) -> void:
	if skeleton == null:
		return
	var styles: Dictionary = GameData.models.get("hair_styles", {})
	if styles.has(style):
		_swap_head(str(styles[style]["model"]), str(styles[style]["part"]))
	_hair = color if GameData.models.get("hair_colors", {}).has(color) else ""
	var ours := _body_parts()
	if ours.has("Head"):
		_skin(ours["Head"])


## Swaps the body's head for another KayKit model's, skinned onto this
## skeleton; it counts as the body's own Head, so headgear covers it and the
## race's skin colors it.
func _swap_head(model_id: String, part: String) -> void:
	var src := _source(model_id).find_child(part, true, false) as MeshInstance3D
	if src == null:
		return
	var ours := _body_parts()
	if ours.has("Head"):
		var old := ours["Head"] as Node
		old.get_parent().remove_child(old)
		old.queue_free()
	var mi := src.duplicate() as MeshInstance3D
	mi.name = "Chosen_Head"
	skeleton.add_child(mi)
	mi.skeleton = NodePath("..")
	mi.skin = _skin_by_name(src)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	Entity.use_entity_layer(mi)


## Repaints one mesh's palette texture: the race's skin on the skin cells and,
## on the head, the chosen hair color on the hair cells. The mesh keeps its
## original texture (meta "palette") so repaints never stack.
func _skin(mi: MeshInstance3D) -> void:
	var base := (mi.material_override if mi.material_override != null else mi.get_active_material(0)) as BaseMaterial3D
	if base == null:
		return
	if not mi.has_meta("palette"):
		if base.albedo_texture == null or base.albedo_texture.resource_path == "":
			return
		mi.set_meta("palette", base.albedo_texture)
	var tex: Texture2D = mi.get_meta("palette")
	var path := tex.resource_path
	var race: Dictionary = GameData.races.get(_race, {})
	var jobs: Array = []  # [[cells, [light, dark]]...]
	var skin_key := ""
	var hair_key := ""
	var skin_cells: Array = GameData.models.get("skin_cells", {}).get(path, [])
	if race.get("skin") is Array and not skin_cells.is_empty():
		jobs.append([skin_cells, race["skin"]])
		skin_key = _race
	var hair_cells: Array = GameData.models.get("hair_cells", {}).get(path, [])
	if _hair != "" and _region_of(str(mi.name)) == "Head" and not hair_cells.is_empty():
		var hc: Dictionary = GameData.models["hair_colors"][_hair]
		jobs.append([hair_cells, [hc["light"], hc["dark"]]])
		hair_key = _hair
	if jobs.is_empty():
		return
	var key := "%s|%s|%s" % [path, skin_key, hair_key]
	if not _race_textures.has(key):
		_race_textures[key] = _recolored(tex, jobs)
	var mat := base.duplicate() as BaseMaterial3D
	mat.albedo_texture = _race_textures[key]
	mi.material_override = mat


## A copy of a palette texture with some cells remapped from their own
## light-to-dark gradient onto new colors: jobs [[cells, [light, dark hex]]...].
static func _recolored(tex: Texture2D, jobs: Array) -> ImageTexture:
	var img := tex.get_image()
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	var cw := img.get_width() / 8
	var ch := img.get_height() / 4
	for job: Array in jobs:
		var light := Color("#" + str(job[1][0]))
		var dark := Color("#" + str(job[1][1]))
		for cell: Array in job[0]:
			var x0 := int(cell[0]) * cw
			var y0 := int(cell[1]) * ch  # rows count from the top, like the image
			var lo := 1.0
			var hi := 0.0
			for y in range(y0, y0 + ch, 4):
				for x in range(x0, x0 + cw, 4):
					var l := img.get_pixel(x, y).get_luminance()
					lo = minf(lo, l)
					hi = maxf(hi, l)
			var span := maxf(hi - lo, 0.0001)
			for y in range(y0, y0 + ch):
				for x in range(x0, x0 + cw):
					var c := img.get_pixel(x, y)
					var t := clampf((c.get_luminance() - lo) / span, 0.0, 1.0)
					var n := dark.lerp(light, t)
					img.set_pixel(x, y, Color(n.r, n.g, n.b, c.a))
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


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
		for node: Node in _worn[slot][1]:
			_finish(node, str(_tiers.get(slot, "")))
	_show_covered()


## Copies a wearable's skinned parts from their KayKit model onto this skeleton.
## A part replacing one of ours takes on our tint (a gnoll's fur-tinted arms
## stay furry in a jerkin's sleeves).
func _swap_parts(look: Dictionary) -> Array:
	var source := _source(str(look["model"]))
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
	for node: Node in added:  # swapped-in parts (bare arms, legs) take the race's skin too
		for mi: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false) + ([node] if node is MeshInstance3D else []):
			_skin(mi)
	return added


## A hidden instance of a models.json character to copy body parts from.
static func _source(model_id: String) -> Node:
	var entry: Variant = GameData.models["characters"][model_id]
	var path: String = entry["path"] if entry is Dictionary else str(entry)
	if not _part_sources.has(path):  # kept under GameData so it lives as long as the game does
		var src_model: Node3D = (load(path) as PackedScene).instantiate()
		# GameData is an autoload under /root, and /root is a Viewport with the
		# default World3D - so these sources DO draw, standing at the origin,
		# unanimated and untargetable. Hide the root (and don't process it);
		# the parts underneath keep visible = true, so the copies we take from
		# them still show.
		src_model.visible = false
		src_model.process_mode = Node.PROCESS_MODE_DISABLED
		GameData.add_child(src_model)
		_part_sources[path] = src_model
	return _part_sources[path]


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


## The quality of what's held and worn ({slot: tier id}); better gear gets a
## subtle finish (loot.json tier "finish"). Refinishes what's already on.
func set_tiers(tiers: Dictionary) -> void:
	if tiers == _tiers:
		return
	_tiers = tiers.duplicate()
	for bone: String in _held:
		_finish(_held[bone][1], str(_tiers.get(HAND_SLOTS.get(bone, ""), "")))
	for slot: String in _worn:
		for node: Node in _worn[slot][1]:
			_finish(node, str(_tiers.get(slot, "")))


const HAND_SLOTS := {"handslot.r": "primary", "handslot.l": "secondary"}


## Gives every mesh under a node its tier's finish, or its own materials back.
## The originals are remembered on each mesh, so finishes never stack up.
func _finish(node: Node, tier_id: String) -> void:
	if node == null or not is_instance_valid(node):
		return
	var f := GameData.tier_finish(tier_id)
	for mi: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false) + ([node] if node is MeshInstance3D else []):
		if not mi.has_meta("own_override"):
			mi.set_meta("own_override", mi.material_override)
		var own: Material = mi.get_meta("own_override")
		if f.is_empty():
			mi.material_override = own
			for i in mi.get_surface_override_material_count():
				mi.set_surface_override_material(i, null)
			continue
		if own != null:
			mi.material_override = _finished(own, f)
			continue
		for i in mi.get_surface_override_material_count():
			var base := mi.mesh.surface_get_material(i) if mi.mesh != null else null
			mi.set_surface_override_material(i, _finished(base, f))


static func _finished(base: Material, f: Dictionary) -> Material:
	var m := base.duplicate() as BaseMaterial3D if base is BaseMaterial3D else StandardMaterial3D.new()
	if f.has("tint"):
		m.albedo_color *= Color.html(str(f["tint"]))
	if f.has("metallic"):
		m.metallic = float(f["metallic"])
		m.metallic_specular = 0.6
	if f.has("roughness"):
		m.roughness = float(f["roughness"])
	if f.has("rim"):
		m.rim_enabled = true
		m.rim = float(f["rim"])
		m.rim_tint = 0.3
	if f.has("glow"):
		m.emission_enabled = true
		m.emission = Color.html(str(f["glow"]))
		m.emission_energy_multiplier = float(f.get("glow_energy", 0.2))
	return m


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
	_finish(slot, str(_tiers.get(HAND_SLOTS.get(bone, ""), "")))


## For a ranged shot: hides what the hands hold and, for a bow, puts it in the
## left hand, for `seconds` (the length of the shot); then the usual gear returns.
func show_ranged(model_id: String, seconds: float) -> void:
	_end_ranged()
	for h: Array in _held.values():
		if h[1] != null:
			(h[1] as Node3D).visible = false
	if model_id != "" and GameData.models["weapons"].has(model_id) and skeleton != null:
		var grip: Dictionary = GameData.models.get("grips", {}).get(model_id, {})
		var slot := BoneAttachment3D.new()
		slot.bone_name = "handslot.l"
		skeleton.add_child(slot)
		var held: Node3D = (load(GameData.models["weapons"][model_id]) as PackedScene).instantiate()
		var r: Array = grip.get("rot", [0, 0, 0])
		held.rotation_degrees = Vector3(r[0], r[1], r[2])
		slot.add_child(held)
		Entity.use_entity_layer(slot)
		_ranged = slot
	_ranged_left = seconds


func _end_ranged() -> void:
	if _ranged != null and is_instance_valid(_ranged):
		_ranged.queue_free()
	_ranged = null
	_ranged_left = 0.0
	for h: Array in _held.values():
		if h[1] != null and is_instance_valid(h[1]):
			(h[1] as Node3D).visible = true


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
	if c == "" and action in ["kick", "bash"]:
		c = _clip("attack")  # a rig without the move swings instead
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
	if _ranged_left > 0.0:
		_ranged_left -= delta
		if _ranged_left <= 0.0:
			_end_ranged()
	var moving := Vector2(e.velocity.x, e.velocity.z).length()
	if not e.is_on_floor() and absf(e.velocity.y) > 2.0:
		_loop("jump")
	elif moving > 4.2:
		_loop("run")
	elif moving > 0.3:
		_loop("walk")
	elif _one_shot_left > 0.0:
		return
	elif e.feigning and _clip("dead") != "":  # Feign Death: down as if slain
		if anim.current_animation != _clip("dead") and anim.current_animation != _clip("death"):
			anim.play(_clip("death"), BLEND)
			anim.queue(_clip("dead"))
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
