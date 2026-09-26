class_name Pet
extends Entity
## A Magician's elemental or a Necromancer's skeleton, EverQuest style. It
## belongs to one player (`owner_id`) and fights for them: it follows at heel,
## attacks what you tell it to (or what you're fighting, or what hits you or
## it), backs off when told, guards a spot, sits to heal, and taunts if its
## taunt is on. Its stats come from data/pets.json at the summoner's level;
## the rules that move it live here, the ones that change state in World.

enum Mode { FOLLOW, GUARD, SIT }

const FOLLOW_DISTANCE := 3.0
const WARP_DISTANCE := 70.0  # left this far behind (a fall, a run): it catches up at once
const TAUNT_EVERY := 6.0

var owner_id := -1
var kind := ""  # pets.json kind: "earth", "skeleton"...
var spell_id := ""  # the summoning spell, for re-summoning after a zone or a login
var mode := Mode.FOLLOW
var taunting := false
var guard_spot := Vector3.ZERO
var speed := 5.5
var proc: Dictionary = {}
var model_id := ""
var weapon_id := ""
var body_scale := 1.0
var _backoff := 0.0  # seconds after Back Off during which it won't pick a fight on its own
var _taunt_timer := 0.0
var _think := 0.0
var _base := {}  # stats as summoned, before buffs (Burnout, Elemental Bond)


## Server: rolls the pet for its owner from the summoning spell's pets.json kind.
func setup(owner: Player, from_spell: String) -> void:
	owner_id = owner.entity_id
	spell_id = from_spell
	kind = str(GameData.spells[from_spell]["pet"])
	var k: Dictionary = GameData.pets["kinds"][kind]
	var base: Dictionary = GameData.pets["base"]
	level = owner.level
	var tier := tier_for(level)
	display_name = random_name()
	faction = owner.faction
	max_hp = roundi((float(base["hp"]) + float(base["hp_per_level"]) * level) * float(k.get("hp", 1.0)))
	hp = max_hp
	dmg_min = maxi(1, roundi((float(base["dmg_min"]) + float(base["dmg_min_per_level"]) * level) * float(k.get("dmg", 1.0))))
	dmg_max = maxi(dmg_min + 1, roundi((float(base["dmg_max"]) + float(base["dmg_max_per_level"]) * level) * float(k.get("dmg", 1.0))))
	ac = roundi((float(base["ac"]) + float(base["ac_per_level"]) * level) * float(k.get("ac", 1.0)))
	attack_delay = float(k.get("delay", 3.0))
	attack_verb = k.get("verb", ["hit", "hits"])
	hp_regen = 1 + level / 5
	speed = float(k.get("speed", 5.5))
	taunting = bool(k.get("taunt", false))
	proc = k.get("proc", {})
	model_id = str((k["models"] as Array)[mini(tier, (k["models"] as Array).size() - 1)])
	weapon_id = str(k.get("weapon", ""))
	body_scale = float((k.get("scales", [1.0]) as Array)[mini(tier, (k.get("scales", [1.0]) as Array).size() - 1)])
	look = {"model": model_id, "weapon": weapon_id, "scale": body_scale}
	_base = {"max_hp": max_hp, "ac": ac, "dmg_min": dmg_min, "dmg_max": dmg_max, "attack_delay": attack_delay, "hp_regen": hp_regen}


## A pet's buffs (its owner's Burnout, Elemental Bond, Dark Empowerment) on
## top of what it was summoned with.
func recalc_stats() -> void:
	if _base.is_empty():
		return
	max_hp = int(_base["max_hp"]) + buff_total("hp")
	hp = mini(hp, max_hp)
	ac = int(_base["ac"]) + buff_total("ac")
	dmg_min = int(_base["dmg_min"]) + buff_total("dmg")
	dmg_max = int(_base["dmg_max"]) + buff_total("dmg")
	attack_delay = float(_base["attack_delay"]) / (1.0 + buff_total("haste") / 100.0)
	hp_regen = int(_base["hp_regen"]) + buff_total("hp_regen")
	stats_changed.emit()


## Client: a mirror of the server's pet, drawn as described.
func setup_remote(info: Dictionary) -> void:
	entity_id = int(info["id"])
	owner_id = int(info.get("owner", -1))
	display_name = str(info["name"])
	level = int(info["level"])
	max_hp = int(info["max_hp"])
	hp = int(info["hp"])
	look = info["look"]
	model_id = str(look.get("model", ""))
	weapon_id = str(look.get("weapon", ""))
	body_scale = float(look.get("scale", 1.0))
	faction = "players"


static func tier_for(lvl: int) -> int:
	var tier := 0
	for i in (GameData.pets["tiers"] as Array).size():
		if lvl >= int(GameData.pets["tiers"][i]):
			tier = i
	return tier


