class_name Corpse
extends StaticBody3D
## A lootable body. Mob corpses hold rolled loot; player corpses hold
## everything the player was carrying and only their owner may loot them.

var object_id := -1
var display_name := ""
var owner_name := ""  # empty = anyone may loot
var entries: Array = []  # [{item, slot}] — slot is set for gear a player was wearing
var coin := 0
var decay_left := 300.0
var rights: Array = []  # names who may loot it for now (the group that earned the kill); empty = anyone
var rights_until := 0  # msec when anyone may loot it

var look: Dictionary = {}
var _restored := false


func setup(name_: String, look_: Dictionary, contents: Array, coin_amount: int,
		decay_seconds: float, owner := "", restored := false) -> void:
	display_name = "%s's corpse" % name_
	look = look_.duplicate()
	_restored = restored
	entries = contents
	coin = coin_amount
	decay_left = decay_seconds
	owner_name = owner


func _enter_tree() -> void:
	if object_id < 0:
		object_id = World.register(self)
	else:
		World.objects[object_id] = self  # a client mirror, under the server's id


func _exit_tree() -> void:
	World.unregister(object_id)
	object_id = -1


func _ready() -> void:
	collision_layer = Layers.CORPSES
	collision_mask = 0
	var s := float(look.get("scale", 1.0))
	var v := Entity.make_visual(look)
	add_child(v)
	if v is CharacterModel:
		(v as CharacterModel).pose_dead(_restored)
	elif str(look.get("shape", "")) == "beetle":
		v.rotation.z = PI
		v.position.y = 0.9 * s
	else:
		v.rotation.x = -PI / 2.0
		v.position.y = 0.3 * s

	var box := BoxShape3D.new()
	box.size = Vector3(1.2, 0.6, 2.0) * s
	var cs := CollisionShape3D.new()
	cs.shape = box
	cs.position.y = 0.3 * s
	add_child(cs)

	var label := Label3D.new()
	label.text = display_name
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 32
	label.pixel_size = 0.006
	label.outline_size = 8
	label.modulate = Color(0.75, 0.75, 0.75)
	label.position.y = 1.1 * s
	label.visibility_range_end = 40.0
	add_child(label)


func _process(delta: float) -> void:
	if not Net.is_authority():
		return  # the server decides when it rots
	decay_left -= delta
	if decay_left <= 0.0:
		World.remove_corpse(self)


func to_save() -> Dictionary:
	var p := global_position
	return {"owner": owner_name, "look": look, "entries": entries, "coin": coin, "decay_left": decay_left,
			"position": [p.x, p.y, p.z]}
