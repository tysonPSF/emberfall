class_name GroundItem
extends StaticBody3D
## Something dropped on the ground, EverQuest style: whatever was on your
## cursor, lying at your feet for anyone to pick up (a bag keeps its contents).
## Weapons and shields show their own model lying flat; anything else shows
## its icon, facing you and bobbing gently. Rots away after a while, like a
## corpse.

const DECAY_SECONDS := 900.0

var object_id := -1
var entry: Dictionary = {}  # a pack entry: {item, count[, contents]}
var decay_left := DECAY_SECONDS
var _bob: Node3D


func _enter_tree() -> void:
	if object_id < 0:
		object_id = World.register(self)
	else:
		World.objects[object_id] = self  # a client mirror, under the server's id


func _exit_tree() -> void:
	World.unregister(object_id)
	object_id = -1


func label_text() -> String:
	var n := GameData.item_name(str(entry.get("item", "")))
	var count := int(entry.get("count", 1))
	return n if count <= 1 else "%s (%d)" % [n, count]


func _ready() -> void:
	collision_layer = Layers.CORPSES  # clickable like a corpse, never in the way
	collision_mask = 0
	var it := GameData.item(str(entry.get("item", "")))
	var model := str(it.get("model", ""))
	if model != "" and GameData.models["weapons"].has(model):
		var held: Node3D = (load(GameData.models["weapons"][model]) as PackedScene).instantiate()
		held.rotation_degrees = Vector3(90, 0, 0)  # lying flat
		held.position.y = 0.08
		held.scale = Vector3.ONE * 0.75
		add_child(held)
		Entity.use_entity_layer(held)
	else:
		_bob = Node3D.new()
		_bob.position.y = 0.45
		add_child(_bob)
		var sprite := Sprite3D.new()
		sprite.texture = GameData.item_icon(str(entry.get("item", "")))
		sprite.pixel_size = 0.005
		sprite.billboard = BaseMaterial3D.BILLBOARD_FIXED_Y
		sprite.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
		sprite.shaded = false
		_bob.add_child(sprite)
	var box := BoxShape3D.new()
	box.size = Vector3(0.9, 0.9, 0.9)
	var cs := CollisionShape3D.new()
	cs.shape = box
	cs.position.y = 0.45
	add_child(cs)
	var label := Label3D.new()
	label.text = label_text()
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 28
	label.pixel_size = 0.005
	label.outline_size = 8
	label.modulate = GameData.item_color(str(entry.get("item", "")))
	label.position.y = 1.05
	label.visibility_range_end = 20.0
	add_child(label)


func _process(delta: float) -> void:
	if _bob != null:
		_bob.position.y = 0.45 + sin(Time.get_ticks_msec() / 500.0) * 0.05
	if not Net.is_authority():
		return  # the server decides when it's gone
	decay_left -= delta
	if decay_left <= 0.0:
		queue_free()
