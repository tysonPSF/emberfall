class_name Npc
extends Entity
## A townsperson from data/npcs.json: stands at its post, can be hailed, and
## answers keywords. It never fights and can't be attacked; what it says and
## the quests it runs are rules in the World autoload.

const NAME_COLOR := Color(0.55, 0.85, 1.0)

var npc_id := ""
var data: Dictionary = {}
var _face_timer := 0.0
var _post_yaw := 0.0


func setup(id: String) -> void:
	npc_id = id
	data = GameData.npcs[id]
	display_name = data["name"]
	level = int(data.get("level", 10))
	faction = "town"
	max_hp = 1000
	hp = max_hp


func _ready() -> void:
	build_body("humanoid", Color.WHITE, 1.0, str(data.get("model", "")), str(data.get("weapon", "")))
	nameplate.text = display_name
	nameplate.modulate = NAME_COLOR
	_post_yaw = rotation.y


## Turns to face whoever is talking to it for a while, then back to its post.
func greet(who: Entity) -> void:
	face_toward(who.global_position)
	_face_timer = 12.0


func _physics_process(delta: float) -> void:
	apply_gravity(delta)
	velocity.x = 0.0
	velocity.z = 0.0
	move_and_slide()
	if _face_timer > 0.0:
		_face_timer -= delta
		if _face_timer <= 0.0:
			rotation.y = _post_yaw