## EverQuest's pet names: a few syllables, never the same twice in a row.
static func random_name() -> String:
	var a: Array = ["Ga", "Bo", "Ja", "Ka", "Le", "Xa", "Zo", "Ne", "Ob", "Ra", "Vo", "Ti", "Se", "Ku", "Mar", "Jo"]
	var b: Array = ["ba", "be", "ka", "na", "ti", "sa", "zo", "re", "ne", "ab", "ob", "ek", "an", "ar", "el", "on"]
	var c: Array = ["n", "r", "k", "b", "ab", "er", "ek", "ob", "tik", "ner", "sar", "zor", "rn", "l", ""]
	return str(a.pick_random()) + str(b.pick_random()) + str(c.pick_random())


func owner_player() -> Player:
	return World.get_object(owner_id) as Player


func _ready() -> void:
	build_body("humanoid", Color(0.6, 0.7, 0.9), body_scale, model_id, weapon_id)
	var owner := owner_player()
	nameplate.text = display_name
	nameplate.modulate = Color(0.75, 0.95, 0.75)
	var title := Label3D.new()
	title.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	title.fixed_size = true
	title.pixel_size = nameplate.pixel_size
	title.font_size = 22
	title.outline_size = 6
	title.text = "<%s's pet>" % owner.display_name if owner != null else "<pet>"
	title.modulate = Color(0.75, 0.9, 0.75)
	title.offset = Vector2(0, -30)
	title.visibility_range_end = nameplate.visibility_range_end
	nameplate.add_child(title)


## Hit by something: it fights back, unless told to back off a moment ago.
func add_hate(src: Entity, _amount: float) -> void:
	if dead or src == null or src.dead or src == owner_player():
		return
	if valid_target_entity() == null and _backoff <= 0.0 and mode != Mode.SIT:
		attack(src)


func attack(who: Entity) -> void:
	if who == null or not World.can_attack(self, who):
		return
	target = who
	auto_attack = true
	sitting = false
	if mode == Mode.SIT:
		mode = Mode.FOLLOW


func back_off() -> void:
	target = null
	auto_attack = false
	_backoff = 4.0


func _physics_process(delta: float) -> void:
	if not Net.is_authority():
		puppet(delta)
		return
	apply_gravity(delta)
	if dead:
		return
	_backoff = maxf(0.0, _backoff - delta)
	var owner := owner_player()
	if owner == null or World.zone_of(owner) != World.zone_of(self):
		return  # World moves or dismisses it
	_think -= delta
	if _think <= 0.0:
		_think = 0.4
		_pick_fight(owner)
	var move := Vector3.ZERO
	var t := valid_target_entity()
	if auto_attack and t != null and World.can_attack(self, t):
		face_toward(t.global_position)
		if distance_to(t) > World.melee_range() * 0.7:
			move = nav_dir(t.global_position, delta)
		if taunting:
			_taunt_timer -= delta
			if _taunt_timer <= 0.0 and t is Mob:
				_taunt_timer = TAUNT_EVERY
				World.pet_taunt(self, t as Mob)
	else:
		if auto_attack:
			auto_attack = false
			target = null
		var goal := guard_spot if mode == Mode.GUARD else owner.global_position
		if mode != Mode.GUARD and global_position.distance_to(owner.global_position) > WARP_DISTANCE:
			global_position = owner.global_position + Vector3(1.5, 0.5, 1.5)
		elif mode != Mode.SIT and _flat(goal) > (FOLLOW_DISTANCE if mode == Mode.FOLLOW else 0.8):
			move = nav_dir(goal, delta)
		sitting = mode == Mode.SIT
	if root_left > 0.0 or stun_left > 0.0:
		move = Vector3.ZERO
	var spd := speed * (0.5 if snare_left > 0.0 else 1.0)
	if move != Vector3.ZERO and not auto_attack:
		face_toward(global_position + move)
	velocity.x = move.x * spd
	velocity.z = move.z * spd
	if move != Vector3.ZERO or not is_on_floor():
		move_and_slide()


## EQ pets join in: whatever their owner is swinging at, and whatever is
## hitting their owner. Not while backing off, sitting, or already busy.
func _pick_fight(owner: Player) -> void:
	if _backoff > 0.0 or mode == Mode.SIT or valid_target_entity() != null:
		return
	var ot := owner.valid_target_entity()
	if owner.auto_attack and ot != null and World.can_attack(self, ot):
		attack(ot)
		return
	for m in World.get_mobs():
		if not m.dead and m.hate.has(owner.entity_id) and m.distance_to(self) < 40.0:
			attack(m)
			return


func _flat(pos: Vector3) -> float:
	return Vector2(pos.x - global_position.x, pos.z - global_position.z).length()
